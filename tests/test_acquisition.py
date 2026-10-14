import hashlib
import os

import pytest

from context_integrity import acquisition, inventory
from context_integrity.acquisition import SKIPPED_DIRECTORIES, normalize_path, read_source
from context_integrity.inventory import inventory_repository, scan_repository
from context_integrity.repository import RepositoryError, discover_repository


def test_git_ignore_dirty_and_raw_bytes(git_repo, git):
    (git_repo / ".gitignore").write_text("docs/ignored.md\n")
    git(git_repo, "add", ".")
    git(git_repo, "commit", "-m", "fixture")
    before = scan_repository(git_repo)
    assert all(s.revision.git_status == "tracked_clean" for s in before.sources)
    (git_repo / "docs/ignored.md").write_text("ignored")
    (git_repo / "docs/untracked.md").write_bytes(b"\xff\r\n\x00")
    (git_repo / "AGENTS.md").write_bytes(b"dirty\r\n")
    (git_repo / "src.py").write_text("raise Exception('must not execute')")
    after = scan_repository(git_repo)
    sources = {s.path: s for s in after.sources}
    assert set(sources) == {"AGENTS.md", "docs/architecture.md", "docs/untracked.md"}
    assert after.repository.git_dirty is True
    assert sources["AGENTS.md"].revision.git_head == before.repository.git_head
    assert sources["AGENTS.md"].revision.git_status == "tracked_modified"
    assert sources["AGENTS.md"].revision.observed_revision_basis == "working_tree_content"
    assert sources["AGENTS.md"].revision.content_sha256 != before.sources[0].revision.content_sha256
    assert sources["docs/untracked.md"].revision.git_status == "untracked"
    assert (
        sources["docs/untracked.md"].revision.content_sha256
        == hashlib.sha256(b"\xff\r\n\x00").hexdigest()
    )


def test_deleted_tracked_source_is_not_in_inventory(git_repo, git):
    git(git_repo, "add", ".")
    git(git_repo, "commit", "-m", "fixture")
    (git_repo / "docs/architecture.md").unlink()

    result = scan_repository(git_repo)

    assert result.repository.git_dirty is True
    assert [source.path for source in result.sources] == ["AGENTS.md"]
    assert result.summary.source_count == 1
    assert result.summary.by_kind == {"agent_instruction": 1}
    assert not any(warning.path == "docs/architecture.md" for warning in result.warnings)


@pytest.mark.parametrize("directory", sorted(SKIPPED_DIRECTORIES))
def test_vendor_exclusions(tmp_path, directory):
    child = tmp_path / directory / "docs"
    child.mkdir(parents=True)
    (child / "architecture.md").write_text("excluded")
    assert scan_repository(tmp_path).sources == ()


def test_non_git_candidate_selection(tmp_path):
    for name in [
        "docs/a.mdx",
        "docs/b.adoc",
        "docs/c.rst",
        "docs/d.txt",
        "docs/code.py",
        "generic.md",
        "README.md",
        "nested/architecture.md",
        "nested/file.ts",
    ]:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("data")
    assert [s.path for s in scan_repository(tmp_path).sources] == [
        "README.md",
        "docs/a.mdx",
        "docs/b.adoc",
        "docs/c.rst",
        "docs/d.txt",
        "nested/architecture.md",
    ]


@pytest.mark.parametrize("path", ["../docs/a.md", "/docs/a.md", "docs/../../a.md", "", ".", "a\0b"])
def test_unsafe_paths(path):
    with pytest.raises(ValueError):
        normalize_path(path)


def test_path_normalization():
    assert normalize_path("./docs//Case.md") == "docs/Case.md"


def test_symlinks_and_size_limit(tmp_path):
    outside = tmp_path.parent / "outside.md"
    outside.write_text("secret")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/link.md").symlink_to(outside)
    (tmp_path / "docs/internal.md").write_text("inside")
    (tmp_path / "docs/alias.md").symlink_to(tmp_path / "docs/internal.md")
    (tmp_path / "docs/linked-dir").symlink_to(tmp_path.parent, target_is_directory=True)
    large = tmp_path / "docs/large.md"
    with large.open("wb") as file:
        file.truncate(acquisition.MAX_SOURCE_BYTES + 1)
    result = scan_repository(tmp_path)
    assert [s.path for s in result.sources] == ["docs/internal.md", "docs/large.md"]
    assert result.sources[1].revision.content_sha256 is None
    assert result.sources[1].size_bytes == acquisition.MAX_SOURCE_BYTES + 1
    assert sum(w.code == "symlink_skipped" for w in result.warnings) == 3
    assert any(w.code == "source_too_large" for w in result.warnings)


def test_git_symlink_ancestor(git_repo, git):
    git(git_repo, "add", ".")
    git(git_repo, "commit", "-m", "fixture")
    (git_repo / "docs/architecture.md").unlink()
    (git_repo / "docs").rmdir()
    (git_repo / "docs").symlink_to(git_repo.parent, target_is_directory=True)
    context = discover_repository(git_repo)

    _, _, skipped = read_source(context, "docs/architecture.md")

    assert skipped
    assert any(w.code == "symlink_skipped" for w in context.warnings)


