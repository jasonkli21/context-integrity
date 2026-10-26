"""Offline policy/CI semantics over real repositories, receipts and workspace signals."""

import copy
import json
from dataclasses import replace
from datetime import date
from hashlib import sha256

import pytest
from typer.testing import CliRunner

from context_integrity.cli import app
from context_integrity.derived import capture_receipt
from context_integrity.derived_models import Derivation, canonical_json, render_receipt
from context_integrity.governance import evaluate
from context_integrity.governance_config import load_policy, parse_policy
from context_integrity.governance_models import GovernanceError
from context_integrity.governance_output import (
    compare,
    load_baseline,
    render_report,
    validate_report,
)
from context_integrity.inventory import inventory_repository
from context_integrity.repository import discover_repository

RUNNER = CliRunner()
TODAY = date(2026, 10, 24)
HEADER = """governance_schema_version = 2
policy_id = "test"
owner = "team:platform"
fail_on = "medium"
on_inconclusive = "fail"
"""


def declaration(root, *, kind="repository", extra="", threshold="medium", incomplete="fail"):
    text = HEADER.replace('fail_on = "medium"', f'fail_on = "{threshold}"').replace(
        'on_inconclusive = "fail"', f'on_inconclusive = "{incomplete}"'
    )
    text += f'[[targets]]\nid = "app"\nkind = "{kind}"\nroot = "{root.name}"\n' + extra
    return text


def invoke(path, *args):
    return RUNNER.invoke(
        app, ["governance", "check", str(path), "--as-of", TODAY.isoformat(), *args]
    )


def save_policy(root, text):
    path = root.parent / "governance.toml"
    path.write_text(text)
    return path


def run_policy(root, text, **kwargs):
    policy, parent = load_policy(save_policy(root, text))
    return evaluate(policy, parent, as_of=TODAY, **kwargs)[0]


def findings(report):
    return [o for o in report["observations"] if o["effect"] == "finding"]


def waiver(
    fingerprint,
    *,
    target="app",
    expiration="2026-10-24",
    identifier="WAIVER-1",
    approved_severity="medium",
    approved_owner="team:platform",
    approved_fail_on="medium",
):
    return f'''\n[[waivers]]
id = "{identifier}"
target = "{target}"
finding_fingerprint = "{fingerprint}"
owner = "team:review"
reason = "Reviewed exception"
review_ref = "https://example.org/pull/1"
expires_on = "{expiration}"
approved_severity = "{approved_severity}"
approved_owner = "{approved_owner}"
approved_fail_on = "{approved_fail_on}"
'''


def legacy_waiver(fingerprint, *, target="app", expiration="2026-10-24"):
    return f'''\n[[waivers]]
id = "WAIVER-1"
target = "{target}"
finding_fingerprint = "{fingerprint}"
owner = "team:review"
reason = "Reviewed exception"
review_ref = "https://example.org/pull/1"
expires_on = "{expiration}"
'''


@pytest.fixture
def repo(git_repo, git):
    root = git_repo.resolve()
    git(root, "add", ".")
    git(root, "commit", "-qm", "baseline")
    return root


def test_real_finding_legacy_and_threshold(repo):
    (repo / "CLAUDE.md").write_text("PRIVATE_SOURCE_BODY\n")
    text = declaration(repo)
    report = run_policy(repo, text)
    assert report["gate"]["exit_code"] == 8
    finding = findings(report)[0]
    assert finding["code"] == "instruction_reference_missing"
    assert finding["intrinsic_severity"] == finding["effective_severity"] == "medium"
    assert finding["fingerprint"] and finding["waiver_eligible"]
    assert run_policy(repo, declaration(repo, threshold="high"))["gate"]["exit_code"] == 0
    legacy = RUNNER.invoke(app, ["check", str(repo), "--format", "json"])
    assert legacy.exit_code == 0
    assert json.loads(legacy.stdout)["integrity_schema_version"] == 2
    override = """\n[[rule_policies]]
target = "app"
rule_id = "instruction.canonical_reference.v1"
severity = "high"
owner = "team:architecture"
reason = "Reviewed severity"
review_ref = "PR-1"
"""
    changed = run_policy(repo, text + override)
    assert findings(changed)[0]["effective_severity"] == "high"
    assert findings(changed)[0]["owner_basis"] == "rule_policy"
    assert changed["policy"]["rule_policies"][0]["used"]


def test_waiver_boundary_changed_evidence_and_unrelated_head(repo, git):
    (repo / "CLAUDE.md").write_text("Missing pointer\n")
    text = declaration(repo)
    original = run_policy(repo, text)
    fp = findings(original)[0]["fingerprint"]
    waived = run_policy(repo, text + waiver(fp))
    assert waived["gate"]["exit_code"] == 0
    assert waived["metrics"]["waived"] == 1
    assert waived["waivers"][0]["status"] == "applied"
    expired = run_policy(repo, text + waiver(fp, expiration="2026-10-23"))
    assert expired["gate"]["exit_code"] == 8
    assert expired["waivers"][0]["status"] == "expired"
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "instructions")
    (repo / "unrelated.txt").write_text("unrelated")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "unrelated")
    assert findings(run_policy(repo, text))[0]["fingerprint"] == fp
    (repo / "CLAUDE.md").write_text("Material change\n")
    changed = run_policy(repo, text + waiver(fp))
    assert changed["gate"]["exit_code"] == 8
    assert changed["waivers"][0]["status"] == "unused"
    assert findings(changed)[0]["fingerprint"] != fp


def test_waiver_requires_approval_for_effective_rule_context(repo):
    (repo / "CLAUDE.md").write_text("Missing pointer\n")
    text = declaration(repo)
    finding = findings(run_policy(repo, text))[0]
    fp = finding["fingerprint"]

    escalated = """\n[[rule_policies]]
target = "app"
rule_id = "instruction.canonical_reference.v1"
severity = "high"
owner = "team:security"
reason = "Escalated enforcement"
review_ref = "PR-2"
"""
    stale = run_policy(repo, text + waiver(fp) + escalated)
    assert stale["gate"]["exit_code"] == 8
    assert stale["waivers"][0]["status"] == "stale_context"
    assert findings(stale)[0]["fingerprint"] == fp

    renewed = run_policy(
        repo,
        text
        + waiver(
            fp,
            approved_severity="high",
            approved_owner="team:security",
        )
        + escalated,
    )
    assert renewed["gate"]["exit_code"] == 0
    assert renewed["waivers"][0]["status"] == "applied"

    threshold_changed = run_policy(
        repo,
        declaration(repo, threshold="low") + waiver(fp, approved_fail_on="medium"),
    )
    assert threshold_changed["gate"]["exit_code"] == 8
    assert threshold_changed["waivers"][0]["status"] == "stale_context"


