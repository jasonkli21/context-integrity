# Phase 6 Implementation Report — Task Context Compiler

**Date:** 2026-10-16
**Phase:** 6 — Task Context Compiler
**Status:** Implemented and offline-verified; independent review pending
**Plan:** `docs/plans/phase-6-implementation-plan.md`
**Actual start HEAD:** `9a4ee1dd56fcec63799e6fa777eccb68ec9ae0b4`
(`Fix Phase 5 contract review findings`)

## Starting state

HEAD matched the supplied plan's baseline; branch was `main`. The only initial
working-tree item was the supplied untracked `docs/plans/phase-6-implementation-plan.md`.
It is included with requirements preserved; only trailing header whitespace was removed
for the staged whitespace check. No unrelated user edits were present. No historical
review was repeated or claimed complete. The separately pending Phase 4 final independent
verification remains pending.

## Delivered semantics and acceptance mapping

- Configuration v6 retains v1–v5. `ContextContract.budget_bytes` accepts a positive integer
  or None. `ContextContractRule.priority` defaults to 0 and accepts nonnegative integers;
  `authority_policy` optionally references a syntactically valid effective policy ID.
  Booleans are invalid integers. Parsing gates every new key to v6, rejects unknown keys
  and policy IDs, preserves schema versions and sanitizes errors. Direct models enforce
  policy field types/ranges; `RepositoryConfig` rejects nondefault compiler policy under v5.
- `require_bound_contract` is shared by compiler and validator. Exact configured equality
  and matching observed configuration revision preserve Phase 5 behavior, including
  rejection of foreign, modified and stale contracts.
- `compiler.py` is pure selection policy over `manifest.sources`. It never expands the
  inventory or reads arbitrary files. Existing `matches_rule` provides selector semantics.
  Excluded rules veto a source globally; conflicts remain visible in candidate rule
  relationships and final required-shortfall findings.
- Compiler lifecycle defaults to unknown/active; explicit selectors permit other states.
  Validator semantics remain unchanged. No filename/mtime/Git-date currentness is inferred.
- Authority policies resolve within each rule's matching, lifecycle-eligible, nonexcluded
  subset via `resolve_authority_for_sources`. Existing `resolve_authority` delegates over
  all manifest sources, retaining its source-metadata override argument and output.
  Existing lifecycle authority eligibility, explicit ineligibility and policy membership
  remain owned by authority/lifecycle modules. Only highest eligible tiers are selectable;
  lower tiers cannot become a budget or missing-revision fallback. Equal-tier alternatives
  retain paths/tier metadata. Effective policy definitions, origin, version and config
  revision are also retained in compiler output.
- Selection greedily prioritizes the number of unsatisfied required rules covered, then
  highest applicable priority, summed applicable priority, and relative path. Requirements
  share sources and bytes once. Maxima count all raw matching rules, including optional
  rules. Required minima are filled first, then optional rules by priority descending/ID
  ascending and candidates by path. Extra required-only matches are omitted. Optional
  selection cannot remove/displace required selections.
- Source cost is observed `size_bytes`. CLI override wins over contract budget, otherwise
  selection is unbounded. Every addition checks budget before selection; exact fits and
  zero-byte sources work. Missing/unusable content SHA256 or size produces an inspectable
  omission rather than fabricated provenance/cost. Budget models enforce positive limits,
  nonnegative usage and bounded totals; result models check unique sources, exact byte
  totals, dependencies and agreement with final validation/status.
- Final selected paths always pass through the existing Phase 5 validator. Findings
  determine incomplete versus complete. Incomplete is a result, not a fatal error.
- `compile CONTRACT_ID [PATH]` supports opaque `--task`, positive `--budget-bytes`,
  `--format text|json`, and `--output`. Complete/incomplete retain exit 0; usage/unknown
  contract/invalid budget 2, repository 3, output 4 and config 6 retain existing categories.
  The CLI contains no selection policy.
- Separate deliberate compiled-context JSON v1 includes repository/contract/config identity,
  compiler policy, source revisions, selected sources, all observed-source decisions,
  matched/contributing rule IDs, per-rule reason codes/authority context, budget origin and
  arithmetic, unique dependencies, warnings and final Phase 5 validation. Arrays produced
  by the compiler sort deterministically. Output is newline-terminated and excludes absolute
  roots, runtime timestamps and source bodies. Earlier JSON v1 projections remain untouched.

## Clarifications, deviations and rationale

1. **Overlapping policy intersection:** the plan did not fully specify how a source selected
   via one rule interacts with another matching rule's selection restrictions. Compilation
   conservatively requires every matching selection rule's lifecycle/authority restriction
   to hold. Otherwise the Phase 5 validator's raw matches could count lower-authority context
   selected through an optional rule toward an authoritative required rule. This can omit
   more context in conflicting policies; it never silently bypasses them. Architecture and
   a focused overlap regression encode the decision. Contracts requesting historical context
   must make overlapping lifecycle selectors consistent.
