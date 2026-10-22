"""Workspace CLI exits, projections, safe publication and additive compatibility."""

import json

import pytest
from typer.testing import CliRunner

from context_integrity.cli import app
from context_integrity.workspace_output import render_workspace
from test_workspace import git, write
from test_workspace import workspace as workspace_fixture

workspace = workspace_fixture

runner = CliRunner()


def invoke(manifest, command="check", *options):
    return runner.invoke(app, ["workspace", command, str(manifest), *options])


def test_cli_text_json_parity_and_no_writes(workspace):
    manifest, api, web = workspace
    before = {str(p): p.read_bytes() for root in (api, web) for p in root.rglob("*") if p.is_file()}
    result = invoke(manifest, "check", "--format", "json")
    assert result.exit_code == 0, result.output
    value = json.loads(result.output)
    assert value["workspace_check_schema_version"] == 1
    text = invoke(manifest)
    assert text.exit_code == 0
    assert text.output == render_workspace(value, as_json=False)
    after = {str(p): p.read_bytes() for root in (api, web) for p in root.rglob("*") if p.is_file()}
    assert before == after


def test_findings_exit_zero_and_compile_separates_checks(workspace):
    manifest, api, _ = workspace
    write(api, "spec/api.json", b"changed")
    result = invoke(manifest, "compile", "--task", "PRIVATE_TASK", "--format", "json")
    assert result.exit_code == 0, result.output
    value = json.loads(result.output)
    assert value["workspace_context_schema_version"] == 1
    assert value["selection_complete"]
    assert value["checks_status"] == "review_required"
    assert value["review_required"]
    assert "PRIVATE_TASK" not in result.output
    assert "PRIVATE_SOURCE_BODY" not in result.output
    assert len({t["repository_id"] for t in value["targets"]}) == 2
    for t in value["targets"]:
        assert t["selected_sources"] and t["decisions"] and t["dependencies"]
        assert isinstance(t["authority_policies"], list)
        assert t["contract_sha256"]
        assert t["config_sha256"]


@pytest.mark.parametrize(
    "options",
    [
        ("compile",),
        ("check", "--format", "xml"),
        ("compile", "--task", "x", "--evidence-provider", "context-engine"),
    ],
)
def test_usage_errors(workspace, options):
    manifest, *_ = workspace
    command, *flags = options
    assert invoke(manifest, command, *flags).exit_code == 2


@pytest.mark.parametrize(
    "mode,expected",
    [
        ("manifest", 6),
        ("config", 6),
        ("lock", 6),
        ("identity", 3),
        ("missing_repo", 3),
        ("manifest_symlink", 6),
        ("targets", 6),
        ("oversize_manifest", 6),
        ("contract", 6),
    ],
)
def test_sanitized_errors(workspace, mode, expected):
    manifest, api, web = workspace
    if mode == "manifest":
        manifest.write_text("SECRET_MALFORMED_TEXT")
    elif mode == "config":
        write(api, ".context-integrity.toml", "SECRET_MALFORMED_TEXT")
    elif mode == "lock":
        write(web, "contracts/api.lock.json", "SECRET_MALFORMED_TEXT")
    elif mode == "identity":
        git(api, "remote", "remove", "origin")
    elif mode == "missing_repo":
        manifest.write_text(manifest.read_text().replace('root = "api"', 'root = "missing"'))
    elif mode == "manifest_symlink":
        link = manifest.parent / "link.toml"
        link.symlink_to(manifest)
        manifest = link
    elif mode == "oversize_manifest":
        manifest.write_bytes(b"x" * (256 * 1024 + 1))
    elif mode == "contract":
        manifest.write_text(
            manifest.read_text().replace('contract_id = "work"', 'contract_id = "missing"')
        )
    else:
        data = manifest.read_text()
        manifest.write_text(data[: data.index("[[context_targets]]")])
    command = "compile" if mode in {"targets", "contract"} else "check"
    options = ("--task", "work") if command == "compile" else ()
    result = invoke(manifest, command, *options)
    assert result.exit_code == expected, result.output
    assert "SECRET" not in result.output and str(manifest.parent) not in result.output


