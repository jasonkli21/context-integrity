"""Pure human and stable JSON renderers."""

import json

from context_integrity.lifecycle import (
    active_authority_exclusion_reason,
    lifecycle_authority_eligible,
    lifecycle_entry,
)
from context_integrity.models import (
    AuthorityPolicy,
    AuthorityResolution,
    AuthorityTier,
    ClaimRecord,
    ClaimsOverview,
    ClassificationResult,
    InventoryManifest,
    InventorySummary,
    LifecycleEntry,
    LifecycleOverview,
    RepositoryRef,
    ResolvedSupersession,
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


def render_explanation(source: SourceRecord, entry: LifecycleEntry | None = None) -> str:
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
    if source.source_metadata is not None and (
        source.source_metadata.authority_class_override is not None
        or source.source_metadata.authority_eligible is not None
    ):
        metadata = source.source_metadata
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
    entry = entry or lifecycle_entry(source)
    builtin = next(m for m in source.classification.basis if m.dimension == "lifecycle")
    lines.extend(["", f"Built-in lifecycle: {builtin.result} ({builtin.rule_id})"])
    lines.extend(
        [
            "",
            "Effective lifecycle:",
            f"- state: {source.lifecycle}",
            f"- origin: {entry.origin}",
            f"- reason: {display(entry.reason)}",
            "- lifecycle authority eligibility: "
            + str(lifecycle_authority_eligible(source.lifecycle)).lower(),
            "- direct superseded_by: "
            + (display(entry.superseded_by.superseded_by.path) if entry.superseded_by else "none"),
        ]
    )
    metadata = source.source_metadata
    if metadata and metadata.lifecycle_override is not None:
        lines.extend(
            [
                "Explicit lifecycle metadata:",
                f"- lifecycle: {metadata.lifecycle_override}",
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
            "- lifecycle or supersession from recency, filenames, Git dates, or source bodies",
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


def _supersession_v1(edge: ResolvedSupersession) -> dict:
    return {
        "source": _authority_source(edge.source),
        "superseded_by": _authority_source(edge.superseded_by),
        "reason": edge.reason,
        "config_sha256": edge.config_sha256,
    }


def _lifecycle_entry_v1(entry: LifecycleEntry) -> dict:
    source = entry.source
    explicit = source.source_metadata.authority_eligible if source.source_metadata else None
    reason = active_authority_exclusion_reason(source.lifecycle, explicit)
    return {
        **_authority_source(source),
        "lifecycle_origin": entry.origin.value,
        "lifecycle_reason": entry.reason,
        "lifecycle_authority_eligible": lifecycle_authority_eligible(source.lifecycle),
        "explicit_authority_eligible": explicit,
        "active_authority_eligible": reason is None,
        "active_authority_exclusion_reason": reason,
        "superseded_by": _supersession_v1(entry.superseded_by) if entry.superseded_by else None,
        "supersedes": [_supersession_v1(e) for e in entry.supersedes],
    }


def lifecycle_dict(overview: LifecycleOverview) -> dict:
    """Independent lifecycle JSON v1; inventory/authority projections remain separate."""
    return {
        "schema_version": 1,
        "repository": _repository_v1(overview.repository),
        "config_sha256": overview.config_sha256,
        "sources": [
            _lifecycle_entry_v1(e) for e in sorted(overview.sources, key=lambda e: e.source.path)
        ],
        "supersession": [_supersession_v1(e) for e in overview.supersession],
        "warnings": [_warning_v1(w) for w in overview.warnings],
    }


def render_lifecycle_json(overview: LifecycleOverview) -> str:
    return json.dumps(lifecycle_dict(overview), indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def render_lifecycle_text(overview: LifecycleOverview, detail: bool = False) -> str:
    lines = [
        "Context Integrity — Source Lifecycle",
        "",
        f"Repository: {display(overview.repository.name)}",
        f"Config sha256: {overview.config_sha256 or 'absent'}",
        "",
    ]
    for entry in overview.sources:
        source = entry.source
        lines.extend(
            [
                f"Source: {display(source.path)}",
                f"  source_id: {display(source.id)}",
                f"  lifecycle: {source.lifecycle}",
                f"  origin: {entry.origin}",
                f"  reason: {display(entry.reason)}",
                "  superseded_by: "
                + (
                    display(entry.superseded_by.superseded_by.path)
                    if entry.superseded_by
                    else "none"
                ),
                "  supersedes: "
                + (", ".join(display(e.source.path) for e in entry.supersedes) or "none"),
            ]
        )
        if entry.superseded_by:
            lines.append(f"  supersession reason: {display(entry.superseded_by.reason)}")
        if detail:
            rev = source.revision
            eligibility = _lifecycle_entry_v1(entry)
            lines.extend(
                [
                    f"  kind: {source.kind}",
                    f"  authority_class: {source.authority_class}",
                    f"  sha256: {rev.content_sha256 or 'unavailable'}",
                    f"  git HEAD: {rev.git_head or 'unavailable'}",
                    f"  git status: {rev.git_status}",
                    f"  observed basis: {rev.observed_revision_basis}",
                    "  lifecycle authority eligibility: "
                    + str(lifecycle_authority_eligible(source.lifecycle)).lower(),
                    "  explicit authority eligibility: "
                    + (
                        str(eligibility["explicit_authority_eligible"]).lower()
                        if eligibility["explicit_authority_eligible"] is not None
                        else "unspecified"
                    ),
                    "  active authority eligible: "
                    + str(eligibility["active_authority_eligible"]).lower(),
                    "  active authority exclusion reason: "
                    + (eligibility["active_authority_exclusion_reason"] or "none"),
                ]
            )
        lines.append("")
    lines.extend(
        f"Warning: {w.code} [{display(w.path) if w.path else 'repository'}]: {display(w.message)}"
        for w in overview.warnings
    )
    return "\n".join(lines) + "\n"


def _claim_v1(claim: ClaimRecord) -> dict:
    provenance = claim.provenance
    return {
        "id": claim.id,
        "claim_type": claim.claim_type,
        "subject": claim.subject,
        "predicate": claim.predicate,
        "value": claim.value,
        "scope": claim.scope,
        "validity": claim.validity.value,
        "provenance_complete": claim.provenance_complete,
        "provenance": {
            "source_id": provenance.source_id,
            "path": provenance.path,
            "revision": _revision_v1(provenance.revision),
            "locator": provenance.locator,
            "extraction_method": provenance.extraction_method,
            "extractor_version": provenance.extractor_version,
        },
        "dependencies": [
            {
                "path": d.path,
                "source_id": d.source_id,
                "revision": _revision_v1(d.revision) if d.revision else None,
                "resolved": d.resolved,
            }
            for d in sorted(claim.dependencies, key=lambda d: d.path)
        ],
    }


def claims_dict(overview: ClaimsOverview) -> dict:
    """Independent explicit claims JSON v1; no source bodies or internal config fields."""
    if overview.schema_version != 1:
        raise ValueError("Unsupported claims schema version.")
    return {
        "schema_version": 1,
        "repository": _repository_v1(overview.repository),
        "config_sha256": overview.config_sha256,
        "claims": [_claim_v1(c) for c in sorted(overview.claims, key=lambda c: c.id)],
        "warnings": [
            _warning_v1(w)
            for w in sorted(overview.warnings, key=lambda w: (w.path or "", w.code, w.message))
        ],
    }


def render_claims_json(overview: ClaimsOverview) -> str:
    return json.dumps(claims_dict(overview), indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def _claim_revision_text(revision: SourceRevision) -> list[str]:
    return [
        f"    sha256: {display(revision.content_sha256 or 'unavailable')}",
        f"    git HEAD: {display(revision.git_head or 'unavailable')}",
        f"    git status: {display(revision.git_status.value)}",
        f"    observed basis: {display(revision.observed_revision_basis)}",
    ]


def render_claims_text(overview: ClaimsOverview, detail: bool = False) -> str:
    lines = [
        "Context Integrity — Claims",
        "",
        f"Repository: {display(overview.repository.name)}",
        "",
    ]
    if not detail:
        lines.append("ID  TYPE  VALIDITY  PROVENANCE")
    for claim in sorted(overview.claims, key=lambda c: c.id):
        if not detail:
            lines.append(
                f"{display(claim.id)}  {display(claim.claim_type)}  "
                f"{display(claim.validity.value)}  "
                + ("complete" if claim.provenance_complete else "incomplete")
            )
            continue
        lines.extend(
            [
                f"Claim: {display(claim.id)}",
                f"Type: {display(claim.claim_type)}",
                f"Subject: {display(claim.subject)}",
                f"Predicate: {display(claim.predicate)}",
                f"Value: {display(claim.value)}",
                f"Scope: {display(claim.scope) if claim.scope is not None else 'unspecified'}",
                f"Validity: {display(claim.validity.value)}",
                f"Provenance complete: {str(claim.provenance_complete).lower()}",
                "",
                "Declared by:",
                f"  path: {display(claim.provenance.path)}",
                f"  source id: {display(claim.provenance.source_id)}",
                f"  locator: {display(claim.provenance.locator)}",
                f"  extraction: {display(claim.provenance.extraction_method)}",
                f"  extractor version: {display(claim.provenance.extractor_version)}",
            ]
        )
        lines.extend(_claim_revision_text(claim.provenance.revision))
        lines.extend(["", "Depends on:"])
        if not claim.dependencies:
            lines.append("  none")
        for dependency in sorted(claim.dependencies, key=lambda d: d.path):
            lines.extend(
                [
                    f"  {display(dependency.path)}",
                    f"    resolved: {str(dependency.resolved).lower()}",
                    "    source id: "
                    + (display(dependency.source_id) if dependency.source_id else "unavailable"),
                ]
            )
            if dependency.revision:
                lines.extend(_claim_revision_text(dependency.revision))
        lines.append("")
    lines.extend(
        [
            "",
            "Claim validity is not derived from source lifecycle or authority resolution.",
            f"Warnings: {len(overview.warnings)}",
        ]
    )
    lines.extend(
        f"Warning: {display(w.code)} [{display(w.path) if w.path else 'repository'}]: "
        f"{display(w.message)}"
        for w in overview.warnings
    )
    return "\n".join(lines) + "\n"
