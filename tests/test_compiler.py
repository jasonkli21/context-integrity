"""Offline compiler acceptance cases over small observed repositories."""

import json
from dataclasses import replace
from pathlib import Path

import pytest
from typer.testing import CliRunner

from context_integrity.authority import (
    effective_policies,
    resolve_authority,
    resolve_authority_for_sources,
)
from context_integrity.cli import app
from context_integrity.compiler import compile_context
from context_integrity.configuration import ConfigurationError, parse_config
from context_integrity.contracts import validate_contract
from context_integrity.inventory import scan_repository
from context_integrity.models import (
    AuthorityClass,
    ChangeScope,
    ChangeSet,
    CompilationBudget,
    CompilationStatus,
    CompiledDependency,
    CompilerCandidate,
    ContextContract,
    ContextContractRule,
    FindingSeverity,
    IntegrityEvaluationStatus,
    IntegrityEvidence,
    IntegrityFinding,
    IntegrityOverview,
    LifecycleState,
    RepositoryConfig,
    SourceMetadata,
    make_source_id,
)
from context_integrity.models import (
    CandidateDecisionKind as Reason,
)
from context_integrity.models import (
    ContextRuleMode as Mode,
)
from context_integrity.rendering import render_compiled_context_json, render_compiled_context_text

CONFIG = """schema_version = 6
[[context_contracts]]
id = "work"
task_class = "implementation"
description = "Compile instructions"
budget_bytes = 100
[[context_contracts.rules]]
id = "instructions"
mode = "required"
paths = ["AGENTS.md"]
priority = 10
authority_policy = "operating_instructions"
"""


def rule(id="instructions", mode=Mode.REQUIRED, **kwargs):
    return ContextContractRule(id, mode, **({"paths": ("AGENTS.md",)} | kwargs))


def bind(manifest, *rules, budget=None, metadata=()):
    contract = ContextContract(
        "work", "implementation", "Fixture", rules or (rule(),), "a" * 64, budget
    )
    config = RepositoryConfig(
        content_sha256=contract.config_revision,
        schema_version=6,
        context_contracts=(contract,),
        source_metadata=metadata,
    )
    return replace(manifest, repository_config=config), contract


def compile_rules(manifest, *rules, budget=None, override=None, metadata=()):
    manifest, contract = bind(manifest, *rules, budget=budget, metadata=metadata)
    return compile_context(manifest, contract, budget_bytes=override)


def selected(result):
    return tuple(s.path for s in result.selected_sources)


def decisions(result):
    return {d.source.path: d for d in result.decisions}


def source_change(manifest, path="AGENTS.md", **changes):
    return replace(
        manifest,
        sources=tuple(replace(s, **changes) if s.path == path else s for s in manifest.sources),
    )


def test_config_v6():
    config = parse_config(CONFIG.encode())
    contract = config.context_contracts[0]
    assert config.schema_version == 6
    assert contract.config_revision == config.content_sha256
    assert contract.budget_bytes == 100
    assert contract.rules[0].priority == 10
    assert contract.rules[0].authority_policy == "operating_instructions"


@pytest.mark.parametrize("version", range(1, 6))
@pytest.mark.parametrize(
    "field", ["budget_bytes = 100", "priority = 10", 'authority_policy = "operating_instructions"']
)
def test_old_versions_reject_compiler_fields(version, field):
    text = CONFIG.replace("schema_version = 6", f"schema_version = {version}")
    for key in [
        "budget_bytes = 100",
        "priority = 10",
        'authority_policy = "operating_instructions"',
    ]:
        if key != field:
            text = text.replace(key, "")
    with pytest.raises(
        ConfigurationError, match=r"^Invalid .context-integrity.toml configuration.$"
    ):
        parse_config(text.encode())


@pytest.mark.parametrize(
    "old,new",
    [
        ("budget_bytes = 100", "budget_bytes = true"),
        ("budget_bytes = 100", "budget_bytes = 0"),
        ("budget_bytes = 100", "budget_bytes = -1"),
        ("priority = 10", "priority = true"),
        ("priority = 10", "priority = -1"),
        ("priority = 10", 'priority = "secret"'),
        ('authority_policy = "operating_instructions"', 'authority_policy = "unknown"'),
        ('authority_policy = "operating_instructions"', 'authority_policy = "bad id"'),
        ("priority = 10", "unknown = 1"),
    ],
)
def test_config_rejects_invalid_sanitized(old, new):
    with pytest.raises(
        ConfigurationError, match=r"^Invalid .context-integrity.toml configuration.$"
    ):
        parse_config(CONFIG.replace(old, new).encode())


