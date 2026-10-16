"""Deterministic required-first context compilation over an observed inventory."""

from dataclasses import replace

from context_integrity.authority import effective_policies, resolve_authority_for_sources
from context_integrity.configuration import ConfigurationError
from context_integrity.contracts import matches_rule, require_bound_contract, validate_contract
from context_integrity.models import (
    CandidateDecisionKind as Reason,
)
from context_integrity.models import (
    CompilationBudget,
    CompilationStatus,
    CompiledContext,
    CompiledDependency,
    CompiledRuleDecision,
    CompiledSourceDecision,
    ContextContract,
    InventoryManifest,
    LifecycleState,
    usable_content_revision,
)
from context_integrity.models import (
    ContextRuleMode as Mode,
)


def compile_context(
    manifest: InventoryManifest,
    contract: ContextContract,
    *,
    task: str | None = None,
    budget_bytes: int | None = None,
) -> CompiledContext:
    """Compile a selection manifest, then validate it with the Phase 5 validator.

    Eligibility is conservative across overlapping rules: selecting via another rule
    cannot bypass a matching rule's lifecycle or authority restriction. Maxima count
    raw matches, exactly as final validation does.
    """
    require_bound_contract(manifest, contract)
    budget = CompilationBudget(contract.budget_bytes, budget_bytes, 0)
    rules = tuple(sorted(contract.rules, key=lambda r: r.id))
    sources = tuple(sorted(manifest.sources, key=lambda s: s.path))
    policies = {p.id: p for p in effective_policies(manifest.repository_config)}
    if any(r.authority_policy is not None and r.authority_policy not in policies for r in rules):
        raise ConfigurationError("Invalid context contract authority policy.")
    matched = {r.id: tuple(s for s in sources if matches_rule(s, r)) for r in rules}
    excluded = {s.path for r in rules if r.mode == Mode.EXCLUDED for s in matched[r.id]}
    relationships = {s.path: [] for s in sources}
    for rule in rules:
        candidates = matched[rule.id]
        lifecycle_paths = {
            s.path
            for s in candidates
            if rule.lifecycles or s.lifecycle in {LifecycleState.UNKNOWN, LifecycleState.ACTIVE}
        }
        resolution = None
        tiers = {}
        exclusions = {}
        highest_paths = ()
        if rule.authority_policy and rule.mode != Mode.EXCLUDED:
            resolution = resolve_authority_for_sources(
                manifest,
                policies[rule.authority_policy],
                tuple(
                    s for s in candidates if s.path in lifecycle_paths and s.path not in excluded
                ),
            )
            tiers = {
                c.source.path: c.tier_index
                for c in (*resolution.highest_candidates, *resolution.lower_candidates)
            }
            exclusions = {c.source.path: c.reason for c in resolution.excluded}
            highest_paths = tuple(c.source.path for c in resolution.highest_candidates)
        for source in candidates:
            reason = Reason.NOT_SELECTED
            if source.path in excluded:
                reason = Reason.EXCLUDED_BY_CONTRACT
            elif source.path not in lifecycle_paths:
                reason = Reason.INELIGIBLE_LIFECYCLE
            elif resolution is not None:
                if source.path in exclusions:
                    reason = Reason.INELIGIBLE_AUTHORITY
                elif source.path not in highest_paths:
                    reason = Reason.LOWER_AUTHORITY_TIER
            relationships[source.path].append(
                CompiledRuleDecision(
                    rule.id,
                    reason,
                    rule.authority_policy,
                    tiers.get(source.path),
                    resolution.highest_observed_tier if resolution else None,
                    highest_paths,
                    exclusions.get(source.path),
                )
            )

    selected = set()
    used = 0
    counts = {r.id: 0 for r in rules}
    raw_rules = {s.path: tuple(r for r in rules if matches_rule(s, r)) for s in sources}
    eligibility = {}
    for source in sources:
        reasons = relationships[source.path]
        blocked = next((d.reason for d in reasons if d.reason != Reason.NOT_SELECTED), None)
        if blocked is None and not usable_content_revision(source.revision):
            blocked = Reason.UNVERIFIABLE_REVISION
        if blocked is None and (type(source.size_bytes) is not int or source.size_bytes < 0):
            blocked = Reason.UNVERIFIABLE_SIZE
        eligibility[source.path] = blocked

    def constraint(source):
        if any(
            r.max_count is not None and counts[r.id] >= r.max_count for r in raw_rules[source.path]
        ):
            return Reason.BLOCKED_BY_RULE_MAX
        if budget.effective_bytes is not None and used + source.size_bytes > budget.effective_bytes:
            return Reason.BLOCKED_BY_BUDGET
        return None

    def select(source):
        nonlocal used
        selected.add(source.path)
        used += source.size_bytes
        for rule in raw_rules[source.path]:
            counts[rule.id] += 1

    required = tuple(r for r in rules if r.mode == Mode.REQUIRED)
    while True:
        unsatisfied = {r.id for r in required if counts[r.id] < r.min_count}
        ranked = []
        for source in sources:
            if source.path in selected or eligibility[source.path] is not None:
                continue
            helpful = [r for r in raw_rules[source.path] if r.id in unsatisfied]
            if not helpful or constraint(source) is not None:
                continue
            priorities = [r.priority for r in helpful]
            # Authority has already narrowed each rule to its highest tier. Tier
            # indices from unrelated policies do not form a global source rank.
            ranked.append(
                ((-len(helpful), -max(priorities), -sum(priorities), source.path), source)
            )
        if not ranked:
            break
        select(min(ranked, key=lambda item: item[0])[1])

    for rule in sorted(
        (r for r in rules if r.mode == Mode.OPTIONAL), key=lambda r: (-r.priority, r.id)
    ):
        for source in matched[rule.id]:
            if (
                source.path not in selected
                and eligibility[source.path] is None
                and constraint(source) is None
            ):
                select(source)

    decisions = []
    for source in sources:
        relations = relationships[source.path]
        if source.path in selected:
            reason = Reason.SELECTED
        elif eligibility[source.path] is not None:
            reason = eligibility[source.path]
        elif not relations:
            reason = Reason.NOT_SELECTED
        else:
            reason = constraint(source) or Reason.REDUNDANT
        # Preserve the individual policy rejections even if another rule also
        # matched; selected relations identify every satisfied rule contribution.
        decisions.append(
            CompiledSourceDecision(
                source,
                reason,
                tuple(d.rule_id for d in relations),
                tuple(d.rule_id for d in relations) if reason == Reason.SELECTED else (),
                tuple(
                    replace(d, reason=reason) if d.reason == Reason.NOT_SELECTED else d
                    for d in relations
                ),
            )
        )
    chosen = tuple(s for s in sources if s.path in selected)
    validation = validate_contract(manifest, contract, tuple(s.path for s in chosen))
    return CompiledContext(
        manifest.repository,
        task,
        contract,
        validation.config_sha256,
        CompilationStatus.INCOMPLETE if validation.findings else CompilationStatus.COMPLETE,
        CompilationBudget(contract.budget_bytes, budget_bytes, used),
        chosen,
        tuple(decisions),
        validation,
        tuple(CompiledDependency(s.id, s.path, s.revision) for s in chosen),
        validation.warnings,
        authority_policies=tuple(
            policies[id]
            for id in sorted({r.authority_policy for r in rules if r.authority_policy is not None})
        ),
    )
