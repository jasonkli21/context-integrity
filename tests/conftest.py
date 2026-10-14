"""Small purpose-specific repositories generated at test time, never downloaded."""

import os
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def git():
    def run(root: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            check=True,
            env={
                **os.environ,
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_AUTHOR_NAME": "Fixture",
                "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
                "GIT_COMMITTER_NAME": "Fixture",
                "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
                "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z",
                "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z",
            },
        )
        return result.stdout.decode().strip()

    return run


@pytest.fixture
def git_repo(tmp_path, git):
    root = tmp_path / "basic-context"
    root.mkdir()
    git(root, "init", "--initial-branch=main", "--object-format=sha1")
    git(root, "config", "remote.origin.url", "git@example.invalid:team/basic-context.git")
    (root / "AGENTS.md").write_bytes(b"Instructions\n")
    (root / "docs").mkdir()
    (root / "docs/architecture.md").write_bytes(b"Architecture\n")
    (root / "AGENTS.md").chmod(0o644)
    (root / "docs/architecture.md").chmod(0o644)
    return root