@pytest.mark.parametrize("value", [True, False, 0, -1, 1.5, "100"])
def test_budget_construction_invariants(value):
    with pytest.raises(ValueError):
        CompilationBudget(value, None, 0)
    with pytest.raises(ValueError):
        CompilationBudget(None, value, 0)
    with pytest.raises(ValueError):
        replace(ContextContract("work", "implementation", "Fixture", (rule(),)), budget_bytes=value)


@pytest.mark.parametrize("value", [True, -1, 1.2, "0"])
def test_priority_model_invariants(value):
    with pytest.raises(ValueError):
        rule(priority=value)


def test_budget_arithmetic():
    budget = CompilationBudget(50, 20, 12)
    assert (budget.effective_bytes, budget.remaining_bytes, budget.origin) == (20, 8, "override")
    assert CompilationBudget(None, None, 100).remaining_bytes is None
    for args in [(1, None, 2), (None, None, True), (None, None, -1)]:
        with pytest.raises(ValueError):
            CompilationBudget(*args)


@pytest.mark.parametrize(
    "mutation", [{"id": "foreign"}, {"description": "modified"}, {"config_revision": "b" * 64}]
)
def test_binding_shared_with_validator(git_repo, mutation):
    manifest, contract = bind(scan_repository(git_repo))
    changed = replace(contract, **mutation)
    for operation in (compile_context, validate_contract):
        with pytest.raises(ValueError, match="not bound"):
            operation(manifest, changed)
    assert compile_context(manifest, contract).status == CompilationStatus.COMPLETE
    stale = replace(
        manifest, repository_config=replace(manifest.repository_config, content_sha256="c" * 64)
    )
    with pytest.raises(ValueError, match="not bound"):
        compile_context(stale, contract)


@pytest.mark.parametrize("state", list(LifecycleState))
def test_default_and_explicit_lifecycle(git_repo, state):
    manifest = source_change(scan_repository(git_repo), lifecycle=state)
    default = compile_rules(manifest)
    assert bool(default.selected_sources) == (
        state in {LifecycleState.UNKNOWN, LifecycleState.ACTIVE}
    )
    if not default.selected_sources:
        assert decisions(default)["AGENTS.md"].decision == Reason.INELIGIBLE_LIFECYCLE
    explicit = compile_rules(manifest, rule(lifecycles=(state,)))
    assert selected(explicit) == ("AGENTS.md",)
    bound, contract = bind(manifest)
    assert not validate_contract(bound, contract, ("AGENTS.md",)).findings


def test_excluded_conflict(git_repo):
    result = compile_rules(scan_repository(git_repo), rule(), rule("exclude", Mode.EXCLUDED))
    assert not result.selected_sources
    assert result.status == CompilationStatus.INCOMPLETE
    assert decisions(result)["AGENTS.md"].decision == Reason.EXCLUDED_BY_CONTRACT
    assert decisions(result)["AGENTS.md"].matched_rule_ids == ("exclude", "instructions")
    assert result.validation.findings[0].code == "required_context_missing"


def test_overlapping_required_coverage_dedupe(git_repo):
    # Architecture satisfies both rules; a lexical-only rule-first selector would
    # spend the entire budget on AGENTS first and fail the second requirement.
    result = compile_rules(
        scan_repository(git_repo),
        rule(paths=("AGENTS.md", "docs/architecture.md")),
        rule("architecture", paths=("docs/architecture.md",)),
        budget=13,
    )
    assert selected(result) == ("docs/architecture.md",)
    assert result.budget.used_bytes == 13
    assert result.status == CompilationStatus.COMPLETE
    assert len(result.dependencies) == 1
    assert decisions(result)["docs/architecture.md"].contributing_rule_ids == (
        "architecture",
        "instructions",
    )


