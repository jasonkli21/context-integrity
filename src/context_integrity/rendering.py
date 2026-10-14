"""Pure human and stable JSON renderers."""

import json
from dataclasses import asdict

from context_integrity.models import InventoryManifest, SourceRecord


def manifest_dict(manifest: InventoryManifest) -> dict:
    repo = manifest.repository
    return {
        "schema_version": manifest.schema_version,
        "repository": {
            "id": repo.id,
            "name": repo.name,
            "identity_basis": repo.identity_basis,
            "git": {
                "available": repo.git_available,
                "head": repo.git_head,
                "dirty": repo.git_dirty,
            },
        },
        "sources": [asdict(s) for s in sorted(manifest.sources, key=lambda s: s.path)],
        "summary": asdict(manifest.summary),
        "warnings": [asdict(w) for w in manifest.warnings],
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
