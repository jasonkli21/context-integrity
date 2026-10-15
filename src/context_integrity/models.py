"""Typed inventory and authority values. No filesystem or rendering dependencies."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from typing import NewType

SourceId = NewType("SourceId", str)


class SourceKind(StrEnum):
    CONFIGURATION = "configuration"
    AGENT_INSTRUCTION = "agent_instruction"
    README = "readme"
    ARCHITECTURE = "architecture"
    PRODUCT_REQUIREMENT = "product_requirement"
    DECISION_RECORD = "decision_record"
    CURRENT_STATE = "current_state"
    IMPLEMENTATION_PLAN = "implementation_plan"
    REVIEW = "review"
    VERIFICATION_RECORD = "verification_record"
    RELEASE_RECORD = "release_record"
    HANDOFF = "handoff"
    GENERATED_SUMMARY = "generated_summary"
    OTHER_DOCUMENT = "other_document"
    UNKNOWN = "unknown"


class AuthorityClass(StrEnum):
    EXECUTABLE_TRUTH = "executable_truth"
    VERIFICATION_EVIDENCE = "verification_evidence"
    DECISION = "decision"
    ARCHITECTURE_PRODUCT = "architecture_product"
    OPERATING_INSTRUCTION = "operating_instruction"
    PLAN = "plan"
    GENERATED_DERIVATIVE = "generated_derivative"
    HISTORICAL = "historical"
    UNKNOWN = "unknown"


class LifecycleState(StrEnum):
    UNKNOWN = "unknown"
    DRAFT = "draft"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    HISTORICAL = "historical"
    EXPIRED = "expired"
    INVALID = "invalid"


class ClassificationConfidence(StrEnum):
    EXPLICIT = "explicit"
    STRONG = "strong"
    HEURISTIC = "heuristic"
    UNKNOWN = "unknown"


class GitFileStatus(StrEnum):
    TRACKED_CLEAN = "tracked_clean"
    TRACKED_MODIFIED = "tracked_modified"
    UNTRACKED = "untracked"
    DELETED = "deleted"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class RepositoryRef:
    id: str
    name: str
    identity_basis: str
    git_available: bool
    git_head: str | None
    git_dirty: bool | None


@dataclass(frozen=True)
class SourceRevision:
    content_sha256: str | None
    git_head: str | None
    git_status: GitFileStatus
    observed_revision_basis: str


@dataclass(frozen=True)
class RuleMatch:
    rule_id: str
    dimension: str
    result: str
    confidence: ClassificationConfidence
    basis: str


@dataclass(frozen=True)
class ClassificationResult:
    kind: SourceKind
    authority_class: AuthorityClass
    lifecycle: LifecycleState
    confidence: ClassificationConfidence
    matched_rules: tuple[str, ...]
    basis: tuple[RuleMatch, ...]


@dataclass(frozen=True)
class SourceRecord:
    id: SourceId
    path: str
    kind: SourceKind
    authority_class: AuthorityClass
    lifecycle: LifecycleState
    revision: SourceRevision
    classification: ClassificationResult
    size_bytes: int | None
    source_metadata: SourceMetadata | None = None


@dataclass(frozen=True)
class ScanWarning:
    code: str
    path: str | None
    message: str


@dataclass(frozen=True)
class InventorySummary:
    source_count: int
    by_kind: dict[str, int]
    by_authority_class: dict[str, int]
    by_lifecycle: dict[str, int]
    warning_count: int
    unclassified_kind_count: int
    unclassified_authority_count: int


@dataclass(frozen=True)
class InventoryManifest:
    repository: RepositoryRef
    sources: tuple[SourceRecord, ...]
    summary: InventorySummary
    warnings: tuple[ScanWarning, ...]
    schema_version: int = 1
    repository_config: RepositoryConfig | None = None
    supersession: tuple[ResolvedSupersession, ...] = ()


def make_source_id(repository_id: str, normalized_path: str) -> SourceId:
    digest = sha256(f"{repository_id}\0{normalized_path}".encode("utf-8", "surrogateescape"))
    return SourceId("src_" + digest.hexdigest()[:32])


@dataclass(frozen=True)
class AuthorityTier:
    classes: tuple[AuthorityClass, ...]

    def __post_init__(self) -> None:
        if not self.classes or len(set(self.classes)) != len(self.classes):
            raise ValueError("Authority tiers must be nonempty with distinct classes.")
        if any(
            c not in AuthorityClass or c in {AuthorityClass.HISTORICAL, AuthorityClass.UNKNOWN}
            for c in self.classes
        ):
            raise ValueError("Invalid active authority class.")


@dataclass(frozen=True)
class AuthorityPolicy:
    id: str
    description: str
    tiers: tuple[AuthorityTier, ...]
    origin: str = "builtin"
    policy_version: str = "builtin-v1"
    config_revision: str | None = None

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9_-]*", self.id):
            raise ValueError("Invalid authority policy ID.")
        classes = [c for t in self.tiers for c in t.classes]
        if not self.tiers or len(set(classes)) != len(classes):
            raise ValueError("Policy tiers must be nonempty without repeated classes.")


@dataclass(frozen=True)
class SourceMetadata:
    path: str
    reason: str
    authority_class_override: AuthorityClass | None = None
    authority_eligible: bool | None = None
    lifecycle_override: LifecycleState | None = None


@dataclass(frozen=True)
class RepositoryConfig:
    policies: tuple[AuthorityPolicy, ...] = ()
    source_metadata: tuple[SourceMetadata, ...] = ()
    content_sha256: str | None = None
    schema_version: int = 1
    supersession: tuple[SupersessionSpec, ...] = ()


@dataclass(frozen=True)
class AuthorityCandidate:
    source: SourceRecord
    tier_index: int


@dataclass(frozen=True)
class AuthorityExclusion:
    source: SourceRecord
    reason: str
    metadata_reason: str | None = None


class AuthorityResolutionStatus(StrEnum):
    CANDIDATES_FOUND = "candidates_found"
    NO_ELIGIBLE_CANDIDATES = "no_eligible_candidates"


@dataclass(frozen=True)
class AuthorityResolution:
    repository: RepositoryRef
    policy: AuthorityPolicy
    config_sha256: str | None
    status: AuthorityResolutionStatus
    highest_observed_tier: int | None
    highest_candidates: tuple[AuthorityCandidate, ...]
    lower_candidates: tuple[AuthorityCandidate, ...]
    missing_stronger_tiers: tuple[int, ...]
    excluded: tuple[AuthorityExclusion, ...]
    warnings: tuple[ScanWarning, ...]


@dataclass(frozen=True)
class SupersessionSpec:
    source_path: str
    superseded_by_path: str
    reason: str


@dataclass(frozen=True)
class ResolvedSupersession:
    source: SourceRecord
    superseded_by: SourceRecord
    reason: str
    config_sha256: str | None


class LifecycleOrigin(StrEnum):
    FALLBACK_UNKNOWN = "fallback_unknown"
    PATH_HEURISTIC = "path_heuristic"
    REPOSITORY_METADATA = "repository_metadata"
    SUPERSESSION = "supersession"


@dataclass(frozen=True)
class LifecycleEntry:
    source: SourceRecord
    origin: LifecycleOrigin
    reason: str
    superseded_by: ResolvedSupersession | None = None
    supersedes: tuple[ResolvedSupersession, ...] = ()


@dataclass(frozen=True)
class LifecycleOverview:
    repository: RepositoryRef
    config_sha256: str | None
    sources: tuple[LifecycleEntry, ...]
    supersession: tuple[ResolvedSupersession, ...]
    warnings: tuple[ScanWarning, ...]