@pytest.mark.parametrize(
    "budget,override,expected",
    [(None, None, 2), (26, None, 2), (25, None, 1), (1, 26, 2), (26, 13, 1), (12, None, 0)],
)
def test_required_first_optional_and_budget(git_repo, budget, override, expected):
    result = compile_rules(
        scan_repository(git_repo),
        rule(priority=0),
        rule("optional", Mode.OPTIONAL, paths=("docs/architecture.md",), priority=1000),
        budget=budget,
        override=override,
    )
    assert len(result.selected_sources) == expected
    assert ("AGENTS.md" in selected(result)) == (expected > 0)
    assert result.budget.used_bytes == sum(s.size_bytes for s in result.selected_sources)
    if result.budget.effective_bytes is not None:
        assert result.budget.used_bytes <= result.budget.effective_bytes
    assert result.status == (
        CompilationStatus.COMPLETE if expected else CompilationStatus.INCOMPLETE
    )


def test_max_counts_across_all_matches(git_repo):
    result = compile_rules(
        scan_repository(git_repo),
        rule(),
        rule("optional", Mode.OPTIONAL, paths=("AGENTS.md", "docs/architecture.md"), max_count=1),
    )
    assert selected(result) == ("AGENTS.md",)
    assert decisions(result)["docs/architecture.md"].decision == Reason.BLOCKED_BY_RULE_MAX
    assert not result.validation.findings


def test_required_priority_and_no_extra_required_matches(git_repo):
    manifest = scan_repository(git_repo)
    result = compile_rules(
        manifest,
        rule("low", priority=0),
        rule("high", paths=("docs/architecture.md",), priority=1),
        budget=13,
    )
    assert selected(result) == ("docs/architecture.md",)
    result = compile_rules(manifest, rule(paths=("AGENTS.md", "docs/architecture.md")))
    assert selected(result) == ("AGENTS.md",)
    assert decisions(result)["docs/architecture.md"].decision == Reason.REDUNDANT


def test_optional_priority_and_rule_id_order(git_repo):
    manifest = scan_repository(git_repo)
    result = compile_rules(
        manifest,
        rule("z", Mode.OPTIONAL, priority=1),
        rule("a", Mode.OPTIONAL, paths=("docs/architecture.md",)),
        budget=13,
    )
    assert selected(result) == ("AGENTS.md",)
    result = compile_rules(
        manifest,
        rule("z", Mode.OPTIONAL),
        rule("a", Mode.OPTIONAL, paths=("docs/architecture.md",)),
        budget=13,
    )
    assert selected(result) == ("docs/architecture.md",)


def test_authority_subset_and_no_budget_downgrade(git_repo):
    (git_repo / "docs/other.md").write_text("small")
    manifest = source_change(
        scan_repository(git_repo), "docs/other.md", authority_class=AuthorityClass.PLAN
    )
    manifest = source_change(manifest, "AGENTS.md", authority_class=AuthorityClass.DECISION)
    r = rule(
        paths=("docs/architecture.md", "docs/other.md"), authority_policy="architectural_intent"
    )
    result = compile_rules(manifest, r, budget=5)
    assert not result.selected_sources
    assert decisions(result)["docs/architecture.md"].decision == Reason.BLOCKED_BY_BUDGET
    lower = decisions(result)["docs/other.md"]
    assert lower.decision == Reason.LOWER_AUTHORITY_TIER
    assert lower.rule_decisions[0].tier_index == 2
    assert lower.rule_decisions[0].highest_tier_index == 1
    result = compile_rules(manifest, r)
    assert selected(result) == ("docs/architecture.md",)
    policy = next(p for p in effective_policies() if p.id == "architectural_intent")
    assert resolve_authority(manifest, policy) == resolve_authority_for_sources(
        manifest, policy, manifest.sources
    )


def test_equal_tier_alternatives_and_explicit_authority_eligibility(git_repo):
    (git_repo / "docs/other.md").write_text("other")
    manifest = source_change(
        scan_repository(git_repo),
        "docs/other.md",
        authority_class=AuthorityClass.ARCHITECTURE_PRODUCT,
    )
    r = rule(
        paths=("docs/architecture.md", "docs/other.md"),
        authority_policy="architectural_intent",
        max_count=1,
    )
    result = compile_rules(manifest, r)
    assert selected(result) == ("docs/architecture.md",)
    assert decisions(result)["docs/other.md"].rule_decisions[0].equal_tier_paths == (
        "docs/architecture.md",
        "docs/other.md",
    )
    metadata = (
        SourceMetadata("docs/architecture.md", "Explicitly ineligible", authority_eligible=False),
    )
    result = compile_rules(manifest, r, metadata=metadata)
    assert selected(result) == ("docs/other.md",)
    assert decisions(result)["docs/architecture.md"].decision == Reason.INELIGIBLE_AUTHORITY


