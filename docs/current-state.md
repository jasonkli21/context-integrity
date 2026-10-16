# Current State

**Last updated:** 2026-10-15
**Current phase:** Phase 3 — Claims and Provenance
**Active plan:** `docs/plans/phase-3-implementation-plan.md`
**Status:** Implemented and verified offline; independent Phase 3 review pending.

## Delivered

- Phase 0 safe inventory, stable source IDs/raw-byte revisions, Git boundary protections,
  classification, scan/explain/version, and inventory JSON v1 remain intact.
- Phase 1 question-specific authority policies preserve equal-precedence tiers, all top
  candidates, and missing stronger tiers. Source-role precedence never proves correctness.
- Phase 2 explicit lifecycle/supersession, lifecycle-aware authority gating, and lifecycle
  list/show remain intact. Cumulative Phase 0–2 independent review corrections are implemented;
  final independent verification of those fixes remains pending.
- Strict config v1 is authority-only; v2 adds lifecycle/supersession; v3 adds explicit
  structured claims while preserving v2 behavior. Older versions reject claim keys.
- Stable configured claim IDs; required type/subject/predicate/value and optional scope and
  dependency paths. Unknown/malformed fields, unsafe paths, duplicate IDs/dependencies,
  and config self-dependency fail closed. Bounded config/hash consistency checks remain.
- Declaration provenance identifies config SourceId/raw-byte SourceRevision, `claim:<id>`,
  `repository_config_explicit`, and `claims-v1`. Dependencies resolve only against observed
  inventory identities/revisions; dirty bytes retain content hashes separate from Git HEAD.
- Missing/unavailable dependencies remain visible, warn, and make provenance incomplete.
  Every claim remains `unverified`, independently of source lifecycle and completeness.
- `claims list/show` support text/JSON and output files. Separate deterministic claims JSON
  v1 exposes statement, validity, declaration/dependency provenance, resolution, and warnings.
  Original inventory/authority/lifecycle JSON v1 projections and golden fixtures are unchanged.

## Verification

`UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check` passed:
Ruff lint/format and **419 tests**, Python 3.12.13/macOS. Baseline: **353 tests** at
`14ce25d6fcc3ecf65a8aaf79c177323ac3cb5772`. Focused claims/config gate: **121 passed**.
Original Phase 0–2 goldens remain byte-identical; two new claims goldens pass.
Real-checkout empty claims list and synthetic v3 list/show/output smoke checks passed.

Acceptance evidence: `docs/implementation-reports/phase-3-implementation-report.md`.
Prior independent review navigation: `docs/reviews/README.md`.

## Known limitations / findings

No intentionally unresolved implementation findings; independent Phase 3 review pending.
Claims are explicit config assertions only; dependency bodies are not parsed or treated as
proof. Ordinary code and other non-inventoried paths stay unresolved. No automatic validity,
staleness, claim authority, contradiction, drift, persistence, or external integration.
Scans remain sequential observations rather than atomic snapshots; safe reads target POSIX.

## Next expected step

Independent Phase 3 review against the active plan, architecture, and code/tests; verify
findings separately before proceeding to Phase 4 — Documentation / Instruction Drift.
