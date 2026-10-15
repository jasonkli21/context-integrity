# Current State

**Last updated:** 2026-10-14
**Current phase:** Phase 2 — Lifecycle and Supersession
**Active plan:** `docs/plans/phase-2-implementation-plan.md`
**Status:** Implemented and verified offline; independent Phase 2 review pending.

## Delivered

- Phase 0 safe inventory, raw-byte revisions/IDs, classification, Git protections,
  scan/explain/version, and inventory JSON v1 remain intact.
- Phase 1 question-specific authority policies retain equal-precedence tiers, all top
  candidates, and missing stronger tiers. No correctness or agreement claims.
- Seven lifecycle states: unknown, draft, active, superseded, historical, expired, invalid.
  Only unknown/active pass the lifecycle authority gate; unknown remains unestablished.
- Strict config schema v1 retains authority-only behavior; v2 adds explicit lifecycle and
  directional supersession with required reasons. Safe bounded reads/hash consistency
  remain fail-closed. No config rewriting or lifecycle management of the control-plane file.
- Two-pass inventory resolves only observed supersession endpoints. Chains/convergence
  supported; cycles, self edges, duplicate successors, and lifecycle conflicts rejected.
  Missing endpoints warn and do not activate edges. Targets are never inferred active.
- Explicit non-historical lifecycle overrides restore kind-derived authority under historical
  paths; explicit authority overrides still win. Per-dimension rule provenance retained.
- `lifecycle list/show` text/JSON and output files; separate explicit lifecycle JSON v1 with
  direct relations, identities/revisions, origins/reasons, config hash, and warnings.
- Scan exposes effective lifecycle/counts; explain shows built-in and explicit evidence,
  effective lifecycle, direct successor, and lifecycle eligibility without policy resolution.

## Verification

`UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check` passed:
Ruff lint/format and **343 tests**, Python 3.12.13/macOS. Baseline: **226 tests** at
`36d150af6cf67b8bab41c528b4304fa83da51309`. All three original Phase 0 inventory and all three
Phase 1 authority goldens remain byte-identical. Three lifecycle goldens and one new
lifecycle-aware authority golden pass. Real-checkout lifecycle list/show smoke checks passed.

Acceptance evidence: `docs/implementation-reports/phase-2-implementation-report.md`.

## Known limitations / findings

Independent Phase 2 review remains pending; no unresolved implementation acceptance failures.
Scans are sequential observations, not atomic snapshots; safe reads target POSIX.
Lifecycle/supersession comes only from built-in path rules and explicit config, never source
bodies or recency. Missing endpoints are unresolved warnings. No automatic expiry, claims,
semantic agreement/contradiction, drift, persistence, or Codebase Intelligence integration.
Ordinary code is not inventoried; executable truth may remain an unobserved stronger tier.

## Next expected step

Independent Phase 2 review and any fixes, then Phase 3 — Claims and Provenance. Phase 3
should use SourceId and raw-byte SourceRevision dependencies while keeping claim validity
separate from source lifecycle. Phase 3 extraction is not implemented.
