import pytest

from context_integrity.acquisition import is_context_candidate
from context_integrity.classification import (
    AUTHORITY_BY_KIND,
    HISTORICAL_DIRECTORIES,
    KIND_RULES,
    classify_source,
)
from context_integrity.models import AuthorityClass, LifecycleState, SourceKind

# One independent example for every kind rule, in declared precedence order.
RULE_CASES = [
    (".context-integrity.toml", "configuration"),
    ("AGENTS.md", "agent_instruction"),
    (".github/copilot-instructions.md", "agent_instruction"),
    ("current-state.md", "current_state"),
    ("architecture.md", "architecture"),
    ("prd.md", "product_requirement"),
    ("README.md", "readme"),
    ("adr/0001.md", "decision_record"),
    ("docs/implementation-reports/work.md", "verification_record"),
    ("plans/work.md", "implementation_plan"),
    ("reviews/work.md", "review"),
    ("verification/work.md", "verification_record"),
    ("releases/work.md", "release_record"),
    ("status/current-work.md", "current_state"),
    ("architecture/work.md", "architecture"),
    ("requirements/product-one.md", "product_requirement"),
    ("generated/work.md", "generated_summary"),
    ("ADR-one.md", "decision_record"),
    ("phase-0-plan.md", "implementation_plan"),
    ("work-review.md", "review"),
    ("work-verification.md", "verification_record"),
    ("release-one.md", "release_record"),
    ("old-architecture.md", "architecture"),
    ("old-prd.md", "product_requirement"),
    ("CODEX_HANDOFF.md", "handoff"),
    ("work-summary.md", "generated_summary"),
]


@pytest.mark.parametrize("case,rule", list(zip(RULE_CASES, KIND_RULES, strict=True)))
def test_each_kind_rule(case, rule):
    path, kind = case
    result = classify_source(path)
    assert result.kind == kind
    assert result.matched_rules[0] == rule.id
    assert result.authority_class == AUTHORITY_BY_KIND[result.kind]
    assert result.lifecycle == LifecycleState.UNKNOWN
    assert result.confidence == rule.confidence
    assert is_context_candidate(path)


@pytest.mark.parametrize(
    "path,kind",
    [
        ("CLAUDE.md", "agent_instruction"),
        ("GEMINI.md", "agent_instruction"),
        ("nested/AGENTS.md", "agent_instruction"),
        ("README.rst", "readme"),
        ("docs/adrs/a.md", "decision_record"),
        ("decisions/a.md", "decision_record"),
        ("planning/a.md", "implementation_plan"),
        ("docs/implementation-plan.md", "implementation_plan"),
        ("docs/post-implementation-review.md", "review"),
        ("docs/independent-review.md", "review"),
        ("docs/verification-record.md", "verification_record"),
        ("current_state.md", "current_state"),
        ("system-design.md", "architecture"),
        ("product-requirements-v1.md", "product_requirement"),
        ("docs/requirements/product-a.md", "product_requirement"),
        ("handoff.md", "handoff"),
        ("handoff-work.md", "handoff"),
        ("summary/work.md", "generated_summary"),
        ("docs/misc.md", "other_document"),
    ],
)
def test_aliases(path, kind):
    assert classify_source(path).kind == kind
    assert is_context_candidate(path)


@pytest.mark.parametrize("directory", HISTORICAL_DIRECTORIES)
@pytest.mark.parametrize(
    "name,kind", [("old-architecture.md", "architecture"), ("adr/0001.md", "decision_record")]
)
def test_history_overlay(directory, name, kind):
    result = classify_source(f"docs/{directory}/{name}")
    assert result.kind == kind
    assert result.lifecycle == "historical"
    assert result.authority_class == "historical"
    assert f"lifecycle.historical.directory_{directory}" in result.matched_rules
    assert "authority.historical.overlay" in result.matched_rules


def test_precedence_and_conservative_fallback():
    assert classify_source("docs/plans/architecture.md").kind == "architecture"
    assert classify_source("docs/adr/README.md").kind == "readme"
    result = classify_source("docs/misc.md")
    assert result.kind == SourceKind.OTHER_DOCUMENT
    assert result.authority_class == AuthorityClass.UNKNOWN
    assert result.confidence == "unknown"
    assert result.matched_rules[0] == "kind.other_document.fallback"
    assert classify_source("docs/architecture-2099.md").lifecycle == "unknown"


def test_builtin_rule_ids_are_stable():
    assert [r.id for r in KIND_RULES] == [
        "kind.configuration.exact_context_integrity",
        "kind.agent_instruction.filename",
        "kind.agent_instruction.copilot",
        "kind.current_state.filename",
        "kind.architecture.exact_filename",
        "kind.product.exact_filename",
        "kind.readme.filename",
        "kind.decision.directory",
        "kind.verification.implementation_reports",
        "kind.plan.directory",
        "kind.review.directory",
        "kind.verification.directory",
        "kind.release.directory",
        "kind.current_state.status_path",
        "kind.architecture.directory",
        "kind.product.requirements_path",
        "kind.generated.directory",
        "kind.decision.filename",
        "kind.plan.filename",
        "kind.review.filename",
        "kind.verification.filename",
        "kind.release.filename",
        "kind.architecture.filename",
        "kind.product.filename",
        "kind.handoff.filename",
        "kind.generated.filename",
    ]