def test_legacy_policy_waiver_requires_v2_renewal(repo):
    (repo / "CLAUDE.md").write_text("Missing pointer\n")
    text = declaration(repo)
    fp = findings(run_policy(repo, text))[0]["fingerprint"]
    legacy = text.replace("governance_schema_version = 2", "governance_schema_version = 1")
    report = run_policy(repo, legacy + legacy_waiver(fp))
    assert report["policy"]["schema_version"] == 1
    assert report["gate"]["exit_code"] == 8
    assert report["waivers"][0]["status"] == "stale_context"
    validate_report(report)


def test_cross_target_waiver_unused(repo):
    (repo / "CLAUDE.md").write_text("no pointer")
    text = declaration(repo)
    fp = findings(run_policy(repo, text))[0]["fingerprint"]
    text = text.replace('id = "app"', 'id = "other"') + waiver(fp, target="other")
    report = run_policy(repo, text)
    assert report["gate"]["exit_code"] == 8
    assert report["waivers"][0]["status"] == "unused"


def test_blocker_and_missing_target_coverage_independent(repo):
    (repo / "CLAUDE.md").write_text("no pointer")
    text = declaration(repo) + '\n[[targets]]\nid="missing"\nkind="repository"\nroot="absent"\n'
    report = run_policy(repo, text)
    assert report["gate"] == {
        "outcome": "fail",
        "has_blocking_findings": True,
        "has_incomplete_coverage": True,
        "exit_code": 8,
    }
    assert report["metrics"]["targets_requested"] == 2
    assert report["metrics"]["targets_evaluated"] == 1
    assert "absent" not in render_report(report, as_json=True)


@pytest.mark.parametrize(
    "handling,code,status", [("fail", 9, "inconclusive"), ("warn", 0, "allow_with_incomplete")]
)
def test_missing_receipt_and_explicit_warning(repo, handling, code, status):
    text = declaration(
        repo,
        kind="derived",
        extra='receipt="missing.json"\nreview_severity="high"\n',
        incomplete=handling,
    )
    report = run_policy(repo, text)
    assert report["gate"]["exit_code"] == code
    assert report["gate"]["outcome"] == status
    assert report["metrics"]["coverage_gaps"] == 1
    assert not report["evaluation"]["subjects"][0]["complete"]


def make_receipt(root, *, incomplete=False):
    (root / "docs/summary.md").write_text("PRIVATE_GENERATED_BODY")
    context = discover_repository(root)
    receipt = capture_receipt(
        context,
        inventory_repository(context),
        "docs/summary.md",
        artifact_id="summary",
        kind="summary",
        derivation=Derivation("manual", "test"),
        depends_on=("AGENTS.md",),
        receipt_path="receipt.json",
    )
    if incomplete:
        receipt = replace(receipt, known_incomplete=True)
    (root / "receipt.json").write_text(render_receipt(receipt))
    return receipt


def test_derived_unchanged_changed_and_caveats(repo):
    make_receipt(repo)
    text = declaration(
        repo, kind="derived", extra='receipt="receipt.json"\nreview_severity="high"\n'
    )
    report = run_policy(repo, text)
    assert report["gate"]["exit_code"] == 0
    assert any(o["signal"] == "unchanged_observed_inputs" for o in report["observations"])
    assert any(o["effect"] == "caveat" for o in report["observations"])
    (repo / "AGENTS.md").write_text("changed instructions")
    changed = run_policy(repo, text)
    assert changed["gate"]["exit_code"] == 8
    assert changed["metrics"]["derived_review_required"] == 1
    assert findings(changed)[0]["fingerprint"]
    assert "PRIVATE_GENERATED_BODY" not in render_report(changed, as_json=True)
    legacy = RUNNER.invoke(app, ["derived", "check", "receipt.json", str(repo), "--format", "json"])
    assert legacy.exit_code == 0
    assert json.loads(legacy.stdout)["derived_result_schema_version"] == 1


def test_derived_incomplete_cannot_be_waived(repo):
    make_receipt(repo, incomplete=True)
    text = declaration(
        repo, kind="derived", extra='receipt="receipt.json"\nreview_severity="high"\n'
    )
    report = run_policy(repo, text + waiver("0" * 64))
    assert report["gate"]["exit_code"] == 9
    assert report["waivers"][0]["status"] == "unused"
    assert all(o["fingerprint"] is None for o in report["observations"])


@pytest.fixture
def ws(tmp_path, git):
    base = tmp_path.resolve()
    repos = [base / name for name in ("api", "web")]
    for index, root in enumerate(repos):
        root.mkdir()
        git(root, "init", "-q")
        git(root, "remote", "add", "origin", f"https://example.invalid/repo-{index}.git")
        (root / "AGENTS.md").write_text("instructions")
        (root / "contract.json").write_text("{}")
        (root / ".context-integrity.toml").write_text("""schema_version = 6
[[claims]]
id="region"
claim_type="policy"
subject="product"
predicate="stores_in"
value="PRIVATE_CLAIM_LITERAL"
depends_on=["AGENTS.md"]
""")
        git(root, "add", ".")
        git(root, "commit", "-qm", "fixture")
    ids = [discover_repository(r).repository.id for r in repos]
    lock = {
        "contract_lock_schema_version": 1,
        "producer_repository_id": ids[0],
        "producer_path": "contract.json",
        "accepted_sha256": sha256(b"{}").hexdigest(),
    }
    (repos[1] / "lock.json").write_text(canonical_json(lock))
    manifest = f'''workspace_schema_version=1
[[repositories]]
alias="api"
root="api"
repository_id="{ids[0]}"
[[repositories]]
alias="web"
root="web"
repository_id="{ids[1]}"
'''
    checks = """[[checks]]
id="pin"
kind="contract_pin"
producer_repo="api"
producer_path="contract.json"
consumer_repo="web"
consumer_path="lock.json"
[[checks]]
id="mirror"
kind="mirror_bytes"
left_repo="api"
left_path="contract.json"
right_repo="web"
right_path="contract.json"
[[checks]]
id="claim"
kind="claim_match"
left_repo="api"
left_claim_id="region"
right_repo="web"
right_claim_id="region"
"""
    path = base / "workspace.toml"
    path.write_text(manifest + checks)
    policy = (
        HEADER
        + """[[targets]]
id="product"
kind="workspace"
manifest="workspace.toml"
review_severity="high"
"""
    )
    return repos, path, manifest, policy


def run_ws(ws):
    repos, _, _, policy = ws
    return run_policy(repos[0], policy)