def test_exclusive_output_and_no_inventory_side_effect(workspace):
    manifest, api, _ = workspace
    path = manifest.parent / "result.json"
    result = invoke(manifest, "check", "--format", "json", "--output", str(path))
    assert result.exit_code == 0, result.output
    original = path.read_bytes()
    assert json.loads(original)["workspace_check_schema_version"] == 1
    assert invoke(manifest, "check", "--output", str(path)).exit_code == 4
    assert path.read_bytes() == original
    assert invoke(manifest, "check", "--output", str(api / "result.json")).exit_code == 4
    assert not (api / "result.json").exists()


@pytest.mark.parametrize(
    "mode", ["symlink_parent", "symlink_target", "missing_parent", "directory", "git"]
)
def test_unsafe_output_paths(workspace, mode):
    manifest, api, _ = workspace
    base = manifest.parent
    path = base / "result.json"
    if mode == "symlink_parent":
        (base / "linked").symlink_to(base, target_is_directory=True)
        path = base / "linked/result.json"
    elif mode == "symlink_target":
        path.symlink_to(api / "spec/api.json")
    elif mode == "missing_parent":
        path = base / "absent/result.json"
    elif mode == "directory":
        path.mkdir()
    else:
        path = api / ".git/forbidden.json"
    result = invoke(manifest, "check", "--output", str(path))
    assert result.exit_code == 4, result.output
    assert "PRIVATE_SOURCE_BODY" not in result.output


def test_default_offline_with_no_provider_binary(workspace, monkeypatch):
    manifest, *_ = workspace
    monkeypatch.setenv("PATH", "/nonexistent")
    # Git absence changes origin identity, so bind explicitly to the local fallback.
    # This verifies filesystem-only discovery and compiler operation without any executable.
    from context_integrity.repository import discover_repository

    for root in workspace[1:]:
        import os

        old_path = os.environ["PATH"]
        monkeypatch.setenv("PATH", "/usr/bin:/bin")
        old = discover_repository(root).repository.id
        monkeypatch.setenv("PATH", old_path)
        new = discover_repository(root).repository.id
        manifest.write_text(manifest.read_text().replace(old, new))
    # The lock also needs explicit rebinding; the command never rewrites it.
    lock_path = workspace[2] / "contracts/api.lock.json"
    lock = json.loads(lock_path.read_bytes())
    lock["producer_repository_id"] = discover_repository(workspace[1]).repository.id
    lock_path.write_text(json.dumps(lock))
    result = invoke(manifest, "compile", "--task", "offline", "--format", "json")
    assert result.exit_code == 0, result.output
    value = json.loads(result.output)
    assert value["checks_status"] == "inconclusive"
    assert value["selection_complete"]


def test_existing_compile_v3_keeps_task_and_other_versions(workspace):
    _, api, _ = workspace
    result = runner.invoke(
        app, ["compile", "work", str(api), "--task", "original-task", "--format", "json"]
    )
    assert result.exit_code == 0, result.output
    value = json.loads(result.output)
    assert value["schema_version"] == 3
    assert value["task"]["text"] == "original-task"
    result = runner.invoke(app, ["check", str(api), "--format", "json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["integrity_schema_version"] == 2


def test_output_failure_is_sanitized(workspace, monkeypatch):
    manifest, *_ = workspace

    def fail(*args, **kwargs):
        raise OSError("PRIVATE_OS_MESSAGE")

    monkeypatch.setattr("context_integrity.derived_output.os.link", fail)
    output = manifest.parent / "result.json"
    result = invoke(manifest, "check", "--output", str(output))
    assert result.exit_code == 4
    assert "PRIVATE_OS_MESSAGE" not in result.output
    assert not output.exists()
    assert not list(output.parent.glob(".derived-*"))
