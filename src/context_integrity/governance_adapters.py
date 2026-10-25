"""Typed evaluator adapters; no legacy rendered reports or source prose cross this seam."""

from dataclasses import asdict
from pathlib import Path

from context_integrity.context_engine import ContextEngineProvider
from context_integrity.derived import Checker, Reader, fingerprint
from context_integrity.derived_models import path_value, require, token
from context_integrity.governance_models import (
    MAX_EVIDENCE,
    MAX_OBSERVATIONS,
    Evidence,
    GovernanceError,
    Observation,
    Subject,
)
from context_integrity.integrity import integrity_overview
from context_integrity.inventory import inventory_repository
from context_integrity.relations import EvidenceRelationRequest
from context_integrity.repository import RepositoryError, discover_repository
from context_integrity.workspace import Workspace
from context_integrity.workspace_config import load_workspace, safe_directory
from context_integrity.workspace_models import Signal

NATIVE_CODES = {
    "instruction.canonical_reference.v1": {
        "instruction_canonical_missing",
        "instruction_compatibility_missing",
        "instruction_source_kind_mismatch",
        "instruction_source_unusable",
        "instruction_reference_missing",
    },
    "current_state.navigation.v1": {
        "current_state_multiple_candidates",
        "current_state_metadata_incomplete",
        "current_state_active_plan_unsafe",
        "current_state_active_plan_missing",
        "current_state_active_plan_kind_mismatch",
        "current_state_active_plan_unusable",
        "current_state_phase_plan_mismatch",
        "current_state_next_phase_invalid",
    },
    "current_state.delivery_evidence.v1": {
        "current_state_delivery_evidence_missing",
        "current_state_lags_verification_evidence",
    },
    "document_dependency.change_review.v1": {
        "drift_dependent_missing",
        "document_dependency_changed",
    },
    "architecture.forbid_relation.v1": {"architecture_prohibited_relation"},
}
WORKSPACE_CODES = {
    "accepted_revision_observed",
    "producer_contract_revision_changed",
    "byte_equality_observed",
    "mirror_bytes_diverged",
    "consumer_implementation_not_verified",
    "byte_comparison_not_semantic_validation",
    "declarations_agree",
    "declared_claim_disagreement",
    "claims_unverified",
    "dependency_history_not_pinned",
    "not_comparable",
    "claim_missing",
    "claim_inventory_unavailable",
    "claim_inventory_incomplete",
    "claim_evidence_incomplete",
    "claim_provenance_not_active",
    "claim_dependency_changed_or_unknown",
    "claim_dependency_revalidation_unavailable",
}
DERIVED_EFFECTS = {
    **{
        f"{label}_{suffix}": effect
        for label in ("artifact", "source", "config", "upstream_receipt")
        for suffix, effect in (
            ("changed", "review"),
            ("missing", "review"),
            ("unobservable", "uncertainty"),
            ("too_large", "uncertainty"),
            ("budget_exceeded", "uncertainty"),
        )
    },
    **{
        code: "review"
        for code in (
            "source_metadata_changed",
            "contract_changed",
            "contract_missing",
            "policies_changed",
            "selection_context_changed",
            "compiler_implementation_changed",
            "upstream_review_required",
        )
    },
    **{
        code: "uncertainty"
        for code in (
            "source_metadata_unobservable",
            "compilation_context_unobservable",
            "provenance_incomplete",
            "unlinked_derived_dependency",
            "compiler_implementation_unobservable",
            "provider_not_revalidated",
            "upstream_receipt_untrusted",
            "upstream_inconclusive",
        )
    },
    "declared_inputs_not_semantic_validation": "caveat",
    "selection_not_replayed": "caveat",
}


class Collector:
    """Bound normalized work before copying/multiplying underlying evidence."""

    def __init__(self):
        self.items = []
        self.evidence_count = 0

    def add(self, item):
        self.evidence_count += len(item.evidence)
        if len(self.items) >= MAX_OBSERVATIONS or self.evidence_count > MAX_EVIDENCE:
            raise GovernanceError("governance_observation_limit_exceeded")
        self.items.append(item)

    def gap(self, code, entity="target", *, signal="inconclusive"):
        self.add(Observation("governance.coverage.v1", code, entity, signal, "uncertainty"))


def descriptor(context, alias=None):
    repo = context.repository
    return {
        "alias": alias,
        "repository_id": repo.id,
        "identity_basis": repo.identity_basis,
        "git_head": repo.git_head,
        "git_dirty": repo.git_dirty,
    }