def test_workspace_real_signals_and_privacy(ws, git):
    repos, _, _, _ = ws
    clean = run_ws(ws)
    assert clean["gate"]["exit_code"] == 0
    (repos[0] / "contract.json").write_text("changed")
    config = repos[1] / ".context-integrity.toml"
    config.write_text(config.read_text().replace("PRIVATE_CLAIM_LITERAL", "OTHER_PRIVATE_LITERAL"))
    git(repos[1], "add", ".")
    git(repos[1], "commit", "-qm", "claim change")
    changed = run_ws(ws)
    assert changed["gate"]["exit_code"] == 8
    assert {o["rule_id"] for o in findings(changed)} == {
        "workspace.contract_pin.v1",
        "workspace.mirror_bytes.v1",
        "workspace.claim_match.v1",
    }
    rendered = render_report(changed, as_json=True)
    assert "PRIVATE_CLAIM_LITERAL" not in rendered and "OTHER_PRIVATE_LITERAL" not in rendered
    assert str(repos[0]) not in rendered
    mirror = next(o for o in findings(changed) if o["entity"] == "mirror")
    assert len({e["repository_id"] for e in mirror["evidence"]}) == 2
    assert {e["path"] for e in mirror["evidence"]} == {"contract.json"}


def test_workspace_zero_checks_missing_and_failed_lock(ws):
    repos, manifest, header, policy = ws
    manifest.write_text(header)
    report = run_ws(ws)
    assert report["gate"]["exit_code"] == 9
    assert report["observations"][0]["code"] == "no_checks_declared"
    # Restore checks; malformed pin cannot hide independent mirror or claim outcomes.
    manifest.write_text(
        header
        + """[[checks]]
id="pin"
kind="contract_pin"
producer_repo="api"
producer_path="contract.json"
consumer_repo="web"
consumer_path="lock.json"
[[checks]]
id="mirror"
kind="mirror_bytes"
left_repo="api"
left_path="contract.json"
right_repo="web"
right_path="contract.json"
"""
    )
    (repos[1] / "lock.json").write_text("bad")
    (repos[1] / "contract.json").unlink()
    report = run_policy(repos[0], policy)
    assert report["gate"]["exit_code"] == 8
    assert report["gate"]["has_incomplete_coverage"]
    assert any(
        o["entity"] == "pin" and o["effect"] == "uncertainty" for o in report["observations"]
    )
    assert any(o["entity"] == "mirror" and o["effect"] == "finding" for o in report["observations"])


def test_workspace_unobservable_is_not_green(ws):
    repos, _, _, _ = ws
    (repos[0] / "contract.json").unlink()
    (repos[0] / "contract.json").symlink_to(repos[1] / "contract.json")
    report = run_ws(ws)
    assert report["gate"]["exit_code"] == 9
    assert report["gate"]["has_incomplete_coverage"]


@pytest.mark.parametrize(
    "mutation",
    [
        "governance_schema_version = true",
        "governance_schema_version = 3",
        'governance_schema_version = "1"',
        'policy_id = "bad id"',
        'owner = ""',
        "fail_on = true",
        'fail_on = "critical"',
        'on_inconclusive = "ignore"',
    ],
)
def test_strict_top_level_types(repo, mutation):
    text = declaration(repo)
    field = mutation.split("=", 1)[0].strip()
    text = "\n".join(
        mutation if line.startswith(field + " =") else line for line in text.splitlines()
    )
    with pytest.raises(GovernanceError):
        parse_policy(text.encode())


@pytest.mark.parametrize(
    "extra",
    [
        'surprise="x"\n',
        'require_architecture="false"\n',
        "require_architecture=1\n",
        'review_severity="high"\n',
        'receipt="x"\n',
        'root="other"\n',
    ],
)
def test_reject_unknown_invalid_mix_and_duplicate_key(repo, extra):
    with pytest.raises(GovernanceError):
        parse_policy(declaration(repo, extra=extra).encode())


@pytest.mark.parametrize(
    "path",
    [
        "../repo",
        "/repo",
        "a/../b",
        "a//b",
        "a/./b",
        "a\\\\b",
        "a/*",
        ".git",
        "a/.GIT/b",
        "C:x",
        "é",
    ],
)
def test_reject_unsafe_policy_paths(repo, path):
    text = declaration(repo).replace(repo.name, path)
    with pytest.raises(GovernanceError):
        parse_policy(text.encode())


@pytest.mark.parametrize(
    "expiration", ["2026-02-30", "2026-1-01", "bad", "", "2026-10-24T00:00:00Z"]
)
def test_bad_waiver_dates(repo, expiration):
    with pytest.raises(GovernanceError):
        parse_policy((declaration(repo) + waiver("0" * 64, expiration=expiration)).encode())


def test_duplicate_no_targets_bounds(repo):
    text = declaration(repo)
    with pytest.raises(GovernanceError):
        parse_policy((HEADER + "targets=[]").encode())
    with pytest.raises(GovernanceError):
        parse_policy((text + text[text.index("[[targets]]") :]).encode())
    with pytest.raises(GovernanceError):
        parse_policy((text + waiver("0" * 64) + waiver("0" * 64, identifier="WAIVER-2")).encode())
    with pytest.raises(GovernanceError):
        parse_policy((text + waiver("0" * 64) * 257).encode())
    with pytest.raises(GovernanceError):
        parse_policy(b"#" * (256 * 1024 + 1))
    with pytest.raises(GovernanceError):
        parse_policy(
            text.replace('owner = "team:platform"', 'owner = "' + "x" * 101 + '"').encode()
        )


def test_policy_and_baseline_symlink_stability(repo, monkeypatch):
    path = save_policy(repo, declaration(repo))
    link = path.with_name("link.toml")
    link.symlink_to(path)
    assert invoke(link).exit_code == 6
    parent = repo.parent / "linked"
    parent.symlink_to(repo.parent, target_is_directory=True)
    assert invoke(parent / path.name).exit_code == 6
    import context_integrity.governance_config as config

    monkeypatch.setattr(config, "read_source_bytes", lambda *a, **k: None)
    assert invoke(path).exit_code == 6


def test_json_text_parity_golden_and_output(repo, tmp_path):
    path = save_policy(repo, declaration(repo))
    result = invoke(path, "--format", "json")
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert render_report(report, as_json=True) == result.stdout
    text = invoke(path)
    assert json.loads(text.stdout[text.stdout.index("{") :]) == report
    assert invoke(path, "--format", "json").stdout == result.stdout
    output = tmp_path.resolve() / "report.json"
    saved = invoke(path, "--format", "json", "--output", str(output))
    assert saved.exit_code == 0 and not saved.stdout
    assert output.read_text() == result.stdout
    assert invoke(path, "--output", str(output)).exit_code == 4
    assert output.read_text() == result.stdout
    assert invoke(path, "--output", str(repo / "forbidden.json")).exit_code == 4
    assert not (repo / "forbidden.json").exists()
    assert not list(tmp_path.glob(".derived-*"))


