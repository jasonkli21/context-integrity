"""Small governance declarations and normalized observations, independent of I/O."""

from dataclasses import dataclass
from datetime import date


class GovernanceError(ValueError):
    """Sanitized policy/report input or resource failure."""


@dataclass(frozen=True)
class Target:
    id: str
    kind: str
    root: str | None = None
    manifest: str | None = None
    receipt: str | None = None
    review_severity: str | None = None
    require_architecture: bool = False
    repository_id: str | None = None


@dataclass(frozen=True)
class RulePolicy:
    target: str
    rule_id: str
    severity: str
    owner: str
    reason: str
    review_ref: str


@dataclass(frozen=True)
class Waiver:
    id: str
    target: str
    finding_fingerprint: str
    owner: str
    reason: str
    review_ref: str
    expires_on: date
    approved_severity: str | None = None
    approved_owner: str | None = None
    approved_fail_on: str | None = None


@dataclass(frozen=True)
class Policy:
    schema_version: int
    id: str
    owner: str
    sha256: str
    fail_on: str
    on_inconclusive: str
    targets: tuple[Target, ...]
    rule_policies: tuple[RulePolicy, ...]
    waivers: tuple[Waiver, ...]


@dataclass(frozen=True)
class Evidence:
    repository_id: str
    path: str
    state: str
    sha256: str | None
    basis: str


@dataclass(frozen=True)
class Observation:
    rule_id: str
    code: str
    entity: str
    signal: str
    effect: str  # finding, uncertainty, caveat, observation
    severity: str | None = None
    evidence: tuple[Evidence, ...] = ()
    material_sha256: str | None = None
    reasons: tuple[str, ...] = ()
    waiver_eligible: bool = False
    pinned_sha256: str | None = None
    observed_sha256: str | None = None
    related_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class Subject:
    target: Target
    repositories: tuple[dict, ...]
    config_sha256: str | None
    scope: dict
    observations: tuple[Observation, ...]
    limitations: tuple[str, ...]


SEVERITIES = ("low", "medium", "high")
MAX_POLICY_BYTES = 256 * 1024
MAX_REPORT_BYTES = 8 * 1024 * 1024
MAX_OBSERVATIONS = 4096
MAX_EVIDENCE = 16384
