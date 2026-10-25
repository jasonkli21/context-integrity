"""Local workspace resolution, bounded acquisition and deterministic explicit checks."""

from dataclasses import dataclass, replace
from hashlib import sha256
from pathlib import Path

from context_integrity.acquisition import MAX_SOURCE_BYTES, read_source, read_source_bytes
from context_integrity.claims import claims_overview
from context_integrity.compiler import compile_context
from context_integrity.configuration import ConfigurationError
from context_integrity.contracts import resolve_contract
from context_integrity.derived_models import path_value
from context_integrity.inventory import InventoryObservationBudget, inventory_repository
from context_integrity.models import CompiledContext, InventoryManifest, LifecycleState
from context_integrity.repository import RepositoryContext, RepositoryError, discover_repository
from context_integrity.workspace_config import (
    LOCK_LIMIT,
    WorkspaceInputError,
    load_workspace,
    parse_lock,
    safe_directory,
)
from context_integrity.workspace_models import (
    CheckSpec,
    ClaimObservation,
    QualifiedClaimRef,
    QualifiedSourceRef,
    RuleKind,
    Signal,
    SourceObservation,
    WorkspaceFinding,
    WorkspaceSpec,
)

OBSERVATION_BYTES = 64 * 1024 * 1024
OBSERVATION_ATTEMPTS = 4096


@dataclass(frozen=True)
class WorkspaceRepository:
    alias: str
    context: RepositoryContext


class WorkspaceRepositoryError(RepositoryError):
    """Safe codes plus validated declared alias/identity; never local roots."""


