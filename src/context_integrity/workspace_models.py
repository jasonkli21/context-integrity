"""Workspace-only typed declarations and observations; no filesystem operations."""

from dataclasses import dataclass
from enum import StrEnum

from context_integrity.derived_models import digest, path_value, repo_value, require, token
from context_integrity.models import ClaimRecord


class RuleKind(StrEnum):
    CONTRACT_PIN = "contract_pin"
    MIRROR_BYTES = "mirror_bytes"
    CLAIM_MATCH = "claim_match"


class Signal(StrEnum):
    ALIGNED = "aligned"
    REVIEW = "review_required"
    DISAGREEMENT = "declared_disagreement"
    UNKNOWN = "not_established"


@dataclass(frozen=True)
class QualifiedSourceRef:
    repo_alias: str
    repository_id: str
    path: str

    def __post_init__(self):
        token(self.repo_alias)
        repo_value(self.repository_id)
        path_value(self.path)


@dataclass(frozen=True)
class QualifiedClaimRef:
    repo_alias: str
    repository_id: str
    claim_id: str

    def __post_init__(self):
        token(self.repo_alias)
        repo_value(self.repository_id)
        token(self.claim_id)


@dataclass(frozen=True)
class RepositorySpec:
    alias: str
    root: str
    repository_id: str

    def __post_init__(self):
        token(self.alias)
        repo_value(self.repository_id)
        root_value(self.root)


@dataclass(frozen=True)
class CheckSpec:
    id: str
    kind: RuleKind
    left_repo: str
    left: str
    right_repo: str
    right: str

    def __post_init__(self):
        token(self.id)
        require(isinstance(self.kind, RuleKind))
        token(self.left_repo)
        token(self.right_repo)
        require(self.left_repo != self.right_repo)
        validate = token if self.kind == RuleKind.CLAIM_MATCH else path_value
        validate(self.left)
        validate(self.right)


@dataclass(frozen=True)
class ContextTarget:
    repo: str
    contract_id: str
    budget_bytes: int

    def __post_init__(self):
        token(self.repo)
        token(self.contract_id)
        require(type(self.budget_bytes) is int and 1 <= self.budget_bytes <= 64 * 1024 * 1024)


@dataclass(frozen=True)
class WorkspaceSpec:
    manifest_sha256: str
    repositories: tuple[RepositorySpec, ...]
    checks: tuple[CheckSpec, ...]
    context_targets: tuple[ContextTarget, ...]

    def __post_init__(self):
        digest(self.manifest_sha256)
        require(type(self.repositories) is tuple and 2 <= len(self.repositories) <= 8)
        require(all(isinstance(r, RepositorySpec) for r in self.repositories))
        aliases = {r.alias for r in self.repositories}
        require(len(aliases) == len(self.repositories))
        require(len({r.repository_id for r in self.repositories}) == len(self.repositories))
        require(type(self.checks) is tuple and len(self.checks) <= 128)
        require(all(isinstance(c, CheckSpec) for c in self.checks))
        require(len({c.id for c in self.checks}) == len(self.checks))
        require(all(c.left_repo in aliases and c.right_repo in aliases for c in self.checks))
        require(type(self.context_targets) is tuple and len(self.context_targets) <= 16)
        require(
            all(isinstance(t, ContextTarget) and t.repo in aliases for t in self.context_targets)
        )
        require(
            len({(t.repo, t.contract_id) for t in self.context_targets})
            == len(self.context_targets)
        )
        require(sum(t.budget_bytes for t in self.context_targets) <= 64 * 1024 * 1024)


@dataclass(frozen=True)
class ContractLock:
    producer_repository_id: str
    producer_path: str
    accepted_sha256: str

    def __post_init__(self):
        repo_value(self.producer_repository_id)
        path_value(self.producer_path)
        digest(self.accepted_sha256)


@dataclass(frozen=True)
class SourceObservation:
    ref: QualifiedSourceRef
    state: str
    content_sha256: str | None
    lifecycle: str | None = None
    authority: str | None = None

    def __post_init__(self):
        require(isinstance(self.ref, QualifiedSourceRef))
        require(
            self.state in {"observed", "missing", "unobservable", "too_large", "budget_exceeded"}
        )
        digest(self.content_sha256, nullable=True)
        require((self.state == "observed") == (self.content_sha256 is not None))


@dataclass(frozen=True)
class ClaimObservation:
    ref: QualifiedClaimRef
    claim: ClaimRecord | None
    sources: tuple[SourceObservation, ...]
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class WorkspaceFinding:
    id: str
    kind: RuleKind
    signal: Signal
    reasons: tuple[str, ...]
    sources: tuple[SourceObservation, ...] = ()
    claims: tuple[ClaimObservation, ...] = ()
    accepted_sha256: str | None = None

    @property
    def evaluation_status(self):
        return "inconclusive" if self.signal == Signal.UNKNOWN else "evaluated"


def aggregate(findings: tuple[WorkspaceFinding, ...]) -> str:
    if any(f.signal in {Signal.REVIEW, Signal.DISAGREEMENT} for f in findings):
        return "review_required"
    if not findings or any(f.signal == Signal.UNKNOWN for f in findings):
        return "inconclusive"
    return "aligned_observed"


def root_value(value):
    require(isinstance(value, str) and 0 < len(value) <= 512)
    require(not value.startswith("/") and len(value.split("/")) <= 32)
    require(all(32 <= ord(c) < 127 for c in value) and not any(c in value for c in "\\:*?[]"))
    require(all(p and p.lower() != ".git" for p in value.split("/")))
