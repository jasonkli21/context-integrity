"""Local observations and provider contract v1; integrity policy lives separately."""

import os
import re
import subprocess
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from context_integrity.acquisition import normalize_path, read_source_bytes
from context_integrity.models import (
    CandidateOrigin,
    ChangeScope,
    ChangeSet,
    CompilerCandidate,
    RepositoryRef,
    ScanWarning,
    SourceRecord,
    _validate_integrity_path,
    make_source_id,
    usable_content_revision,
)
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


# Provider contract v1. Runtime roots exist only on requests, never on results.


class EvidenceProviderError(Exception):
    """Sanitized, typed provider failure. Never includes upstream text."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(f"Evidence provider failed ({code}).")


@dataclass(frozen=True)
class EvidenceProviderDescriptor:
    id: str
    version: str
    contract_version: int = 1
    capabilities: tuple[str, ...] = ("context_candidates",)
    derivation: str = "provider-v1"

    def __post_init__(self):
        if (
            not re.fullmatch(r"[a-z][a-z0-9-]*", self.id)
            or not re.fullmatch(r"[A-Za-z0-9_.+-]{1,80}", self.version)
            or type(self.contract_version) is not int
            or self.contract_version != 1
            or "context_candidates" not in self.capabilities
            or len(set(self.capabilities)) != len(self.capabilities)
            or set(self.capabilities) - {"context_candidates", "change_context"}
            or not re.fullmatch(r"[a-z0-9_-]{1,80}", self.derivation)
        ):
            raise ValueError("Invalid evidence provider descriptor.")


@dataclass(frozen=True)
class EvidenceContextRequest:
    repository_root: Path
    repository: RepositoryRef
    task: str
    acquisition_budget_bytes: int = 1024 * 1024
    change_range: str | None = None

    def __post_init__(self):
        if not isinstance(self.task, str) or not self.task.strip() or "\0" in self.task:
            raise ValueError("Provider compilation requires nonblank task text.")
        if type(self.acquisition_budget_bytes) is not int or not (
            1 <= self.acquisition_budget_bytes <= 16 * 1024 * 1024
        ):
            raise ValueError("Evidence budget must be between 1 and 16777216 bytes.")
        if self.change_range is not None and (
            not isinstance(self.change_range, str)
            or not self.change_range.strip()
            or "\0" in self.change_range
        ):
            raise ValueError("Invalid evidence change range.")


@dataclass(frozen=True)
class EvidenceRepositorySnapshot:
    repository_id: str
    git_head: str | None
    git_dirty: bool | None
    provider_schema_version: int = 1
    command: str = "context"

    def __post_init__(self):
        if (
            not self.repository_id
            or type(self.provider_schema_version) is not int
            or self.provider_schema_version != 1
            or self.command != "context"
            or (
                self.git_head is not None
                and not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", self.git_head)
            )
            or (self.git_dirty is not None and type(self.git_dirty) is not bool)
        ):
            raise ValueError("Invalid evidence snapshot.")


@dataclass(frozen=True)
class EvidenceCoverage:
    signals: tuple[tuple[str, int | bool], ...]
    incomplete: bool

    def __post_init__(self):
        keys = [k for k, _ in self.signals]
        if (
            keys != sorted(set(keys))
            or any(
                not re.fullmatch(r"[a-z0-9_]+", k) or type(v) not in {int, bool} or v < 0
                for k, v in self.signals
            )
            or type(self.incomplete) is not bool
        ):
            raise ValueError("Invalid evidence coverage.")


@dataclass(frozen=True)
class EvidenceProviderState:
    descriptor: EvidenceProviderDescriptor
    snapshot: EvidenceRepositorySnapshot
    task: str
    ranker_version: str
    acquisition_budget_bytes: int
    coverage: EvidenceCoverage
    change: tuple[tuple[str, str | int], ...] = ()
    fallback_mode: str | None = None
    warnings: tuple[ScanWarning, ...] = ()

    def __post_init__(self):
        if (
            not isinstance(self.task, str)
            or not self.task.strip()
            or not isinstance(self.ranker_version, str)
            or not re.fullmatch(r"[A-Za-z0-9_.+-]{1,100}", self.ranker_version)
            or type(self.acquisition_budget_bytes) is not int
            or not 1 <= self.acquisition_budget_bytes <= 16 * 1024 * 1024
            or (self.change and "change_context" not in self.descriptor.capabilities)
        ):
            raise ValueError("Invalid evidence provider state.")


@dataclass(frozen=True)
class EvidenceContextBatch:
    state: EvidenceProviderState
    candidates: tuple[CompilerCandidate, ...]

    def __post_init__(self):
        paths = [c.path for c in self.candidates]
        if len(set(paths)) != len(paths):
            raise EvidenceProviderError("duplicate_path")
        for c in self.candidates:
            _validate_integrity_path(c.path)
            if (
                c.origin != CandidateOrigin.EVIDENCE_PROVIDER
                or c.provider_id != self.state.descriptor.id
                or c.provider_version != self.state.descriptor.version
                or c.id != make_source_id(self.state.snapshot.repository_id, c.path)
                or c.source is None
                or CompilerCandidate.from_source(c.source)
                != CompilerCandidate(
                    c.id,
                    c.path,
                    c.kind,
                    c.authority_class,
                    c.lifecycle,
                    c.revision,
                    c.size_bytes,
                    source=c.source,
                )
                or c.revision.git_head != self.state.snapshot.git_head
                or not usable_content_revision(c.revision)
                or type(c.size_bytes) is not int
                or c.size_bytes < 0
                or c.relevance is None
                or type(c.relevance.rank) is not int
                or c.relevance.rank < 1
            ):
                raise EvidenceProviderError("invalid_candidate")


class EvidenceProvider(Protocol):
    def context_candidates(self, request: EvidenceContextRequest) -> EvidenceContextBatch:
        """Return body-free, snapshot-scoped candidates or a typed failure."""
        ...
