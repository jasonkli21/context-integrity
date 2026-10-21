"""Exclusive descriptor-relative output publication, with rollback on ordinary pair failure."""

import os
from pathlib import Path
from uuid import uuid4

from context_integrity.derived_models import path_value, require


class DerivedOutputError(Exception):
    """Explicit outputs could not be published; input paths and OS errors are private."""


def output_path(root: Path, value: Path | str) -> str:
    value = Path(value)
    if value.is_absolute():
        try:
            value = value.relative_to(root)
        except ValueError as exc:
            raise DerivedOutputError("Derived outputs must be inside the repository.") from exc
    raw = str(value)
    try:
        path_value(raw)
    except ValueError as exc:
        raise DerivedOutputError("Invalid derived output path.") from exc
    return raw


def write_outputs(
    root: Path, outputs: tuple[tuple[str, bytes], ...], *, forbidden: set[str]
) -> None:
    """Prepare all bytes before publishing; never replace any existing path.

    POSIX cannot atomically publish two independent names. Ordinary failures roll back
    our published inodes. Process/power loss can leave a recoverable orphan; never
    report success before both links exist. A rollback failure is explicitly reported.
    """
    prepared = []
    published = []
    rollback_failed = False
    try:
        require(len({p for p, _ in outputs}) == len(outputs))
        for path, data in outputs:
            path_value(path)
            require(path not in forbidden)
            fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                for part in path.split("/")[:-1]:
                    child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                    os.close(fd)
                    fd = child
                name = path.split("/")[-1]
                try:
                    os.stat(name, dir_fd=fd, follow_symlinks=False)
                except FileNotFoundError:
                    pass
                else:
                    raise DerivedOutputError("Derived outputs already exist; use new paths.")
                temporary = ".derived-" + uuid4().hex
                temp_fd = os.open(
                    temporary,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                    0o600,
                    dir_fd=fd,
                )
                prepared.append((fd, temporary, name))
                fd = None
                with os.fdopen(temp_fd, "wb") as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
            finally:
                if fd is not None:
                    os.close(fd)
        for fd, temporary, name in prepared:
            os.link(temporary, name, src_dir_fd=fd, dst_dir_fd=fd, follow_symlinks=False)
            published.append((fd, temporary, name))
    except (OSError, ValueError, DerivedOutputError) as exc:
        for fd, temporary, name in reversed(published):
            try:
                if (
                    os.stat(name, dir_fd=fd, follow_symlinks=False).st_ino
                    == os.stat(temporary, dir_fd=fd, follow_symlinks=False).st_ino
                ):
                    os.unlink(name, dir_fd=fd)
                else:
                    rollback_failed = True
            except OSError:
                rollback_failed = True
        message = (
            "Derived output publication failed; partial outputs may remain."
            if rollback_failed
            else "Derived output publication failed; no outputs were retained."
        )
        raise DerivedOutputError(message) from exc
    finally:
        cleanup_failed = False
        for fd, temporary, _ in prepared:
            try:
                os.unlink(temporary, dir_fd=fd)
            except OSError:
                cleanup_failed = True
            finally:
                os.close(fd)
        if cleanup_failed:
            raise DerivedOutputError(
                "Derived output cleanup failed; partial outputs or temporary files may remain."
            )
