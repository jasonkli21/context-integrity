"""Phase 8 repository policy, normalized relation semantics and stable output."""

import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest
from typer.testing import CliRunner

from context_integrity.claims import claims_overview
from context_integrity.cli import app
from context_integrity.configuration import ConfigurationError, parse_config
from context_integrity.evidence import (
    EvidenceCoverage,
    EvidenceProviderDescriptor,
    EvidenceRepositorySnapshot,
)
from context_integrity.integrity import integrity_overview, selector_matches
from context_integrity.inventory import inventory_repository
from context_integrity.models import ArchitectureSelector, RepositoryConfig
from context_integrity.relations import (
    EvidenceEntity,
    EvidencePoint,
    EvidenceRange,
    EvidenceRelation,
    EvidenceRelationBatch,
    EvidenceRelationCoverage,
    EvidenceRelationFileState,
    EvidenceRelationState,
    EvidenceRelationTarget,
)
from context_integrity.rendering import render_integrity_json, render_integrity_text
from context_integrity.repository import discover_repository

CONFIG = """schema_version = 8
[[claims]]
id = "boundary"
claim_type = "architecture_invariant"
subject = "application"
predicate = "must_not_depend_on"
value = "storage"
depends_on = ["docs/architecture.md"]
[[architecture_invariants]]
id = "boundary"
claim_id = "boundary"
rule = "forbid_relation"
relation_kinds = ["imports", "references"]
source_path_prefixes = ["src/application/"]
target_paths = ["src/storage.py"]
target_names = ["Storage"]
"""
DESCRIPTOR = EvidenceProviderDescriptor("fixture", "1", capabilities=("relations",))
SPAN = EvidenceRange(EvidencePoint(0, 0, 0), EvidencePoint(10, 0, 10))


def relation(kind="imports", source="src/application/main.py", target="src/storage.py", name=None):
    return EvidenceRelation(
        kind,
        EvidenceEntity("file", source),
        EvidenceRelationTarget(name=name)
        if name
        else EvidenceRelationTarget(EvidenceEntity("file", target)),
        "unresolved" if name else "exact_same_file_qualified_name",
        source,
        SPAN,
        "python",
        "python_import_syntax" if kind == "imports" else "python_call_syntax",
    )


def setup(tmp_path, config=CONFIG):
    (tmp_path / ".context-integrity.toml").write_text(config)
    context = discover_repository(tmp_path)
    context.repository = replace(context.repository, id="repo_fixture", name="fixture")
    manifest = inventory_repository(context)
    return context, manifest


def batch(manifest, relations=(), incomplete=False):
    files = tuple(
        EvidenceRelationFileState(
            p,
            "analyzed",
            "analyzed",
            unresolved=sum(
                r.source.path == p and r.target.name is not None for r in set(relations)
            ),
        )
        for p in sorted({r.source.path for r in relations} | {"src/application/main.py"})
    )
    coverage = EvidenceRelationCoverage(
        EvidenceCoverage((), incomplete or any(f.incomplete for f in files)), files
    )
    return EvidenceRelationBatch(
        EvidenceRelationState(
            DESCRIPTOR,
            EvidenceRepositorySnapshot(
                manifest.repository.id,
                manifest.repository.git_head,
                manifest.repository.git_dirty,
                command="graph",
            ),
            coverage,
        ),
        tuple(sorted(set(relations), key=lambda r: r.sort_key())),
    )


@pytest.mark.parametrize("version", range(1, 8))
def test_legacy_schema_rejects_phase8(version):
    assert parse_config(f"schema_version = {version}".encode()).schema_version == version
    with pytest.raises(ConfigurationError):
        parse_config(CONFIG.replace("schema_version = 8", f"schema_version = {version}").encode())


def test_config_valid_and_direct_construction():
    config = parse_config(CONFIG.encode())
    assert config.schema_version == 8
    assert config.architecture_invariants[0].source.path_prefixes == ("src/application/",)
    with pytest.raises(ValueError):
        replace(config, schema_version=7)
    with pytest.raises(ValueError):
        replace(config, claims=())
    with pytest.raises(ValueError):
        replace(config, architecture_invariants=config.architecture_invariants * 2)
    with pytest.raises(ValueError):
        RepositoryConfig(schema_version=8, architecture_invariants=({},))


@pytest.mark.parametrize(
    "before,after",
    [
        ('claim_id = "boundary"', 'claim_id = "missing"'),
        ('claim_type = "architecture_invariant"', 'claim_type = "architecture"'),
        ('predicate = "must_not_depend_on"', 'predicate = "uses"'),
        ('rule = "forbid_relation"', 'rule = "allow_relation"'),
        ('relation_kinds = ["imports", "references"]', 'relation_kinds = ["contains"]'),
        ('relation_kinds = ["imports", "references"]', "relation_kinds = []"),
        ('source_path_prefixes = ["src/application/"]', ""),
        ('target_paths = ["src/storage.py"]\ntarget_names = ["Storage"]', ""),
        ('source_path_prefixes = ["src/application/"]', 'source_path_prefixes = ["../src/"]'),
        (
            'source_path_prefixes = ["src/application/"]',
            'source_path_prefixes = ["src/application"]',
        ),
        (
            'source_path_prefixes = ["src/application/"]',
            'source_path_prefixes = ["/src/application/"]',
        ),
        ('source_path_prefixes = ["src/application/"]', 'source_path_prefixes = ["src/*/"]'),
        ('target_paths = ["src/storage.py"]', 'target_paths = ["src/../storage.py"]'),
        ('target_names = ["Storage"]', 'target_names = ["Storage", "Storage"]'),
        ('target_names = ["Storage"]', 'unknown = ["Storage"]'),
    ],
)
def test_config_fail_closed(before, after):
    with pytest.raises(ConfigurationError):
        parse_config(CONFIG.replace(before, after).encode())