class Workspace:
    """Invocation-local state. All caches are explicitly repository qualified."""

    def __init__(self, spec: WorkspaceSpec, repositories: tuple[WorkspaceRepository, ...]):
        self.spec = spec
        self.repositories = repositories
        self.contexts = {r.alias: r.context for r in repositories}
        self.discovery_warnings = {r.alias: tuple(r.context.warnings) for r in repositories}
        self.cache: dict[tuple[str, str, int], tuple[SourceObservation, bytes | None]] = {}
        self.inventories: dict[str, InventoryManifest | None] = {}
        self.bytes = self.attempts = 0
        self.inventory_budget = InventoryObservationBudget()

    def ref(self, alias: str, path: str) -> QualifiedSourceRef:
        return QualifiedSourceRef(alias, self.contexts[alias].repository.id, path)

    def observe(self, alias: str, path: str, *, lock=False):
        ref = self.ref(alias, path)
        limit = LOCK_LIMIT if lock else MAX_SOURCE_BYTES
        key = (ref.repository_id, path, limit)
        if key in self.cache:
            return self.cache[key]
        self.attempts += 1
        if self.attempts > OBSERVATION_ATTEMPTS or self.bytes >= OBSERVATION_BYTES:
            return SourceObservation(ref, "budget_exceeded", None), None
        context = replace(self.contexts[alias], warnings=[])
        bound = min(limit, OBSERVATION_BYTES - self.bytes)
        data = None
        if lock:
            data = read_source_bytes(context, path, max_bytes=bound, require_stable=True)
            digest = sha256(data).hexdigest() if data is not None else None
            size = len(data) if data is not None else None
        else:
            size, digest, _ = read_source(context, path, max_bytes=bound, require_stable=True)
        self.bytes += size if digest is not None else bound
        warnings = context.warnings
        state = "observed"
        if digest is None:
            state = (
                "missing"
                if any(
                    w.message == "Candidate disappeared before it could be opened."
                    for w in warnings
                )
                else "budget_exceeded"
                if bound < limit
                else "too_large"
                if any(w.code == "source_too_large" for w in warnings)
                else "unobservable"
            )
        observation = SourceObservation(ref, state, digest)
        self.cache[key] = observation, data
        return observation, data

    def inventory(self, alias: str) -> InventoryManifest | None:
        if alias not in self.inventories:
            context = replace(self.contexts[alias], warnings=list(self.discovery_warnings[alias]))
            remaining = min(OBSERVATION_BYTES, self.inventory_budget.remaining_bytes)
            attempts = min(OBSERVATION_ATTEMPTS, self.inventory_budget.remaining_attempts)
            try:
                if remaining <= 0 or attempts <= 0:
                    raise RepositoryError("workspace_inventory_budget_exceeded")
                manifest = inventory_repository(
                    context,
                    max_observation_bytes=remaining,
                    max_sources=attempts,
                    require_stable=True,
                    observation_budget=self.inventory_budget,
                )
                # Inventory paths entering a workspace projection obey the narrower grammar.
                for source in manifest.sources:
                    path_value(source.path)
                self.inventories[alias] = manifest
            except RepositoryError:
                self.inventory_budget.remaining_bytes = 0
                self.inventories[alias] = None
            except ConfigurationError as exc:
                raise WorkspaceInputError(
                    f"workspace_config_error:{alias}:{context.repository.id}"
                ) from exc
            except ValueError as exc:
                raise WorkspaceInputError(
                    f"unsafe_workspace_inventory_path:{alias}:{context.repository.id}"
                ) from exc
        return self.inventories[alias]

    def claim(self, alias: str, claim_id: str) -> ClaimObservation:
        context = self.contexts[alias]
        ref = QualifiedClaimRef(alias, context.repository.id, claim_id)
        manifest = self.inventory(alias)
        if manifest is None:
            return ClaimObservation(ref, None, (), ("claim_inventory_unavailable",))
        claim = next((c for c in claims_overview(manifest).claims if c.id == claim_id), None)
        if claim is None:
            return ClaimObservation(ref, None, (), ("claim_missing",))
        sources = {s.path: s for s in manifest.sources}
        reasons = set()
        if manifest.warnings:
            reasons.add("claim_inventory_incomplete")
        observations = []
        for path in (claim.provenance.path, *(d.path for d in claim.dependencies)):
            path_value(path)
            source = sources.get(path)
            observations.append(
                SourceObservation(
                    self.ref(alias, path),
                    "observed" if source and source.revision.content_sha256 else "unobservable",
                    source.revision.content_sha256 if source else None,
                    source.lifecycle.value if source else None,
                    source.authority_class.value if source else None,
                )
            )
            if source is None or not source.revision.content_sha256:
                reasons.add("claim_evidence_incomplete")
            elif source.lifecycle not in {LifecycleState.ACTIVE, LifecycleState.UNKNOWN}:
                reasons.add("claim_provenance_not_active")
            if path != claim.provenance.path:
                if not context.status_known or path in context.statuses:
                    reasons.add("claim_dependency_changed_or_unknown")
                if source and source.authority_class == "generated_derivative":
                    reasons.add("claim_dependency_revalidation_unavailable")
        if not claim.provenance_complete:
            reasons.add("claim_evidence_incomplete")
        return ClaimObservation(ref, claim, tuple(observations), tuple(sorted(reasons)))

    def check(self) -> tuple[WorkspaceFinding, ...]:
        findings = []
        for spec in self.spec.checks:
            if spec.kind == RuleKind.CLAIM_MATCH:
                findings.append(
                    compare_claims(
                        spec,
                        self.claim(spec.left_repo, spec.left),
                        self.claim(spec.right_repo, spec.right),
                    )
                )
                continue
            left, _ = self.observe(spec.left_repo, spec.left)
            right, data = self.observe(
                spec.right_repo, spec.right, lock=spec.kind == RuleKind.CONTRACT_PIN
            )
            try:
                lock = parse_lock(data) if data is not None else None
            except WorkspaceInputError as exc:
                raise WorkspaceInputError(
                    f"invalid_contract_lock:{right.ref.repo_alias}:{right.ref.repository_id}:{right.ref.path}"
                ) from exc
            if lock and (
                lock.producer_repository_id != left.ref.repository_id
                or lock.producer_path != left.ref.path
            ):
                raise WorkspaceInputError(
                    f"contract_lock_producer_mismatch:{right.ref.repo_alias}:{right.ref.repository_id}:{right.ref.path}"
                )
            findings.append(
                compare_sources(spec, left, right, lock.accepted_sha256 if lock else None)
            )
        return tuple(findings)

    def compile(self, task: str) -> tuple[tuple[str, str, int, CompiledContext | None], ...]:
        if not self.spec.context_targets:
            raise WorkspaceInputError("context_targets_required")
        if not isinstance(task, str) or len(task.encode("utf-8")) > 64 * 1024:
            raise WorkspaceInputError("invalid_workspace_task")
        results = []
        for target in self.spec.context_targets:
            manifest = self.inventory(target.repo)
            compiled = None
            if manifest is not None:
                try:
                    contract = resolve_contract(manifest.repository_config, target.contract_id)
                    compiled = compile_context(
                        manifest, contract, task=task, budget_bytes=target.budget_bytes
                    )
                except (ConfigurationError, ValueError) as exc:
                    raise WorkspaceInputError(
                        f"workspace_contract_error:{target.repo}:{manifest.repository.id}:{target.contract_id}"
                    ) from exc
            results.append((target.repo, target.contract_id, target.budget_bytes, compiled))
        return tuple(results)


