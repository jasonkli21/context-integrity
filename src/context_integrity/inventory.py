"""Inventory application use case; no printing or output writes."""

from collections import Counter
from pathlib import Path

from context_integrity.acquisition import enumerate_candidates, read_source
from context_integrity.classification import classify_source
from context_integrity.models import (
    AuthorityClass,
    GitFileStatus,
    InventoryManifest,
    InventorySummary,
    SourceKind,
    SourceRecord,
    SourceRevision,
    make_source_id,
)
from context_integrity.repository import RepositoryContext, discover_repository


def inventory_repository(context: RepositoryContext) -> InventoryManifest:
    sources = []
    for path in enumerate_candidates(context):
        size, digest, skipped = read_source(context, path)
        if skipped:
            continue
        classification = classify_source(path)
        status = (
            context.statuses.get(path, GitFileStatus.TRACKED_CLEAN)
            if context.status_known
            else GitFileStatus.UNKNOWN
        )
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
            )
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
    return InventoryManifest(context.repository, tuple(sources), summary, warnings)


def scan_repository(path: Path | str) -> InventoryManifest:
    return inventory_repository(discover_repository(path))
