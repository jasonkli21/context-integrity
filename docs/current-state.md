# Current State

**Last updated:** 2026-10-21
**Current phase:** Phase 8 — Architectural Integrity
**Active plan:** `docs/plans/phase-8-implementation-plan.md`
**Status:** Phase 8 review findings F8-001–F8-004 are fixed and offline-verified; fresh independent re-review remains pending.

## Delivered

- Phases 0–7 inventory, authority, lifecycle/supersession, explicit claims, deterministic
  drift checks, contracts and mixed context compilation remain intact. Claim validity
  remains `unverified`; compiler/contract behavior and their output versions are unchanged.
- Strict config v8 adds typed `architecture_invariants` linked to explicit architecture
  claims with predicate `must_not_depend_on`. Literal path/prefix/symbol selectors and
  unresolved target names drive `forbid_relation` for imports/references. Older schemas
  reject the new key; direct construction validates version, selectors and claim linkage.
- Separate replaceable `RelationEvidenceProvider` preserves Phase 7 context providers.
  Context Engine public schema-v1 `ctx graph` supplies descriptive facts, normalized
  without numeric graph identities. Envelope/root/known HEAD/dirty checks, safe paths,
  typed ranges, entity inventory, relation endpoints and graph/file counts fail closed.
  Resolved endpoints must be in the declared file coverage. Bounded subprocess controls,
  sanitized failures, explicit coverage and body-free output remain mandatory.
- `check` evaluates repository-owned policy and retains Phase 4 findings. Observed
  prohibited edges produce grouped deterministic HIGH findings with claim/policy,
  stable entities, occurrence ranges, provider/version/derivation, snapshot and coverage.
  Unmatched source selectors report a count and caveat and yield `inconclusive`; a matched
  source with no observed relation can yield `no_violation_observed` only with complete
  global coverage. Results also distinguish `violated` and `not_evaluated`.
  Missing provenance dependencies remain visible without disabling explicit rules.
- Compiled selectors and entity/relation indexes bound policy matching. Config allows at most
  128 invariants and 16,384 selector values; evaluation is capped at 250,000 counted work
  entries and fails explicitly without partial results when the budget is exceeded.
- Integrity JSON v2 deliberately replaces v1, including legacy-only checks; other JSON
  surfaces keep their versions. Explicit projectors omit bodies, absolute roots, raw
  stderr, numeric graph IDs and timestamps. CLI provider/executable settings remain
  runtime-only. Findings exit 0; provider failures exit 7. No task is needed for graph evidence.

## Verification

`UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check` passed:
Ruff lint, formatting (**83 files**) and **965 tests**, Python 3.12.13/macOS.
The focused architecture/graph suite passed **115 tests**. `git diff --check` passed.
Implementation evidence: `docs/implementation-reports/phase-8-implementation-report.md`;
review-fix evidence: `docs/implementation-reports/phase-8-review-fixes-report.md`.
Durable semantics: `docs/architecture-integrity-contract.md` and `docs/evidence-contract.md`.

## Known limitations / findings

No observed violation is no compliance proof. Coverage is globally conservative: even
apparently unrelated gaps can make an unviolated invariant inconclusive. Imports may
remain unresolved; reference resolution is largely same-file syntax evidence, without
compiler/type/dispatch semantics. Dirty/unknown graph snapshots lack provider content
fingerprints and remain incomplete. Separate bounded local post-graph hashes identify
local observations, not certified provider bytes; observations are sequential, not atomic.
Definition range movement can change symbol edge identity. POSIX/macOS was locally
verified; cross-platform execution and independent architectural acceptance are not claimed.

Phase 4 final independent verification and Phase 7 fresh independent review remain pending.
No claim verification, generic contradiction engine, Phase 9 revalidation, source-body
bundling, persistence, LLM, cross-repository policy or CI enforcement is delivered.
The evaluation work budget can reject very large normalized graphs/policies; it never silently
skips configured checks. Phase 8 independent acceptance of the remediation remains pending.

## Next expected step

Fresh independent re-review of the Phase 8 remediation against the active plan, architecture,
evidence contract, architecture-integrity contract, code/tests and material downstream seams.
Phase 9 derived context revalidation remains separately scoped. Earlier pending reviews remain
explicit.