def test_bounded_report_no_partial_output(repo, monkeypatch, tmp_path):
    import context_integrity.governance_output as output

    path = save_policy(repo, declaration(repo))
    monkeypatch.setattr(output, "MAX_REPORT_BYTES", 10)
    result = invoke(path, "--format", "json", "--output", str(tmp_path / "new.json"))
    assert result.exit_code == 6 and not result.stdout
    assert not (tmp_path / "new.json").exists()


def test_compare_metrics_scope_and_never_suppresses(repo, tmp_path):
    (repo / "CLAUDE.md").write_text("no pointer")
    text = declaration(repo)
    path = save_policy(repo, text)
    original = json.loads(invoke(path, "--format", "json").stdout)
    baseline = tmp_path / "prior.json"
    baseline.write_text(canonical_json(original))
    compared = invoke(path, "--format", "json", "--compare-to", str(baseline))
    assert compared.exit_code == 8
    report = json.loads(compared.stdout)
    assert report["comparison"]["status"] == "comparable"
    assert report["comparison"]["metric_deltas"]["blocking"] == 0
    assert len(report["comparison"]["persisting"]) == 1
    (repo / "CLAUDE.md").write_text("AGENTS.md")
    current = run_policy(repo, text)
    comparison = compare(current, original)
    assert comparison["metric_deltas"]["blocking"] == -1
    assert len(comparison["removed"]) == 1
    for field in ("id", "sha256"):
        changed = copy.deepcopy(original)
        changed["policy"][field] = "other" if field == "id" else "0" * 64
        assert compare(current, changed)["status"] == "incomparable"
    changed = copy.deepcopy(original)
    changed["evaluation"]["subjects"][0]["repositories"][0]["repository_id"] = "repo_" + "0" * 32
    assert compare(current, changed)["status"] == "incomparable"
    assert compare(current, {"governance_report_schema_version": 3})["status"] == "incomparable"
    baseline.write_text(canonical_json(report))
    assert load_baseline(baseline) == report


def test_compare_requires_same_git_base_but_allows_target_progression(repo, git, tmp_path):
    (repo / ".context-integrity.toml").write_text("""schema_version=4
[[drift_dependencies]]
id="architecture"
dependent="docs/architecture.md"
upstream=["src/app.py"]
reason="Review changed application"
""")
    (repo / "src").mkdir()
    (repo / "src/app.py").write_text("before")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "A")
    revision_a = git(repo, "rev-parse", "HEAD")
    (repo / "src/app.py").write_text("after")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "B")
    git(repo, "commit", "--allow-empty", "-qm", "C")
    revision_c = git(repo, "rev-parse", "HEAD")
    path = save_policy(repo, declaration(repo))

    first = invoke(path, "--diff", f"app={revision_a}..HEAD", "--format", "json")
    assert first.exit_code == 8
    first_report = json.loads(first.stdout)
    baseline = tmp_path / "prior.json"
    baseline.write_text(first.stdout)

    working_tree = invoke(path, "--format", "json")
    assert working_tree.exit_code == 0
    assert (
        "target_repository_scope_changed"
        in compare(first_report, json.loads(working_tree.stdout))["reasons"]
    )

    git(repo, "branch", "base-a", revision_a)
    same_commit_ref = invoke(
        path,
        "--diff",
        "app=base-a..HEAD",
        "--format",
        "json",
        "--compare-to",
        str(baseline),
    )
    assert same_commit_ref.exit_code == 8
    assert json.loads(same_commit_ref.stdout)["comparison"]["status"] == "comparable"

    changed_base = invoke(
        path,
        "--diff",
        f"app={revision_c}..HEAD",
        "--format",
        "json",
        "--compare-to",
        str(baseline),
    )
    assert changed_base.exit_code == 0, changed_base.output
    changed_base_report = json.loads(changed_base.stdout)
    assert changed_base_report["comparison"] == {
        "status": "incomparable",
        "reasons": ["diff_base_changed"],
    }
    assert changed_base_report["gate"]["exit_code"] == 0

    (repo / "unrelated.txt").write_text("D")
    git(repo, "add", "unrelated.txt")
    git(repo, "commit", "-qm", "D")
    progressed = invoke(
        path,
        "--diff",
        f"app={revision_a}..HEAD",
        "--format",
        "json",
        "--compare-to",
        str(baseline),
    )
    assert progressed.exit_code == 8
    assert json.loads(progressed.stdout)["comparison"]["status"] == "comparable"


def test_compare_marks_provider_contract_and_coverage_changes(repo):
    report = run_policy(repo, declaration(repo))
    provider = {
        "id": "fixture",
        "version": "1.0",
        "contract_version": 1,
        "capabilities": ["relations"],
        "derivation": "fixture-v1",
        "coverage_incomplete": False,
        "coverage_signals": {"parsed_files": 1},
        "warning_categories": [],
    }
    prior = copy.deepcopy(report)
    current = copy.deepcopy(report)
    prior["evaluation"]["subjects"][0]["scope"]["architecture"]["provider"] = provider
    changed = copy.deepcopy(provider) | {"version": "2.0"}
    current["evaluation"]["subjects"][0]["scope"]["architecture"]["provider"] = changed
    assert "provider_contract_changed" in compare(current, prior)["reasons"]

    current["evaluation"]["subjects"][0]["scope"]["architecture"]["provider"] = provider
    changed_coverage = copy.deepcopy(provider) | {
        "coverage_incomplete": True,
        "coverage_signals": {"parsed_files": 0, "unavailable_files": 1},
        "warning_categories": ["source_unavailable"],
    }
    current["evaluation"]["subjects"][0]["scope"]["architecture"]["provider"] = changed_coverage
    assert "provider_coverage_changed" in compare(current, prior)["reasons"]


def test_compare_marks_repository_evaluation_config_change(repo):
    baseline = run_policy(repo, declaration(repo))
    (repo / ".context-integrity.toml").write_text("schema_version=4\n")
    current = run_policy(repo, declaration(repo))
    assert "evaluation_config_changed" in compare(current, baseline)["reasons"]


@pytest.mark.parametrize(
    "data",
    [
        b"{}",
        b"[]",
        b"bad",
        b'{"x":1,"x":2}',
        b'{"governance_report_schema_version":true}',
        b'{"governance_report_schema_version":NaN}',
    ],
)
def test_invalid_baselines(repo, data, tmp_path):
    path = save_policy(repo, declaration(repo))
    baseline = tmp_path / "invalid.json"
    baseline.write_bytes(data)
    result = invoke(path, "--compare-to", str(baseline))
    assert result.exit_code == 6 and not result.stdout


