"""Typed inventory and authority values. No filesystem or rendering dependencies."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, NewType

if TYPE_CHECKING:
    from context_integrity.evidence import EvidenceProviderState

SourceId = NewType("SourceId", str)
ClaimId = NewType("ClaimId", str)


class SourceKind(StrEnum):
    SOURCE_CODE = "source_code"
    TEST = "test"
    SCHEMA = "schema"
    MIGRATION = "migration"
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


PROVIDER_SOURCE_KINDS = frozenset(
    {SourceKind.SOURCE_CODE, SourceKind.TEST, SourceKind.SCHEMA, SourceKind.MIGRATION}
)
SUPPORTED_CONFIG_SCHEMA_VERSIONS = frozenset({1, 2, 3, 4, 5, 6, 7})


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
        if (
            type(self.schema_version) is not int
            or self.schema_version not in SUPPORTED_CONFIG_SCHEMA_VERSIONS
        ):
            raise ValueError("Unsupported configuration schema version.")
        if self.context_contracts and self.schema_version < 5:
            raise ValueError("Repository contracts require configuration schema v5 or newer.")
        if not isinstance(self.context_contracts, tuple) or any(
            not isinstance(c, ContextContract) for c in self.context_contracts
        ):
            raise ValueError("Repository contracts must be a typed tuple.")
        if self.schema_version < 6 and any(
            c.budget_bytes is not None
            or any(r.priority or r.authority_policy is not None for r in c.rules)
            for c in self.context_contracts
        ):
            raise ValueError("Compiler policy requires configuration schema v6.")
        if self.schema_version < 7 and any(
            kind in PROVIDER_SOURCE_KINDS
            for c in self.context_contracts
            for r in c.rules
            for kind in r.kinds
        ):
            raise ValueError("Provider source kinds require configuration schema v7.")
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


class IntegrityEvaluationStatus(StrEnum):
    NOT_EVALUATED = "not_evaluated"
    EVALUATED = "evaluated"


@dataclass(frozen=True)
class CompiledIntegrityState:
    evaluation_status: IntegrityEvaluationStatus = IntegrityEvaluationStatus.NOT_EVALUATED
    findings: tuple[IntegrityFinding, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.evaluation_status, IntegrityEvaluationStatus):
            raise ValueError("Invalid integrity evaluation status.")
        if not isinstance(self.findings, tuple) or any(
            not isinstance(f, IntegrityFinding) for f in self.findings
        ):
            raise ValueError("Integrity findings must be a typed tuple.")
        if self.evaluation_status == IntegrityEvaluationStatus.NOT_EVALUATED and self.findings:
            raise ValueError("Unevaluated integrity state cannot contain findings.")


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
    priority: int = 0
    authority_policy: str | None = None

    def __post_init__(self) -> None:
        _contract_identifier(self.id)
        if type(self.priority) is not int or self.priority < 0:
            raise ValueError("Priority must be a nonnegative integer.")
        if self.authority_policy is not None:
            _contract_identifier(self.authority_policy)
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
    budget_bytes: int | None = None

    def __post_init__(self) -> None:
        _positive_budget(self.budget_bytes)
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


class CompilationStatus(StrEnum):
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"


class CandidateDecisionKind(StrEnum):
    SELECTED = "selected"
    EXCLUDED_BY_CONTRACT = "excluded_by_contract"
    INELIGIBLE_LIFECYCLE = "ineligible_lifecycle"
    INELIGIBLE_AUTHORITY = "ineligible_authority"
    LOWER_AUTHORITY_TIER = "lower_authority_tier"
    BLOCKED_BY_RULE_MAX = "blocked_by_rule_max"
    BLOCKED_BY_BUDGET = "blocked_by_budget"
    UNVERIFIABLE_REVISION = "unverifiable_revision"
    UNVERIFIABLE_SIZE = "unverifiable_size"
    REDUNDANT = "redundant"
    NOT_SELECTED = "not_selected"


def _positive_budget(value: int | None) -> None:
    if value is not None and (type(value) is not int or value <= 0):
        raise ValueError("Byte budget must be a positive integer.")


@dataclass(frozen=True)
class CompilationBudget:
    configured_bytes: int | None
    requested_bytes: int | None
    used_bytes: int

    def __post_init__(self) -> None:
        _positive_budget(self.configured_bytes)
        _positive_budget(self.requested_bytes)
        if type(self.used_bytes) is not int or self.used_bytes < 0:
            raise ValueError("Used bytes must be a nonnegative integer.")
        if self.effective_bytes is not None and self.used_bytes > self.effective_bytes:
            raise ValueError("Compilation exceeds byte budget.")

    @property
    def effective_bytes(self) -> int | None:
        return self.requested_bytes if self.requested_bytes is not None else self.configured_bytes

    @property
    def remaining_bytes(self) -> int | None:
        return None if self.effective_bytes is None else self.effective_bytes - self.used_bytes

    @property
    def origin(self) -> str:
        return (
            "override"
            if self.requested_bytes is not None
            else ("contract" if self.configured_bytes is not None else "unbounded")
        )


@dataclass(frozen=True)
class CompiledRuleDecision:
    rule_id: str
    reason: CandidateDecisionKind
    authority_policy: str | None = None
    tier_index: int | None = None
    highest_tier_index: int | None = None
    equal_tier_paths: tuple[str, ...] = ()
    authority_exclusion: str | None = None


@dataclass(frozen=True)
class CompiledSourceDecision:
    source: CompilerCandidate
    decision: CandidateDecisionKind
    matched_rule_ids: tuple[str, ...]
    contributing_rule_ids: tuple[str, ...]
    rule_decisions: tuple[CompiledRuleDecision, ...]


@dataclass(frozen=True)
class CompiledDependency:
    source_id: SourceId
    path: str
    source_revision: SourceRevision

    def __post_init__(self) -> None:
        _validate_integrity_path(self.path)
        if not usable_content_revision(self.source_revision):
            raise ValueError("Compiled dependency requires a content SHA256.")


class CandidateOrigin(StrEnum):
    INVENTORY = "inventory"
    EVIDENCE_PROVIDER = "evidence_provider"


@dataclass(frozen=True)
class CandidateRelevance:
    rank: int
    score: int
    score_components: tuple[tuple[str, int], ...]
    reasons: tuple[str, ...]
    matched_entities: tuple[tuple[str, str, int, int], ...] = ()
    matched_entities_omitted: int = 0
    graph_distance: int | None = None
    change_distance: int | None = None

    def __post_init__(self) -> None:
        safe_token = re.compile(r"[a-z][a-z0-9_-]{0,79}")
        if (
            type(self.rank) is not int
            or self.rank < 1
            or type(self.score) is not int
            or self.score < 0
            or not isinstance(self.score_components, tuple)
            or any(
                not isinstance(item, tuple)
                or len(item) != 2
                or not isinstance(item[0], str)
                or not safe_token.fullmatch(item[0])
                or type(item[1]) is not int
                or item[1] < 0
                for item in self.score_components
            )
            or tuple(sorted(self.score_components)) != self.score_components
            or len({key for key, _ in self.score_components}) != len(self.score_components)
            or not isinstance(self.reasons, tuple)
            or any(
                not isinstance(reason, str) or not safe_token.fullmatch(reason)
                for reason in self.reasons
            )
            or tuple(sorted(set(self.reasons))) != self.reasons
            or not isinstance(self.matched_entities, tuple)
            or any(
                not isinstance(entity, tuple)
                or len(entity) != 4
                or not isinstance(entity[0], str)
                or not safe_token.fullmatch(entity[0])
                or not isinstance(entity[1], str)
                or not safe_token.fullmatch(entity[1])
                or type(entity[2]) is not int
                or type(entity[3]) is not int
                or entity[2] < 0
                or entity[3] < entity[2]
                for entity in self.matched_entities
            )
            or tuple(sorted(set(self.matched_entities))) != self.matched_entities
            or type(self.matched_entities_omitted) is not int
            or self.matched_entities_omitted < 0
            or any(
                distance is not None and (type(distance) is not int or distance < 0)
                for distance in (self.graph_distance, self.change_distance)
            )
        ):
            raise ValueError("Invalid normalized candidate relevance.")


@dataclass(frozen=True)
class CompilerCandidate:
    """Selection-core item; SourceRecord is an optional inventory adapter payload."""

    id: str
    path: str
    kind: SourceKind
    authority_class: AuthorityClass
    lifecycle: LifecycleState
    revision: SourceRevision
    size_bytes: int | None
    source: SourceRecord | None = None
    evidence_location: str | None = None
    derivation: str | None = None
    origin: CandidateOrigin = CandidateOrigin.INVENTORY
    provider_id: str | None = None
    provider_version: str | None = None
    relevance: CandidateRelevance | None = None

    def __post_init__(self) -> None:
        if self.origin == CandidateOrigin.EVIDENCE_PROVIDER:
            safe_id = re.compile(r"[a-z][a-z0-9_-]{0,79}(?::[A-Za-z0-9_.+-]{1,100})?")
            if (
                not isinstance(self.evidence_location, str)
                or not self.evidence_location
                or self.evidence_location.startswith("/")
                or "\\" in self.evidence_location
                or any(part in {"", ".", ".."} for part in self.evidence_location.split("/"))
                or not isinstance(self.derivation, str)
                or len(self.derivation) > 200
                or not all(safe_id.fullmatch(part) for part in self.derivation.split(":"))
                or not isinstance(self.provider_id, str)
                or not re.fullmatch(r"[a-z][a-z0-9-]{0,79}", self.provider_id)
                or not isinstance(self.provider_version, str)
                or not re.fullmatch(r"[A-Za-z0-9_.+-]{1,80}", self.provider_version)
                or not isinstance(self.relevance, CandidateRelevance)
            ):
                raise ValueError("Invalid normalized provider candidate provenance.")

    @classmethod
    def from_source(cls, source: SourceRecord) -> CompilerCandidate:
        return cls(
            source.id,
            source.path,
            source.kind,
            source.authority_class,
            source.lifecycle,
            source.revision,
            source.size_bytes,
            source=source,
        )


def usable_content_revision(revision: SourceRevision) -> bool:
    return isinstance(revision.content_sha256, str) and bool(
        re.fullmatch(r"[0-9a-f]{64}", revision.content_sha256)
    )


@dataclass(frozen=True)
class CompiledContext:
    repository: RepositoryRef
    task: str | None
    contract: ContextContract
    config_sha256: str | None
    status: CompilationStatus
    budget: CompilationBudget
    selected_sources: tuple[SourceRecord, ...]
    decisions: tuple[CompiledSourceDecision, ...]
    validation: ContractValidationOverview
    dependencies: tuple[CompiledDependency, ...]
    warnings: tuple[ScanWarning, ...]
    integrity_state: CompiledIntegrityState = CompiledIntegrityState()
    authority_policies: tuple[AuthorityPolicy, ...] = ()
    schema_version: int = 3
    providers: tuple[EvidenceProviderState, ...] = ()

    def __post_init__(self) -> None:
        if self.task is not None and not isinstance(self.task, str):
            raise ValueError("Task metadata must be text.")
        paths = tuple(s.path for s in self.selected_sources)
        if len(set(paths)) != len(paths) or len({s.id for s in self.selected_sources}) != len(
            paths
        ):
            raise ValueError("Compiled sources must be unique.")
        if any(type(s.size_bytes) is not int or s.size_bytes < 0 for s in self.selected_sources):
            raise ValueError("Compiled sources require observed sizes.")
        if self.budget.used_bytes != sum(s.size_bytes for s in self.selected_sources):
            raise ValueError("Compiled budget must count unique source bytes.")
        expected = tuple(
            CompiledDependency(s.id, s.path, s.revision) for s in self.selected_sources
        )
        if self.dependencies != expected:
            raise ValueError("Compiled dependencies must match selected sources.")
        if (
            self.validation.contract != self.contract
            or tuple(s.path for s in self.validation.package.resolved_sources) != paths
            or self.config_sha256 != self.validation.config_sha256
        ):
            raise ValueError("Compiled validation must describe the selected package.")
        expected_status = (
            CompilationStatus.INCOMPLETE if self.validation.findings else CompilationStatus.COMPLETE
        )
        if self.status != expected_status or not isinstance(self.status, CompilationStatus):
            raise ValueError("Compiled status must reflect final validation.")
