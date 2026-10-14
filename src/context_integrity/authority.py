"""Question-specific policy definitions and pure observed source-role resolution."""

from context_integrity.models import (
    AuthorityCandidate,
    AuthorityClass,
    AuthorityExclusion,
    AuthorityPolicy,
    AuthorityResolution,
    AuthorityResolutionStatus,
    AuthorityTier,
    InventoryManifest,
    LifecycleState,
    RepositoryAuthorityConfig,
    SourceAuthorityMetadata,
)

BUILTIN_POLICY_VERSION = "builtin-v1"


def _policy(id: str, description: str, *classes: str) -> AuthorityPolicy:
    return AuthorityPolicy(
        id,
        description,
        tuple(AuthorityTier((AuthorityClass(c),)) for c in classes),
        policy_version=BUILTIN_POLICY_VERSION,
    )


BUILTIN_POLICIES = (
    _policy(
        "delivered_behavior",
        "Preferred sources for delivered behavior",
        "executable_truth",
        "verification_evidence",
        "generated_derivative",
    ),
    _policy(
        "architectural_intent",
        "Preferred sources for intended architecture",
        "decision",
        "architecture_product",
        "plan",
    ),
    _policy(
        "operating_instructions",
        "Preferred sources for agent/developer operations",
        "operating_instruction",
        "architecture_product",
        "plan",
    ),
    _policy(
        "implementation_status",
        "Preferred sources for implementation status",
        "verification_evidence",
        "generated_derivative",
        "plan",
    ),
    _policy(
        "future_work",
        "Preferred sources for authorized future work",
        "plan",
        "architecture_product",
        "generated_derivative",
    ),
)


def effective_policies(
    config: RepositoryAuthorityConfig | None = None,
) -> tuple[AuthorityPolicy, ...]:
    policies = {p.id: p for p in BUILTIN_POLICIES}
    if config is not None:
        policies.update((p.id, p) for p in config.policies)
    return tuple(policies[id] for id in sorted(policies))


def resolve_authority(
    manifest: InventoryManifest,
    policy: AuthorityPolicy,
    source_metadata: tuple[SourceAuthorityMetadata, ...] | None = None,
) -> AuthorityResolution:
    config = manifest.authority_config or RepositoryAuthorityConfig()
    metadata = {
        m.path: m for m in (config.source_metadata if source_metadata is None else source_metadata)
    }
    tiers = {c: i for i, tier in enumerate(policy.tiers) for c in tier.classes}
    candidates = []
    excluded = []
    for source in sorted(manifest.sources, key=lambda s: s.path):
        entry = metadata.get(source.path)
        if source.lifecycle == LifecycleState.HISTORICAL:
            reason = "historical_lifecycle"
        elif entry is not None and entry.authority_eligible is False:
            reason = "explicitly_ineligible"
        elif source.authority_class not in tiers:
            reason = "not_in_policy"
        else:
            candidates.append(AuthorityCandidate(source, tiers[source.authority_class]))
            continue
        excluded.append(AuthorityExclusion(source, reason, entry.reason if entry else None))
    highest = min((c.tier_index for c in candidates), default=None)
    return AuthorityResolution(
        manifest.repository,
        policy,
        config.content_sha256,
        AuthorityResolutionStatus.CANDIDATES_FOUND
        if highest is not None
        else AuthorityResolutionStatus.NO_ELIGIBLE_CANDIDATES,
        highest,
        tuple(c for c in candidates if c.tier_index == highest),
        tuple(c for c in candidates if c.tier_index != highest),
        tuple(range(highest if highest is not None else len(policy.tiers))),
        tuple(excluded),
        manifest.warnings,
    )