def bind_repository(root: Path, expected=None):
    root = safe_directory(root)
    context = discover_repository(root)
    if context.root != root or (expected is not None and context.repository.id != expected):
        raise RepositoryError("governance_repository_binding_failed")
    return context


def inventory(context):
    return inventory_repository(
        context, max_observation_bytes=64 * 1024 * 1024, max_sources=4096, require_stable=True
    )


def repository_subject(target, context, diff=None, provider=None):
    manifest = inventory(context)
    collected = Collector()
    relations = None
    if provider:
        # Failure is retained independently; inventory checks still run.
        try:
            relations = provider.relations(
                EvidenceRelationRequest(context.root, manifest.repository)
            )
        except Exception:
            collected.gap("provider_evaluation_failed")
    overview = integrity_overview(context, manifest, diff, relation_batch=relations)
    if overview.schema_version != 2:
        collected.gap("unsupported_integrity_schema")
    if overview.change_set.scope not in {"working_tree", "git_range"}:
        collected.gap("change_evidence_unavailable")
    # Warnings may indicate skipped text/inventory work. Never forward arbitrary warning prose.
    for code in sorted({w.code for w in overview.warnings}):
        token(code)
        collected.add(
            Observation(
                "governance.coverage.v1",
                "repository_warning",
                "target",
                "inconclusive",
                "uncertainty",
                reasons=(code,),
            )
        )
    source_map = {s.path: s for s in manifest.sources}
    architecture = overview.architecture
    if target.require_architecture and not architecture.invariants:
        collected.gap("architecture_rules_not_declared")
    for result in architecture.invariants:
        incomplete = result.status not in {"violated", "no_violation_observed"} or bool(
            result.caveats
        )
        collected.add(
            Observation(
                "architecture.forbid_relation.v1",
                "architecture_coverage_incomplete" if incomplete else "architecture_evaluated",
                result.invariant_id,
                result.status.value,
                "uncertainty" if incomplete else "observation",
                reasons=result.caveats,
            )
        )
    if not architecture.invariants:
        collected.add(
            Observation(
                "architecture.forbid_relation.v1",
                "no_architecture_rules",
                "target",
                "not_configured",
                "caveat",
            )
        )
    provider_material = (
        None
        if architecture.state is None
        else {
            "id": architecture.state.descriptor.id,
            "version": architecture.state.descriptor.version,
            "derivation": architecture.state.descriptor.derivation,
            "coverage_sha256": fingerprint(asdict(architecture.state.coverage)),
        }
    )
    require(len(overview.findings) <= MAX_OBSERVATIONS)
    for finding in overview.findings:
        if finding.code not in NATIVE_CODES.get(finding.rule_id, set()):
            collected.gap("unknown_integrity_signal")
            continue
        require(len(finding.evidence) + len(finding.affected_paths) <= MAX_EVIDENCE)
        evidence = {}
        for item in finding.evidence:
            path_value(item.path)
            digest = item.source_revision.content_sha256 if item.source_revision else None
            evidence[item.path] = Evidence(
                context.repository.id,
                item.path,
                "observed" if digest else "unobservable",
                digest,
                item.derivation,
            )
        for path in finding.affected_paths:
            path_value(path)
            if path not in evidence:
                source = source_map.get(path)
                digest = source.revision.content_sha256 if source else None
                if relations and not digest:
                    digest = dict(relations.state.observed_content).get(path)
                evidence[path] = Evidence(
                    context.repository.id,
                    path,
                    "observed" if digest else "unobservable",
                    digest,
                    "local_bytes",
                )
        eligible = bool(evidence) and all(e.state == "observed" for e in evidence.values())
        if finding.relations:
            # Provider graph dirty bytes cannot be certified by post-graph local hashes.
            eligible &= relations is not None and relations.state.snapshot.git_dirty is False
        material = fingerprint(
            {
                "config_sha256": overview.config_sha256,
                "provider": provider_material,
                "dependency_id": finding.dependency_id,
                "invariant_id": finding.invariant_id,
                "claim_id": finding.claim_id,
                "relations": [r.identity() for r in finding.relations],
                "metadata": [
                    {
                        "path": p,
                        "kind": source_map[p].kind.value,
                        "lifecycle": source_map[p].lifecycle.value,
                        "authority": source_map[p].authority_class.value,
                    }
                    for p in sorted(evidence)
                    if p in source_map
                ],
            }
        )
        collected.add(
            Observation(
                finding.rule_id,
                finding.code,
                finding.id,
                "review_required",
                "finding",
                finding.severity.value,
                tuple(evidence[p] for p in sorted(evidence)),
                material,
                waiver_eligible=eligible,
                related_ids=tuple(
                    sorted(
                        {
                            value
                            for value in (
                                finding.dependency_id,
                                finding.invariant_id,
                                finding.claim_id,
                            )
                            if value
                        }
                    )
                ),
            )
        )
        if not eligible:
            collected.gap("finding_evidence_incomplete", finding.id)
    changes = overview.change_set
    scope = {
        "kind": target.kind,
        "change_scope": changes.scope.value,
        "base_revision": changes.base_revision,
        "target_revision": changes.target_revision,
        "architecture": {
            "evaluation_status": architecture.evaluation_status,
            "invariants_declared": len(architecture.invariants),
            "provider": None
            if architecture.state is None
            else {
                "id": architecture.state.descriptor.id,
                "version": architecture.state.descriptor.version,
                "derivation": architecture.state.descriptor.derivation,
                "coverage_incomplete": architecture.state.coverage.summary.incomplete,
                "coverage_signals": dict(architecture.state.coverage.summary.signals),
                "warning_categories": list(architecture.state.coverage.warning_categories),
            },
        },
    }
    return Subject(
        target,
        (descriptor(context),),
        overview.config_sha256,
        scope,
        tuple(collected.items),
        ("declared_rules_only", "no_semantic_validation", "sequential_non_atomic_observations"),
    )


