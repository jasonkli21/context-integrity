"""Typed inventory and authority values. No filesystem or rendering dependencies."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from pathlib import PurePosixPath
from typing import NewType

SourceId = NewType("SourceId", str)
ClaimId = NewType("ClaimId", str)


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
    claims: tuple[ClaimSpec, ...] = ()
    instruction_policy: InstructionPolicySpec | None = None
    drift_dependencies: tuple[DriftDependencySpec, ...] = ()
    context_contracts: tuple[ContextContract, ...] = ()

    def __post_init__(self) -> None:
        if self.context_contracts and self.schema_version < 5:
            raise ValueError("Repository contracts require configuration schema v5 or newer.")
        if not isinstance(self.context_contracts, tuple) or any(
            not isinstance(c, ContextContract) for c in self.context_contracts
        ):
            raise ValueError("Repository contracts must be a typed tuple.")
        contract_ids = [c.id for c in self.context_contracts]
        if len(set(contract_ids)) != len(contract_ids):
            raise ValueError("Duplicate contract ID.")
        ids = [dependency.id for dependency in self.drift_dependencies]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate drift dependency ID.")


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


class ClaimValidity(StrEnum):
    UNVERIFIED = "unverified"


def _validate_claim_identifier(value: str, label: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"[a-z][a-z0-9_-]*", value):
        raise ValueError(f"Invalid claim {label}.")


def validate_unique_claim_ids(claims: tuple[ClaimSpec, ...] | tuple[ClaimRecord, ...]) -> None:
    ids = [claim.id for claim in claims]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate claim ID.")


@dataclass(frozen=True)
class ClaimSpec:
    id: ClaimId
    claim_type: str
    subject: str
    predicate: str
    value: str
    scope: str | None = None
    depends_on: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_claim_identifier(self.id, "ID")
        _validate_claim_identifier(self.claim_type, "type")


@dataclass(frozen=True)
class ClaimProvenance:
    source_id: SourceId
    path: str
    revision: SourceRevision
    locator: str
    extraction_method: str
    extractor_version: str


@dataclass(frozen=True)
class ClaimDiagnostic:
    claim_id: ClaimId
    code: str
    path: str
    message: str

    def __post_init__(self) -> None:
        _validate_claim_identifier(self.claim_id, "ID")


@dataclass(frozen=True)
class ClaimDependency:
    path: str
    source_id: SourceId | None
    revision: SourceRevision | None
    resolved: bool


@dataclass(frozen=True)
class ClaimRecord:
    id: ClaimId
    claim_type: str
    subject: str
    predicate: str
    value: str
    scope: str | None
    validity: ClaimValidity
    provenance: ClaimProvenance
    dependencies: tuple[ClaimDependency, ...]
    provenance_complete: bool

    def __post_init__(self) -> None:
        _validate_claim_identifier(self.id, "ID")
        _validate_claim_identifier(self.claim_type, "type")


@dataclass(frozen=True)
class ClaimsOverview:
    repository: RepositoryRef
    config_sha256: str | None
    claims: tuple[ClaimRecord, ...]
    warnings: tuple[ScanWarning, ...]
    diagnostics: tuple[ClaimDiagnostic, ...] = ()
    schema_version: int = 1


@dataclass(frozen=True)
class InstructionPolicySpec:
    canonical: str
    compatibility: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.compatibility, tuple):
            raise ValueError("Compatibility instruction paths must be a tuple.")
        _validate_integrity_path(self.canonical)
        for path in self.compatibility:
            _validate_integrity_path(path)
        paths = (self.canonical, *self.compatibility)
        if ".context-integrity.toml" in paths or len(set(paths)) != len(paths):
            raise ValueError("Instruction paths must be distinct and cannot reference config.")


@dataclass(frozen=True)
class DriftDependencySpec:
    id: str
    dependent: str
    upstream: tuple[str, ...]
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not re.fullmatch(r"[a-z][a-z0-9_-]*", self.id):
            raise ValueError("Invalid drift dependency ID.")
        if not isinstance(self.upstream, tuple):
            raise ValueError("Drift upstream paths must be a tuple.")
        _validate_integrity_path(self.dependent)
        for path in self.upstream:
            _validate_integrity_path(path)
        if (
            not self.upstream
            or len(set(self.upstream)) != len(self.upstream)
            or self.dependent in self.upstream
            or self.dependent == ".context-integrity.toml"
        ):
            raise ValueError("Invalid drift dependency paths.")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("Drift dependency reason must be nonblank.")


def _validate_integrity_path(path: str) -> None:
    """Require an already-normalized safe repository-relative POSIX path."""
    if (
        not isinstance(path, str)
        or not path
        or "\0" in path
        or "\\" in path
        or ":" in path
        or path.endswith("/")
    ):
        raise ValueError("Invalid repository-relative path.")
    pure = PurePosixPath(path)
    if pure.is_absolute() or ".." in pure.parts or not pure.parts or pure.as_posix() != path:
        raise ValueError("Path must be normalized and repository-relative.")


class FindingSeverity(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ChangeScope(StrEnum):
    WORKING_TREE = "working_tree"
    GIT_RANGE = "git_range"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class ChangeSet:
    scope: ChangeScope
    changed_paths: tuple[str, ...] = ()
    base_revision: str | None = None
    target_revision: str | None = None
    derivation: str = "local_git"


@dataclass(frozen=True)
class IntegrityEvidence:
    role: str
    path: str
    source_id: SourceId | None = None
    source_revision: SourceRevision | None = None
    derivation: str = "inventory"


@dataclass(frozen=True)
class IntegrityFinding:
    id: str
    rule_id: str
    code: str
    severity: FindingSeverity
    message: str
    affected_paths: tuple[str, ...]
    evidence: tuple[IntegrityEvidence, ...]
    dependency_id: str | None = None


@dataclass(frozen=True)
class IntegrityOverview:
    repository: RepositoryRef
    config_sha256: str | None
    change_set: ChangeSet
    findings: tuple[IntegrityFinding, ...]
    warnings: tuple[ScanWarning, ...]
    schema_version: int = 1


class ContextRuleMode(StrEnum):
    REQUIRED = "required"
    OPTIONAL = "optional"
    EXCLUDED = "excluded"


def _contract_identifier(value: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"[a-z][a-z0-9_-]*", value):
        raise ValueError("Invalid contract identifier.")


@dataclass(frozen=True)
class ContextContractRule:
    id: str
    mode: ContextRuleMode
    paths: tuple[str, ...] = ()
    kinds: tuple[SourceKind, ...] = ()
    authority_classes: tuple[AuthorityClass, ...] = ()
    lifecycles: tuple[LifecycleState, ...] = ()
    min_count: int | None = None
    max_count: int | None = None

    def __post_init__(self) -> None:
        _contract_identifier(self.id)
        if not isinstance(self.mode, ContextRuleMode):
            raise ValueError("Invalid contract rule mode.")
        dimensions = (self.paths, self.kinds, self.authority_classes, self.lifecycles)
        for values, cls in zip(
            dimensions, (str, SourceKind, AuthorityClass, LifecycleState), strict=True
        ):
            if not isinstance(values, tuple) or any(not isinstance(v, cls) for v in values):
                raise ValueError("Contract selectors must be typed tuples.")
            if len(set(values)) != len(values):
                raise ValueError("Duplicate contract selector value.")
        if not any(dimensions):
            raise ValueError("Contract rule requires a selector.")
        for path in self.paths:
            _validate_integrity_path(path)
        for count in (self.min_count, self.max_count):
            if count is not None and (type(count) is not int or count < 0):
                raise ValueError("Contract counts must be nonnegative integers.")
        minimum = self.min_count
        maximum = self.max_count
        if self.mode == ContextRuleMode.REQUIRED:
            minimum = 1 if minimum is None else minimum
            if minimum < 1:
                raise ValueError("Required rules need a positive minimum.")
        else:
            minimum = 0 if minimum is None else minimum
            if minimum != 0:
                raise ValueError("Optional/excluded rules cannot require a minimum.")
        if self.mode == ContextRuleMode.EXCLUDED:
            maximum = 0 if maximum is None else maximum
            if maximum != 0:
                raise ValueError("Excluded rules must exclude every match.")
        if maximum is not None and maximum < minimum:
            raise ValueError("Contract maximum is less than minimum.")
        object.__setattr__(self, "min_count", minimum)
        object.__setattr__(self, "max_count", maximum)


@dataclass(frozen=True)
class ContextContract:
    id: str
    task_class: str
    description: str
    rules: tuple[ContextContractRule, ...]
    config_revision: str | None = None

    def __post_init__(self) -> None:
        _contract_identifier(self.id)
        _contract_identifier(self.task_class)
        if not isinstance(self.description, str) or not self.description.strip():
            raise ValueError("Contract description must be nonblank.")
        if (
            not isinstance(self.rules, tuple)
            or not self.rules
            or any(not isinstance(r, ContextContractRule) for r in self.rules)
        ):
            raise ValueError("Contract requires a nonempty tuple of rules.")
        if len({r.id for r in self.rules}) != len(self.rules):
            raise ValueError("Duplicate contract rule ID.")


@dataclass(frozen=True)
class ContextPackage:
    requested_paths: tuple[str, ...]
    resolved_sources: tuple[SourceRecord, ...]
    unresolved_paths: tuple[str, ...]
    duplicate_paths: tuple[str, ...]


@dataclass(frozen=True)
class ContextRuleResult:
    rule_id: str
    mode: ContextRuleMode
    matched_paths: tuple[str, ...]
    match_count: int
    min_count: int
    max_count: int | None
    satisfied: bool


@dataclass(frozen=True)
class ContractFinding:
    id: str
    contract_id: str
    rule_id: str | None
    code: str
    severity: FindingSeverity
    message: str
    affected_paths: tuple[str, ...]


@dataclass(frozen=True)
class ContractValidationOverview:
    repository: RepositoryRef
    config_sha256: str | None
    contract: ContextContract
    package: ContextPackage
    rule_results: tuple[ContextRuleResult, ...]
    findings: tuple[ContractFinding, ...]
    warnings: tuple[ScanWarning, ...]
    schema_version: int = 1
