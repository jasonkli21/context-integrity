"""Generic provider boundary and mixed compiler acceptance tests."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from context_integrity.compiler import compile_context
from context_integrity.configuration import ConfigurationError, parse_config
from context_integrity.contracts import validate_contract, validate_contract_sources
from context_integrity.evidence import (
    EvidenceContextBatch,
    EvidenceContextRequest,
    EvidenceCoverage,
    EvidenceProviderDescriptor,
    EvidenceProviderError,
    EvidenceProviderState,
    EvidenceRepositorySnapshot,
)
from context_integrity.inventory import scan_repository
from context_integrity.models import (
    AuthorityClass,
    CandidateOrigin,
    CandidateRelevance,
    ClassificationConfidence,
    ClassificationResult,
    CompilerCandidate,
    ContextContract,
    ContextContractRule,
    ContextRuleMode,
    GitFileStatus,
    LifecycleState,
    RepositoryConfig,
    ScanWarning,
    SourceKind,
    SourceRecord,
    SourceRevision,
    make_source_id,
)
from context_integrity.rendering import render_compiled_context_json
from test_context_engine import BODY, normalize, response, selected_file


def setup_mixed(root, rules=None, files=None, budget=None):
    (root / "AGENTS.md").write_text("doc")
    manifest = scan_repository(root)
    rules = rules or (
        ContextContractRule("docs", ContextRuleMode.REQUIRED, paths=("AGENTS.md",)),
        ContextContractRule(
            "code", ContextRuleMode.REQUIRED, kinds=(SourceKind.SOURCE_CODE,), max_count=1
        ),
        ContextContractRule(
            "tests", ContextRuleMode.OPTIONAL, kinds=(SourceKind.TEST,), max_count=1
        ),
    )
    contract = ContextContract("work", "implementation", "Mixed", rules, "a" * 64, budget)
    config = RepositoryConfig(
        content_sha256="a" * 64, schema_version=7, context_contracts=(contract,)
    )
    manifest = replace(manifest, repository_config=config)
    request = EvidenceContextRequest(root, manifest.repository, "sample", 4096)
    batch = normalize(response(request, files), request)
    return manifest, contract, batch


def compile_mixed(manifest, contract, batch, **kwargs):
    return compile_context(manifest, contract, task="sample", evidence=batch, **kwargs)


def paths(result):
    return tuple(s.path for s in result.selected_sources)


def test_mixed_validation_budget_privacy_and_golden(tmp_path):
    manifest, contract, batch = setup_mixed(
        tmp_path, files=[selected_file(), selected_file("tests/spec.py", 2, "test")]
    )
    result = compile_mixed(manifest, contract, batch)
    assert paths(result) == ("AGENTS.md", "src/sample.py", "tests/spec.py")
    assert result.status == "complete" and result.validation.package.unresolved_paths == ()
    assert result.budget.used_bytes == 3 + 2 * len(BODY.encode())
    assert len(result.dependencies) == 3 and len(manifest.sources) == 1
    standalone = validate_contract(manifest, contract, paths(result))
    assert standalone.package.unresolved_paths == ("src/sample.py", "tests/spec.py")
    assert standalone.findings
    rendered = render_compiled_context_json(result)
    assert BODY not in rendered and str(tmp_path) not in rendered and '"file_id"' not in rendered
    assert rendered == render_compiled_context_json(
        compile_mixed(manifest, contract, replace(batch, candidates=batch.candidates[::-1]))
    )
    data = provider_projection(result)
    assert set(data["providers"][0]) == {
        "descriptor",
        "snapshot",
        "task",
        "ranker_version",
        "acquisition_budget_bytes",
        "coverage",
        "change",
        "fallback_mode",
        "warnings",
    }
    assert set(data["providers"][0]["descriptor"]) == {
        "id",
        "version",
        "contract_version",
        "capabilities",
        "derivation",
    }
    assert set(next(d for d in data["decisions"] if d["relevance"])["relevance"]) == {
        "rank",
        "score",
        "score_components",
        "reasons",
        "matched_entities",
        "matched_entities_omitted",
        "graph_distance",
        "change_distance",
    }
    golden = Path(__file__).parent / "fixtures/compiled-context-provider-v3.json"
    assert json.dumps(data, indent=2, sort_keys=True) + "\n" == golden.read_text()


def provider_projection(result):
    # Root identity of non-Git repositories is runtime-scoped: replace only that
    # hash for the portable golden, not any provider provenance or policy fields.
    data = json.loads(render_compiled_context_json(result))
    data["repository"]["id"] = "fixture-repository"
    data["repository"]["name"] = "fixture"
    for source in data["selected_sources"]:
        source["id"] = "fixture:" + source["path"]
    for decision in data["decisions"]:
        decision["source_id"] = "fixture:" + decision["path"]
    for dep in data["dependencies"]:
        dep["source_id"] = "fixture:" + dep["path"]
    for source in data["validation"]["package"]["sources"]:
        source["source_id"] = "fixture:" + source["path"]
    data["validation"]["repository"] = data["repository"]
    data["providers"][0]["snapshot"]["repository_id"] = "fixture-repository"
    return data


def test_rank_after_policy_and_no_doc_demotion(tmp_path):
    manifest, contract, batch = setup_mixed(
        tmp_path, files=[selected_file("src/a.py", 2), selected_file("src/z.py", 1)]
    )
    assert paths(compile_mixed(manifest, contract, batch)) == ("AGENTS.md", "src/z.py")
    # An unranked document sharing a policy-equivalent rule keeps its lexical slot.
    broad = ContextContractRule(
        "any", ContextRuleMode.REQUIRED, paths=("AGENTS.md", "src/z.py"), max_count=1
    )
    contract = replace(contract, rules=(broad,))
    manifest = replace(
        manifest,
        repository_config=replace(manifest.repository_config, context_contracts=(contract,)),
    )
    assert paths(compile_mixed(manifest, contract, batch)) == ("AGENTS.md",)


def test_exclusions_lifecycle_authority_beat_rank(tmp_path):
    files = [selected_file("src/a.py", 1), selected_file("src/z.py", 2)]
    manifest, contract, batch = setup_mixed(tmp_path, files=files)
    excluded = ContextContractRule("excluded", ContextRuleMode.EXCLUDED, paths=("src/a.py",))
    new = replace(contract, rules=(*contract.rules, excluded))
    updated = replace(
        manifest, repository_config=replace(manifest.repository_config, context_contracts=(new,))
    )
    assert "src/a.py" not in paths(compile_mixed(updated, new, batch))
    # Real provider candidates have executable_truth/unknown metadata.  A rule
    # limited to active lifecycle cannot select them, regardless of rank.
    rules = tuple(
        replace(r, lifecycles=(LifecycleState.ACTIVE,)) if r.id == "code" else r
        for r in contract.rules
    )
    new = replace(contract, rules=rules)
    updated = replace(
        manifest, repository_config=replace(manifest.repository_config, context_contracts=(new,))
    )
    assert paths(compile_mixed(updated, new, batch)) == ("AGENTS.md",)

    # A question-specific authority policy for architectural intent does not
    # admit provider code's executable_truth class.
    rules = tuple(
        replace(r, authority_policy="architectural_intent") if r.id == "code" else r
        for r in contract.rules
    )
    new = replace(contract, rules=rules)
    updated = replace(
        manifest, repository_config=replace(manifest.repository_config, context_contracts=(new,))
    )
    assert paths(compile_mixed(updated, new, batch)) == ("AGENTS.md",)


def test_optional_rank_and_exact_budget(tmp_path):
    manifest, contract, batch = setup_mixed(
        tmp_path,
        files=[
            selected_file(),
            selected_file("tests/a.py", 3, "test"),
            selected_file("tests/z.py", 2, "test"),
        ],
    )
    required_cost = 3 + len(BODY.encode())
    assert paths(compile_mixed(manifest, contract, batch, budget_bytes=required_cost)) == (
        "AGENTS.md",
        "src/sample.py",
    )
    assert paths(
        compile_mixed(manifest, contract, batch, budget_bytes=required_cost + len(BODY.encode()))
    ) == ("AGENTS.md", "src/sample.py", "tests/z.py")
    assert (
        compile_mixed(manifest, contract, batch, budget_bytes=required_cost - 1).status
        == "incomplete"
    )


def test_provider_feasibility_repair(tmp_path):
    rules = (
        ContextContractRule("one", ContextRuleMode.REQUIRED, paths=("src/a.py", "src/b.py")),
        ContextContractRule("two", ContextRuleMode.REQUIRED, paths=("src/a.py", "src/c.py")),
    )
    # Rank prefers a.py, but only b+c fits the budget. Exact repair finds it.
    files = [
        selected_file("src/a.py", 1, body="x" * 20),
        selected_file("src/b.py", 2, body="x" * 12),
        selected_file("src/c.py", 3, body="x" * 12),
    ]
    # Make a fit initially but prevent it from covering both rules using max on
    # a+c: greedy chooses a, then cannot complete; repair selects b+c.
    rules = (
        replace(rules[0], paths=("src/a.py", "src/b.py")),
        replace(rules[1], paths=("src/c.py",)),
        ContextContractRule(
            "max", ContextRuleMode.OPTIONAL, paths=("src/a.py", "src/c.py"), max_count=1
        ),
    )
    manifest, contract, batch = setup_mixed(tmp_path, rules, files, budget=24)
    assert paths(compile_mixed(manifest, contract, batch)) == ("src/b.py", "src/c.py")


def test_provider_incomplete_contract_complete(tmp_path):
    manifest, contract, batch = setup_mixed(tmp_path)
    coverage = replace(batch.state.coverage, incomplete=True)
    warnings = (
        ScanWarning(
            "provider_incomplete",
            None,
            "Provider analysis or candidate acquisition is incomplete; see provider coverage.",
        ),
    )
    batch = replace(batch, state=replace(batch.state, coverage=coverage, warnings=warnings))
    result = compile_mixed(manifest, contract, batch)
    assert result.status == "complete" and result.providers[0].coverage.incomplete


def test_duplicate_collision_unbound_and_snapshot(tmp_path):
    manifest, contract, batch = setup_mixed(tmp_path, files=[selected_file("AGENTS.md")])
    with pytest.raises(EvidenceProviderError, match="inventory_collision"):
        compile_mixed(manifest, contract, batch)
    with pytest.raises(EvidenceProviderError, match="duplicate_path"):
        replace(batch, candidates=batch.candidates * 2)
    with pytest.raises(ValueError, match="not bound"):
        validate_contract_sources(manifest, replace(contract, description="different"), (), ())
    batch = replace(
        batch,
        state=replace(batch.state, snapshot=replace(batch.state.snapshot, repository_id="other")),
        candidates=(),
    )
    with pytest.raises(EvidenceProviderError, match="snapshot_mismatch"):
        compile_mixed(manifest, contract, batch)


@pytest.mark.parametrize("kind", ["source_code", "test", "schema", "migration"])
@pytest.mark.parametrize("version", [5, 6, 7])
def test_config_provider_kind_gates(kind, version):
    text = f'''schema_version = {version}
[[context_contracts]]
id = "work"
task_class = "implementation"
description = "Provider kind"
[[context_contracts.rules]]
id = "code"
mode = "required"
kinds = ["{kind}"]
'''.encode()
    if version < 7:
        with pytest.raises(ConfigurationError):
            parse_config(text)
    else:
        assert parse_config(text).context_contracts[0].rules[0].kinds == (kind,)


@pytest.mark.parametrize(
    "changes",
    [
        {"version": "private/version"},
        {"contract_version": 2},
        {"capabilities": ()},
        {"capabilities": ("context_candidates", "future")},
    ],
)
def test_descriptor_invariants(changes):
    with pytest.raises(ValueError):
        EvidenceProviderDescriptor(**({"id": "generic", "version": "1"} | changes))


@pytest.mark.parametrize(
    "changes",
    [
        {"task": " "},
        {"task": None},
        {"acquisition_budget_bytes": True},
        {"acquisition_budget_bytes": 16777217},
    ],
)
def test_request_invariants(tmp_path, changes):
    with pytest.raises(ValueError):
        EvidenceContextRequest(
            **(
                {
                    "repository_root": tmp_path,
                    "repository": scan_repository(tmp_path).repository,
                    "task": "sample",
                }
                | changes
            )
        )


def test_coverage_snapshot_invariants():
    with pytest.raises(ValueError):
        EvidenceCoverage((("bad", -1),), True)
    with pytest.raises(ValueError):
        EvidenceRepositorySnapshot("repo", "bad", False)


def test_replaceable_generic_provider(tmp_path):
    from context_integrity.evidence import EvidenceProvider

    manifest, contract, _batch = setup_mixed(tmp_path)

    class Replacement:
        def context_candidates(self, request):
            assert request.repository == manifest.repository
            descriptor = EvidenceProviderDescriptor("replacement", "1")
            path = "src/generic.py"
            source = SourceRecord(
                make_source_id(request.repository.id, path),
                path,
                SourceKind.SOURCE_CODE,
                AuthorityClass.EXECUTABLE_TRUTH,
                LifecycleState.UNKNOWN,
                SourceRevision(
                    "b" * 64,
                    request.repository.git_head,
                    GitFileStatus.UNKNOWN,
                    "provider_content_sha256",
                ),
                ClassificationResult(
                    SourceKind.SOURCE_CODE,
                    AuthorityClass.EXECUTABLE_TRUTH,
                    LifecycleState.UNKNOWN,
                    ClassificationConfidence.EXPLICIT,
                    ("provider-role-v1",),
                    (),
                ),
                12,
            )
            candidate = replace(
                CompilerCandidate.from_source(source),
                origin=CandidateOrigin.EVIDENCE_PROVIDER,
                provider_id=descriptor.id,
                provider_version=descriptor.version,
                evidence_location=path,
                derivation=descriptor.derivation,
                relevance=CandidateRelevance(1, 1, (("total", 1),), ("task_match",)),
            )
            state = EvidenceProviderState(
                descriptor,
                EvidenceRepositorySnapshot(
                    request.repository.id,
                    request.repository.git_head,
                    request.repository.git_dirty,
                ),
                request.task,
                "replacement-ranker-v1",
                request.acquisition_budget_bytes,
                EvidenceCoverage((), False),
            )
            return EvidenceContextBatch(state, (candidate,))

    provider: EvidenceProvider = Replacement()
    request = EvidenceContextRequest(tmp_path, manifest.repository, "sample")
    result = compile_mixed(manifest, contract, provider.context_candidates(request))
    assert result.status == "complete" and result.providers[0].descriptor.id == "replacement"


@pytest.mark.parametrize(
    "args",
    [
        (1, -1, (), ()),
        (1, 0, (("total", 1), ("total", 2)), ()),
        (1, 0, (), ("unsorted", "task_match")),
        (1, 0, (), (), (("symbol", "x", 3, 2),)),
        (1, 0, (), (), (), -1),
        (1, 0, (), (), (), 0, -1, None),
    ],
)
def test_malformed_candidate_relevance_rejected(args):
    with pytest.raises(ValueError):
        CandidateRelevance(*args)


@pytest.mark.parametrize(
    "provenance",
    [
        {"evidence_location": "/private/source.py"},
        {"derivation": "private source body"},
    ],
)
def test_provider_candidate_rejects_unsafe_provenance(tmp_path, provenance):
    _, _, batch = setup_mixed(tmp_path, files=[selected_file()])
    with pytest.raises(ValueError):
        replace(batch.candidates[0], **provenance)


def test_generic_batch_rejects_inconsistent_source_classification(tmp_path):
    _, _, batch = setup_mixed(tmp_path, files=[selected_file()])
    candidate = batch.candidates[0]
    classification = replace(candidate.source.classification, authority_class=AuthorityClass.PLAN)
    source = replace(candidate.source, classification=classification)
    with pytest.raises(EvidenceProviderError, match="invalid_candidate"):
        replace(batch, candidates=(replace(candidate, source=source),))


@pytest.mark.parametrize(
    "changes",
    [
        {"fallback_mode": "provider-private-detail"},
        {"change": (("private", "source text"),)},
        {"warnings": (ScanWarning("provider_incomplete", None, "arbitrary private warning"),)},
    ],
)
def test_provider_state_rejects_unstable_or_private_metadata(tmp_path, changes):
    _, _, batch = setup_mixed(tmp_path, files=[selected_file()])
    with pytest.raises(ValueError):
        replace(batch.state, **changes)


@pytest.mark.parametrize("field", ['kinds = ["unknown_kind"]', 'context_engine_bin = "/tmp/ctx"'])
def test_v7_stays_strict(field):
    text = f"""schema_version = 7
