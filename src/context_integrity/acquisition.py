"""Candidate selection, filesystem safety, and raw-byte hashing."""

import errno
import os
import stat
from fnmatch import fnmatchcase
from hashlib import sha256
from pathlib import PurePosixPath

from context_integrity.models import ScanWarning
from context_integrity.repository import RepositoryContext, RepositoryError, try_git

MAX_SOURCE_BYTES = 5 * 1024 * 1024
SKIPPED_DIRECTORIES = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "node_modules",
        ".venv",
        "venv",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "target",
        "dist",
        "build",
        "coverage",
        ".coverage",
        "vendor",
        ".next",
        ".cache",
    }
)
DOCUMENT_EXTENSIONS = frozenset({".md", ".mdx", ".rst", ".txt", ".adoc"})
CONTEXT_DIRECTORIES = frozenset(
    {
        "docs",
        "doc",
        "documentation",
        "adr",
        "adrs",
        "decisions",
        "architecture",
        "plans",
        "planning",
        "reviews",
        "releases",
        "history",
        "historical",
        "archive",
        "archived",
        "deprecated",
        "verification",
        "status",
        "requirements",
        "summary",
        "generated",
    }
)

# Candidate selection is broader than kind classification and makes no policy decision.
CONTEXT_FILENAMES = (
    "agents.md",
    "claude.md",
    "gemini.md",
    "contributing.md",
    "readme.*",
    "current-state.md",
    "current_state.md",
    "architecture.md",
    "system-design.md",
    "prd.md",
    "adr-*",
    "*implementation-plan*",
    "phase-*-plan*",
    "*-review.*",
    "*post-implementation-review*",
    "*independent-review*",
    "*-verification.*",
    "*verification-record*",
    "release-*",
    "*-architecture.*",
    "*-prd.*",
    "product-requirements*",
    "handoff.*",
    "handoff-*",
    "*-handoff.*",
    "*_handoff.*",
    "*-summary.*",
)


def normalize_path(path: str) -> str:
    pure = PurePosixPath(path)
    if pure.is_absolute() or ".." in pure.parts or not pure.parts or "\0" in path:
        raise ValueError("Source path must be relative and contain no traversal.")
    return pure.as_posix()


def is_context_candidate(path: str) -> bool:
    if path == ".context-integrity.toml":
        return True
    pure = PurePosixPath(normalize_path(path))
    if any(p.lower() in SKIPPED_DIRECTORIES for p in pure.parts[:-1]):
        return False
    if pure.suffix.lower() not in DOCUMENT_EXTENSIONS:
        return False
    return (
        any(p.lower() in CONTEXT_DIRECTORIES for p in pure.parts[:-1])
        or pure.as_posix().lower() == ".github/copilot-instructions.md"
        or any(fnmatchcase(pure.name.lower(), pattern) for pattern in CONTEXT_FILENAMES)
    )


def enumerate_candidates(context: RepositoryContext) -> list[str]:
    if context.repository.git_available:
        listing = try_git(
            context.root,
            context.warnings,
            "ls-files",
            "-z",
            "--cached",
            "--others",
            "--exclude-standard",
        )
        if listing is None:
            # Walking would include ignored files, silently breaking the Git contract.
            raise RepositoryError("Git file enumeration failed; scan cannot continue safely.")
        paths = set()
        for raw in listing.split(b"\0"):
            if not raw:
                continue
            try:
                path = normalize_path(os.fsdecode(raw))
                if is_context_candidate(path):
                    paths.add(path)
            except ValueError:
                context.warnings.append(
                    ScanWarning(
                        "candidate_metadata_failed", None, "Git returned an unsafe source path."
                    )
                )
        return sorted(paths)
    paths = []

    def walk_error(exc: OSError) -> None:
        try:
            relative = os.path.relpath(exc.filename, context.root)
            relative = normalize_path(relative)
        except (TypeError, ValueError):
            relative = None
        context.warnings.append(
            ScanWarning("candidate_metadata_failed", relative, "Directory could not be enumerated.")
        )

    try:
        # scandir upfront distinguishes a fatal unreadable scan root from a subtree warning.
        with os.scandir(context.root):
            pass
        for directory, dirs, files in os.walk(context.root, followlinks=False, onerror=walk_error):
            keep = []
            for name in sorted(dirs):
                path = os.path.join(directory, name)
                if name.lower() in SKIPPED_DIRECTORIES:
                    continue
                if os.path.islink(path):
                    context.warnings.append(
                        ScanWarning(
                            "symlink_skipped",
                            os.path.relpath(path, context.root),
                            "Symlink directory was not followed.",
                        )
                    )
                else:
                    keep.append(name)
            dirs[:] = keep
            for name in files:
                path = normalize_path(os.path.relpath(os.path.join(directory, name), context.root))
                if is_context_candidate(path):
                    paths.append(path)
    except OSError as exc:
        raise RepositoryError("Scan root could not be enumerated.") from exc
    return sorted(paths)


