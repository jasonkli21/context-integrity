"""Pure explicit lifecycle, graph validation, and inventory endpoint resolution."""

from dataclasses import replace

from context_integrity.classification import AUTHORITY_BY_KIND
from context_integrity.models import (
    ClassificationConfidence,
    ClassificationResult,
    InventoryManifest,
    LifecycleEntry,
    LifecycleOrigin,
    LifecycleOverview,
    LifecycleState,
    RepositoryConfig,
    ResolvedSupersession,
    RuleMatch,
    ScanWarning,
    SourceMetadata,
    SourceRecord,
    SupersessionSpec,
)


def lifecycle_authority_eligible(state: LifecycleState) -> bool:
    return state in {LifecycleState.UNKNOWN, LifecycleState.ACTIVE}


def validate_supersession(
    specs: tuple[SupersessionSpec, ...], metadata: tuple[SourceMetadata, ...]
) -> None:
    """Validate the configured graph even when endpoints are not observed. No recursion."""
    successors: dict[str, str] = {}
    states = {m.path: m.lifecycle_override for m in metadata}
    for spec in specs:
        source, target = spec.source_path, spec.superseded_by_path
        if source == target or source in successors:
            raise ValueError("Self supersession or duplicate outgoing relation.")
        if states.get(source) not in {None, LifecycleState.SUPERSEDED}:
            raise ValueError("Lifecycle contradicts outgoing supersession.")
        successors[source] = target
    complete: set[str] = set()
    for start in successors:
        visiting: set[str] = set()
        node = start
        while node in successors and node not in complete:
            if node in visiting:
                raise ValueError("Supersession cycle.")
            visiting.add(node)
            node = successors[node]
        complete.update(visiting)


def apply_lifecycle(
    classification: ClassificationResult,
    state: LifecycleState,
    reason: str,
    rule_id: str,
    metadata: SourceMetadata | None,
) -> ClassificationResult:
    matches = [
        RuleMatch(rule_id, "lifecycle", state.value, ClassificationConfidence.EXPLICIT, reason)
    ]
    authority = classification.authority_class
    # Only undo the historical path overlay. Explicit authority metadata remains strongest.
    if (
        state != LifecycleState.HISTORICAL
        and "authority.historical.overlay" in classification.matched_rules
        and (metadata is None or metadata.authority_class_override is None)
    ):
        authority = AUTHORITY_BY_KIND[classification.kind]
        if authority != classification.authority_class:
            matches.append(
                RuleMatch(
                    "authority.lifecycle.restore_kind_role",
                    "authority_class",
                    authority.value,
                    ClassificationConfidence.EXPLICIT,
                    "explicit_lifecycle_overrides_historical_path",
                )
            )
    return replace(
        classification,
        lifecycle=state,
        authority_class=authority,
        matched_rules=(*classification.matched_rules, *(m.rule_id for m in matches)),
        basis=(*classification.basis, *matches),
    )


def apply_lifecycle_metadata(
    classification: ClassificationResult, metadata: SourceMetadata | None
) -> ClassificationResult:
    if metadata is None or metadata.lifecycle_override is None:
        return classification
    return apply_lifecycle(
        classification,
        metadata.lifecycle_override,
        metadata.reason,
        "lifecycle.metadata.repository_override",
        metadata,
    )


def resolve_supersession(
    sources: tuple[SourceRecord, ...], config: RepositoryConfig
) -> tuple[tuple[SourceRecord, ...], tuple[ResolvedSupersession, ...], tuple[ScanWarning, ...]]:
    observed = {s.path: s for s in sources}
    valid = []
    warnings = []
    for spec in sorted(config.supersession, key=lambda e: (e.source_path, e.superseded_by_path)):
        for path, endpoint in ((spec.source_path, "source"), (spec.superseded_by_path, "target")):
            if path not in observed:
                warnings.append(
                    ScanWarning(
                        f"supersession_{endpoint}_missing",
                        path,
                        f"Supersession {endpoint} is absent from inventory.",
                    )
                )
        if spec.source_path not in observed or spec.superseded_by_path not in observed:
            continue
        valid.append(spec)
        source = observed[spec.source_path]
        classification = apply_lifecycle(
            source.classification,
            LifecycleState.SUPERSEDED,
            f"superseded_by={spec.superseded_by_path}; reason={spec.reason}",
            "lifecycle.supersession.explicit",
            source.source_metadata,
        )
        observed[source.path] = replace(
            source,
            classification=classification,
            lifecycle=classification.lifecycle,
            authority_class=classification.authority_class,
        )
    # Attach final endpoint records (including effective lifecycle and revisions).
    edges = tuple(
        ResolvedSupersession(
            observed[s.source_path], observed[s.superseded_by_path], s.reason, config.content_sha256
        )
        for s in valid
    )
    return tuple(observed[p] for p in sorted(observed)), edges, tuple(warnings)


def lifecycle_entry(source: SourceRecord) -> LifecycleEntry:
    match = next(m for m in reversed(source.classification.basis) if m.dimension == "lifecycle")
    origin = (
        LifecycleOrigin.SUPERSESSION
        if match.rule_id == "lifecycle.supersession.explicit"
        else LifecycleOrigin.REPOSITORY_METADATA
        if match.rule_id == "lifecycle.metadata.repository_override"
        else LifecycleOrigin.PATH_HEURISTIC
        if source.lifecycle == LifecycleState.HISTORICAL
        else LifecycleOrigin.FALLBACK_UNKNOWN
    )
    return LifecycleEntry(source, origin, match.basis)


def lifecycle_overview(manifest: InventoryManifest) -> LifecycleOverview:
    edges = tuple(
        sorted(manifest.supersession, key=lambda e: (e.source.path, e.superseded_by.path))
    )
    outgoing = {e.source.path: e for e in edges}
    incoming: dict[str, list[ResolvedSupersession]] = {}
    for edge in edges:
        incoming.setdefault(edge.superseded_by.path, []).append(edge)
    return LifecycleOverview(
        manifest.repository,
        manifest.repository_config.content_sha256 if manifest.repository_config else None,
        tuple(
            replace(
                lifecycle_entry(s),
                reason=outgoing[s.path].reason if s.path in outgoing else lifecycle_entry(s).reason,
                superseded_by=outgoing.get(s.path),
                supersedes=tuple(incoming.get(s.path, ())),
            )
            for s in sorted(manifest.sources, key=lambda s: s.path)
        ),
        edges,
        manifest.warnings,
    )
