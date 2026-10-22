"""CLI journeys, provider seam and output publication failure tests."""

import json
import os
from dataclasses import replace
from hashlib import sha256

import pytest
from typer.testing import CliRunner

from context_integrity.cli import app
from context_integrity.compiler import compile_context
from context_integrity.contracts import resolve_contract
from context_integrity.derived import (
    check_receipt,
    compiler_implementation_identity,
    compiler_receipt,
)
from context_integrity.derived_models import parse_receipt, render_receipt
from context_integrity.derived_output import DerivedOutputError, write_outputs
from context_integrity.evidence import EvidenceContextRequest
from context_integrity.inventory import inventory_repository
from context_integrity.rendering import render_compiled_context_json
from context_integrity.repository import discover_repository
from test_context_engine import BODY, normalize, response

runner = CliRunner()
CONFIG = """schema_version = 8
[[context_contracts]]
id = "work"
task_class = "implementation"
description = "Instructions and code"
[[context_contracts.rules]]
id = "instructions"
mode = "required"
paths = ["AGENTS.md"]
authority_policy = "operating_instructions"
[[context_contracts.rules]]
id = "code"
mode = "optional"
kinds = ["source_code"]
"""


def invoke_capture(root, *extra):
    if not (root / "docs/handoff.md").exists():
        (root / "docs/handoff.md").write_text("private summary body")
    return runner.invoke(
        app,
        [
            "derived",
            "capture",
            "docs/handoff.md",
            str(root),
            "--id",
            "handoff",
            "--kind",
            "handoff",
            "--derivation",
            "model",
            "--producer",
            "agent",
            "--depends-on",
            "AGENTS.md",
            "--receipt-output",
            "docs/handoff.receipt.json",
            *extra,
        ],
    )


def invoke_check(root, *extra):
    return runner.invoke(
        app,
        ["derived", "check", "docs/handoff.receipt.json", str(root), "--format", "json", *extra],
    )


def test_real_git_worktree_journey(git_repo, git, tmp_path):
    git(git_repo, "add", ".")
    git(git_repo, "commit", "-m", "initial")
    worktree = tmp_path / "linked"
    git(git_repo, "worktree", "add", "-b", "fixture", str(worktree))
    assert invoke_capture(worktree).exit_code == 0
    before = (worktree / "docs/handoff.receipt.json").read_bytes()
    initial = invoke_check(worktree)
    assert initial.exit_code == 0, initial.output
    assert json.loads(initial.stdout)["status"] == "unchanged_observed_inputs"
    head = git(worktree, "rev-parse", "HEAD")
    (worktree / "AGENTS.md").write_text("staged changed input")
    git(worktree, "add", "AGENTS.md")
    (worktree / "docs/architecture.md").write_text("unstaged unrelated input")
    result = invoke_check(worktree)
    assert result.exit_code == 0
    assert json.loads(result.stdout)["status"] == "review_required"
    assert git(worktree, "rev-parse", "HEAD") == head
    assert (worktree / "docs/handoff.receipt.json").read_bytes() == before
    assert "private summary body" not in initial.output + result.output + before.decode()


@pytest.mark.parametrize(
    "args",
    [
        ("--depends-on", "../secret"),
        ("--depends-on", "/etc/passwd"),
        ("--depends-on", "docs/handoff.md"),
        ("--depends-on", "missing"),
        ("--depends-on", "docs/handoff.receipt.json"),
        ("--kind", "unknown"),
        ("--producer", "private prose"),
    ],
)
def test_invalid_capture_inputs(git_repo, args):
    result = invoke_capture(git_repo, *args)
    assert result.exit_code == 6, result.output
    assert not (git_repo / "docs/handoff.receipt.json").exists()
    assert "private prose" not in result.output


