"""Small offline repositories exercise deterministic policy and safe evidence boundaries."""

import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest
from typer.testing import CliRunner

from context_integrity.cli import app
from context_integrity.configuration import ConfigurationError, parse_config
from context_integrity.evidence import changed_paths
from context_integrity.integrity import integrity_overview, references_canonical
from context_integrity.inventory import inventory_repository
from context_integrity.models import (
    ChangeScope,
    DriftDependencySpec,
    InstructionPolicySpec,
    RepositoryConfig,
)
from context_integrity.rendering import render_integrity_json, render_integrity_text
from context_integrity.repository import RepositoryError, discover_repository


def write(root, path, text):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)


def evaluate(root, diff=None):
    context = discover_repository(root)
    manifest = inventory_repository(context)
    return integrity_overview(context, manifest, diff)


def codes(overview):
    return {f.code for f in overview.findings}


def state(
    root,
    phase=4,
    plan="docs/plans/phase-4-implementation-plan.md",
    status="Implemented",
    next_phase=5,
):
    write(
        root,
        "docs/current-state.md",
        f"""**Current phase:** Phase {phase} — Test
**Active plan:** `{plan}`
**Status:** {status}

## Next expected step

Proceed to Phase {next_phase}.
""",
    )


def report(root, phase):
    write(root, f"docs/implementation-reports/phase-{phase}-implementation-report.md", "Evidence")


@pytest.mark.parametrize(
    "reference",
    [
        "AGENTS.md",
        "/AGENTS.md",
        "./AGENTS.md",
        "[AGENTS.md](AGENTS.md)",
        "[`AGENTS.md`](AGENTS.md)",
        "Follow `AGENTS.md` for instructions.",
    ],
)
def test_structural_instruction_reference(tmp_path, reference):
    write(tmp_path, "AGENTS.md", "Canonical")
    write(tmp_path, "CLAUDE.md", reference)
    assert not evaluate(tmp_path).findings


@pytest.mark.parametrize(
    "text",
    [
        "OTHER_AGENTS.md",
        "x/AGENTS.md",
        "AGENTS.md.bak",
        "https://host/AGENTS.md",
        "agents.md",
        "unrelated",
    ],
)
def test_reference_boundaries(text):
    assert not references_canonical(text, "AGENTS.md")


def test_instruction_missing_and_no_root_convention(tmp_path):
    write(tmp_path, "CLAUDE.md", "Standalone instructions")
    assert not evaluate(tmp_path).findings
    write(tmp_path, "AGENTS.md", "Canonical")
    assert codes(evaluate(tmp_path)) == {"instruction_reference_missing"}
    write(
        tmp_path,
        ".context-integrity.toml",
        """schema_version = 4
[instruction_policy]
canonical = "GEMINI.md"
compatibility = ["missing.md"]
""",
    )
    assert codes(evaluate(tmp_path)) == {
        "instruction_canonical_missing",
        "instruction_compatibility_missing",
    }


def test_instruction_wrong_kind_and_nested_policy(tmp_path):
    write(tmp_path, "docs/architecture.md", "Architecture")
    write(tmp_path, "nested/AGENTS.md", "Local additive rules")
    assert not evaluate(tmp_path).findings
    write(
        tmp_path,
        ".context-integrity.toml",
        """schema_version = 4
[instruction_policy]
canonical = "docs/architecture.md"
compatibility = []
""",
    )
    assert codes(evaluate(tmp_path)) == {"instruction_source_kind_mismatch"}


def test_current_state_valid_and_claims_unchanged(tmp_path):
    state(tmp_path)
    write(tmp_path, "docs/plans/phase-4-implementation-plan.md", "Plan")
    report(tmp_path, 4)
    assert not evaluate(tmp_path).findings


@pytest.mark.parametrize(
    "status,expected",
    [
        ("Implemented, offline verified", True),
        ("**Implemented**", True),
        ("**Implemented**, offline verified", True),
        ("`Delivered`", True),
        ("__Verified__", True),
        ("Delivered", True),
        ("Complete", True),
        ("Completed", True),
        ("Verified", True),
        ("not implemented", False),
        ("Implementation planned", False),
        ("unverified", False),
    ],
)
def test_plan_and_review_never_satisfy_delivered_status(tmp_path, status, expected):
    state(tmp_path, status=status)
    write(tmp_path, "docs/plans/phase-4-implementation-plan.md", "Plan")
    write(tmp_path, "docs/reviews/phase-4-review.md", "Review")
    assert ("current_state_delivery_evidence_missing" in codes(evaluate(tmp_path))) == expected


