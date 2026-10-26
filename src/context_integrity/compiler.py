"""Deterministic required-first context compilation over an observed inventory."""

from dataclasses import replace

from context_integrity.authority import effective_policies, resolve_authority_for_sources
from context_integrity.configuration import ConfigurationError
from context_integrity.contracts import (
    matches_rule,
    require_bound_contract,
    validate_contract_sources,
)
from context_integrity.evidence import EvidenceContextBatch, EvidenceProviderError
from context_integrity.models import (
    CandidateDecisionKind as Reason,
)
from context_integrity.models import (
    CompilationBudget,
    CompilationStatus,
    CompiledContext,
    CompiledDependency,
    CompiledIntegrityState,
    CompiledRuleDecision,
    CompiledSourceDecision,
    CompilerCandidate,
    ContextContract,
    IntegrityEvaluationStatus,
    IntegrityOverview,
    InventoryManifest,
    LifecycleState,
    ScanWarning,
    usable_content_revision,
)
from context_integrity.models import (
    ContextRuleMode as Mode,
)

MAX_REPAIR_WORK = 250_000


class _RepairLimit(Exception):
    pass


def _repair_required(candidates, raw_rules, rules, required, byte_limit):
    """Exact repair within deterministic work, with conservative feasibility pruning.

    Charge node copies, candidate/rule visits and cost sorting before doing the work.
    Iteration avoids Python recursion limits. Exhaustion retains the original greedy
    package, even if an unproven optimum was found; it never claims infeasibility.
    """
    work = 0

    def charge(amount):
        nonlocal work
        work += amount
        if work > MAX_REPAIR_WORK:
            raise _RepairLimit

    best = None
    stack = [(0, (), 0, dict.fromkeys((r.id for r in rules), 0))]
    try:
        while stack:
            index, chosen, cost, counts = stack.pop()
            charge(1 + len(chosen) + len(rules))
            if byte_limit is not None and cost > byte_limit:
                continue
            deficits = [r for r in required if counts[r.id] < r.min_count]
            if not deficits:
                result = (cost, chosen)  # candidates and chosen paths are lexical
                if best is None or result < best:
                    best = result
                continue
            if index == len(candidates) or (best is not None and cost > best[0]):
                continue
            # Each deficit independently gives a lower bound. Use max, never sum:
            # one source may satisfy several rules and its bytes count only once.
            impossible = False
            for rule in deficits:
                costs = []
                for j in range(index, len(candidates)):
                    source = candidates[j]
                    matches = raw_rules[source.path]
                    charge(1 + len(matches))
                    if rule not in matches or any(
                        r.max_count is not None and counts[r.id] >= r.max_count for r in matches
                    ):
                        continue
                    costs.append(source.size_bytes)
                need = rule.min_count - counts[rule.id]
                if len(costs) < need:
                    impossible = True
                    break
                charge(len(costs) * max(1, len(costs).bit_length()))
                lower_cost = cost + sum(sorted(costs)[:need])
                if (byte_limit is not None and lower_cost > byte_limit) or (
                    best is not None and lower_cost > best[0]
                ):
                    impossible = True
                    break
            if impossible:
                continue
            source = candidates[index]
            matches = raw_rules[source.path]
            charge(1 + len(chosen) + len(rules) + len(matches))
            # LIFO: include first, retaining the former lexical search order.
            stack.append((index + 1, chosen, cost, counts))
            if not any(r.max_count is not None and counts[r.id] >= r.max_count for r in matches):
                updated = counts.copy()
                for rule in matches:
                    updated[rule.id] += 1
                stack.append((index + 1, (*chosen, source.path), cost + source.size_bytes, updated))
    except _RepairLimit:
        return None, True
    return best, False