def test_baseline_strict_types_metrics_and_extras(repo, tmp_path):
    report = run_policy(repo, declaration(repo))
    baseline = tmp_path / "baseline.json"
    for mutation in ("metrics", "extra", "path", "bool"):
        raw = copy.deepcopy(report)
        if mutation == "metrics":
            raw["metrics"]["findings"] = 100
        elif mutation == "extra":
            raw["secret"] = "PRIVATE"
        elif mutation == "path":
            raw["observations"][0]["entity"] = "/private/root"
        else:
            raw["metrics"]["targets_requested"] = True
        baseline.write_text(canonical_json(raw))
        with pytest.raises(GovernanceError):
            load_baseline(baseline)
    baseline.write_bytes(b" " * (8 * 1024 * 1024 + 1))
    with pytest.raises(GovernanceError):
        load_baseline(baseline)


@pytest.mark.parametrize(
    "args",
    [
        ["--as-of", "bad"],
        ["--diff", "app=HEAD...HEAD"],
        ["--diff", "no=HEAD..HEAD"],
        ["--diff", "app=HEAD..HEAD", "--diff", "app=HEAD..HEAD"],
        ["--format", "xml"],
        ["--evidence-provider", "other"],
        ["--context-engine-bin", "ctx"],
    ],
)
def test_cli_usage(repo, args):
    assert invoke(save_policy(repo, declaration(repo)), *args).exit_code == 2


def test_real_pr_range_dirty_and_help(repo, git):
    (repo / ".context-integrity.toml").write_text("""schema_version=4
[[drift_dependencies]]
id="architecture"
dependent="docs/architecture.md"
upstream=["src/app.py"]
reason="Review changed application"
""")
    (repo / "src").mkdir()
    (repo / "src/app.py").write_text("before")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "before")
    base = git(repo, "rev-parse", "HEAD")
    (repo / "src/app.py").write_text("after")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "after")
    path = save_policy(repo, declaration(repo))
    result = invoke(path, "--diff", f"app={base}..HEAD", "--format", "json")
    assert result.exit_code == 8, result.output
    report = json.loads(result.stdout)
    assert report["evaluation"]["subjects"][0]["scope"]["change_scope"] == "git_range"
    assert any(o["code"] == "document_dependency_changed" for o in findings(report))
    (repo / "src/app.py").write_text("dirty")
    dirty = json.loads(invoke(path, "--format", "json").stdout)
    assert dirty["evaluation"]["subjects"][0]["repositories"][0]["git_dirty"]
    assert invoke(path, "--help").exit_code == 0


def test_governance_diff_must_match_clean_checkout_head(repo, git, tmp_path):
    (repo / ".context-integrity.toml").write_text("""schema_version=4
[[drift_dependencies]]
id="architecture"
dependent="docs/architecture.md"
upstream=["src/app.py"]
reason="Review changed application"
""")
    (repo / "src").mkdir()
    (repo / "src/app.py").write_text("before")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "A")
    revision_a = git(repo, "rev-parse", "HEAD")
    (repo / "src/app.py").write_text("after")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "B")
    revision_b = git(repo, "rev-parse", "HEAD")
    path = None
    for incomplete in ("warn", "fail"):
        path = save_policy(repo, declaration(repo, incomplete=incomplete))
        for endpoint in (f"{revision_a}..{revision_a}", f"{revision_a}..{revision_a[:12]}"):
            result = invoke(path, "--diff", f"app={endpoint}", "--format", "json")
            assert result.exit_code == 6
            assert result.stdout == ""
            assert "governance_diff_scope_invalid" in result.stderr

    valid = invoke(path, "--diff", f"app={revision_a}..HEAD", "--format", "json")
    assert valid.exit_code == 8, valid.output
    assert any(
        o["code"] == "document_dependency_changed" for o in findings(json.loads(valid.stdout))
    )

    detached = git(repo, "checkout", "--detach", revision_b)
    assert detached == ""
    by_sha = invoke(path, "--diff", f"app={revision_a}..{revision_b}", "--format", "json")
    assert by_sha.exit_code == 8, by_sha.output

    output = tmp_path / "must-not-exist.json"
    stale = invoke(
        path,
        "--diff",
        f"app={revision_a}..{revision_a}",
        "--format",
        "json",
        "--output",
        str(output),
    )
    assert stale.exit_code == 6 and not output.exists()

    (repo / "untracked.txt").write_text("dirty")
    dirty = invoke(path, "--diff", f"app={revision_a}..HEAD", "--format", "json")
    assert dirty.exit_code == 6 and dirty.stdout == ""
    (repo / "untracked.txt").unlink()
    (repo / "src/app.py").write_text("dirty tracked bytes")
    path = save_policy(repo, declaration(repo, incomplete="fail"))
    dirty = invoke(path, "--diff", f"app={revision_a}..HEAD", "--format", "json")
    assert dirty.exit_code == 6 and dirty.stdout == ""


def test_governance_diff_missing_and_advanced_target_fail_closed(repo, git):
    path = save_policy(repo, declaration(repo, incomplete="warn"))
    head_b = git(repo, "rev-parse", "HEAD")
    missing = invoke(path, "--diff", "app=missing-base..HEAD", "--format", "json")
    assert missing.exit_code == 6 and missing.stdout == ""

    (repo / "unrelated.txt").write_text("later commit")
    git(repo, "add", "unrelated.txt")
    git(repo, "commit", "-qm", "C")
    advanced = invoke(path, "--diff", f"app={head_b}..{head_b}", "--format", "json")
    assert advanced.exit_code == 6 and advanced.stdout == ""


def test_governance_rechecks_all_diff_targets_before_report(repo, git, monkeypatch):
    import context_integrity.governance as governance

    app_head = git(repo, "rev-parse", "HEAD")
    other = repo.parent / "other"
    other.mkdir()
    git(other, "init", "--initial-branch=main", "--object-format=sha1")
    git(other, "config", "remote.origin.url", "git@example.invalid:team/other.git")
    (other / "AGENTS.md").write_text("Instructions\n")
    (other / "docs").mkdir()
    (other / "docs/architecture.md").write_text("Architecture\n")
    git(other, "add", ".")
    git(other, "commit", "-qm", "other")
    other_head = git(other, "rev-parse", "HEAD")
    text = declaration(repo, incomplete="warn") + (
        '\n[[targets]]\nid="second"\nkind="repository"\nroot="other"\n'
    )

    original = governance._evaluate

    def advance_first_repo(target, *args):
        subject = original(target, *args)
        if target.id == "app":
            (repo / "unrelated.txt").write_text("commit after first target evaluation")
            git(repo, "add", "unrelated.txt")
            git(repo, "commit", "-qm", "advance after first target")
        return subject

    monkeypatch.setattr(governance, "_evaluate", advance_first_repo)
    with pytest.raises(GovernanceError, match="governance_diff_scope_invalid"):
        run_policy(
            repo,
            text,
            diffs={"app": f"{app_head}..{app_head}", "second": f"{other_head}..HEAD"},
        )


