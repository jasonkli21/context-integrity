"""Pure explicit-package contract validation over current inventory metadata."""

import json
from collections import Counter
from hashlib import sha256

from context_integrity.acquisition import normalize_path
from context_integrity.models import (
    ContextContract,
    ContextContractRule,
    ContextPackage,
    ContextRuleMode,
    ContextRuleResult,
    ContractFinding,
    ContractValidationOverview,
    FindingSeverity,
    InventoryManifest,
    RepositoryConfig,
    ScanWarning,
    SourceRecord,
    _validate_integrity_path,
)


def effective_contracts(config: RepositoryConfig | None) -> tuple[ContextContract, ...]:
    return tuple(sorted(config.context_contracts, key=lambda c: c.id)) if config else ()


def resolve_contract(config: RepositoryConfig | None, contract_id: str) -> ContextContract:
    for contract in effective_contracts(config):
        if contract.id == contract_id:
            return contract
    raise ValueError("Unknown context contract ID.")


def matches_rule(source: SourceRecord, rule: ContextContractRule) -> bool:
    """AND across dimensions, OR within each dimension, no implicit lifecycle filter."""
    return all(
        not values or value in values
        for value, values in (
            (source.path, rule.paths),
            (source.kind, rule.kinds),
            (source.authority_class, rule.authority_classes),
            (source.lifecycle, rule.lifecycles),
        )
    )


def resolve_package(manifest: InventoryManifest, paths: tuple[str, ...]) -> ContextPackage:
    normalized = []
    for path in paths:
        # Reject drive, backslash, trailing slash ambiguity before POSIX normalization.
        if not isinstance(path, str) or "\\" in path or ":" in path or path.endswith("/"):
            raise ValueError("Invalid package source path.")
        value = normalize_path(path)
        _validate_integrity_path(value)
        normalized.append(value)
    counts = Counter(normalized)
    sources = {s.path: s for s in manifest.sources}
    return ContextPackage(
        tuple(sorted(normalized)),
        tuple(sources[p] for p in sorted(counts) if p in sources),
        tuple(sorted(counts.keys() - sources.keys())),
        tuple(sorted(p for p, count in counts.items() if count > 1)),
    )


def _finding(
    contract_id: str, rule_id: str | None, code: str, paths: tuple[str, ...], message: str
) -> ContractFinding:
    identity = json.dumps([contract_id, rule_id, code, sorted(paths)], ensure_ascii=True)
    return ContractFinding(
        "contract_" + sha256(identity.encode()).hexdigest()[:32],
        contract_id,
        rule_id,
        code,
        FindingSeverity.MEDIUM,
        message,
        tuple(sorted(paths)),
    )


def validate_contract(
    manifest: InventoryManifest, contract: ContextContract, paths: tuple[str, ...] = ()
) -> ContractValidationOverview:
    config = manifest.repository_config
    configured = (
        next((item for item in config.context_contracts if item.id == contract.id), None)
        if config is not None
        else None
    )
    if (
        configured is None
        or configured != contract
        or contract.config_revision != config.content_sha256
    ):
        raise ValueError("Context contract is not bound to the observed repository configuration.")

    package = resolve_package(manifest, paths)
    findings = [
        _finding(
            contract.id,
            None,
            "package_source_unavailable",
            (path,),
            "Package source is absent from the current inventory.",
        )
        for path in package.unresolved_paths
    ]
    results = []
    for rule in sorted(contract.rules, key=lambda r: r.id):
        matched = tuple(s.path for s in package.resolved_sources if matches_rule(s, rule))
        count = len(matched)
        code = None
        if count < rule.min_count:
            code = "required_context_missing"
            message = f"Rule requires at least {rule.min_count} matching sources; found {count}."
        elif rule.max_count is not None and count > rule.max_count:
            code = (
                "excluded_context_present"
                if rule.mode == ContextRuleMode.EXCLUDED
                else "context_rule_overfilled"
            )
            message = f"Rule allows at most {rule.max_count} matching sources; found {count}."
        if code:
            findings.append(_finding(contract.id, rule.id, code, matched, message))
        results.append(
            ContextRuleResult(
                rule.id, rule.mode, matched, count, rule.min_count, rule.max_count, code is None
            )
        )
    warnings = [
        *manifest.warnings,
        *(
            ScanWarning(
                "duplicate_package_source", path, "Duplicate package source counts only once."
            )
            for path in package.duplicate_paths
        ),
    ]
    return ContractValidationOverview(
        manifest.repository,
        config.content_sha256,
        contract,
        package,
        tuple(results),
        tuple(
            sorted(
                findings,
                key=lambda f: (f.contract_id, f.rule_id or "", f.code, f.affected_paths, f.id),
            )
        ),
        tuple(sorted(warnings, key=lambda w: (w.path or "", w.code, w.message))),
    )
