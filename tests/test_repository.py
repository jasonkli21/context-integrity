import subprocess

import pytest

from context_integrity import repository
from context_integrity.models import GitFileStatus
from context_integrity.repository import (
    RepositoryError,
    discover_repository,
    normalize_remote,
    parse_status,
)


def test_discovery_root_nested_and_identity(git_repo, git):
    root = discover_repository(git_repo)
    nested = discover_repository(git_repo / "docs")
    assert root.repository == nested.repository
    assert root.root == nested.root == git_repo
    assert root.repository.identity_basis == "git_remote"
    assert root.repository.git_head is None
    assert root.repository.git_dirty is True
    assert root.warnings == []
    git(git_repo, "add", ".")
    git(git_repo, "commit", "-m", "fixture")
    clean = discover_repository(git_repo)
    assert clean.repository.git_head == git(git_repo, "rev-parse", "HEAD")
    assert clean.repository.git_dirty is False
    assert clean.status_known


def test_local_fallback(tmp_path):
    first, second = discover_repository(tmp_path), discover_repository(tmp_path)
    assert first.repository == second.repository
    assert first.repository.identity_basis == "local_fallback"
    assert not first.repository.git_available
    assert first.repository.git_dirty is None
    assert str(tmp_path) not in first.repository.id


def test_remote_normalization():
    expected = "github.com/Team/repo"
    for remote in [
        "git@github.com:Team/repo.git",
        "https://user:secret@GitHub.com/Team/repo.git",
        "ssh://git@github.com/Team/repo.git?secret=abc#fragment",
    ]:
        assert normalize_remote(remote) == expected
    assert normalize_remote("/private/local.git") is None
    assert normalize_remote("file:///private/local.git") is None
    assert normalize_remote("https://github.com:invalid/team/repo") is None
    assert normalize_remote("ssh://host:2222/team/repo.git") == "host:2222/team/repo"


def test_git_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr(repository.shutil, "which", lambda _: None)
    context = discover_repository(tmp_path)
    assert not context.repository.git_available
    assert context.warnings[0].code == "git_command_failed"


def test_status_failure_degrades(git_repo, monkeypatch):
    original = repository.git_command

    def failing(root, *args):
        if args[0] == "status":
            raise OSError("private absolute path must not leak")
        return original(root, *args)

    monkeypatch.setattr(repository, "git_command", failing)
    context = discover_repository(git_repo)
    assert context.repository.git_dirty is None
    assert not context.status_known
    assert any(w.code == "git_command_failed" for w in context.warnings)


def test_rename_status():
    statuses = parse_status(b"R  docs/new name.md\0docs/old.md\0?? docs/new\nline.md\0")
    assert statuses["docs/new name.md"] == GitFileStatus.TRACKED_MODIFIED
    assert statuses["docs/old.md"] == GitFileStatus.DELETED
    assert statuses["docs/new\nline.md"] == GitFileStatus.UNTRACKED


def test_worktree_and_renamed_dirty_source(git_repo, git):
    from context_integrity.inventory import scan_repository

    git(git_repo, "add", ".")
    git(git_repo, "commit", "-m", "fixture")
    worktree = git_repo.parent / "linked-worktree"
    git(git_repo, "worktree", "add", "-b", "fixture-branch", str(worktree))
    assert discover_repository(worktree / "docs").root == worktree
    git(worktree, "mv", "docs/architecture.md", "docs/renamed-architecture.md")
    source = next(s for s in scan_repository(worktree).sources if s.path.startswith("docs/"))
    assert source.revision.git_status == "tracked_modified"
    assert source.path == "docs/renamed-architecture.md"


def test_fsmonitor_is_not_executed_and_index_is_read_only(git_repo, git):
    from context_integrity.inventory import scan_repository

    git(git_repo, "add", ".")
    git(git_repo, "commit", "-m", "fixture")
    marker = git_repo / "hook-was-run"
    hook = git_repo / "monitor.sh"
    hook.write_text('#!/bin/sh\ntouch "$(dirname "$0")/hook-was-run"\n')
    hook.chmod(0o755)
    git(git_repo, "config", "core.fsmonitor", str(hook))
    index = git_repo / ".git/index"
    before = index.read_bytes(), index.stat().st_mtime_ns
    scan_repository(git_repo)
    assert not marker.exists()
    assert (index.read_bytes(), index.stat().st_mtime_ns) == before