def test_overlapping_rule_cannot_bypass_authority(git_repo):
    manifest = scan_repository(git_repo)
    result = compile_rules(
        manifest,
        rule(
            paths=("AGENTS.md", "docs/architecture.md"), authority_policy="operating_instructions"
        ),
        rule("optional", Mode.OPTIONAL, paths=("docs/architecture.md",)),
    )
    assert selected(result) == ("AGENTS.md",)
    assert decisions(result)["docs/architecture.md"].decision == Reason.LOWER_AUTHORITY_TIER


@pytest.mark.parametrize("digest", [None, "", "HEAD", "a" * 63, "g" * 64])
def test_unusable_revision(git_repo, digest):
    manifest = scan_repository(git_repo)
    source = next(s for s in manifest.sources if s.path == "AGENTS.md")
    manifest = source_change(manifest, revision=replace(source.revision, content_sha256=digest))
    result = compile_rules(manifest)
    assert result.status == CompilationStatus.INCOMPLETE
    assert decisions(result)["AGENTS.md"].decision == Reason.UNVERIFIABLE_REVISION
    with pytest.raises(ValueError):
        CompiledDependency(source.id, source.path, replace(source.revision, content_sha256=digest))


@pytest.mark.parametrize("size", [None, -1, True])
def test_unusable_size(git_repo, size):
    result = compile_rules(source_change(scan_repository(git_repo), size_bytes=size))
    assert not result.selected_sources
    assert decisions(result)["AGENTS.md"].decision == Reason.UNVERIFIABLE_SIZE


def test_provenance_determinism_models_and_golden(git_repo):
    manifest, contract = bind(
        scan_repository(git_repo), rule(authority_policy="operating_instructions"), budget=13
    )
    result = compile_context(manifest, contract, task="opaque task")
    rendered = render_compiled_context_json(result)
    assert rendered == render_compiled_context_json(
        compile_context(
            replace(manifest, sources=manifest.sources[::-1]), contract, task="opaque task"
        )
    )
    assert json.loads(rendered)["schema_version"] == 2
    assert json.loads(rendered)["integrity_state"]["evaluation_status"] == "not_evaluated"
    assert rendered == (Path(__file__).parent / "fixtures/compiled-context-v2.json").read_text()
    data = json.loads(rendered)
    assert data["schema_version"] == 2
    assert result.config_sha256 == contract.config_revision
    assert result.dependencies[0].source_revision == result.selected_sources[0].revision
    assert str(git_repo) not in rendered and "Instructions" not in rendered
    assert rendered.endswith("\n")
    assert "opaque task" in render_compiled_context_text(result)
    for changes in [
        {"dependencies": ()},
        {"selected_sources": result.selected_sources * 2},
        {"status": CompilationStatus.INCOMPLETE},
        {"budget": CompilationBudget(None, None, 0)},
    ]:
        with pytest.raises(ValueError):
            replace(result, **changes)


def test_unknown_policy_on_bound_domain_contract(git_repo):
    manifest, contract = bind(scan_repository(git_repo), rule(authority_policy="unknown"))
    with pytest.raises(ConfigurationError):
        compile_context(manifest, contract)