def test_duplicate_invariant_config():
    duplicate = CONFIG.split("[[architecture_invariants]]")[1]
    with pytest.raises(ConfigurationError):
        parse_config((CONFIG + "\n[[architecture_invariants]]" + duplicate).encode())


@pytest.mark.parametrize("path", ["../x", "/x", "a/../b", "a//b", "a\\b", "a:b", "a/", "a\n"])
def test_entity_paths(path):
    with pytest.raises(ValueError):
        EvidenceEntity("file", path)


@pytest.mark.parametrize("point", [(True, 0, 0), (-1, 0, 0), (2**64, 0, 0)])
def test_source_points(point):
    with pytest.raises(ValueError):
        EvidencePoint(*point)


def test_range_entity_target_and_batch_validation(tmp_path):
    with pytest.raises(ValueError):
        EvidenceRange(SPAN.end, SPAN.start)
    symbol = EvidenceEntity("symbol", "src/a.py", "App.run", "run", "method", "python", SPAN)
    assert symbol.qualified_name == "App.run"
    with pytest.raises(ValueError):
        EvidenceEntity("symbol", "src/a.py")
    for kwargs in ({}, {"entity": symbol, "name": "App"}, {"name": "/private/SECRET"}):
        with pytest.raises(ValueError):
            EvidenceRelationTarget(**kwargs)
    _, manifest = setup(tmp_path)
    b = batch(manifest, (relation(),))
    with pytest.raises(ValueError):
        replace(b, relations=b.relations * 2)
    with pytest.raises(ValueError):
        replace(b.relations[0], resolution="unresolved")
    with pytest.raises(ValueError):
        replace(
            b.state.coverage,
            files=(EvidenceRelationFileState("a.py", "parse_failed", "not_analyzed"),),
        )
    with pytest.raises(ValueError):
        replace(b.state, observed_content=(("src/application/main.py", "bad-hash"),))


def test_selectors_exact_prefix_symbol_or_and_names():
    file = EvidenceEntity("file", "src/application/main.py")
    symbol = EvidenceEntity("symbol", "src/a.py", "App.run", "run", "method", "python", SPAN)
    assert selector_matches(ArchitectureSelector(paths=(file.path,)), file)
    assert selector_matches(ArchitectureSelector(path_prefixes=("src/application/",)), file)
    assert not selector_matches(
        ArchitectureSelector(path_prefixes=("src/application/",)),
        EvidenceEntity("file", "src/application_old/main.py"),
    )
    assert selector_matches(ArchitectureSelector(symbols=("App.run",)), symbol)
    assert selector_matches(ArchitectureSelector(paths=("other.py",), symbols=("App.run",)), symbol)
    assert selector_matches(ArchitectureSelector(names=("Storage",)), unresolved_name="Storage")
    assert not selector_matches(
        ArchitectureSelector(paths=("src/storage.py",)), unresolved_name="src/storage.py"
    )
    assert not selector_matches(ArchitectureSelector(names=("Storage",)), file)


@pytest.mark.parametrize("kind", ["imports", "references"])
def test_violation_and_no_domain_mutation(tmp_path, kind):
    context, manifest = setup(tmp_path)
    before_manifest = deepcopy(manifest)
    before = claims_overview(manifest)
    result = integrity_overview(
        context, manifest, relation_batch=batch(manifest, (relation(kind),))
    )
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.severity == "high"
    assert finding.claim_id == finding.invariant_id == "boundary"
    assert result.architecture.invariants[0].status == "violated"
    assert claims_overview(manifest) == before
    assert before.claims[0].validity == "unverified"
    assert result.architecture.invariants[0].provenance_complete is False
    assert "claim_provenance_incomplete" in result.architecture.invariants[0].caveats
    assert manifest == before_manifest


@pytest.mark.parametrize(
    "incomplete,status", [(False, "no_violation_observed"), (True, "inconclusive")]
)
def test_absence_language_and_incompleteness(tmp_path, incomplete, status):
    context, manifest = setup(tmp_path)
    result = integrity_overview(
        context,
        manifest,
        relation_batch=batch(manifest, (relation(target="other.py"),), incomplete),
    )
    assert not result.findings
    assert result.architecture.invariants[0].status == status
    rendered = render_integrity_json(result) + render_integrity_text(result)
    assert status in rendered
    assert all(word not in rendered for word in ('"compliant"', '"satisfied"', '"pass"'))


