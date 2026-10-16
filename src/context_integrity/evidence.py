"""Bounded local observations only; integrity policy belongs to integrity.py."""

import os
import re
import subprocess
from hashlib import sha256

from context_integrity.acquisition import normalize_path, read_source_bytes
from context_integrity.models import ChangeScope, ChangeSet, ScanWarning, SourceRecord
from context_integrity.repository import RepositoryContext, RepositoryError, git_command


def changed_paths(context: RepositoryContext, diff: str | None = None) -> ChangeSet:
    """Observe status or a two-commit local range, with rename inference disabled."""
    if diff is None:
        if context.repository.git_available and context.status_known:
            return ChangeSet(
                ChangeScope.WORKING_TREE,
                tuple(sorted(normalize_path(p) for p in context.statuses)),
                base_revision=context.repository.git_head,
            )
        return ChangeSet(ChangeScope.UNAVAILABLE)
    endpoints = diff.split("..")
    if (
        len(endpoints) != 2
        or "..." in diff
        or any(not p.strip() or p != p.strip() or p.startswith("-") for p in endpoints)
        or not context.repository.git_available
    ):
        raise RepositoryError("Diff requires two local commit endpoints: BASE..TARGET.")
    try:
        revisions = []
        for endpoint in endpoints:
            result = git_command(
                context.root, "rev-parse", "--verify", "--end-of-options", endpoint + "^{commit}"
            )
            revision = result.stdout.decode("ascii").strip()
            if result.returncode or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", revision):
                raise ValueError
            revisions.append(revision)
        result = git_command(
            context.root,
            "diff",
            "--no-ext-diff",
            "--no-textconv",
            "--no-renames",
            "--name-only",
            "-z",
            *revisions,
            "--",
        )
        if result.returncode:
            raise ValueError
        paths = tuple(
            sorted({normalize_path(os.fsdecode(p)) for p in result.stdout.split(b"\0") if p})
        )
        return ChangeSet(ChangeScope.GIT_RANGE, paths, *revisions)
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        raise RepositoryError("Requested local Git diff could not be evaluated.") from exc


def source_text(context: RepositoryContext, source: SourceRecord) -> str | None:
    """Read safe bounded UTF-8 bytes and bind text to the inventoried content hash."""
    data = read_source_bytes(context, source.path)
    if data is not None and sha256(data).hexdigest() == source.revision.content_sha256:
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            pass
    context.warnings.append(
        ScanWarning(
            "integrity_text_unavailable",
            source.path,
            "Integrity text could not be read consistently as bounded UTF-8.",
        )
    )
    return None
