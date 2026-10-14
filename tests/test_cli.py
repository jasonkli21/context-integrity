import pytest
from typer.testing import CliRunner

from context_integrity import __version__
from context_integrity.cli import app

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == __version__


def test_root_help() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Inspect and validate software-development context." in result.stdout


def test_scan_json_and_output(git_repo, tmp_path):
    import json

    result = runner.invoke(app, ["scan", str(git_repo), "--format", "json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["summary"]["source_count"] == 2
    output = tmp_path / "inventory.json"
    result = runner.invoke(
        app, ["scan", str(git_repo), "--format", "json", "--output", str(output)]
    )
    assert result.exit_code == 0
    assert result.stdout == ""
    assert json.loads(output.read_text())["schema_version"] == 1


def test_invalid_paths_and_arguments(tmp_path):
    assert runner.invoke(app, ["scan", str(tmp_path / "missing")]).exit_code == 3
    file = tmp_path / "file.md"
    file.write_text("test")
    assert runner.invoke(app, ["scan", str(file)]).exit_code == 3
    assert runner.invoke(app, ["scan", str(tmp_path), "--format", "invalid"]).exit_code == 2
    assert runner.invoke(app, ["explain", "../AGENTS.md", "--root", str(tmp_path)]).exit_code == 2
    assert runner.invoke(app, ["explain", "/AGENTS.md", "--root", str(tmp_path)]).exit_code == 2
    assert runner.invoke(app, ["explain", "missing.md", "--root", str(tmp_path)]).exit_code == 2
    assert runner.invoke(app, ["scan", str(tmp_path), "--output", str(tmp_path)]).exit_code == 4


def test_summary_and_explain(git_repo):
    summary = runner.invoke(app, ["scan", str(git_repo), "--summary-only"])
    assert summary.exit_code == 0
    assert "Sources: 2" in summary.stdout
    assert "PATH |" not in summary.stdout
    result = runner.invoke(app, ["explain", "AGENTS.md", "--root", str(git_repo / "docs")])
    assert result.exit_code == 0
    for label in [
        "kind: agent_instruction",
        "authority_class: operating_instruction",
        "lifecycle: unknown",
        "kind.agent_instruction.filename",
        "sha256:",
        "Not inferred:",
        "superseded",
    ]:
        assert label in result.stdout


def test_fail_on_warning_and_runtime(tmp_path):
    import json

    (tmp_path / "AGENTS.md").symlink_to(tmp_path / "missing")
    normal = runner.invoke(app, ["scan", str(tmp_path), "--format", "json"])
    assert normal.exit_code == 0
    assert json.loads(normal.stdout)["warnings"][0]["code"] == "symlink_skipped"
    strict = runner.invoke(app, ["scan", str(tmp_path), "--fail-on-warning"])
    assert strict.exit_code == 5
    assert "symlink_skipped" in strict.stdout
    runtime = runner.invoke(
        app, ["scan", str(tmp_path), "--format", "json", "--include-runtime-meta"]
    )
    assert runtime.exit_code == 0
    assert json.loads(runtime.stdout)["runtime_meta"]["resolved_root"] == str(tmp_path)


def test_default_scan_non_git(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "README.md").write_text("readme")
    result = runner.invoke(app, ["scan"])
    assert result.exit_code == 0
    assert "Git: no" in result.stdout
    assert "README.md | readme" in result.stdout


def test_scan_dot_git(git_repo, monkeypatch):
    monkeypatch.chdir(git_repo)
    result = runner.invoke(app, ["scan", "."])
    assert result.exit_code == 0
    assert "Git: yes" in result.stdout
    assert "Sources: 2" in result.stdout


def test_scan_rejects_git_worktree_redirect(git_repo, tmp_path, git):
    redirected = tmp_path / "redirected"
    redirected.mkdir()
    git(redirected, "init", "--initial-branch=main", "--object-format=sha1")
    (redirected / "docs").mkdir()
    (redirected / "docs/architecture.md").write_text("redirected secret content")
    git(git_repo, "config", "core.worktree", str(redirected))

    result = runner.invoke(app, ["scan", str(git_repo), "--format", "json"])

    assert result.exit_code == 3
    assert "identity could not be verified" in result.stderr
    assert str(redirected) not in result.stdout + result.stderr
    assert "redirected secret content" not in result.stdout + result.stderr


@pytest.mark.parametrize(
    "path,kind,authority,rule",
    [
        ("docs/adr/0001.md", "decision_record", "decision", "kind.decision.directory"),
        ("docs/plans/phase-1.md", "implementation_plan", "plan", "kind.plan.directory"),
        (
            "docs/history/old-architecture.md",
            "architecture",
            "historical",
            "authority.historical.overlay",
        ),
        ("docs/misc.md", "other_document", "unknown", "kind.other_document.fallback"),
    ],
)
def test_explain_document_roles(tmp_path, path, kind, authority, rule):
    source = tmp_path / path
    source.parent.mkdir(parents=True)
    source.write_text("fixture")
    result = runner.invoke(app, ["explain", path, "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert f"kind: {kind}" in result.stdout
    assert f"authority_class: {authority}" in result.stdout
    assert rule in result.stdout
    assert "Not inferred:" in result.stdout