def workspace_subject(target, workspace):
    collected = Collector()
    if not workspace.spec.checks:
        collected.gap("no_checks_declared")
    # Evaluate each declared check separately so a malformed lock cannot hide later checks.
    for spec in workspace.spec.checks:
        from dataclasses import replace

        original = workspace.spec
        workspace.spec = replace(original, checks=(spec,))
        try:
            findings = workspace.check()
        except Exception:
            collected.gap("workspace_check_failed", spec.id)
            continue
        finally:
            workspace.spec = original
        if len(findings) != 1:
            collected.gap("workspace_check_missing", spec.id)
            continue
        finding = findings[0]
        codes = []
        for code in finding.reasons:
            tail = code.split(":", 1)[-1]
            valid_source = tail in {
                f"source_{s}" for s in ("missing", "unobservable", "too_large", "budget_exceeded")
            }
            if code not in WORKSPACE_CODES and not valid_source:
                collected.gap("unknown_workspace_reason", spec.id)
            else:
                codes.append(code)
        if finding.signal not in set(Signal):
            collected.gap("unknown_workspace_signal", spec.id)
            continue
        sources = [*finding.sources]
        claims = []
        for claim in finding.claims:
            sources.extend(claim.sources)
            claims.append(
                {"repository_id": claim.ref.repository_id, "claim_id": claim.ref.claim_id}
            )
        require(len(sources) <= MAX_EVIDENCE)
        evidence = tuple(
            sorted(
                {
                    Evidence(
                        s.ref.repository_id,
                        s.ref.path,
                        s.state,
                        s.content_sha256,
                        "workspace_observation",
                    )
                    for s in sources
                },
                key=lambda e: (e.repository_id, e.path),
            )
        )
        eligible = bool(evidence) and all(e.state == "observed" for e in evidence)
        if not eligible:
            collected.gap("workspace_inputs_incomplete", spec.id)
        if finding.signal == Signal.UNKNOWN:
            collected.gap("workspace_check_inconclusive", spec.id, signal=finding.signal.value)
        effect = (
            "finding" if finding.signal in {Signal.REVIEW, Signal.DISAGREEMENT} else "observation"
        )
        collected.add(
            Observation(
                f"workspace.{spec.kind.value}.v1",
                finding.signal.value,
                spec.id,
                finding.signal.value,
                effect,
                evidence=evidence,
                material_sha256=fingerprint(
                    {
                        "check": asdict(spec),
                        "claims": claims,
                        "accepted_sha256": finding.accepted_sha256,
                        "metadata": [
                            (s.ref.repository_id, s.ref.path, s.lifecycle, s.authority)
                            for s in sources
                        ],
                    }
                ),
                reasons=tuple(sorted(codes)),
                waiver_eligible=eligible,
                pinned_sha256=finding.accepted_sha256,
                observed_sha256=finding.sources[0].content_sha256
                if finding.accepted_sha256 and finding.sources
                else None,
            )
        )
    for alias, warnings in workspace.discovery_warnings.items():
        if warnings:
            collected.gap("workspace_repository_warnings", alias)
    return Subject(
        target,
        tuple(descriptor(r.context, r.alias) for r in workspace.repositories),
        workspace.spec.manifest_sha256,
        {"kind": "workspace", "checks_declared": len(workspace.spec.checks)},
        tuple(collected.items),
        (
            "declared_checks_only",
            "no_semantic_validation",
            "claims_unverified",
            "claim_dependency_freshness_not_established",
            "sequential_non_atomic_observations",
        ),
    )


