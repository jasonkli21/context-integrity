"""Pure explicit claim resolution over an already verified inventory observation."""

from context_integrity.configuration import CONFIG_PATH, ConfigurationError
from context_integrity.models import (
    ClaimDependency,
    ClaimDiagnostic,
    ClaimProvenance,
    ClaimRecord,
    ClaimsOverview,
    ClaimValidity,
    InventoryManifest,
    RepositoryConfig,
    SourceRevision,
    validate_unique_claim_ids,
)


def _content_available(revision: SourceRevision) -> bool:
    return (
        revision.content_sha256 is not None
        and revision.observed_revision_basis == "working_tree_content"
    )


def claims_overview(manifest: InventoryManifest) -> ClaimsOverview:
    """Attach observed identities/revisions; completeness never establishes validity.

    Call after inventory's config consistency check. No source bodies are read here.
    A broken declaration observation fails closed, just as inventory config reads do.
    Dependencies with unavailable revisions remain visible and unresolved.
    """
    config = manifest.repository_config or RepositoryConfig()
    observed = {s.path: s for s in manifest.sources}
    declaration = observed.get(CONFIG_PATH)
    if config.claims and (
        declaration is None
        or not _content_available(declaration.revision)
        or declaration.revision.content_sha256 != config.content_sha256
    ):
        raise ConfigurationError("Claim declaration revision is unavailable or inconsistent.")
    validate_unique_claim_ids(config.claims)
    claims = []
    diagnostics = []
    for spec in sorted(config.claims, key=lambda c: c.id):
        dependencies = []
        for path in sorted(spec.depends_on):
            source = observed.get(path)
            resolved = source is not None and _content_available(source.revision)
            dependencies.append(
                ClaimDependency(
                    path,
                    source.id if source else None,
                    source.revision if source else None,
                    resolved,
                )
            )
            if not resolved:
                diagnostics.append(
                    ClaimDiagnostic(
                        spec.id,
                        "claim_dependency_revision_unavailable"
                        if source
                        else "claim_dependency_missing",
                        path,
                        "Dependency "
                        + (
                            "content revision is unavailable."
                            if source
                            else "is absent from inventory."
                        ),
                    )
                )
        claims.append(
            ClaimRecord(
                spec.id,
                spec.claim_type,
                spec.subject,
                spec.predicate,
                spec.value,
                spec.scope,
                ClaimValidity.UNVERIFIED,
                ClaimProvenance(
                    declaration.id,
                    CONFIG_PATH,
                    declaration.revision,
                    f"claim:{spec.id}",
                    "repository_config_explicit",
                    "claims-v1",
                ),
                tuple(dependencies),
                all(d.resolved for d in dependencies),
            )
        )
    return ClaimsOverview(
        manifest.repository,
        config.content_sha256,
        tuple(claims),
        manifest.warnings,
        tuple(sorted(diagnostics, key=lambda d: (d.path, d.code, d.claim_id, d.message))),
    )