def test_symlink_ancestor_and_capture_size(git_repo, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "input.py").write_text("private outside bytes")
    (git_repo / "link").symlink_to(outside, target_is_directory=True)
    assert invoke_capture(git_repo, "--depends-on", "link/input.py").exit_code == 6
    (git_repo / "big.py").write_bytes(b"x" * (5 * 1024 * 1024 + 1))
    assert invoke_capture(git_repo, "--depends-on", "big.py").exit_code == 6
    (git_repo / "docs/handoff.md").write_bytes(b"x" * (5 * 1024 * 1024 + 1))
    assert invoke_capture(git_repo).exit_code == 6


def test_output_refusal_and_read_only(git_repo):
    assert invoke_capture(git_repo).exit_code == 0
    original = (git_repo / "docs/handoff.receipt.json").read_bytes()
    assert invoke_capture(git_repo).exit_code == 4
    assert invoke_check(git_repo, "--output", "AGENTS.md").exit_code == 4
    assert invoke_check(git_repo, "--output", "docs/handoff.receipt.json").exit_code == 4
    assert invoke_check(git_repo, "--output", "docs/report.json").exit_code == 0
    assert (git_repo / "docs/handoff.receipt.json").read_bytes() == original
    (git_repo / "docs/handoff.receipt.json").write_text('{"duplicate":1,"duplicate":2}')
    result = invoke_check(git_repo)
    assert result.exit_code == 6
    assert "duplicate" not in result.output
    assert invoke_check(git_repo / "missing").exit_code == 3


def compile_args(root):
    return [
        "compile",
        "work",
        str(root),
        "--format",
        "json",
        "--task",
        "PRIVATE TASK TEXT",
        "--output",
        "docs/compiled.json",
        "--receipt-output",
        "docs/compiled.receipt.json",
    ]


def test_compiler_v3_unchanged_and_receipt_context(git_repo, monkeypatch):
    (git_repo / ".context-integrity.toml").write_text(CONFIG)
    context = discover_repository(git_repo)
    manifest = inventory_repository(context)
    compiled = compile_context(
        manifest, resolve_contract(manifest.repository_config, "work"), task="PRIVATE TASK TEXT"
    )
    expected = render_compiled_context_json(compiled)
    result = runner.invoke(app, compile_args(git_repo))
    assert result.exit_code == 0, result.output
    assert (git_repo / "docs/compiled.json").read_text() == expected
    data = (git_repo / "docs/compiled.receipt.json").read_bytes()
    receipt = parse_receipt(data)
    assert receipt.derived_receipt_schema_version == 1
    assert receipt.artifact.content_sha256 == sha256(expected.encode()).hexdigest()
    assert receipt.compilation.task_sha256 == sha256(b"PRIVATE TASK TEXT").hexdigest()
    assert "+" in receipt.compilation.compiler_version
    assert receipt.compilation.contract_id == "work"
    assert receipt.config_sha256 == sha256(CONFIG.encode()).hexdigest()
    assert {p.path for p in receipt.dependencies} == {"AGENTS.md"}
    assert b"PRIVATE TASK TEXT" not in data
    checked, _ = check_receipt(discover_repository(git_repo), "docs/compiled.receipt.json")
    assert checked.status == "unchanged_observed_inputs"
    import context_integrity.derived as derived_module

    original_identity = derived_module.compiler_implementation_identity
    monkeypatch.setattr(
        derived_module,
        "compiler_implementation_identity",
        lambda: original_identity()[:-1] + ("0" if not original_identity().endswith("0") else "1"),
    )
    checked, _ = check_receipt(discover_repository(git_repo), "docs/compiled.receipt.json")
    assert checked.status == "review_required"
    assert "compiler_implementation_changed" in {r.code for r in checked.reasons}
    monkeypatch.setattr(derived_module, "compiler_implementation_identity", original_identity)
    (git_repo / "docs/new.md").write_text("newly eligible input")
    checked, _ = check_receipt(discover_repository(git_repo), "docs/compiled.receipt.json")
    assert checked.status == "review_required"
    assert "selection_context_changed" in {r.code for r in checked.reasons}