def test_grouping_distinct_edges_and_stability(tmp_path):
    context, manifest = setup(tmp_path)
    first = relation()
    duplicate = replace(
        first, range=EvidenceRange(EvidencePoint(20, 1, 0), EvidencePoint(30, 1, 10))
    )
    other = relation(source="src/application/other.py")
    observed = batch(manifest, (first, duplicate, other), True)
    result = integrity_overview(context, manifest, relation_batch=observed)
    assert len(result.findings) == 2
    assert sorted(len(f.relations) for f in result.findings) == [1, 2]
    assert result.architecture.invariants[0].status == "violated"
    shuffled = batch(manifest, (other, duplicate, first), True)
    assert result == integrity_overview(context, manifest, relation_batch=shuffled)
    assert result.findings[0].id.startswith("finding_")


@pytest.mark.parametrize(
    "name,expected", [("Storage", "violated"), ("src/storage.py", "inconclusive")]
)
def test_unresolved_only_explicit_names(tmp_path, name, expected):
    # Relative path-shaped names remain names, with no path-selector conversion.
    context, manifest = setup(tmp_path)
    result = integrity_overview(
        context, manifest, relation_batch=batch(manifest, (relation(name=name),))
    )
    assert result.architecture.invariants[0].status == expected


def test_relation_kind_and_source_filtering(tmp_path):
    context, manifest = setup(tmp_path, CONFIG.replace('["imports", "references"]', '["imports"]'))
    result = integrity_overview(
        context,
        manifest,
        relation_batch=batch(
            manifest, (relation("references"), relation(source="src/application_old/a.py"))
        ),
    )
    assert not result.findings


def test_no_provider_visible_and_existing_checks(tmp_path):
    context, manifest = setup(tmp_path)
    (tmp_path / "AGENTS.md").write_text("Canonical")
    (tmp_path / "CLAUDE.md").write_text("No reference")
    manifest = inventory_repository(context)
    result = integrity_overview(context, manifest)
    assert result.architecture.invariants[0].status == "not_evaluated"
    assert "instruction_reference_missing" in {f.code for f in result.findings}
    assert "architecture_not_evaluated" in {w.code for w in result.warnings}
    response = CliRunner().invoke(app, ["check", str(tmp_path), "--format", "json"])
    assert response.exit_code == 0, response.output
    assert json.loads(response.output)["architecture"]["invariants"][0]["status"] == "not_evaluated"


def test_rendering_golden_and_portability(tmp_path):
    context, manifest = setup(tmp_path)
    result = integrity_overview(
        context, manifest, relation_batch=batch(manifest, (relation(),), True)
    )
    rendered = render_integrity_json(result)
    assert str(tmp_path) not in rendered
    assert "provider_numeric_id" not in rendered
    assert "source body" not in rendered
    golden = Path(__file__).parent / "fixtures/integrity-architecture-v2.json"
    assert rendered == golden.read_text()


def test_symbol_identity_preserves_distinct_definitions_and_prose_independence(tmp_path):
    context, manifest = setup(tmp_path)
    symbol = EvidenceEntity(
        "symbol", "src/application/main.py", "App.run", "run", "method", "python", SPAN
    )
    first = replace(relation(), source=symbol)
    # Same qualified name at a distinct definition range is a distinct entity.
    other_span = EvidenceRange(EvidencePoint(30, 2, 0), EvidencePoint(40, 2, 10))
    second = replace(first, source=replace(symbol, range=other_span), range=other_span)
    result = integrity_overview(context, manifest, relation_batch=batch(manifest, (first, second)))
    assert len(result.findings) == 2
    ids = {f.id for f in result.findings}
    _, updated_manifest = setup(
        tmp_path, CONFIG.replace('value = "storage"', 'value = "storage intent changed"')
    )
    updated = integrity_overview(
        context, updated_manifest, relation_batch=batch(updated_manifest, (second, first))
    )
    assert {f.id for f in updated.findings} == ids
    assert replace(result.findings[0], message="New wording").id in ids


def test_linked_policy_exposed_with_complete_claim_provenance(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/architecture.md").write_text("Policy intent")
    context, manifest = setup(tmp_path)
    result = integrity_overview(context, manifest, relation_batch=batch(manifest, (relation(),)))
    invariant = json.loads(render_integrity_json(result))["architecture"]["invariants"][0]
    assert invariant["provenance_complete"]
    assert invariant["policy"]["rule"] == "forbid_relation"
    assert invariant["policy"]["source"]["path_prefixes"] == ["src/application/"]
    assert invariant["claim_provenance"]["dependencies"][0]["revision"]["content_sha256"]


def test_generic_provider_snapshot_mismatch(tmp_path):
    from context_integrity.evidence import EvidenceProviderError

    context, manifest = setup(tmp_path)
    observed = batch(manifest)
    mismatched = replace(
        observed,
        state=replace(
            observed.state, snapshot=replace(observed.state.snapshot, repository_id="wrong")
        ),
    )
    with pytest.raises(EvidenceProviderError, match="snapshot_mismatch"):
        integrity_overview(context, manifest, relation_batch=mismatched)