def read_source(context: RepositoryContext, path: str) -> tuple[int | None, str | None, bool]:
    return _read_source(context, path)


def read_source_bytes(context: RepositoryContext, path: str) -> bytes | None:
    """Capture bounded bytes through the same descriptor-safe boundary as inventory reads."""
    chunks: list[bytes] = []
    _, digest, skipped = _read_source(context, path, chunks)
    return b"".join(chunks) if digest is not None and not skipped else None


def _read_source(
    context: RepositoryContext, path: str, chunks: list[bytes] | None = None
) -> tuple[int | None, str | None, bool]:
    """Open each component relative to a directory FD, rejecting symlinks even during races.

    Returns size, digest, skipped. Body reads are bounded even if a file grows after stat.
    """
    path = normalize_path(path)
    descriptors = []
    try:
        parent_fd = os.open(context.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        descriptors.append(parent_fd)
        for segment in PurePosixPath(path).parts[:-1]:
            metadata = os.stat(segment, dir_fd=parent_fd, follow_symlinks=False)
            if stat.S_ISLNK(metadata.st_mode):
                context.warnings.append(
                    ScanWarning("symlink_skipped", path, "Symlink source path was not followed.")
                )
                return None, None, True
            parent_fd = os.open(
                segment, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd
            )
            descriptors.append(parent_fd)
        name = PurePosixPath(path).name
        metadata = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if stat.S_ISLNK(metadata.st_mode):
            context.warnings.append(
                ScanWarning("symlink_skipped", path, "Symlink source was not followed.")
            )
            return None, None, True
        if not stat.S_ISREG(metadata.st_mode):
            context.warnings.append(
                ScanWarning("candidate_metadata_failed", path, "Candidate is not a regular file.")
            )
            return metadata.st_size, None, False
        if metadata.st_size > MAX_SOURCE_BYTES:
            context.warnings.append(
                ScanWarning("source_too_large", path, "Candidate exceeds the 5 MiB read limit.")
            )
            return metadata.st_size, None, False
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)
        descriptors.append(fd)
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode):
            context.warnings.append(
                ScanWarning(
                    "candidate_metadata_failed", path, "Candidate changed to a non-regular file."
                )
            )
            return None, None, False
        if opened.st_size > MAX_SOURCE_BYTES:
            context.warnings.append(
                ScanWarning("source_too_large", path, "Candidate exceeds the 5 MiB read limit.")
            )
            return opened.st_size, None, False
        digest = sha256()
        count = 0
        try:
            while chunk := os.read(fd, min(65536, MAX_SOURCE_BYTES + 1 - count)):
                count += len(chunk)
                if count > MAX_SOURCE_BYTES:
                    context.warnings.append(
                        ScanWarning(
                            "source_too_large", path, "Candidate grew beyond the 5 MiB limit."
                        )
                    )
                    return count, None, False
                digest.update(chunk)
                if chunks is not None:
                    chunks.append(chunk)
        except OSError:
            context.warnings.append(ScanWarning("hash_failed", path, "Source hashing failed."))
            return opened.st_size, None, False
        return count, digest.hexdigest(), False
    except OSError as exc:
        if exc.errno in {errno.ENOENT, errno.ENOTDIR}:
            context.warnings.append(
                ScanWarning(
                    "candidate_metadata_failed",
                    path,
                    "Candidate disappeared before it could be opened.",
                )
            )
            return None, None, True
        code = (
            "symlink_skipped"
            if exc.errno == errno.ELOOP
            else (
                "source_unreadable"
                if exc.errno in {errno.EACCES, errno.EPERM}
                else "candidate_metadata_failed"
            )
        )
        context.warnings.append(ScanWarning(code, path, "Candidate could not be opened safely."))
        return None, None, code == "symlink_skipped"
    finally:
        for fd in reversed(descriptors):
            os.close(fd)
