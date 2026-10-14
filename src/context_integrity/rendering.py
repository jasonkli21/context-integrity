"""Pure human and stable JSON renderers."""

import json

from context_integrity.models import (
    AuthorityPolicy,
    AuthorityResolution,
    AuthorityTier,
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
        f"- {m.rule_id}: {m.dimension} -> {m.result} ({m.confidence}; {display(m.basis)})"
        for m in source.classification.basis
    )
    if source.authority_metadata is not None:
        metadata = source.authority_metadata
        eligible = (
            str(metadata.authority_eligible).lower()
            if metadata.authority_eligible is not None
            else "true (default)"
        )
        lines.extend(
            [
                "",
                "Explicit authority metadata:",
                f"- authority_class: {metadata.authority_class_override or 'unchanged'}",
                f"- authority_eligible: {eligible}",
                f"- reason: {display(metadata.reason)}",
            ]
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
            "- authority policy resolution in this explanation (see `authority resolve`), "
            "claim correctness, implementation delivery, or drift",
        ]
    )
    return "\n".join(lines) + "\n"


AUTHORITY_DISCLAIMER = (
    "This resolves observed source-role precedence only. "
    "It does not establish claim correctness or agreement."
)


def policy_dict(policy: AuthorityPolicy) -> dict:
    return {
        "id": policy.id,
        "description": policy.description,
        "origin": policy.origin,
        "policy_version": policy.policy_version,
        "config_sha256": policy.config_revision,
        "tiers": [_tier_dict(i, tier) for i, tier in enumerate(policy.tiers)],
    }


def _tier_dict(index: int, tier: AuthorityTier) -> dict:
    return {"index": index, "classes": [c.value for c in tier.classes]}


def _authority_source(source: SourceRecord) -> dict:
    return {
        "source_id": source.id,
        "path": source.path,
        "kind": source.kind.value,
        "authority_class": source.authority_class.value,
        "lifecycle": source.lifecycle.value,
        "revision": _revision_v1(source.revision),
    }


def authority_dict(resolution: AuthorityResolution) -> dict:
    return {
        "schema_version": 1,
        "repository": _repository_v1(resolution.repository),
        "policy": policy_dict(resolution.policy),
        "config_sha256": resolution.config_sha256,
        "status": resolution.status.value,
        "highest_observed_tier": resolution.highest_observed_tier,
        "missing_stronger_tiers": [
            _tier_dict(i, resolution.policy.tiers[i]) for i in resolution.missing_stronger_tiers
        ],
        "highest_candidates": [
            {**_authority_source(c.source), "tier_index": c.tier_index}
            for c in resolution.highest_candidates
        ],
        "lower_candidates": [
            {**_authority_source(c.source), "tier_index": c.tier_index}
            for c in resolution.lower_candidates
        ],
        # Every inventoried source is accounted for, including not_in_policy.
        "excluded": [
            {
                **_authority_source(e.source),
                "reason": e.reason,
                "metadata_reason": e.metadata_reason,
            }
            for e in resolution.excluded
        ],
        "warnings": [_warning_v1(w) for w in resolution.warnings],
    }


def render_authority_json(resolution: AuthorityResolution) -> str:
    return (
        json.dumps(authority_dict(resolution), indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    )


def render_policy_list(policies: tuple[AuthorityPolicy, ...], as_json: bool = False) -> str:
    if as_json:
        return json.dumps([policy_dict(p) for p in policies], indent=2, sort_keys=True) + "\n"
    return "POLICY | ORIGIN | DESCRIPTION\n" + "".join(
        f"{display(p.id)} | {display(p.origin)} | {display(p.description)}\n" for p in policies
    )


def render_policy(policy: AuthorityPolicy, as_json: bool = False) -> str:
    if as_json:
        return json.dumps(policy_dict(policy), indent=2, sort_keys=True) + "\n"
    lines = [
        f"Policy: {display(policy.id)}",
        f"Origin: {display(policy.origin)}",
        f"Policy version: {display(policy.policy_version)}",
        f"Config sha256: {policy.config_revision or 'absent'}",
        display(policy.description),
        "",
    ]
    lines.extend(f"Tier {i}: {', '.join(t.classes)}" for i, t in enumerate(policy.tiers))
    return "\n".join(lines) + "\n"


def render_authority_text(resolution: AuthorityResolution) -> str:
    tier = resolution.highest_observed_tier
    lines = [
        f"Authority — {display(resolution.policy.id)}",
        "",
        f"Origin: {display(resolution.policy.origin)}",
        f"Policy version: {display(resolution.policy.policy_version)}",
        f"Config sha256: {resolution.config_sha256 or 'absent'}",
        f"Status: {resolution.status.value}",
        f"Highest observed tier: {tier if tier is not None else 'none'}",
        "Missing stronger tiers:",
    ]
    lines.extend(
        f"  {i}: {', '.join(resolution.policy.tiers[i].classes)}"
        for i in resolution.missing_stronger_tiers
    )
    if not resolution.missing_stronger_tiers:
        lines.append("  none")
    lines.extend(["", "Highest-precedence observed candidates:"])
    lines.extend(f"  {display(c.source.path)}" for c in resolution.highest_candidates)
    if not resolution.highest_candidates:
        lines.append("  none")
    lines.extend(["", "Lower-precedence candidates:"])
    lines.extend(
        f"  {display(c.source.path)} (tier {c.tier_index})" for c in resolution.lower_candidates
    )
    lines.extend(["", "Exclusions:"])
    lines.extend(
        f"  {display(e.source.path)}: {e.reason}"
        + (f" ({display(e.metadata_reason)})" if e.metadata_reason else "")
        for e in resolution.excluded
        if e.reason != "not_in_policy"
    )
    lines.append(
        f"  not_in_policy: {sum(e.reason == 'not_in_policy' for e in resolution.excluded)}"
    )
    lines.extend(
        f"Warning: {w.code} [{display(w.path) if w.path else 'repository'}]: {display(w.message)}"
        for w in resolution.warnings
    )
    lines.extend(["", "Important:", AUTHORITY_DISCLAIMER])
    return "\n".join(lines) + "\n"