2. **No cross-policy numeric tier tiebreak:** after highest-tier filtering, every candidate
   within a rule already has equal tier. Numeric indices from unrelated policies are not
   comparable. Required ranking therefore uses coverage, policy priority and path, preserving
   the architecture's contextual-authority invariant rather than introducing a global rank.
3. **Unknown observed cost:** added `unverifiable_size` alongside `unverifiable_revision`.
   `SourceRecord.size_bytes` is nullable; assuming zero would undermine byte-budget guarantees.
4. Existing Phase 4 integrity checks remain a separate `check` workflow. Compilation makes
   no integrity-cleanliness claim and adds no contradiction resolution or integrity gate.
5. Earlier contract list/show/validation JSON retains its exact projection; new v6 policy
   fields appear in compiled-context JSON. This honors the explicit compatibility constraint.

## Files changed

- `src/context_integrity/compiler.py`: new deterministic compile orchestration.
- `src/context_integrity/models.py`: compiler fields, statuses, decisions, dependencies,
  budget/result models and construction invariants.
- `src/context_integrity/configuration.py`: strict v6 parsing/gating/policy references.
- `src/context_integrity/contracts.py`: shared binding check; validator behavior preserved.
- `src/context_integrity/authority.py`: subset resolver with backward-compatible wrapper.
- `src/context_integrity/cli.py`: thin compile command.
- `src/context_integrity/rendering.py`: separate compiled-context text and JSON v1.
- `tests/test_compiler.py`: 87 focused cases over small synthetic repositories.
- `tests/fixtures/compiled-context-v1.json`: small deterministic golden; generated from the
  existing two-source `git_repo` fixture and the compiler test's bound instructions contract,
  operating-instructions policy, 13-byte budget and opaque task metadata.
- `tests/test_configuration.py`, `tests/test_contracts.py`: unsupported-version examples
  advance from 6 to 7; prior behavior assertions remain.
- `README.md`, `docs/architecture.md`, `docs/current-state.md`: delivered commands,
  architecture/selection/provenance semantics, limits and verified navigation.
- Supplied Phase 6 plan and this report.

## Verification

Environment: Python 3.12.13/macOS, pytest 9.1.1; no network, credentials, LLM or database.
Final commands:

```bash
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 uv run pytest tests/test_compiler.py tests/test_contracts.py tests/test_authority.py tests/test_configuration.py -q
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check
git diff --check
git diff --cached --check
git status --short
```

- Final focused suite: **293 passed**.
- Full `make check`: Ruff lint/format passed; **719 tests passed**, including all earlier
  inventory/authority/lifecycle/claims/integrity/contracts golden comparisons.
- Earlier tracked golden files remain unchanged. The compiler golden checks byte-identical
  JSON under reversed inventory order, config/source provenance, budget, structured decisions,
  dependencies, newline termination and absence of absolute root/source bodies.
- `git diff --check` and the staged equivalent passed.
- An additional `UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 uv run python`
  executable smoke used a disposable repository and the installed `context-integrity`
  executable. Text complete output, complete/incomplete exit 0, insufficient budget without
  overrun, repeated byte-identical JSON, output file equality and privacy assertions passed.
  Temporary files were removed.
- Iteration evidence: initial compiler run had 74 passes/4 failures (three fixture-byte
  expectations and the not-yet-created golden). The next combined run had 283 passes/1
  failure (the prior CLI test used now-supported schema v6 as an invalid example). These
  expectations were corrected, targeted coverage expanded, and the final suites above passed.
- Final diff inspection checked shared binding/authority reuse, raw-match maxima, pre-add
  budget checks, deterministic ordering, deduplication, policy-before-budget semantics,
  earlier projections, thin CLI, absence of runtime dependencies, and scope boundaries.
  This is implementation inspection, not independent architectural review.

## Documentation lifecycle and remaining work

README status/commands now describe compilation; architecture updates cover Layer 6,
ContextContract/CompiledContext, compiler module ownership, Section 15 and versioning.
Current state moves to verified Phase 6 only after the full gate. A staleness sweep of
`docs/README.md`, `docs/prd.md`, `AGENTS.md`, `docs/plans/README.md`, and
`docs/implementation-reports/README.md` found no Phase 6 delivery claims needing changes;
these remain general navigation, instructions and long-term intent. Historical Phase 0–5
plans/reports were not rewritten.

Independent Phase 6 review is pending, especially the documented overlapping-rule policy
intersection. No known failing acceptance criterion remains. The separately pending Phase 4
final independent verification remains pending. Greedy selection can be locally suboptimal,
observations are sequential, and contract completeness does not establish semantic correctness.

Deferred Phase 7+: Codebase Intelligence/EvidenceProvider transport, ordinary code retrieval,
AST/symbol/structural relevance, cross-repo compilation, semantic task classification or
retrieval, general contradictions/claim verification/architecture drift, source-body bundles,
LLMs/embeddings, tokenization/token budgets, persistence/cache, CI enforcement, waivers and
automatic fixes. No speculative provider or persistence infrastructure was introduced.