def test_required_architecture_absent_and_provider_failure(repo):
    path = save_policy(repo, declaration(repo, extra="require_architecture=true\n"))
    report = json.loads(invoke(path, "--format", "json").stdout)
    assert report["gate"]["exit_code"] == 9
    report = json.loads(
        invoke(
            path,
            "--format",
            "json",
            "--evidence-provider",
            "context-engine",
            "--context-engine-bin",
            "/no/such/ctx",
        ).stdout
    )
    assert report["gate"]["exit_code"] == 9
    assert any(o["code"] == "provider_evaluation_failed" for o in report["observations"])


def test_unknown_native_and_derived_codes_fail_closed(repo, monkeypatch):
    import context_integrity.governance_adapters as adapters

    (repo / "CLAUDE.md").write_text("no pointer")
    monkeypatch.setattr(adapters, "NATIVE_CODES", {})
    report = run_policy(repo, declaration(repo))
    assert report["gate"]["exit_code"] == 9
    make_receipt(repo)
    monkeypatch.setattr(adapters, "DERIVED_EFFECTS", {})
    report = run_policy(
        repo,
        declaration(repo, kind="derived", extra='receipt="receipt.json"\nreview_severity="high"\n'),
    )
    assert report["gate"]["exit_code"] == 9


def test_normalization_work_bound(repo, monkeypatch):
    import context_integrity.governance_adapters as adapters

    monkeypatch.setattr(adapters, "MAX_OBSERVATIONS", 0)
    result = invoke(save_policy(repo, declaration(repo)), "--format", "json")
    assert result.exit_code == 6 and not result.stdout


def test_leap_day_valid(repo):
    policy = parse_policy((declaration(repo) + waiver("0" * 64, expiration="2028-02-29")).encode())
    assert policy.waivers[0].expires_on == date(2028, 2, 29)


def test_input_binding_and_output_symlink(repo, tmp_path):
    wrong = declaration(repo, extra='repository_id="repo_' + "0" * 32 + '"\n')
    assert run_policy(repo, wrong)["gate"]["exit_code"] == 9
    path = save_policy(repo, declaration(repo))
    destination = tmp_path / "symlink.json"
    destination.symlink_to(repo / "AGENTS.md")
    assert invoke(path, "--output", str(destination)).exit_code == 4
    assert (repo / "AGENTS.md").read_text() == "Instructions\n"


def test_phase10_report_amplification_regression(ws):
    from context_integrity.workspace import resolve_workspace
    from context_integrity.workspace_output import (
        WorkspaceOutputError,
        check_dict,
        render_workspace,
    )

    repos, manifest, header, _ = ws
    for root in repos:
        config = root / ".context-integrity.toml"
        config.write_text(config.read_text().replace("PRIVATE_CLAIM_LITERAL", "x" * 100000))
    checks = "".join(
        f"""[[checks]]
id="claims-{i}"
kind="claim_match"
left_repo="api"
left_claim_id="region"
right_repo="web"
right_claim_id="region"
"""
        for i in range(64)
    )
    manifest.write_text(header + checks)
    workspace = resolve_workspace(manifest)
    value = check_dict(workspace, workspace.check())
    with pytest.raises(WorkspaceOutputError, match="workspace_report_limit_exceeded"):
        render_workspace(value, as_json=True)
    # The governance adapter never materializes the verbose claim-value projection.
    report = run_ws(ws)
    assert report["gate"]["exit_code"] == 0
    assert len(render_report(report, as_json=True)) < 256 * 1024


def test_phase10_warning_isolation_regression(ws):
    from context_integrity.workspace import resolve_workspace

    _, manifest, _, _ = ws
    workspace = resolve_workspace(manifest)
    observed, _ = workspace.observe("api", "missing.json")
    assert observed.state == "missing"
    claim = next(f for f in workspace.check() if f.id == "claim")
    assert claim.signal == "aligned"
    assert not workspace.contexts["api"].warnings
    assert not workspace.inventories["api"].warnings


def test_derived_upstream_uncertainty_and_definite_change(repo):
    parent = make_receipt(repo)
    (repo / "docs/child.md").write_text("derived child")
    context = discover_repository(repo)
    child = capture_receipt(
        context,
        inventory_repository(context),
        "docs/child.md",
        artifact_id="child",
        kind="summary",
        derivation=Derivation("manual", "test"),
        depends_on=(),
        upstream_receipts=("receipt.json",),
        receipt_path="child.json",
    )
    (repo / "child.json").write_text(render_receipt(child))
    # Same pinned upstream bytes, but unobservable upstream dependency.
    (repo / "AGENTS.md").unlink()
    (repo / "AGENTS.md").symlink_to(repo / "docs/architecture.md")
    text = declaration(repo, kind="derived", extra='receipt="child.json"\nreview_severity="high"\n')
    report = run_policy(repo, text)
    assert report["gate"]["exit_code"] == 9
    assert any(o["code"] == "upstream_inconclusive" for o in report["observations"])
    (repo / "AGENTS.md").unlink()
    (repo / "AGENTS.md").write_text("changed original")
    report = run_policy(repo, text)
    assert report["gate"]["exit_code"] == 8
    assert any(o["code"] == "upstream_review_required" for o in report["observations"])
    assert parent.artifact.id == "summary"


def test_ambiguous_observations_never_apply_waiver(repo, monkeypatch):
    import context_integrity.governance as governance

    (repo / "CLAUDE.md").write_text("no pointer")
    text = declaration(repo)
    fp = findings(run_policy(repo, text))[0]["fingerprint"]
    real = governance.repository_subject

    def duplicate(*args, **kwargs):
        subject = real(*args, **kwargs)
        finding = next(o for o in subject.observations if o.effect == "finding")
        return replace(subject, observations=(*subject.observations, finding))

    monkeypatch.setattr(governance, "repository_subject", duplicate)
    report = run_policy(repo, text + waiver(fp))
    assert report["waivers"][0]["status"] == "ambiguous"
    assert report["metrics"]["blocking"] == 2


