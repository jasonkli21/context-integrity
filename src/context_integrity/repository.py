"""Read-only Git discovery and bounded bulk revision metadata."""

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit

from context_integrity.models import GitFileStatus, RepositoryRef, ScanWarning


class RepositoryError(Exception):
    """Fatal discovery/enumeration error."""


@dataclass
class RepositoryContext:
    root: Path
    repository: RepositoryRef
    statuses: dict[str, GitFileStatus]
    status_known: bool
    warnings: list[ScanWarning]


def git_command(root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    # Optional locks disabled: even status must not refresh the repository index.
    return subprocess.run(
        ["git", "--no-optional-locks", "-c", "core.fsmonitor=false", "-C", str(root), *args],
        capture_output=True,
        timeout=30,
        env={
            **{
                k: v
                for k, v in os.environ.items()
                if k
                not in {
                    "GIT_DIR",
                    "GIT_WORK_TREE",
                    "GIT_INDEX_FILE",
                    "GIT_COMMON_DIR",
                    "GIT_OBJECT_DIRECTORY",
                    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
                }
            },
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_NO_LAZY_FETCH": "1",
            "LC_ALL": "C",
        },
        check=False,
    )


def try_git(root: Path, warnings: list[ScanWarning], *args: str) -> bytes | None:
    try:
        result = git_command(root, *args)
        if result.returncode == 0:
            return result.stdout
    except (OSError, subprocess.TimeoutExpired):
        pass
    warnings.append(
        ScanWarning("git_command_failed", None, f"Git {args[0]} failed; metadata is limited.")
    )
    return None


def normalize_remote(remote: str) -> str | None:
    """Normalize network remotes without retaining credentials, query, or fragments."""
    try:
        if "://" in remote:
            url = urlsplit(remote)
            if url.scheme not in {"https", "http", "ssh", "git"} or not url.hostname:
                return None
            host, path = url.hostname.lower(), url.path
            if url.port and url.port not in {22, 80, 443, 9418}:
                host += f":{url.port}"
        else:
            match = re.fullmatch(r"(?:[^/@:]+@)?([^/:]+):(.+)", remote)
            if not match:
                return None
            host, path = match.group(1).lower(), match.group(2)
        path = path.strip("/")
        if path.endswith(".git"):
            path = path[:-4]
        return f"{host}/{path}" if path else None
    except ValueError:
        return None


def parse_status(data: bytes) -> dict[str, GitFileStatus]:
    """Parse porcelain v1 -z, including rename/copy second path fields."""
    entries = iter(data.split(b"\0"))
    statuses = {}
    for entry in entries:
        if not entry:
            continue
        state, path = entry[:2], os.fsdecode(entry[3:])
        statuses[path] = (
            GitFileStatus.UNTRACKED
            if state == b"??"
            else GitFileStatus.DELETED
            if b"D" in state
            else GitFileStatus.TRACKED_MODIFIED
        )
        if b"R" in state or b"C" in state:
            old_path = next(entries, b"")
            if old_path:
                statuses[os.fsdecode(old_path)] = GitFileStatus.DELETED
    return statuses


def discover_repository(path: Path | str) -> RepositoryContext:
    try:
        requested_root = Path(path).expanduser().resolve(strict=True)
        if not requested_root.is_dir():
            raise RepositoryError("Scan path must be an existing directory.")
    except (OSError, RuntimeError) as exc:
        raise RepositoryError("Scan path cannot be opened.") from exc
    root = requested_root
    warnings: list[ScanWarning] = []
    is_git = False
    if shutil.which("git"):
        try:
            top_result = git_command(requested_root, "rev-parse", "--show-toplevel")
            if top_result.returncode == 0:
                try:
                    git_dir_result = git_command(requested_root, "rev-parse", "--absolute-git-dir")
                    if git_dir_result.returncode != 0:
                        raise RepositoryError("Git repository identity could not be verified.")
                    if not top_result.stdout.strip() or not git_dir_result.stdout.strip():
                        raise RepositoryError("Git repository identity could not be verified.")
                    discovered_root = Path(
                        os.fsdecode(top_result.stdout.removesuffix(b"\n"))
                    ).resolve(strict=True)
                    requested_git_dir = Path(
                        os.fsdecode(git_dir_result.stdout.removesuffix(b"\n"))
                    ).resolve(strict=True)
                    normalized_git_dir_result = git_command(
                        discovered_root, "rev-parse", "--absolute-git-dir"
                    )
                    normalized_git_dir = (
                        Path(
                            os.fsdecode(normalized_git_dir_result.stdout.removesuffix(b"\n"))
                        ).resolve(strict=True)
                        if normalized_git_dir_result.returncode == 0
                        else None
                    )
                except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
                    raise RepositoryError("Git repository identity could not be verified.") from exc
                if (
                    discovered_root != requested_root
                    and discovered_root not in requested_root.parents
                ) or normalized_git_dir != requested_git_dir:
                    raise RepositoryError("Git repository identity could not be verified.")
                root = discovered_root
                is_git = True
            elif b"not a git repository" not in top_result.stderr:
                warnings.append(
                    ScanWarning(
                        "git_command_failed",
                        None,
                        "Git discovery failed; using filesystem discovery.",
                    )
                )
        except (OSError, subprocess.TimeoutExpired):
            warnings.append(
                ScanWarning(
                    "git_command_failed", None, "Git discovery failed; using filesystem discovery."
                )
            )
    else:
        warnings.append(
            ScanWarning(
                "git_command_failed", None, "Git is unavailable; using filesystem discovery."
            )
        )
    head = None
    dirty = None
    statuses = {}
    status_known = False
    remote = None
    if is_git:
        # A missing HEAD on an unborn symbolic branch is expected, not a Git failure.
        try:
            result = git_command(root, "rev-parse", "--verify", "--quiet", "HEAD")
            if result.returncode == 0:
                head = result.stdout.decode("ascii").strip()
            else:
                symbolic = git_command(root, "symbolic-ref", "-q", "HEAD")
                unborn = False
                if result.returncode == 1 and symbolic.returncode == 0:
                    ref = os.fsdecode(symbolic.stdout.removesuffix(b"\n"))
                    unborn = (
                        git_command(root, "show-ref", "--verify", "--quiet", ref).returncode == 1
                    )
                if not unborn:
                    warnings.append(
                        ScanWarning(
                            "git_command_failed",
                            None,
                            "Git HEAD lookup failed; revision is unavailable.",
                        )
                    )
        except (OSError, subprocess.TimeoutExpired):
            warnings.append(
                ScanWarning(
                    "git_command_failed", None, "Git HEAD lookup failed; revision is unavailable."
                )
            )
        status = try_git(
            root,
            warnings,
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            "--ignore-submodules=none",
        )
        if status is not None:
            dirty, status_known = bool(status), True
            statuses = parse_status(status)
        # Missing origin is ordinary, so do not warn for this optional lookup.
        try:
            result = git_command(root, "config", "--get", "remote.origin.url")
            if result.returncode == 0:
                remote = normalize_remote(os.fsdecode(result.stdout).strip())
        except (OSError, subprocess.TimeoutExpired):
            warnings.append(ScanWarning("git_command_failed", None, "Git remote lookup failed."))
    basis = "git_remote" if remote else "local_fallback"
    # Local identity includes name + resolved location, opaque in stable output.
    identity = remote or f"{root.name}\0{root}"
    repo_id = "repo_" + sha256(identity.encode("utf-8", "surrogateescape")).hexdigest()[:32]
    ref = RepositoryRef(repo_id, root.name, basis, is_git, head, dirty)
    return RepositoryContext(root, ref, statuses, status_known, warnings)