def test_git_context_environment_is_not_used(git_repo, monkeypatch, tmp_path):
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "unrelated"))
    monkeypatch.setenv("GIT_WORK_TREE", str(tmp_path))
    assert discover_repository(git_repo).root == git_repo


def test_discovery_rejects_git_worktree_redirect(git_repo, tmp_path, git):
    redirected = tmp_path / "redirected"
    redirected.mkdir()
    git(redirected, "init", "--initial-branch=main", "--object-format=sha1")
    (redirected / "docs").mkdir()
    (redirected / "docs/architecture.md").write_text("must not be inventoried")
    git(git_repo, "config", "core.worktree", str(redirected))

    with pytest.raises(RepositoryError, match="identity could not be verified"):
        discover_repository(git_repo)


def test_discovery_fails_closed_when_git_identity_cannot_be_read(git_repo, monkeypatch):
    original = repository.git_command

    def timeout_on_identity(root, *args):
        if args == ("rev-parse", "--absolute-git-dir"):
            raise subprocess.TimeoutExpired("git", timeout=30)
        return original(root, *args)

    monkeypatch.setattr(repository, "git_command", timeout_on_identity)

    with pytest.raises(RepositoryError, match="identity could not be verified"):
        discover_repository(git_repo)


@pytest.mark.parametrize("across", ["0", "1"])
def test_inherited_discovery_controls_preserve_git_inventory(git_repo, monkeypatch, across):
    from context_integrity.inventory import scan_repository

    nested = git_repo / "docs/nested"
    nested.mkdir()
    (git_repo / ".gitignore").write_text("docs/ignored.md\n")
    (git_repo / "docs/ignored.md").write_text("ignored")
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(git_repo / "docs"))
    monkeypatch.setenv("GIT_DISCOVERY_ACROSS_FILESYSTEM", across)
    context = discover_repository(nested)
    assert context.root == git_repo
    assert context.repository.git_available
    manifest = scan_repository(nested)
    assert "docs/architecture.md" in {s.path for s in manifest.sources}
    assert "docs/ignored.md" not in {s.path for s in manifest.sources}


@pytest.mark.parametrize("scope", ["global", "system", "command"])
def test_external_origin_cannot_supply_repository_identity(tmp_path, git, monkeypatch, scope):
    from context_integrity.inventory import scan_repository

    external = tmp_path / "external.gitconfig"
    external.write_text('[remote "origin"]\nurl = https://example.invalid/shared.git\n')
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(external) if scope == "global" else "/dev/null")
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", str(external) if scope == "system" else "/dev/null")
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "0")
    if scope == "command":
        monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
        monkeypatch.setenv("GIT_CONFIG_KEY_0", "remote.origin.url")
        monkeypatch.setenv("GIT_CONFIG_VALUE_0", "https://example.invalid/shared.git")
    manifests = []
    for name in ("one", "two"):
        root = tmp_path / name
        root.mkdir()
        git(root, "init", "--initial-branch=main", "--object-format=sha1")
        (root / "AGENTS.md").write_text("Instructions")
        manifests.append(scan_repository(root))
    assert all(m.repository.git_available for m in manifests)
    assert all(m.repository.identity_basis == "local_fallback" for m in manifests)
    assert manifests[0].repository.id != manifests[1].repository.id
    assert manifests[0].sources[0].id != manifests[1].sources[0].id
    git(tmp_path / "one", "config", "remote.origin.url", "git@example.invalid:team/local.git")
    git(tmp_path / "two", "config", "remote.origin.url", "https://example.invalid/team/local.git")
    local = [discover_repository(tmp_path / name).repository for name in ("one", "two")]
    assert all(r.identity_basis == "git_remote" for r in local)
    assert local[0].id == local[1].id