def resolve_workspace(path: Path) -> Workspace:
    spec, parent = load_workspace(path)
    repositories = []
    for entry in spec.repositories:
        try:
            root = safe_directory(parent / entry.root)
            context = discover_repository(root)
        except (OSError, ValueError, RepositoryError) as exc:
            raise WorkspaceRepositoryError(
                f"workspace_repository_unavailable:{entry.alias}:{entry.repository_id}"
            ) from exc
        if context.root != root:
            raise WorkspaceRepositoryError(
                f"workspace_repository_boundary_mismatch:{entry.alias}:{entry.repository_id}"
            )
        if context.repository.id != entry.repository_id:
            raise WorkspaceRepositoryError(
                f"workspace_repository_identity_mismatch:{entry.alias}:{entry.repository_id}"
            )
        for other in repositories:
            previous = other.context
            if (
                context.repository.id == previous.repository.id
                or root == previous.root
                or root in previous.root.parents
                or previous.root in root.parents
            ):
                raise WorkspaceRepositoryError(
                    f"workspace_repository_collision:{entry.alias}:{entry.repository_id}"
                )
        repositories.append(WorkspaceRepository(entry.alias, context))
    return Workspace(spec, tuple(repositories))


def compare_sources(spec, left, right, accepted):
    reasons = []
    missing = False
    for source in (left, right):
        if source.state != "observed":
            reasons.append(f"{source.ref.repo_alias}:source_{source.state}")
            missing |= source.state == "missing"
    if missing:
        signal = Signal.REVIEW
    elif reasons:
        signal = Signal.UNKNOWN
    elif spec.kind == RuleKind.CONTRACT_PIN:
        signal = Signal.ALIGNED if left.content_sha256 == accepted else Signal.REVIEW
        reasons.append(
            "accepted_revision_observed"
            if signal == Signal.ALIGNED
            else "producer_contract_revision_changed"
        )
    else:
        signal = Signal.ALIGNED if left.content_sha256 == right.content_sha256 else Signal.REVIEW
        reasons.append(
            "byte_equality_observed" if signal == Signal.ALIGNED else "mirror_bytes_diverged"
        )
    reasons.append(
        "consumer_implementation_not_verified"
        if spec.kind == RuleKind.CONTRACT_PIN
        else "byte_comparison_not_semantic_validation"
    )
    return WorkspaceFinding(
        spec.id, spec.kind, signal, tuple(sorted(reasons)), (left, right), accepted_sha256=accepted
    )


def compare_claims(spec: CheckSpec, left: ClaimObservation, right: ClaimObservation):
    reasons = set(left.reasons + right.reasons)
    signal = Signal.UNKNOWN
    if not reasons and left.claim and right.claim:
        a, b = left.claim, right.claim
        if (a.claim_type, a.subject, a.predicate, a.scope) != (
            b.claim_type,
            b.subject,
            b.predicate,
            b.scope,
        ):
            reasons.add("not_comparable")
        else:
            signal = Signal.ALIGNED if a.value == b.value else Signal.DISAGREEMENT
            reasons.add(
                "declarations_agree" if signal == Signal.ALIGNED else "declared_claim_disagreement"
            )
    reasons.add("claims_unverified")
    reasons.add("dependency_history_not_pinned")
    return WorkspaceFinding(
        spec.id, spec.kind, signal, tuple(sorted(reasons)), claims=(left, right)
    )