def derived_subject(target, context):
    reader = Reader(context, require_stable=True)
    checker = Checker(context, reader=reader)
    checker.load(target.receipt)
    collected = Collector()
    try:
        checker.manifest = inventory(context)
    except Exception:
        collected.gap("derived_inventory_unavailable")
    result = checker.evaluate(target.receipt)
    if result.status not in {"unchanged_observed_inputs", "review_required", "inconclusive"}:
        collected.gap("unknown_derived_status")
    require(len(result.reasons) <= MAX_OBSERVATIONS)
    evidence = tuple(
        Evidence(context.repository.id, p, o.state, o.content_sha256, "derived_observation")
        for (p, _), (o, _) in sorted(reader.cache.items())
    )
    require(len(evidence) <= MAX_EVIDENCE)
    material = fingerprint([asdict(e) for e in evidence])
    eligible = bool(evidence) and all(e.state in {"observed", "missing"} for e in evidence)
    for reason in result.reasons:
        path_value(reason.path)
        token(reason.artifact_id)
        if DERIVED_EFFECTS.get(reason.code) != reason.effect:
            collected.gap("unknown_derived_reason")
            continue
        # Reference all observations once in the subject, not once per propagated reason.
        item_evidence = tuple(e for e in evidence if e.path == reason.path)
        collected.add(
            Observation(
                f"derived.{reason.code}.v1",
                reason.code,
                f"{reason.artifact_id}:{reason.path}",
                result.status,
                "finding" if reason.effect == "review" else reason.effect,
                evidence=item_evidence,
                material_sha256=fingerprint(
                    {
                        "inputs": material,
                        "pinned": reason.pinned_sha256,
                        "observed": reason.observed_sha256,
                    }
                ),
                waiver_eligible=eligible and reason.effect == "review",
                pinned_sha256=reason.pinned_sha256,
                observed_sha256=reason.observed_sha256,
                related_ids=(reason.artifact_id,),
            )
        )
    collected.add(
        Observation(
            "derived.inputs.v1",
            "observed_inputs",
            result.artifact_id,
            result.status,
            "observation",
            evidence=evidence,
            material_sha256=material,
        )
    )
    if result.status == "inconclusive" and not any(
        o.effect == "uncertainty" for o in collected.items
    ):
        collected.gap("derived_inconclusive")
    return Subject(
        target,
        (descriptor(context),),
        checker.manifest.repository_config.content_sha256 if checker.manifest else None,
        {
            "kind": "derived",
            "receipt": target.receipt,
            "artifact_id": result.artifact_id,
            "artifact_path": result.artifact_path,
            "provenance_scope": result.provenance_scope,
            "receipts_observed": result.receipts_observed,
        },
        tuple(collected.items),
        ("declared_inputs_only", "no_semantic_validation", "sequential_non_atomic_observations"),
    )


def resolve_workspace_subject(path, roots):
    """Retain every declared root for output exclusion even if a later bind fails."""
    from context_integrity.workspace import WorkspaceRepository

    spec, parent = load_workspace(path)
    repositories = []
    for entry in spec.repositories:
        # Manifest v1 permits parent-relative roots; validate ancestors before normalizing.
        root = safe_directory(parent / entry.root)
        roots.add(root)
    for entry in spec.repositories:
        context = bind_repository(parent / entry.root, entry.repository_id)
        for other in repositories:
            old = other.context
            if (
                old.repository.id == context.repository.id
                or old.root == context.root
                or old.root in context.root.parents
                or context.root in old.root.parents
            ):
                raise RepositoryError("governance_workspace_collision")
        repositories.append(WorkspaceRepository(entry.alias, context))
    return Workspace(spec, tuple(repositories))


def local_provider(binary):
    return ContextEngineProvider(binary or "ctx")