def test_numeric_lag_and_later_plan(tmp_path):
    state(tmp_path, phase=9, plan="docs/plans/phase-9-plan.md", next_phase=10)
    write(tmp_path, "docs/plans/phase-9-plan.md", "Plan")
    write(tmp_path, "docs/plans/phase-10-plan.md", "Plan")
    report(tmp_path, 9)
    assert not evaluate(tmp_path).findings
    report(tmp_path, 10)
    overview = evaluate(tmp_path)
    assert codes(overview) == {"current_state_lags_verification_evidence"}
    assert overview.findings[0].evidence[1].role == "verification_record"


@pytest.mark.parametrize(
    "plan,create,expected",
    [
        ("docs/plans/phase-4-plan.md", False, "current_state_active_plan_missing"),
        ("docs/architecture.md", True, "current_state_active_plan_kind_mismatch"),
        ("docs/plans/phase-3-plan.md", True, "current_state_phase_plan_mismatch"),
        ("docs/history/plans/phase-4-plan.md", True, "current_state_active_plan_unusable"),
        ("../outside-secret.md", False, "current_state_active_plan_unsafe"),
    ],
)
def test_active_plan_consistency(tmp_path, plan, create, expected):
    state(tmp_path, plan=plan)
    report(tmp_path, 4)
    if create:
        write(tmp_path, plan, "Plan")
    overview = evaluate(tmp_path)
    assert codes(overview) == {expected}
    assert "outside-secret" not in render_integrity_json(overview)


@pytest.mark.parametrize("next_phase", [3, 4])
def test_invalid_next_phase(tmp_path, next_phase):
    state(tmp_path, next_phase=next_phase)
    write(tmp_path, "docs/plans/phase-4-implementation-plan.md", "Plan")
    report(tmp_path, 4)
    assert codes(evaluate(tmp_path)) == {"current_state_next_phase_invalid"}


def test_missing_metadata_multiple_and_terminal_current_states(tmp_path):
    write(tmp_path, "docs/current-state.md", "No metadata")
    assert codes(evaluate(tmp_path)) == {"current_state_metadata_incomplete"}
    write(tmp_path, "status/current-state.md", "No metadata")
    assert codes(evaluate(tmp_path)) == {"current_state_multiple_candidates"}
    write(
        tmp_path,
        ".context-integrity.toml",
        """schema_version = 4
[[source_metadata]]
path = "status/current-state.md"
lifecycle = "historical"
reason = "Old snapshot"
""",
    )
    assert codes(evaluate(tmp_path)) == {"current_state_metadata_incomplete"}


def test_terminal_reports_do_not_prove_delivery(tmp_path):
    state(tmp_path)
    write(tmp_path, "docs/plans/phase-4-implementation-plan.md", "Plan")
    report(tmp_path, 4)
    report(tmp_path, 10)
    write(
        tmp_path,
        ".context-integrity.toml",
        """schema_version = 4
[[source_metadata]]
path = "docs/implementation-reports/phase-4-implementation-report.md"
lifecycle = "invalid"
reason = "Unusable"
[[source_metadata]]
path = "docs/implementation-reports/phase-10-implementation-report.md"
lifecycle = "historical"
reason = "Historical"
""",
    )
    assert codes(evaluate(tmp_path)) == {"current_state_delivery_evidence_missing"}


def test_draft_report_does_not_prove_delivery(tmp_path):
    state(tmp_path)
    write(tmp_path, "docs/plans/phase-4-implementation-plan.md", "Plan")
    report(tmp_path, 4)
    write(
        tmp_path,
        ".context-integrity.toml",
        """schema_version = 4
[[source_metadata]]
path = "docs/implementation-reports/phase-4-implementation-report.md"
lifecycle = "draft"
reason = "Not accepted yet"
""",
    )
    assert codes(evaluate(tmp_path)) == {"current_state_delivery_evidence_missing"}