def test_empty_complete_compiler_selection_is_not_provenance_incomplete(git_repo):
    empty_config = """schema_version = 8
[[context_contracts]]
id = "work"
task_class = "implementation"
description = "Optional absent source"
[[context_contracts.rules]]
id = "optional"
mode = "optional"
paths = ["docs/no-match.md"]
"""
    (git_repo / ".context-integrity.toml").write_text(empty_config)
    result = runner.invoke(app, compile_args(git_repo))
    assert result.exit_code == 0, result.output
    receipt = parse_receipt((git_repo / "docs/compiled.receipt.json").read_bytes())
    assert receipt.dependencies == ()
    assert receipt.compilation.status == "complete"
    checked, _ = check_receipt(discover_repository(git_repo), "docs/compiled.receipt.json")
    assert checked.status == "unchanged_observed_inputs"
    assert "provenance_incomplete" not in {r.code for r in checked.reasons}


def test_compiler_implementation_identity_tracks_source_bytes(tmp_path):
    package = tmp_path / "package"
    package.mkdir()
    source = package / "compiler.py"
    source.write_text("return ['a']\n")
    first = compiler_implementation_identity(package)
    assert first is not None
    assert compiler_implementation_identity(package) == first
    source.write_text("return ['b']\n")
    assert compiler_implementation_identity(package) != first


@pytest.mark.parametrize("incomplete", [False, True])
def test_provider_selections_and_uncertainty(git_repo, incomplete):
    (git_repo / ".context-integrity.toml").write_text(CONFIG)
    (git_repo / "src").mkdir()
    (git_repo / "src/sample.py").write_text(BODY)
    context = discover_repository(git_repo)
    manifest = inventory_repository(context)
    request = EvidenceContextRequest(context.root, manifest.repository, "PRIVATE TASK TEXT", 4096)
    payload = response(request)
    payload["data"]["repository"]["coverage"]["analysis_incomplete"] = incomplete
    batch = normalize(payload, request)
    compiled = compile_context(
        manifest,
        resolve_contract(manifest.repository_config, "work"),
        task=request.task,
        evidence=batch,
    )
    # Baseline already adapts provider selections to SourceRecords; preserve that behavior.
    assert {d.path for d in compiled.dependencies} == {"AGENTS.md", "src/sample.py"}
    rendered = render_compiled_context_json(compiled).encode()
    receipt = compiler_receipt(context, manifest, compiled, "docs/compiled.json", rendered)
    assert {p.path for p in receipt.dependencies} == {"AGENTS.md", "src/sample.py"}
    assert receipt.provider_context[0].id == "context-engine"
    assert receipt.provider_context[0].incomplete is incomplete
    pin = next(p for p in receipt.dependencies if p.path == "src/sample.py")
    assert pin.observation_basis == "provider"
    assert pin.derivation and pin.provider_version == "0.1.0"
    (git_repo / "docs/compiled.json").write_bytes(rendered)
    data = render_receipt(receipt)
    assert "PRIVATE TASK TEXT" not in data and "private body" not in data
    (git_repo / "docs/compiled.receipt.json").write_text(data)
    result, _ = check_receipt(discover_repository(git_repo), "docs/compiled.receipt.json")
    assert result.status == "inconclusive"
    assert "provider_not_revalidated" in {r.code for r in result.reasons}
    (git_repo / "src/sample.py").write_text("changed")
    result, _ = check_receipt(discover_repository(git_repo), "docs/compiled.receipt.json")
    assert result.status == "review_required"
    assert {"source_changed", "provider_not_revalidated"} <= {r.code for r in result.reasons}
    with pytest.raises(ValueError):
        compiler_receipt(context, manifest, compiled, "docs/another.json", rendered)