def compile_context(
    manifest: InventoryManifest,
    contract: ContextContract,
    *,
    task: str | None = None,
    budget_bytes: int | None = None,
    integrity_overview: IntegrityOverview | None = None,
    evidence: EvidenceContextBatch | None = None,
) -> CompiledContext:
    """Compile a selection manifest, then validate it with the Phase 5 validator.

    Eligibility is conservative across overlapping rules: selecting via another rule
    cannot bypass a matching rule's lifecycle or authority restriction. Maxima count
    raw matches, exactly as final validation does.
    """
    require_bound_contract(manifest, contract)
    if integrity_overview is not None and (
        integrity_overview.repository != manifest.repository
        or integrity_overview.config_sha256
        != (manifest.repository_config.content_sha256 if manifest.repository_config else None)
    ):
        raise ValueError("Integrity overview must describe the observed repository configuration.")
    budget = CompilationBudget(contract.budget_bytes, budget_bytes, 0)
    rules = tuple(sorted(contract.rules, key=lambda r: r.id))
    sources = tuple(
        CompilerCandidate.from_source(s) for s in sorted(manifest.sources, key=lambda s: s.path)
    )
    if evidence is not None:
        snapshot = evidence.state.snapshot
        if (
            snapshot.repository_id != manifest.repository.id
            or evidence.state.task != task
            or (
                snapshot.git_head is not None
                and manifest.repository.git_head is not None
                and snapshot.git_head != manifest.repository.git_head
            )
            or (
                snapshot.git_dirty is not None
                and manifest.repository.git_dirty is not None
                and snapshot.git_dirty != manifest.repository.git_dirty
            )
        ):
            raise EvidenceProviderError("snapshot_mismatch")
        if {s.path for s in sources} & {s.path for s in evidence.candidates}:
            raise EvidenceProviderError("inventory_collision")
        sources = tuple(sorted((*sources, *evidence.candidates), key=lambda s: s.path))

    def relevance_order(candidates):
        # Rank only provider slots in an otherwise lexical sequence. Inventory
        # documents keep their positions and acquire no invented relevance rank.
        ordered = sorted(candidates, key=lambda s: s.path)
        providers = iter(
            sorted(
                (s for s in ordered if s.relevance is not None),
                key=lambda s: (s.relevance.rank, s.path),
            )
        )
        return tuple(next(providers) if s.relevance is not None else s for s in ordered)

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
                allow_non_current_lifecycle=bool(rule.lifecycles),
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
            ranked.append(((-len(helpful), -max(priorities), -sum(priorities)), source))
        if not ranked:
            break
        best_policy = min(key for key, _ in ranked)
        select(relevance_order(s for key, s in ranked if key == best_policy)[0])

    search_exhausted = False
    # Greedy is the common path. Repair deficits within a deterministic work cap.
    if any(counts[r.id] < r.min_count for r in required):
        search_candidates = tuple(
            s
            for s in sources
            if eligibility[s.path] is None and any(r in required for r in raw_rules[s.path])
        )
        best, search_exhausted = _repair_required(
            search_candidates, raw_rules, rules, required, budget.effective_bytes
        )
        if best is not None:
            selected = set(best[1])
            used = 0
            counts = {r.id: 0 for r in rules}
            for source in sources:
                if source.path in selected:
                    used += source.size_bytes
                    for rule in raw_rules[source.path]:
                        counts[rule.id] += 1

    for rule in sorted(
        (r for r in rules if r.mode == Mode.OPTIONAL and not search_exhausted),
        key=lambda r: (-r.priority, r.id),
    ):
        optional_candidates = (
            s for s in matched[rule.id] if s.path not in selected and eligibility[s.path] is None
        )
        for source in relevance_order(optional_candidates):
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
    chosen_candidates = tuple(s for s in sources if s.path in selected)
    chosen = tuple(s.source for s in chosen_candidates if s.source is not None)
    validation = validate_contract_sources(
        manifest,
        contract,
        tuple(s.source for s in sources),
        tuple(s.path for s in chosen_candidates),
    )
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
        tuple(
            sorted(
                (
                    *validation.warnings,
                    *(evidence.state.warnings if evidence else ()),
                    *(
                        (
                            ScanWarning(
                                "compiler_search_budget_exceeded",
                                None,
                                "Required-context repair work limit exceeded; greedy package "
                                "retained. Feasibility is not established.",
                            ),
                        )
                        if search_exhausted
                        else ()
                    ),
                ),
                key=lambda w: (w.path or "", w.code, w.message),
            )
        ),
        providers=(evidence.state,) if evidence else (),
        integrity_state=(
            CompiledIntegrityState()
            if integrity_overview is None
            else CompiledIntegrityState(
                IntegrityEvaluationStatus.EVALUATED, integrity_overview.findings
            )
        ),
        authority_policies=tuple(
            policies[id]
            for id in sorted({r.authority_policy for r in rules if r.authority_policy is not None})
        ),
    )