def test_ambiguous_delivered_status_requires_evidence_and_reports_metadata(tmp_path):
    state(tmp_path, status="***Implemented***")
    write(tmp_path, "docs/plans/phase-4-implementation-plan.md", "Plan")
    assert codes(evaluate(tmp_path)) == {
        "current_state_delivery_evidence_missing",
        "current_state_metadata_incomplete",
    }


@pytest.mark.parametrize("instruction_path", ["AGENTS.md", "CLAUDE.md"])
@pytest.mark.parametrize("lifecycle", ["historical", "superseded"])
def test_inactive_instruction_sources_do_not_satisfy_policy(tmp_path, instruction_path, lifecycle):
    write(tmp_path, "AGENTS.md", "Canonical")
    write(tmp_path, "CLAUDE.md", "See AGENTS.md")
    write(
        tmp_path,
        ".context-integrity.toml",
        f"""schema_version = 4
[[source_metadata]]
path = "{instruction_path}"
lifecycle = "{lifecycle}"
reason = "No longer current"
""",
    )
    assert "instruction_source_unusable" in codes(evaluate(tmp_path))


def test_active_current_state_wins_over_draft_candidate(tmp_path):
    state(tmp_path)
    write(tmp_path, "docs/plans/phase-4-implementation-plan.md", "Plan")
    report(tmp_path, 4)
    write(tmp_path, "archive/current-state.md", "Draft snapshot")
    write(
        tmp_path,
        ".context-integrity.toml",
        """schema_version = 4
[[source_metadata]]
path = "archive/current-state.md"
lifecycle = "draft"
reason = "Work in progress"
""",
    )
    assert not evaluate(tmp_path).findings


@pytest.mark.parametrize(
    "factory",
    [
        lambda: InstructionPolicySpec("AGENTS.md", ("AGENTS.md",)),
        lambda: InstructionPolicySpec("../AGENTS.md", ()),
        lambda: InstructionPolicySpec(".context-integrity.toml", ()),
        lambda: InstructionPolicySpec("AGENTS.md", ("CLAUDE.md", "CLAUDE.md")),
        lambda: DriftDependencySpec("Bad ID", "docs/a.md", ("src/a.py",), "x"),
        lambda: DriftDependencySpec("a", "docs/a.md", (), "x"),
        lambda: DriftDependencySpec("a", "docs/a.md", ("docs/a.md",), "x"),
        lambda: DriftDependencySpec("a", "docs/a.md", ("src/a.py", "src/a.py"), "x"),
        lambda: DriftDependencySpec("a", "docs/a.md", ("src/a.py",), "  "),
        lambda: DriftDependencySpec("a", "docs//a.md", ("src/a.py",), "x"),
    ],
)
def test_phase_four_domain_specs_reject_invalid_direct_construction(factory):
    with pytest.raises((ValueError, TypeError)):
        factory()


def test_repository_config_rejects_duplicate_drift_ids():
    first = DriftDependencySpec("same", "docs/a.md", ("src/a.py",), "A")
    second = DriftDependencySpec("same", "docs/b.md", ("src/b.py",), "B")
    with pytest.raises(ValueError):
        RepositoryConfig(drift_dependencies=(first, second))


DEPENDENCY = """schema_version = 4
[[drift_dependencies]]
id = "architecture-core"
dependent = "docs/architecture.md"
upstream = ["src/model.py"]
reason = "Core model review"
"""


def commit(root, git):
    git(root, "add", ".")
    git(root, "commit", "-m", "Fixture")
    return git(root, "rev-parse", "HEAD")


@pytest.mark.parametrize(
    "mode,expected",
    [
        ("upstream", True),
        ("both", False),
        ("unrelated", False),
        ("deleted", True),
    ],
)
def test_dependency_changes(git_repo, git, mode, expected):
    write(git_repo, ".context-integrity.toml", DEPENDENCY)
    write(git_repo, "src/model.py", "original")
    commit(git_repo, git)
    if mode == "deleted":
        (git_repo / "src/model.py").unlink()
    elif mode != "unrelated":
        write(git_repo, "src/model.py", "modified")
    else:
        write(git_repo, "src/other.py", "untracked")
    if mode == "both":
        write(git_repo, "docs/architecture.md", "Reviewed")
    overview = evaluate(git_repo)
    assert ("document_dependency_changed" in codes(overview)) == expected
    if expected:
        f = overview.findings[0]
        assert f.dependency_id == "architecture-core"
        assert f.evidence[1].path == "src/model.py"
        assert f.evidence[1].source_id is None