@pytest.mark.parametrize(
    "incomplete,violation", [(False, True), (True, True), (True, False), (False, False)]
)
def test_typed_architecture_provider_preserves_coverage(
    repo, git, monkeypatch, incomplete, violation
):
    import context_integrity.governance as governance
    from context_integrity.governance_adapters import inventory
    from test_architecture import CONFIG, batch, relation

    (repo / ".context-integrity.toml").write_text(CONFIG)
    (repo / "src/application").mkdir(parents=True)
    (repo / "src/application/main.py").write_text("import storage")
    (repo / "src/storage.py").write_text("storage")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "architecture")
    manifest = inventory(discover_repository(repo))
    state = batch(manifest, (relation(),) if violation else (), incomplete=incomplete)
    observations = tuple(
        (p, sha256((repo / p).read_bytes()).hexdigest())
        for p in sorted(
            {"src/application/main.py", "src/storage.py"}
            if violation
            else {"src/application/main.py"}
        )
    )
    state = replace(state, state=replace(state.state, observed_content=observations))

    class Provider:
        def relations(self, request):
            assert request.repository.id == manifest.repository.id
            return state

    monkeypatch.setattr(governance, "local_provider", lambda _: Provider())
    report = run_policy(
        repo, declaration(repo, extra="require_architecture=true\n"), evidence_provider=True
    )
    assert report["gate"]["exit_code"] == (8 if violation else 9 if incomplete else 0)
    assert report["gate"]["has_incomplete_coverage"] == incomplete
    provider = report["evaluation"]["subjects"][0]["scope"]["architecture"]["provider"]
    assert provider["id"] == "fixture" and provider["coverage_incomplete"] == incomplete
    assert render_report(report, as_json=True)
    if violation:
        assert findings(report)[0]["intrinsic_severity"] == "high"
        assert findings(report)[0]["fingerprint"]


def test_unknown_workspace_signal_and_integrity_schema(repo, ws, monkeypatch):
    import context_integrity.governance_adapters as adapters

    monkeypatch.setattr(adapters, "WORKSPACE_CODES", set())
    assert run_ws(ws)["gate"]["exit_code"] == 9
    real = adapters.integrity_overview
    monkeypatch.setattr(
        adapters, "integrity_overview", lambda *a, **kw: replace(real(*a, **kw), schema_version=99)
    )
    assert run_policy(repo, declaration(repo))["gate"]["exit_code"] == 9


def test_output_rollback_on_failed_link(repo, tmp_path, monkeypatch):
    import context_integrity.derived_output as publication

    def fail(*args, **kwargs):
        raise OSError("PRIVATE_OS_ERROR")

    monkeypatch.setattr(publication.os, "link", fail)
    path = save_policy(repo, declaration(repo))
    destination = tmp_path / "failed.json"
    result = invoke(path, "--output", str(destination))
    assert result.exit_code == 4 and not result.stdout
    assert "PRIVATE_OS_ERROR" not in result.output
    assert not destination.exists()
    assert not list(tmp_path.glob(".derived-*"))


def test_offline_read_only(repo, monkeypatch):
    import socket

    def forbidden(*args, **kwargs):
        raise AssertionError("Network forbidden")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    path = save_policy(repo, declaration(repo))
    before = {p.relative_to(repo): p.read_bytes() for p in repo.rglob("*") if p.is_file()}
    assert invoke(path).exit_code == 0
    after = {p.relative_to(repo): p.read_bytes() for p in repo.rglob("*") if p.is_file()}
    assert before == after


def test_golden_report(repo):
    from pathlib import Path

    report = run_policy(repo, declaration(repo))
    expected = Path(__file__).parent / "fixtures/governance-report-v2.json"
    assert render_report(report, as_json=True) == expected.read_text()
    validate_report(report)


def test_v1_report_baseline_is_incomparable_not_enforced(repo, tmp_path):
    from pathlib import Path

    report = run_policy(repo, declaration(repo))
    baseline = tmp_path / "prior-v1.json"
    baseline.write_text((Path(__file__).parent / "fixtures/governance-report-v1.json").read_text())
    previous = load_baseline(baseline)
    assert previous == {"governance_report_schema_version": 1}
    assert compare(report, previous) == {
        "status": "incomparable",
        "reasons": ["unsupported_schema"],
    }


def test_ci_recipe_preserves_exit_codes_and_emits_report(repo):
    import subprocess
    import sys

    def shell_run(path):
        return subprocess.run(
            [
                "bash",
                "-c",
                'set -e; "$@"; printf SHOULD_NOT_RUN',
                "governance-test",
                sys.executable,
                "-c",
                "from context_integrity.cli import app; app()",
                "governance",
                "check",
                str(path),
                "--format",
                "text",
                "--as-of",
                TODAY.isoformat(),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    allowed_path = save_policy(repo, declaration(repo))
    allowed = shell_run(allowed_path)
    assert allowed.returncode == 0
    assert "Governance: allow (exit 0)" in allowed.stdout
    assert "SHOULD_NOT_RUN" in allowed.stdout

    (repo / "CLAUDE.md").write_text("no pointer")
    blocker_path = save_policy(repo, declaration(repo))
    blocker = shell_run(blocker_path)
    assert blocker.returncode == 8
    assert "SHOULD_NOT_RUN" not in blocker.stdout
    assert "Governance: fail (exit 8)" in blocker.stdout
    assert '"has_blocking_findings": true' in blocker.stdout
    assert '"code": "instruction_reference_missing"' in blocker.stdout

    incomplete_path = save_policy(
        repo,
        declaration(repo) + '\n[[targets]]\nid="missing"\nkind="repository"\nroot="absent"\n',
    )
    incomplete = shell_run(incomplete_path)
    assert incomplete.returncode == 8  # A definite blocker still takes precedence over coverage.
    assert "Governance: fail (exit 8)" in incomplete.stdout
    assert '"has_incomplete_coverage": true' in incomplete.stdout

    # A clean repository with a missing target and no blocker exercises exit 9.
    (repo / "CLAUDE.md").unlink()
    incomplete_only = save_policy(
        repo,
        declaration(repo, incomplete="fail").replace('root = "basic-context"', 'root = "."')
        + '\n[[targets]]\nid="missing"\nkind="repository"\nroot="absent"\n',
    )
    result9 = shell_run(incomplete_only)
    assert result9.returncode == 9
    assert "SHOULD_NOT_RUN" not in result9.stdout
    assert "Governance: inconclusive (exit 9)" in result9.stdout
    assert '"has_incomplete_coverage": true' in result9.stdout


def test_unstable_receipt_read_is_uncertainty(repo, monkeypatch):
    import os

    from context_integrity.derived import Reader

    make_receipt(repo)
    context = discover_repository(repo)
    original = os.read
    changed = False

    def changing(fd, count):
        nonlocal changed
        data = original(fd, count)
        if data and not changed:
            changed = True
            (repo / "receipt.json").write_text("mutated while reading")
        return data

    monkeypatch.setattr("context_integrity.acquisition.os.read", changing)
    observation, data = Reader(context, require_stable=True).read("receipt.json", 1024 * 1024)
    assert observation.state == "unobservable" and data is None
    assert any(w.code == "source_changed_during_read" for w in context.warnings)


def test_same_origin_checkout_collision(ws, git):
    repos, _, _, _ = ws
    git(repos[1], "remote", "set-url", "origin", "https://example.invalid/repo-0.git")
    text = declaration(repos[0]) + '\n[[targets]]\nid="clone"\nkind="repository"\nroot="web"\n'
    result = invoke(save_policy(repos[0], text))
    assert result.exit_code == 6 and not result.stdout
    assert "repository_identity_collision" in result.output


def test_baseline_cannot_change_observed_fingerprint_or_waiver(repo, tmp_path):
    (repo / "CLAUDE.md").write_text("no pointer")
    report = run_policy(repo, declaration(repo))
    baseline = tmp_path / "forged.json"
    for field, value in (("fingerprint", "0" * 64), ("waiver_id", "FAKE")):
        previous = copy.deepcopy(report)
        finding = findings(previous)[0]
        finding[field] = value
        baseline.write_text(canonical_json(previous))
        with pytest.raises(GovernanceError):
            load_baseline(baseline)


def test_ignored_config_cannot_flip_committed_gate(repo, git):
    import subprocess
    import sys

    (repo / "CLAUDE.md").write_text("See AGENTS.md\n")
    (repo / ".gitignore").write_text(".context-integrity.toml\n")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "ignore local policy")
    path = save_policy(repo, declaration(repo))
    config = repo / ".context-integrity.toml"
    for canonical, ordinary_exit in (("AGENTS.md", 0), ("GEMINI.md", 8)):
        config.write_text(
            f'schema_version=4\n[instruction_policy]\ncanonical="{canonical}"\n'
            'compatibility=["CLAUDE.md"]\n'
        )
        assert git(repo, "status", "--porcelain") == ""
        args = [
            sys.executable,
            "-c",
            "from context_integrity.cli import app; app()",
            "governance",
            "check",
            str(path),
        ]
        live = subprocess.run([*args, "--format", "json"], capture_output=True, timeout=10)
        assert live.returncode == ordinary_exit, live.stderr
        output = repo.parent / f"rejected-{canonical}.json"
        strict = subprocess.run(
            [*args, "--diff", "app=HEAD..HEAD", "--format", "json", "--output", str(output)],
            capture_output=True,
            timeout=10,
        )
        assert strict.returncode == 6, strict.stdout
        assert strict.stdout == b"" and not output.exists()
        assert b"governance_diff_scope_invalid" in strict.stderr
    config.unlink()
    assert invoke(path, "--diff", "app=HEAD..HEAD", "--format", "json").exit_code == 0


@pytest.mark.parametrize(
    "state",
    ["clean", "staged", "unstaged", "removed", "symlink", "assume_unchanged", "skip_worktree"],
)
def test_strict_committed_config_controls(repo, git, state):
    config = repo / ".context-integrity.toml"
    config.write_text("schema_version=4\n")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "tracked config")
    if state in {"assume_unchanged", "skip_worktree"}:
        git(repo, "update-index", "--" + state.replace("_", "-"), ".context-integrity.toml")
    if state in {"staged", "unstaged", "assume_unchanged", "skip_worktree"}:
        config.write_text("schema_version=4\n# changed\n")
    if state == "staged":
        git(repo, "add", ".context-integrity.toml")
    if state in {"removed", "symlink"}:
        config.unlink()
    if state == "symlink":
        config.symlink_to("AGENTS.md")
    path = save_policy(repo, declaration(repo, incomplete="warn"))
    result = invoke(path, "--diff", "app=HEAD..HEAD", "--format", "json")
    assert result.exit_code == (0 if state == "clean" else 6), result.output
    if state != "clean":
        assert result.stdout == ""