def test_unreadable_hash_and_metadata_failures(tmp_path, monkeypatch):
    path = tmp_path / "AGENTS.md"
    path.write_text("private")
    original_open = acquisition.os.open

    def deny(name, *args, **kwargs):
        if name == "AGENTS.md":
            raise PermissionError(13, "sensitive absolute path")
        return original_open(name, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(acquisition.os, "open", deny)
        result = scan_repository(tmp_path)
        assert result.sources[0].revision.content_sha256 is None
        assert result.warnings[0].code == "source_unreadable"
        assert "sensitive" not in result.warnings[0].message
    context = discover_repository(tmp_path)
    with monkeypatch.context() as patch:
        patch.setattr(acquisition.os, "read", lambda *_: (_ for _ in ()).throw(OSError()))
        assert inventory_repository(context).warnings[0].code == "hash_failed"
    path.unlink()
    os.mkfifo(path)
    assert scan_repository(tmp_path).warnings[0].code == "candidate_metadata_failed"


def test_candidate_disappearing_after_enumeration_is_warned_and_omitted(tmp_path, monkeypatch):
    path = tmp_path / "docs/architecture.md"
    path.parent.mkdir()
    path.write_text("architecture")
    context = discover_repository(tmp_path)
    candidates = acquisition.enumerate_candidates(context)
    assert candidates == ["docs/architecture.md"]
    path.unlink()
    monkeypatch.setattr(inventory, "enumerate_candidates", lambda _: candidates)

    result = inventory.inventory_repository(context)

    assert result.sources == ()
    assert len(result.warnings) == 1
    assert result.warnings[0].code == "candidate_metadata_failed"
    assert result.warnings[0].path == "docs/architecture.md"


def test_failed_git_listing_is_fatal(git_repo, monkeypatch):
    monkeypatch.setattr(acquisition, "try_git", lambda *_: None)
    with pytest.raises(RepositoryError, match="enumeration"):
        scan_repository(git_repo)


def test_oversized_candidate_body_is_not_read(tmp_path, monkeypatch):
    path = tmp_path / "AGENTS.md"
    with path.open("wb") as file:
        file.truncate(acquisition.MAX_SOURCE_BYTES + 1)
    context = discover_repository(tmp_path)

    def must_not_read(*args):
        pytest.fail("Oversized source must not be read")

    monkeypatch.setattr(acquisition.os, "read", must_not_read)
    result = inventory_repository(context)
    assert result.sources[0].revision.content_sha256 is None
    assert result.warnings[0].code == "source_too_large"


def test_growing_file_read_remains_bounded(tmp_path, monkeypatch):
    (tmp_path / "AGENTS.md").write_bytes(b"x")
    context = discover_repository(tmp_path)
    monkeypatch.setattr(acquisition, "MAX_SOURCE_BYTES", 8)
    monkeypatch.setattr(acquisition.os, "read", lambda fd, count: b"x" * count)
    result = inventory_repository(context)
    assert result.sources[0].revision.content_sha256 is None
    assert result.sources[0].size_bytes == 9
    assert result.warnings[0].code == "source_too_large"


def test_unusual_git_filename(git_repo, git):
    (git_repo / "docs/new\nline.md").write_text("data")
    git(git_repo, "add", ".")
    git(git_repo, "commit", "-m", "fixture")
    sources = {s.path: s for s in scan_repository(git_repo).sources}
    assert sources["docs/new\nline.md"].revision.git_status == "tracked_clean"


def test_unsafe_git_listing_paths(git_repo, monkeypatch):
    monkeypatch.setattr(acquisition, "try_git", lambda *_: b"../AGENTS.md\0/README.md\0AGENTS.md\0")
    result = scan_repository(git_repo)
    assert [s.path for s in result.sources] == ["AGENTS.md"]
    assert sum(w.code == "candidate_metadata_failed" for w in result.warnings) == 2


def test_unreadable_scan_root_is_fatal(tmp_path, monkeypatch):
    context = discover_repository(tmp_path)

    def denied(*args):
        raise PermissionError()

    monkeypatch.setattr(acquisition.os, "scandir", denied)
    with pytest.raises(RepositoryError, match="enumerated"):
        inventory_repository(context)


def test_history_repository_inventory(tmp_path):
    for name in [
        "docs/history/old-architecture.md",
        "docs/history/adr/0001.md",
        "docs/misc.md",
        "docs/history/plans/old-plan.md",
    ]:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture")
    result = scan_repository(tmp_path)
    assert result.summary.by_lifecycle == {"historical": 3, "unknown": 1}
    assert result.summary.by_authority_class == {"historical": 3, "unknown": 1}
    assert result.summary.unclassified_authority_count == 1
    assert result.sources[0].kind == "decision_record"
    assert result.sources[1].kind == "architecture"
    assert result.sources[2].kind == "implementation_plan"
    assert all(s.revision.content_sha256 for s in result.sources)


def test_empty_file_hash(tmp_path):
    (tmp_path / "AGENTS.md").write_bytes(b"")
    source = scan_repository(tmp_path).sources[0]
    assert source.size_bytes == 0
    assert source.revision.content_sha256 == hashlib.sha256(b"").hexdigest()


def test_basic_context_repository(tmp_path):
    cases = {
        "AGENTS.md": "agent_instruction",
        "README.md": "readme",
        "docs/architecture.md": "architecture",
        "docs/current-state.md": "current_state",
        "docs/adr/0001-storage.md": "decision_record",
        "docs/plans/phase-1.md": "implementation_plan",
        "docs/reviews/phase-0-review.md": "review",
        "docs/misc.md": "other_document",
    }
    for name in [*cases, "src/app.py"]:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture")
    result = scan_repository(tmp_path)
    assert {s.path: s.kind.value for s in result.sources} == cases
    assert all(s.lifecycle == "unknown" for s in result.sources)
