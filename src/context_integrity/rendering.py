"""Pure human and stable JSON renderers."""

import json

from context_integrity.models import (
    ClassificationResult,
    InventoryManifest,
    InventorySummary,
    RepositoryRef,
    RuleMatch,
    ScanWarning,
    SourceRecord,
    SourceRevision,
)


def _repository_v1(repository: RepositoryRef) -> dict:
    return {
        "id": repository.id,
        "name": repository.name,
        "identity_basis": repository.identity_basis,
        "git": {
            "available": repository.git_available,
            "head": repository.git_head,
            "dirty": repository.git_dirty,
        },
    }


def _revision_v1(revision: SourceRevision) -> dict:
    return {
        "content_sha256": revision.content_sha256,
        "git_head": revision.git_head,
        "git_status": revision.git_status.value,
        "observed_revision_basis": revision.observed_revision_basis,
    }


def _rule_match_v1(match: RuleMatch) -> dict:
    return {
        "rule_id": match.rule_id,
        "dimension": match.dimension,
        "result": match.result,
        "confidence": match.confidence.value,
        "basis": match.basis,
    }


def _classification_v1(classification: ClassificationResult) -> dict:
    return {
        "kind": classification.kind.value,
        "authority_class": classification.authority_class.value,
        "lifecycle": classification.lifecycle.value,
        "confidence": classification.confidence.value,
        "matched_rules": list(classification.matched_rules),
        "basis": [_rule_match_v1(match) for match in classification.basis],
    }


def _source_v1(source: SourceRecord) -> dict:
    return {
        "id": source.id,
        "path": source.path,
        "kind": source.kind.value,
        "authority_class": source.authority_class.value,
        "lifecycle": source.lifecycle.value,
        "revision": _revision_v1(source.revision),
        "classification": _classification_v1(source.classification),
        "size_bytes": source.size_bytes,
    }


def _summary_v1(summary: InventorySummary) -> dict:
    return {
        "source_count": summary.source_count,
        "by_kind": summary.by_kind,
        "by_authority_class": summary.by_authority_class,
        "by_lifecycle": summary.by_lifecycle,
        "warning_count": summary.warning_count,
        "unclassified_kind_count": summary.unclassified_kind_count,
        "unclassified_authority_count": summary.unclassified_authority_count,
    }


def _warning_v1(warning: ScanWarning) -> dict:
    return {"code": warning.code, "path": warning.path, "message": warning.message}


def manifest_dict(manifest: InventoryManifest) -> dict:
    if manifest.schema_version != 1:
        raise ValueError(f"Unsupported inventory schema version: {manifest.schema_version}")
    return {
        "schema_version": 1,
        "repository": _repository_v1(manifest.repository),
        "sources": [_source_v1(s) for s in sorted(manifest.sources, key=lambda s: s.path)],
        "summary": _summary_v1(manifest.summary),
        "warnings": [_warning_v1(w) for w in manifest.warnings],
    }


def render_json(manifest: InventoryManifest, runtime_meta: dict | None = None) -> str:
    data = manifest_dict(manifest)
    if runtime_meta is not None:
        data["runtime_meta"] = runtime_meta
    # Escapes surrogate filenames and control characters; the output remains valid UTF-8.
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def display(value: str) -> str:
    """Keep filenames from injecting terminal controls or extra rows."""
    return json.dumps(value, ensure_ascii=True)[1:-1]


def render_text(manifest: InventoryManifest, summary_only: bool = False) -> str:
    repo, summary = manifest.repository, manifest.summary
    dirty = {True: "dirty", False: "clean", None: "unknown"}[repo.git_dirty]
    lines = [
        "Context Integrity — Source Inventory",
        "",
        f"Repository: {display(repo.name)}",
        f"Revision: {repo.git_head or 'unavailable'} ({dirty})",
        f"Git: {'yes' if repo.git_available else 'no'}",
        "",
        f"Sources: {summary.source_count}",
    ]
    for title, counts in (
        ("By kind", summary.by_kind),
        ("By authority class", summary.by_authority_class),
        ("Lifecycle", summary.by_lifecycle),
    ):
        lines.extend(["", title])
        lines.extend(f"  {key}: {count}" for key, count in sorted(counts.items()))
    if not summary_only:
        lines.extend(["", "Sources", "PATH | KIND | AUTHORITY | LIFECYCLE"])
        lines.extend(
            f"{display(s.path)} | {s.kind} | {s.authority_class} | {s.lifecycle}"
            for s in sorted(manifest.sources, key=lambda s: s.path)
        )
    lines.extend(
        [
            "",
            f"Warnings: {summary.warning_count}",
            f"Unclassified kind: {summary.unclassified_kind_count}",
            f"Unclassified authority: {summary.unclassified_authority_count}",
        ]
    )
    lines.extend(
        f"  {w.code} [{display(w.path) if w.path else 'repository'}]: {w.message}"
        for w in manifest.warnings
    )
    return "\n".join(lines) + "\n"


def render_explanation(source: SourceRecord) -> str:
    lines = [
        f"Source: {display(source.path)}",
        "",
        f"kind: {source.kind}",
        f"authority_class: {source.authority_class}",
        f"lifecycle: {source.lifecycle}",
        f"confidence (kind): {source.classification.confidence}",
        "",
        "Matched rules:",
    ]
    lines.extend(
        f"- {m.rule_id}: {m.dimension} -> {m.result} ({m.confidence}; {m.basis})"
        for m in source.classification.basis
    )
    rev = source.revision
    lines.extend(
        [
            "",
            "Revision:",
            f"- sha256: {rev.content_sha256 or 'unavailable'}",
            f"- git HEAD: {rev.git_head or 'unavailable'}",
            f"- git status: {rev.git_status}",
            f"- observed basis: {rev.observed_revision_basis}",
            "",
            "Not inferred:",
            "- active, superseded, expired, or invalid status; supersession relationships",
            "- authority precedence, claim correctness, implementation delivery, or drift",
        ]
    )
    return "\n".join(lines) + "\n"