def test_compiler_receipt_flag_constraints(git_repo):
    (git_repo / ".context-integrity.toml").write_text(CONFIG)
    for extra in (
        ["--receipt-output", "receipt.json"],
        ["--receipt-output", "receipt.json", "--output", "artifact.json"],
    ):
        result = runner.invoke(app, ["compile", "work", str(git_repo), *extra])
        assert result.exit_code == 2
    args = compile_args(git_repo)
    args[args.index("docs/compiled.json")] = "docs/compiled.md"
    assert runner.invoke(app, args).exit_code == 4
    assert not (git_repo / "docs/compiled.md").exists()


@pytest.mark.parametrize(
    "failure",
    [
        "existing_first",
        "existing_second",
        "same_path",
        "missing_parent",
        "symlink_parent",
        "publish_second",
        "write_second",
    ],
)
def test_pair_failures_do_not_leave_half_success(git_repo, monkeypatch, failure):
    (git_repo / ".context-integrity.toml").write_text(CONFIG)
    args = compile_args(git_repo)
    if failure == "existing_first":
        (git_repo / "docs/compiled.json").write_text("existing")
    elif failure == "existing_second":
        (git_repo / "docs/compiled.receipt.json").write_text("existing")
    elif failure == "same_path":
        args[-1] = "docs/compiled.json"
    elif failure == "missing_parent":
        args[-1] = "missing/receipt.json"
    elif failure == "symlink_parent":
        (git_repo / "link").symlink_to(git_repo / "docs", target_is_directory=True)
        args[-1] = "link/receipt.json"
    elif failure == "publish_second":
        original = os.link
        calls = 0

        def link(*a, **kw):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("PRIVATE STDERR")
            return original(*a, **kw)

        monkeypatch.setattr(os, "link", link)
    else:
        original = os.fsync
        calls = 0

        def fsync(fd):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("PRIVATE STDERR")
            return original(fd)

        monkeypatch.setattr(os, "fsync", fsync)
    result = runner.invoke(app, args)
    assert result.exit_code == 4, result.output
    assert "PRIVATE STDERR" not in result.output
    assert (git_repo / "docs/compiled.json").exists() is (failure == "existing_first")
    assert (git_repo / "docs/compiled.receipt.json").exists() is (failure == "existing_second")
    assert not list((git_repo / "docs").glob(".derived-*"))


def test_output_destination_bounds(git_repo, tmp_path):
    assert (
        invoke_capture(git_repo, "--receipt-output", str(tmp_path / "outside.json")).exit_code == 4
    )
    assert not (tmp_path / "outside.json").exists()
    with pytest.raises(DerivedOutputError):
        write_outputs(git_repo, (("AGENTS.md", b"overwritten"),), forbidden={"AGENTS.md"})
    assert (git_repo / "AGENTS.md").read_bytes() == b"Instructions\n"


def test_upstream_cli_journey(git_repo):
    assert invoke_capture(git_repo).exit_code == 0
    (git_repo / "docs/child.md").write_text("child")
    result = runner.invoke(
        app,
        [
            "derived",
            "capture",
            "docs/child.md",
            str(git_repo),
            "--id",
            "child",
            "--upstream-receipt",
            "docs/handoff.receipt.json",
            "--receipt-output",
            "docs/child.receipt.json",
        ],
    )
    assert result.exit_code == 0, result.output
    (git_repo / "AGENTS.md").write_text("changed original")
    result = runner.invoke(app, ["derived", "check", "docs/child.receipt.json", str(git_repo)])
    assert result.exit_code == 0
    assert "review_required" in result.output
    assert "upstream_review_required" in result.output


def test_incomplete_compile_cannot_look_unchanged(git_repo):
    (git_repo / ".context-integrity.toml").write_text(
        CONFIG.replace('paths = ["AGENTS.md"]', 'paths = ["MISSING.md"]')
    )
    result = runner.invoke(app, compile_args(git_repo))
    assert result.exit_code == 0, result.output
    receipt = parse_receipt((git_repo / "docs/compiled.receipt.json").read_bytes())
    assert receipt.known_incomplete
    checked, _ = check_receipt(discover_repository(git_repo), "docs/compiled.receipt.json")
    assert checked.status == "inconclusive"


