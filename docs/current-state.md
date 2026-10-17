# Current State

**Last updated:** 2026-10-16
**Current phase:** Phase 8 — Architectural Integrity
**Active plan:** `docs/plans/phase-8-implementation-plan.md`
**Status:** Implemented and offline-verified; fresh independent Phase 8 review required.

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
  typed ranges, referenced IDs and graph/file counts fail closed. Bounded subprocess
  controls, sanitized failures, explicit coverage and body-free output remain mandatory.
- `check` evaluates repository-owned policy and retains Phase 4 findings. Observed
  prohibited edges produce grouped deterministic HIGH findings with claim/policy,
  stable entities, occurrence ranges, provider/version/derivation, snapshot and coverage.
  Results distinguish `violated`, `no_violation_observed`, `inconclusive` and `not_evaluated`.
  Missing provenance dependencies remain visible without disabling explicit rules.
- Integrity JSON v2 deliberately replaces v1, including legacy-only checks; other JSON
  surfaces keep their versions. Explicit projectors omit bodies, absolute roots, raw
  stderr, numeric graph IDs and timestamps. CLI provider/executable settings remain
  runtime-only. Findings exit 0; provider failures exit 7. No task is needed for graph evidence.

## Verification

`UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check` passed:
Ruff lint, formatting (**80 files**) and **958 tests**, Python 3.12.13/macOS.
The focused architecture/graph suite passed **108 tests**. `git diff --check` passed.
Existing local `ctx 0.1.0` clean/dirty Git fixture smokes each reported two prohibited
relations with exit 0, explicit incomplete coverage, and no root/body leakage.
Implementation evidence: `docs/implementation-reports/phase-8-implementation-report.md`.
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

## Next expected step

Fresh independent Phase 8 review against the active plan, architecture, evidence contract,
architecture-integrity contract, code/tests and material downstream seams. Phase 9 derived
context revalidation remains separately scoped. Earlier pending reviews remain explicit.