@pytest.mark.parametrize("budget", ["100", "1"])
def test_cli_text_json_and_output(git_repo, tmp_path, budget):
    (git_repo / ".context-integrity.toml").write_text(CONFIG)
    runner = CliRunner()
    args = ["compile", "work", str(git_repo), "--task", "opaque", "--budget-bytes", budget]
    text = runner.invoke(app, args)
    assert text.exit_code == 0, text.output
    assert "Compiled Context" in text.output
    result = runner.invoke(app, [*args, "--format", "json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["status"] == ("complete" if budget == "100" else "incomplete")
    assert data["task"]["text"] == "opaque"
    assert json.loads(runner.invoke(app, [*args, "--format", "json"]).output) == data
    output = tmp_path / "compiled.json"
    result = runner.invoke(app, [*args, "--format", "json", "--output", str(output)])
    assert result.exit_code == 0
    assert json.loads(output.read_text()) == data


@pytest.mark.parametrize(
    "args,exit_code",
    [
        (["missing"], 2),
        (["work", "--budget-bytes", "0"], 2),
        (["work", "--budget-bytes", "-1"], 2),
        (["work", "--budget-bytes", "x"], 2),
        (["work", "--output", "/dev/null/impossible"], 4),
    ],
)
def test_cli_errors(git_repo, args, exit_code):
    (git_repo / ".context-integrity.toml").write_text(CONFIG)
    result = CliRunner().invoke(app, ["compile", args[0], str(git_repo), *args[1:]])
    assert result.exit_code == exit_code, result.output


def test_cli_config_and_repository_failure(git_repo):
    (git_repo / ".context-integrity.toml").write_text(
        CONFIG.replace("budget_bytes = 100", "budget_bytes = true")
    )
    assert CliRunner().invoke(app, ["compile", "work", str(git_repo)]).exit_code == 6
    assert CliRunner().invoke(app, ["compile", "work", str(git_repo / "missing")]).exit_code == 3


@pytest.mark.parametrize("version", [5, 6])
def test_prior_contract_can_compile_and_v6_defaults(git_repo, version):
    data = CONFIG.replace("schema_version = 6", f"schema_version = {version}")
    for line in [
        "budget_bytes = 100",
        "priority = 10",
        'authority_policy = "operating_instructions"',
    ]:
        data = data.replace(line, "")
    (git_repo / ".context-integrity.toml").write_text(data)
    manifest = scan_repository(git_repo)
    contract = manifest.repository_config.context_contracts[0]
    assert (
        contract.budget_bytes,
        contract.rules[0].priority,
        contract.rules[0].authority_policy,
    ) == (None, 0, None)
    assert selected(compile_context(manifest, contract)) == ("AGENTS.md",)


@pytest.mark.parametrize("field", ["budget", "priority", "policy"])
def test_direct_config_gates_compiler_policy(field):
    contract = ContextContract(
        "work",
        "implementation",
        "Fixture",
        (
            rule(
                priority=1 if field == "priority" else 0,
                authority_policy="operating_instructions" if field == "policy" else None,
            ),
        ),
        budget_bytes=10 if field == "budget" else None,
    )
    with pytest.raises(ValueError, match="schema v6"):
        RepositoryConfig(schema_version=5, context_contracts=(contract,))


def test_explicit_history_lifecycle_composes_with_authority_policy(git_repo):
    manifest = source_change(scan_repository(git_repo), lifecycle=LifecycleState.HISTORICAL)
    historical_rule = rule(
        lifecycles=(LifecycleState.HISTORICAL,), authority_policy="operating_instructions"
    )
    manifest, contract = bind(manifest, historical_rule)
    result = compile_context(manifest, contract)
    assert selected(result) == ("AGENTS.md",)
    relation = decisions(result)["AGENTS.md"].rule_decisions[0]
    assert relation.reason == Reason.SELECTED
    assert relation.tier_index == 0
    manifest = replace(
        manifest,
        repository_config=replace(
            manifest.repository_config,
            source_metadata=(SourceMetadata("AGENTS.md", "excluded", authority_eligible=False),),
        ),
    )
    rejected = compile_context(manifest, contract)
    assert not rejected.selected_sources
    assert decisions(rejected)["AGENTS.md"].rule_decisions[0].reason == Reason.INELIGIBLE_AUTHORITY


def test_required_selection_repairs_feasible_budget_solution(git_repo):
    manifest = scan_repository(git_repo)
    template = manifest.sources[0]
    candidates = []
    for path, size in (("ab.md", 5), ("a.md", 2), ("b.md", 2), ("c.md", 3)):
        candidates.append(
            replace(
                template,
                id=make_source_id(manifest.repository.id, path),
                path=path,
                size_bytes=size,
                revision=replace(template.revision, content_sha256=(str(len(path)) * 64)),
            )
        )
    manifest = replace(manifest, sources=tuple(candidates))
    rules = (
        rule("a", paths=("ab.md", "a.md")),
        rule("b", paths=("ab.md", "b.md")),
        rule("c", paths=("c.md",)),
    )
    result = compile_rules(manifest, *rules, budget=7)
    assert selected(result) == ("a.md", "b.md", "c.md")
    assert result.status == CompilationStatus.COMPLETE
    assert result.budget.used_bytes == 7
    assert all(item.satisfied for item in result.validation.rule_results)
    reversed_result = compile_rules(
        replace(manifest, sources=manifest.sources[::-1]), *rules, budget=7
    )
    assert render_compiled_context_json(result) == render_compiled_context_json(reversed_result)
    assert compile_rules(manifest, *rules, budget=6).status == CompilationStatus.INCOMPLETE


def test_candidate_abstraction_and_integrity_state(git_repo):
    manifest = scan_repository(git_repo)
    source = manifest.sources[0]
    candidate = CompilerCandidate.from_source(source)
    evidence_candidate = replace(
        candidate,
        source=None,
        id="provider:item-1",
        evidence_location="src/module.py:10-18",
        derivation="symbol_index:v1",
    )
    assert evidence_candidate.path == source.path
    assert evidence_candidate.source is None
    assert evidence_candidate.evidence_location == "src/module.py:10-18"
    finding = IntegrityFinding(
        "finding-1",
        "rule-1",
        "issue",
        FindingSeverity.MEDIUM,
        "message",
        (source.path,),
        (IntegrityEvidence("subject", source.path, source.id, source.revision),),
    )
    manifest, contract = bind(manifest, rule())
    overview = IntegrityOverview(
        manifest.repository,
        manifest.repository_config.content_sha256,
        ChangeSet(ChangeScope.UNAVAILABLE),
        (finding,),
        (),
    )
    result = compile_context(manifest, contract)
    assert result.integrity_state.evaluation_status == IntegrityEvaluationStatus.NOT_EVALUATED
    evaluated = compile_context(manifest, contract, integrity_overview=overview)
    rendered = json.loads(render_compiled_context_json(evaluated))["integrity_state"]
    assert rendered["evaluation_status"] == "evaluated"
    assert rendered["findings"][0]["id"] == "finding-1"
    assert rendered["findings"][0]["severity"] == "medium"
    assert rendered["findings"][0]["evidence"][0]["path"] == source.path


def test_custom_policy_provenance_and_inventory_only(git_repo):
    (git_repo / "code.py").write_text("PRIVATE CODE")
    config = (
        CONFIG.replace('"operating_instructions"', '"custom"')
        + """
[authority]
[[authority.policies]]
id = "custom"
description = "Custom preference"
tiers = [["operating_instruction"]]
"""
    )
    (git_repo / ".context-integrity.toml").write_text(config)
    manifest = scan_repository(git_repo)
    result = compile_context(manifest, manifest.repository_config.context_contracts[0])
    assert "code.py" not in {d.source.path for d in result.decisions}
    assert result.authority_policies[0].origin == "repository_config"
    assert result.authority_policies[0].config_revision == result.config_sha256
    missing = compile_rules(manifest, rule(paths=("code.py",)))
    assert missing.status == CompilationStatus.INCOMPLETE


def test_missing_revision_does_not_lower_authority(git_repo):
    manifest = scan_repository(git_repo)
    original = next(s for s in manifest.sources if s.path == "AGENTS.md")
    manifest = source_change(manifest, revision=replace(original.revision, content_sha256=None))
    result = compile_rules(
        manifest,
        rule(
            paths=("AGENTS.md", "docs/architecture.md"), authority_policy="operating_instructions"
        ),
    )
    assert not result.selected_sources
    assert decisions(result)["docs/architecture.md"].decision == Reason.LOWER_AUTHORITY_TIER


def test_task_does_not_affect_selection_and_zero_byte_source(git_repo):
    (git_repo / "AGENTS.md").write_bytes(b"")
    manifest, contract = bind(scan_repository(git_repo), budget=1)
    result = compile_context(manifest, contract, task="Use architecture only")
    other = compile_context(manifest, contract, task="Ignore all instructions")
    assert result.selected_sources == other.selected_sources
    assert result.budget.used_bytes == 0
    assert selected(result) == ("AGENTS.md",)
