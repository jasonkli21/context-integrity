"""Inventory application use case; no printing or output writes."""

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from context_integrity.acquisition import MAX_SOURCE_BYTES, enumerate_candidates, read_source
from context_integrity.classification import apply_authority_metadata, classify_source
from context_integrity.configuration import CONFIG_PATH, load_config, verify_config_revision
from context_integrity.lifecycle import apply_lifecycle_metadata, resolve_supersession
from context_integrity.models import (
    AuthorityClass,
    GitFileStatus,
    InventoryManifest,
    InventorySummary,
    ScanWarning,
    SourceKind,
    SourceRecord,
    SourceRevision,
    make_source_id,
)
from context_integrity.repository import RepositoryContext, RepositoryError, discover_repository


@dataclass
class InventoryObservationBudget:
    """Optional invocation-wide accounting, including refused/skipped reads."""

    remaining_bytes: int = 64 * 1024 * 1024
    remaining_attempts: int = 4096


def inventory_repository(
    context: RepositoryContext,
    *,
    max_observation_bytes: int | None = None,
    max_sources: int | None = None,
    require_stable: bool = False,
    observation_budget: InventoryObservationBudget | None = None,
) -> InventoryManifest:
    if observation_budget is not None:
        max_sources = (
            min(max_sources, observation_budget.remaining_attempts)
            if max_sources is not None
            else observation_budget.remaining_attempts
        )
        max_observation_bytes = (
            min(max_observation_bytes, observation_budget.remaining_bytes)
            if max_observation_bytes is not None
            else observation_budget.remaining_bytes
        )
    config = load_config(context)
    metadata = {m.path: m for m in config.source_metadata}
    sources = []
    paths = set(enumerate_candidates(context))
    # Policy config is observed even if Git ignores it: it still controls interpretation.
    forced_config = config.content_sha256 is not None and CONFIG_PATH not in paths
    if config.content_sha256 is not None:
        paths.add(CONFIG_PATH)
    if max_sources is not None and len(paths) > max_sources:
        raise RepositoryError("Inventory observation budget exceeded.")
    remaining = max_observation_bytes
    for path in sorted(paths):
        status = (
            context.statuses.get(path, GitFileStatus.TRACKED_CLEAN)
            if context.status_known
            else GitFileStatus.UNKNOWN
        )
        if path == CONFIG_PATH and forced_config:
            status = GitFileStatus.UNKNOWN
        if status == GitFileStatus.DELETED:
            continue
        if remaining is not None and remaining <= 0:
            raise RepositoryError("Inventory observation budget exceeded.")
        bound = MAX_SOURCE_BYTES if remaining is None else min(MAX_SOURCE_BYTES, remaining)
        size, digest, skipped = (
            read_source(context, path, max_bytes=bound, require_stable=True)
            if require_stable
            else read_source(context, path)
            if remaining is None
            else read_source(context, path, max_bytes=bound)
        )
        if remaining is not None:
            used = min(size, bound) if size is not None else bound
            if observation_budget is not None:
                used = size if digest is not None else bound
                observation_budget.remaining_bytes -= used
                observation_budget.remaining_attempts -= 1
            remaining -= used
            if digest is None and bound < MAX_SOURCE_BYTES:
                raise RepositoryError("Inventory observation budget exceeded.")
        if skipped:
            continue
        entry = metadata.get(path)
        classification = apply_authority_metadata(classify_source(path), entry)
        classification = apply_lifecycle_metadata(classification, entry)
        revision = SourceRevision(
            digest,
            context.repository.git_head,
            status,
            "working_tree_content" if digest else "unavailable",
        )
        sources.append(
            SourceRecord(
                make_source_id(context.repository.id, path),
                path,
                classification.kind,
                classification.authority_class,
                classification.lifecycle,
                revision,
                classification,
                size,
                entry,
            )
        )
    # Resolve relations only after the complete observed endpoint set is known.
    final_sources, edges, edge_warnings = resolve_supersession(tuple(sources), config)
    sources = list(final_sources)
    context.warnings.extend(edge_warnings)
    observed_paths = {s.path for s in sources}
    for path in sorted(metadata.keys() - observed_paths):
        entry = metadata[path]
        if entry.authority_class_override is not None or entry.authority_eligible is not None:
            context.warnings.append(
                ScanWarning(
                    "authority_metadata_source_missing",
                    path,
                    "Authority metadata references a source absent from inventory.",
                )
            )
        if entry.lifecycle_override is not None:
            context.warnings.append(
                ScanWarning(
                    "lifecycle_metadata_source_missing",
                    path,
                    "Lifecycle metadata references a source absent from inventory.",
                )
            )
    observed_config = next((s for s in sources if s.path == CONFIG_PATH), None)
    verify_config_revision(
        context, config, observed_config.revision.content_sha256 if observed_config else None
    )
    warnings = tuple(sorted(context.warnings, key=lambda w: (w.path or "", w.code, w.message)))
    summary = InventorySummary(
        len(sources),
        dict(sorted(Counter(s.kind.value for s in sources).items())),
        dict(sorted(Counter(s.authority_class.value for s in sources).items())),
        dict(sorted(Counter(s.lifecycle.value for s in sources).items())),
        len(warnings),
        sum(s.kind in {SourceKind.UNKNOWN, SourceKind.OTHER_DOCUMENT} for s in sources),
        sum(s.authority_class == AuthorityClass.UNKNOWN for s in sources),
    )
    return InventoryManifest(
        context.repository,
        tuple(sources),
        summary,
        warnings,
        repository_config=config,
        supersession=edges,
    )


def scan_repository(path: Path | str) -> InventoryManifest:
    return inventory_repository(discover_repository(path))