def test_dependency_missing_and_unavailable(tmp_path):
    write(tmp_path, ".context-integrity.toml", DEPENDENCY)
    overview = evaluate(tmp_path)
    assert codes(overview) == {"drift_dependent_missing"}
    assert "change_evidence_unavailable" in {w.code for w in overview.warnings}
    write(tmp_path, "docs/architecture.md", "Architecture")
    assert not evaluate(tmp_path).findings


def test_git_clean_modified_deleted_untracked_and_range(git_repo, git):
    base = commit(git_repo, git)
    assert changed_paths(discover_repository(git_repo)).changed_paths == ()
    write(git_repo, "AGENTS.md", "modified")
    (git_repo / "docs/architecture.md").unlink()
    write(git_repo, "src/new.py", "untracked")
    observed = changed_paths(discover_repository(git_repo))
    assert observed.scope == ChangeScope.WORKING_TREE
    assert observed.changed_paths == ("AGENTS.md", "docs/architecture.md", "src/new.py")
    target = commit(git_repo, git)
    observed = changed_paths(discover_repository(git_repo), f"{base}..HEAD")
    assert observed.scope == ChangeScope.GIT_RANGE
    assert observed.base_revision == base
    assert observed.target_revision == target
    assert observed.changed_paths == ("AGENTS.md", "docs/architecture.md", "src/new.py")
    assert changed_paths(discover_repository(git_repo), "HEAD..HEAD").changed_paths == ()


@pytest.mark.parametrize(
    "diff",
    [
        "HEAD",
        "..HEAD",
        "HEAD..",
        "HEAD...HEAD",
        "HEAD..HEAD..HEAD",
        "--help..HEAD",
        "HEAD..-x",
        "missing..HEAD",
        " ..HEAD",
    ],
)
def test_invalid_diff_is_fatal(git_repo, git, diff):
    commit(git_repo, git)
    with pytest.raises(RepositoryError):
        changed_paths(discover_repository(git_repo), diff)


def test_explicit_diff_without_git_is_fatal(tmp_path):
    with pytest.raises(RepositoryError):
        evaluate(tmp_path, "main..HEAD")


def test_git_range_rename_is_delete_add(git_repo, git):
    base = commit(git_repo, git)
    git(git_repo, "mv", "AGENTS.md", "CLAUDE.md")
    commit(git_repo, git)
    assert changed_paths(discover_repository(git_repo), f"{base}..HEAD").changed_paths == (
        "AGENTS.md",
        "CLAUDE.md",
    )


def test_text_reread_hash_mismatch_and_symlink(tmp_path):
    write(tmp_path, "AGENTS.md", "Canonical")
    write(tmp_path, "CLAUDE.md", "See AGENTS.md")
    context = discover_repository(tmp_path)
    manifest = inventory_repository(context)
    write(tmp_path, "CLAUDE.md", "Source body secret")
    overview = integrity_overview(context, manifest)
    assert not overview.findings
    assert "integrity_text_unavailable" in {w.code for w in overview.warnings}
    assert "Source body secret" not in render_integrity_json(overview)
    (tmp_path / "CLAUDE.md").unlink()
    (tmp_path / "CLAUDE.md").symlink_to(tmp_path / "AGENTS.md")
    overview = integrity_overview(context, manifest)
    assert "symlink_skipped" in {w.code for w in overview.warnings}


def test_invalid_utf8_and_oversized_sources(tmp_path):
    write(tmp_path, "AGENTS.md", "Canonical")
    (tmp_path / "CLAUDE.md").write_bytes(b"\xff")
    assert "integrity_text_unavailable" in {w.code for w in evaluate(tmp_path).warnings}
    (tmp_path / "CLAUDE.md").write_bytes(b"x" * (5 * 1024 * 1024 + 1))
    assert "source_too_large" in {w.code for w in evaluate(tmp_path).warnings}