@pytest.mark.parametrize("mutation", ["create", "remove", "replace", "source"])
def test_strict_final_input_recheck(repo, git, monkeypatch, mutation):
    import context_integrity.governance as governance

    config = repo / ".context-integrity.toml"
    (repo / ".gitignore").write_text(".context-integrity.toml\n")
    if mutation in {"remove", "replace"}:
        config.write_text("schema_version=4\n")
        git(repo, "add", "-f", ".context-integrity.toml")
        # Hide tracked changes from ordinary porcelain to exercise byte binding.
        git(repo, "update-index", "--assume-unchanged", ".context-integrity.toml")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "final recheck fixture")
    if mutation == "source":
        git(repo, "update-index", "--assume-unchanged", "AGENTS.md")
    path = save_policy(repo, declaration(repo))
    original = governance._evaluate

    def mutate(*args):
        subject = original(*args)
        if mutation == "remove":
            config.unlink()
        elif mutation == "replace":
            config.unlink()
            config.symlink_to("AGENTS.md")
        elif mutation == "source":
            (repo / "AGENTS.md").write_text("hidden changed input")
        else:
            config.write_text("schema_version=4\n")
        return subject

    monkeypatch.setattr(governance, "_evaluate", mutate)
    output = repo.parent / "no-partial.json"
    result = invoke(path, "--diff", "app=HEAD..HEAD", "--format", "json", "--output", str(output))
    assert result.exit_code == 6 and result.stdout == "" and not output.exists(), result.output
    assert "governance_diff_scope_invalid" in result.stderr


def test_ignored_config_removed_before_strict_evaluation_is_absent(repo, git):
    config = repo / ".context-integrity.toml"
    (repo / ".gitignore").write_text(".context-integrity.toml\n")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "ignored config absent from commit")
    config.write_text("schema_version=4\n")
    config.unlink()
    path = save_policy(repo, declaration(repo))
    assert invoke(path, "--diff", "app=HEAD..HEAD", "--format", "json").exit_code == 0


def test_provider_mutation_of_ignored_config_rejects_subprocess_report(repo, git):
    import subprocess
    import sys

    from context_integrity.relations import EvidenceRelationRequest
    from test_context_engine import fake_executable
    from test_graph_adapter import graph

    (repo / ".gitignore").write_text(".context-integrity.toml\n")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "provider mutation fixture")
    payload = graph(EvidenceRelationRequest(repo, discover_repository(repo).repository))
    script = (
        "import sys\nfrom pathlib import Path\n"
        "if sys.argv[1:] == ['--version']:\n print('ctx 0.1.0')\n"
        "else:\n"
        f" Path({str(repo / '.context-integrity.toml')!r}).write_text('schema_version=4\\n')\n"
        f" print({json.dumps(payload)!r})\n"
    )
    binary = fake_executable(repo.parent, script=script)
    path = save_policy(repo, declaration(repo, incomplete="warn"))
    output = repo.parent / "mutated-report.json"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from context_integrity.cli import app; app()",
            "governance",
            "check",
            str(path),
            "--diff",
            "app=HEAD..HEAD",
            "--evidence-provider",
            "context-engine",
            "--context-engine-bin",
            binary,
            "--format",
            "json",
            "--output",
            str(output),
        ],
        capture_output=True,
        timeout=15,
    )
    assert result.returncode == 6 and not result.stdout and not output.exists(), result.stderr
    assert b"governance_diff_scope_invalid" in result.stderr
    assert git(repo, "status", "--porcelain") == ""
