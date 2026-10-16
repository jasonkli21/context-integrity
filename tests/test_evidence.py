"""Generic provider boundary and mixed compiler acceptance tests."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from context_integrity.compiler import compile_context
from context_integrity.configuration import ConfigurationError, parse_config
from context_integrity.contracts import validate_contract, validate_contract_sources
from context_integrity.evidence import (
    EvidenceContextRequest,
    EvidenceCoverage,
    EvidenceProviderDescriptor,
    EvidenceProviderError,
    EvidenceRepositorySnapshot,
)
from context_integrity.inventory import scan_repository
from context_integrity.models import (
    AuthorityClass,
    ContextContract,
    ContextContractRule,
    ContextRuleMode,
    LifecycleState,
    RepositoryConfig,
    SourceKind,
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
    for changes in (
        {"lifecycle": LifecycleState.HISTORICAL},
        {"authority_class": AuthorityClass.PLAN},
    ):
        first = batch.candidates[0]
        source = replace(first.source, **changes)
        candidate = replace(first, source=source, **changes)
        changed_batch = replace(batch, candidates=(candidate, batch.candidates[1]))
        rules = tuple(
            replace(r, authority_policy="implementation_truth") if r.id == "code" else r
            for r in contract.rules
        )
        # Use an actual builtin policy identifier.
        from context_integrity.authority import effective_policies

        policy = next(
            p
            for p in effective_policies(None)
            if p.tiers[0].classes == (AuthorityClass.EXECUTABLE_TRUTH,)
        )
        rules = tuple(
            replace(r, authority_policy=policy.id) if r.id == "code" else r for r in rules
        )
        new = replace(contract, rules=rules)
        updated = replace(
            manifest,
            repository_config=replace(manifest.repository_config, context_contracts=(new,)),
        )
        assert paths(compile_mixed(updated, new, changed_batch)) == ("AGENTS.md", "src/z.py")


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
    batch = replace(batch, state=replace(batch.state, coverage=coverage))
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

    manifest, contract, batch = setup_mixed(tmp_path)

    class Replacement:
        def context_candidates(self, request):
            assert request.repository == manifest.repository
            descriptor = EvidenceProviderDescriptor("replacement", "1")
            return replace(
                batch,
                state=replace(batch.state, descriptor=descriptor),
                candidates=tuple(
                    replace(
                        c,
                        provider_id=descriptor.id,
                        provider_version=descriptor.version,
                        derivation=descriptor.derivation,
                    )
                    for c in batch.candidates
                ),
            )

    provider: EvidenceProvider = Replacement()
    request = EvidenceContextRequest(tmp_path, manifest.repository, "sample")
    result = compile_mixed(manifest, contract, provider.context_candidates(request))
    assert result.status == "complete" and result.providers[0].descriptor.id == "replacement"


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
    rule = ContextContractRule(
        "any", ContextRuleMode.OPTIONAL, paths=("A.py", "AGENTS.md", "z.py"), max_count=1
    )
    manifest, contract, batch = setup_mixed(
        tmp_path, rules=(rule,), files=[selected_file("A.py", 2), selected_file("z.py", 1)]
    )
    first = batch.candidates[0]
    first = replace(
        first,
        lifecycle=LifecycleState.HISTORICAL,
        source=replace(first.source, lifecycle=LifecycleState.HISTORICAL),
    )
    batch = replace(batch, candidates=(first, batch.candidates[1]))
    assert paths(compile_mixed(manifest, contract, batch)) == ("AGENTS.md",)
