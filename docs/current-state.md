# Current State

**Last updated:** 2026-10-16
**Current phase:** Phase 7 — Codebase Intelligence EvidenceProvider Integration
**Active plan:** `docs/plans/phase-7-implementation-plan.md`
**Status:** Implemented and offline-verified; independent review required.

## Delivered

- Phase 0–6 inventory, authority, lifecycle/supersession, explicit claims, deterministic
  integrity checks, bound contracts and compiler selection semantics remain intact.
  Earlier JSON v1 surfaces are unchanged; claim validity remains `unverified`.
- Generic EvidenceProvider contract v1 and a local Context Engine CLI/schema-v1 JSON
  adapter supply ranked, snapshot-scoped, body-free code/test/schema/migration candidates.
  Root and known HEAD/dirty mismatches fail closed; full content is byte-validated and
  SHA-256 hashed before body discard. Processes have finite time/output bounds and
  sanitized typed errors. Unsafe/duplicate/colliding paths fail; lossy paths are omitted
  with explicit coverage. No shared database, parser duplication or network is introduced.
- Strict config v7 retains v1–v6 and adds four provider-backed contract kinds. Runtime
  executable/provider settings stay outside repository config. Provider mode requires
  explicit selection and a nonblank task; acquisition bytes and final contract bytes are
  separate. Provider failure exits 7 without silently falling back to inventory alone.
- One mixed compiler preserves exclusions, lifecycle, rule-scoped authority, maxima,
  required-first coverage, exact feasibility repair, optional fill and unique byte counts.
  Provider rank applies after policy equivalence; inventory documents receive no invented
  relevance rank. Final validation uses the exact mixed universe, without mutating inventory.
  Standalone `contracts validate` remains inventory-only.
- Compiled-context JSON v3 and text expose origins, provider/version/ranker/query,
  snapshot, coverage, relevance evidence, revisions and dependencies. Stable output omits
  bodies, absolute roots, timestamps, raw stderr and index-local IDs. Provider completeness
  stays separate from contract completeness; complete/incomplete contracts both exit 0.

## Verification

`UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check` passed: Ruff lint,
format and **831 tests**, Python 3.12.13/macOS. Focused evidence/adapter/compiler/contracts/
configuration/CLI: **371 passed**. v3 inventory/mixed goldens and `git diff --check` passed.
Real `ctx 0.1.0` / `file-ranker-v1` smokes passed for non-Git and clean Git/change fixtures,
selecting documentation plus code with body-free output. Evidence:
`docs/implementation-reports/phase-7-implementation-report.md`; durable boundary:
`docs/evidence-contract.md`.

## Known limitations / findings

Observations are sequential, not atomic. Unknown provider snapshot metadata remains
explicit; acquired candidates carry individual content hashes. Provider shortlists and
upstream syntax/relation/ranking limitations do not prove exhaustive code truth. Required
repair retains its existing exact-search complexity; optional fill remains greedy. Overlapping
rule policy remains conservative. POSIX execution was verified; cross-platform execution
and independent architectural acceptance are not claimed.

The separately pending Phase 4 final independent verification remains pending. No
architectural-integrity evaluation, graph policy, claim verification, generic contradictions,
source-body bundling, token budgets, persistence, LLM, cross-repository support or CI
enforcement is delivered.

## Next expected step

Independent Phase 7 review against the active plan and evidence contract, plus the separately
pending Phase 4 verification. Phase 8 architectural integrity follows a separately authorized
plan; structural evidence remains descriptive and Context Integrity owns its policy.