[[context_contracts]]
id = "work"
task_class = "implementation"
description = "Strict"
[[context_contracts.rules]]
id = "code"
mode = "required"
paths = ["src/sample.py"]
{field}
"""
    with pytest.raises(ConfigurationError):
        parse_config(text.encode())


def test_ineligible_optional_provider_slots_cannot_demote_docs(tmp_path):
    required = ContextContractRule("instructions", ContextRuleMode.REQUIRED, paths=("AGENTS.md",))
    rule = ContextContractRule(
        "any",
        ContextRuleMode.OPTIONAL,
        paths=("A.py", "AGENTS.md", "z.py"),
        lifecycles=(LifecycleState.ACTIVE,),
        max_count=1,
    )
    manifest, contract, batch = setup_mixed(
        tmp_path,
        rules=(required, rule),
        files=[selected_file("A.py", 2), selected_file("z.py", 1)],
    )
    assert paths(compile_mixed(manifest, contract, batch)) == ("AGENTS.md",)


@pytest.mark.parametrize(
    "name", ["crate::Type::method", "pkg.Class.method", "包.类", "r#type::Étage", "a" * 1024]
)
def test_qualified_relevance_model_acceptance(name):
    relevance = CandidateRelevance(1, 0, (), (), ((name, "method", 0, 1),))
    assert relevance.matched_entities[0][0] == name


@pytest.mark.parametrize("value", ["BadToken", "pkg.kind", "crate::kind", "é"])
def test_qualified_names_do_not_loosen_reason_or_kind_tokens(value):
    with pytest.raises(ValueError):
        CandidateRelevance(1, 0, (), (value,))
    with pytest.raises(ValueError):
        CandidateRelevance(1, 0, (), (), (("pkg.Class", value, 0, 1),))