def test_cli_findings_success_output_and_errors(tmp_path):
    runner = CliRunner()
    state(tmp_path)
    result = runner.invoke(app, ["check", str(tmp_path), "--format", "json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["findings"]
    output = tmp_path / "out.json"
    result = runner.invoke(
        app, ["check", str(tmp_path), "--format", "json", "--output", str(output)]
    )
    assert result.exit_code == 0
    assert json.loads(output.read_text())["integrity_schema_version"] == 1
    assert runner.invoke(app, ["check", str(tmp_path), "--output", str(tmp_path)]).exit_code == 4
    assert runner.invoke(app, ["check", str(tmp_path), "--diff", "x..y"]).exit_code == 3
    write(tmp_path, ".context-integrity.toml", "invalid")
    assert runner.invoke(app, ["check", str(tmp_path)]).exit_code == 6
    assert runner.invoke(app, ["check", str(tmp_path / "absent")]).exit_code == 3


def test_integrity_json_golden_privacy_and_stable_ids(tmp_path):
    # Fixed remote identity makes the synthetic manifest portable.
    write(tmp_path, "AGENTS.md", "Canonical secret")
    write(tmp_path, "CLAUDE.md", "Compatibility secret")
    context = discover_repository(tmp_path)
    context.repository = replace(context.repository, id="repo_fixture", name="fixture")
    manifest = inventory_repository(context)
    overview = integrity_overview(context, manifest)
    rendered = render_integrity_json(overview)
    assert rendered == render_integrity_json(integrity_overview(context, manifest))
    assert rendered.endswith("\n")
    assert str(tmp_path) not in rendered
    assert "Canonical secret" not in rendered and "Compatibility secret" not in rendered
    assert rendered == (Path(__file__).parent / "fixtures/integrity-v1.json").read_text()
    write(tmp_path, "CLAUDE.md", "different body")
    updated = integrity_overview(context, inventory_repository(context))
    assert updated.findings[0].id == overview.findings[0].id
    assert (
        updated.findings[0].evidence[1].source_revision.content_sha256
        == sha256(b"different body").hexdigest()
    )
    escaped = render_integrity_text(
        replace(overview, repository=replace(overview.repository, name="x\x1b[31m"))
    )
    assert "\x1b" not in escaped and "\\u001b" in escaped


V4 = """schema_version = 4
[instruction_policy]
canonical = "AGENTS.md"
compatibility = ["CLAUDE.md", ".github/copilot-instructions.md"]
[[drift_dependencies]]
id = "architecture-core"
dependent = "docs/architecture.md"
upstream = ["src/model.py", ".context-integrity.toml"]
reason = "Policy/model review"
[[claims]]
id = "claim-one"
claim_type = "architecture"
subject = "core"
predicate = "uses"
value = "local evidence"
[[source_metadata]]
path = "docs/architecture.md"
lifecycle = "active"
reason = "Current"
"""


def test_v4_preserves_prior_features():
    config = parse_config(V4.encode())
    assert config.schema_version == 4
    assert config.claims[0].id == "claim-one"
    assert config.source_metadata[0].lifecycle_override == "active"
    assert config.instruction_policy.canonical == "AGENTS.md"
    assert config.drift_dependencies[0].upstream == (".context-integrity.toml", "src/model.py")


@pytest.mark.parametrize("old", [1, 2, 3])
@pytest.mark.parametrize(
    "extra",
    [
        '[instruction_policy]\ncanonical="AGENTS.md"\ncompatibility=[]',
        "drift_dependencies=[]",
    ],
)
def test_old_config_rejects_new_policy(old, extra):
    with pytest.raises(ConfigurationError):
        parse_config(f"schema_version={old}\n{extra}".encode())


@pytest.mark.parametrize(
    "before,after",
    [
        ('canonical = "AGENTS.md"', 'canonical = "CLAUDE.md"'),
        ('canonical = "AGENTS.md"', 'canonical = ".context-integrity.toml"'),
        ('canonical = "AGENTS.md"', 'canonical = "../secret"'),
        ('canonical = "AGENTS.md"', 'canonical = "/secret"'),
        ('canonical = "AGENTS.md"', 'canonical = "C:/secret"'),
        (
            'compatibility = ["CLAUDE.md", ".github/copilot-instructions.md"]',
            'compatibility = ["CLAUDE.md", "./CLAUDE.md"]',
        ),
        (
            'compatibility = ["CLAUDE.md", ".github/copilot-instructions.md"]',
            'compatibility = [".context-integrity.toml"]',
        ),
        ('canonical = "AGENTS.md"', 'canonical = "AGENTS.md"\nunknown = "SECRET"'),
        ('id = "architecture-core"', 'id = "Bad ID"'),
        ('dependent = "docs/architecture.md"', 'dependent = ".context-integrity.toml"'),
        ('dependent = "docs/architecture.md"', 'dependent = "../SECRET"'),
        ('upstream = ["src/model.py", ".context-integrity.toml"]', "upstream = []"),
        (
            'upstream = ["src/model.py", ".context-integrity.toml"]',
            'upstream = ["src/model.py", "./src/model.py"]',
        ),
        (
            'upstream = ["src/model.py", ".context-integrity.toml"]',
            'upstream = ["docs/architecture.md"]',
        ),
        ('reason = "Policy/model review"', 'reason = ""'),
    ],
)
def test_v4_strict_sanitized_validation(before, after):
    with pytest.raises(ConfigurationError) as error:
        parse_config(V4.replace(before, after).encode())
    assert str(error.value) == "Invalid .context-integrity.toml configuration."
    assert "SECRET" not in str(error.value)


def test_v4_duplicate_ids():
    with pytest.raises(ConfigurationError):
        parse_config((DEPENDENCY + DEPENDENCY.split("\n", 1)[1]).encode())


@pytest.mark.parametrize(
    "path",
    [
        "docs/implementation-reports/phase-4-implementation-report.md",
        "notes/phase-4-implementation-report.md",
    ],
)
def test_report_classification_and_candidate(tmp_path, path):
    write(tmp_path, path, "Report")
    write(tmp_path, "docs/plans/phase-4-implementation-plan.md", "Plan")
    manifest = inventory_repository(discover_repository(tmp_path))
    source = next(s for s in manifest.sources if s.path == path)
    assert source.kind == "verification_record"
    assert source.authority_class == "verification_evidence"
    assert source.lifecycle == "unknown"
    assert next(s for s in manifest.sources if "/plans/" in s.path).kind == "implementation_plan"


def test_dependency_explicit_range_and_claim_validity(git_repo, git):
    from context_integrity.claims import claims_overview

    write(
        git_repo,
        ".context-integrity.toml",
        DEPENDENCY
        + """
[[claims]]
id = "model"
claim_type = "architecture"
subject = "core"
predicate = "uses"
value = "local evidence"
depends_on = ["docs/architecture.md"]
""",
    )
    write(git_repo, "src/model.py", "original")
    base = commit(git_repo, git)
    write(git_repo, "src/model.py", "changed")
    target = commit(git_repo, git)
    context = discover_repository(git_repo)
    manifest = inventory_repository(context)
    before = claims_overview(manifest)
    overview = integrity_overview(context, manifest, f"{base}..{target}")
    assert codes(overview) == {"document_dependency_changed"}
    assert overview.change_set.target_revision == target
    assert claims_overview(manifest) == before
    assert before.claims[0].validity == "unverified"
    assert not evaluate(git_repo).findings  # clean tree is a different scope
    result = CliRunner().invoke(
        app, ["check", str(git_repo), "--diff", f"{base}..{target}", "--format", "json"]
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["change_set"]["base_revision"] == base
    assert payload["change_set"]["target_revision"] == target
    assert [f["code"] for f in payload["findings"]] == ["document_dependency_changed"]


def test_policy_changed_during_evaluation_fails_closed(tmp_path):
    write(tmp_path, ".context-integrity.toml", "schema_version=4")
    context = discover_repository(tmp_path)
    manifest = inventory_repository(context)
    write(tmp_path, ".context-integrity.toml", DEPENDENCY)
    with pytest.raises(ConfigurationError, match="changed during inventory"):
        integrity_overview(context, manifest)


def test_huge_phase_number_is_incomplete_metadata(tmp_path):
    state(tmp_path, phase="9" * 5000, status="not implemented")
    assert "current_state_metadata_incomplete" in codes(evaluate(tmp_path))


def test_local_git_evidence_failure_is_sanitized(git_repo, git, monkeypatch):
    import subprocess

    import context_integrity.evidence as adapter

    commit(git_repo, git)
    context = discover_repository(git_repo)

    def fail(*args):
        raise subprocess.TimeoutExpired("SECRET", 30)

    monkeypatch.setattr(adapter, "git_command", fail)
    with pytest.raises(
        RepositoryError, match="Requested local Git diff could not be evaluated"
    ) as error:
        changed_paths(context, "main..HEAD")
    assert "SECRET" not in str(error.value)