def test_upstream_output_cannot_be_an_indirect_input(git_repo):
    assert invoke_capture(git_repo).exit_code == 0
    (git_repo / "docs/child.md").write_text("child")
    args = [
        "derived",
        "capture",
        "docs/child.md",
        str(git_repo),
        "--id",
        "child",
        "--upstream-receipt",
        "docs/handoff.receipt.json",
        "--receipt-output",
        "AGENTS.md",
    ]
    assert runner.invoke(app, args).exit_code == 4
    assert (git_repo / "AGENTS.md").read_bytes() == b"Instructions\n"


def test_rollback_failure_is_explicit(git_repo, monkeypatch):
    original_link = os.link
    original_unlink = os.unlink
    calls = 0

    def link(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("private")
        return original_link(*args, **kwargs)

    def unlink(path, **kwargs):
        if path == "first.json":
            raise OSError("private rollback error")
        return original_unlink(path, **kwargs)

    monkeypatch.setattr(os, "link", link)
    monkeypatch.setattr(os, "unlink", unlink)
    with pytest.raises(DerivedOutputError, match="partial outputs may remain"):
        write_outputs(
            git_repo, (("first.json", b"first"), ("second.json", b"second")), forbidden=set()
        )
    assert (git_repo / "first.json").read_bytes() == b"first"
    assert not (git_repo / "second.json").exists()


def test_cli_compiler_receipt_through_public_provider_adapter(git_repo):
    from test_context_engine import fake_executable

    (git_repo / ".context-integrity.toml").write_text(CONFIG)
    (git_repo / "src").mkdir()
    (git_repo / "src/sample.py").write_text(BODY)
    context = discover_repository(git_repo)
    manifest = inventory_repository(context)
    request = EvidenceContextRequest(context.root, manifest.repository, "PRIVATE TASK TEXT", 4096)
    executable = fake_executable(git_repo, response(request))
    args = [
        *compile_args(git_repo),
        "--evidence-provider",
        "context-engine",
        "--context-engine-bin",
        executable,
        "--evidence-budget-bytes",
        "4096",
    ]
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    receipt = parse_receipt((git_repo / "docs/compiled.receipt.json").read_bytes())
    assert {p.path for p in receipt.dependencies} == {"AGENTS.md", "src/sample.py"}
    checked = runner.invoke(
        app, ["derived", "check", "docs/compiled.receipt.json", str(git_repo), "--format", "json"]
    )
    assert checked.exit_code == 0
    assert json.loads(checked.stdout)["status"] == "inconclusive"


def test_cleanup_error_is_sanitized(git_repo, monkeypatch):
    def fail(*args, **kwargs):
        raise OSError("PRIVATE STDERR")

    monkeypatch.setattr(os, "unlink", fail)
    with pytest.raises(DerivedOutputError, match="cleanup failed"):
        write_outputs(git_repo, (("one.json", b"one"),), forbidden=set())


def test_current_inventory_coverage_gap_is_not_equality(git_repo, monkeypatch):
    import context_integrity.derived as module
    from context_integrity.models import ScanWarning

    (git_repo / ".context-integrity.toml").write_text(CONFIG)
    assert runner.invoke(app, compile_args(git_repo)).exit_code == 0
    original = module.inventory_repository

    def incomplete(context, **kwargs):
        manifest = original(context, **kwargs)
        return replace(
            manifest,
            warnings=(ScanWarning("candidate_metadata_failed", "docs", "Directory unavailable."),),
        )

    monkeypatch.setattr(module, "inventory_repository", incomplete)
    checked, _ = check_receipt(discover_repository(git_repo), "docs/compiled.receipt.json")
    assert checked.status == "inconclusive"
    assert "compilation_context_unobservable" in {r.code for r in checked.reasons}
