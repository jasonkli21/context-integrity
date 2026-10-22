# Current State

**Last updated:** 2026-10-21
**Current phase:** Phase 10 — Cross-Repository Integrity
**Active plan:** `docs/plans/phase-10-implementation-plan.md`
**Status:** Implemented and offline-verified; independent Phase 10 review pending.
Phase 9 and Phase 8 fresh independent re-reviews remain pending.

## Delivered

- Phases 0–9 remain intact: inventory, question-specific authority, lifecycle/supersession,
  explicit unverified claims, deterministic checks, contracts, mixed compilation,
  architectural integrity and single-repository derived-context revalidation.
  Config v1–v8, compiled JSON v3, integrity JSON v2 and derived receipt/result v1 are unchanged.
- Strict explicitly supplied workspace TOML v1 binds 2–8 aliases to observed repository IDs,
  rejecting unsafe/nested/duplicate roots, wrong identities and same-origin checkout collisions.
  Qualified source/claim identities prevent collisions between identical repo-relative names.
- Explicit consumer contract lock JSON v1 pins a producer ID/path/raw-byte SHA256. Independent
  `contract_pin`, `mirror_bytes` and `claim_match` checks distinguish observed alignment,
  review/change impact and uncertainty, retaining provenance and coverage limitations.
- `workspace check` emits separate check JSON v1; `workspace compile --task` independently
  applies configured contracts/policies and bounded per-target budgets. Context JSON v1
  preserves decisions/revisions and selection/check distinctions, with task digest only.
- New workspace commands operate offline without provider installation, models, database or
  network. Default stdout is read-only; saved output is exclusive, outside all participating
  roots and protected by descriptor-relative no-follow publication. Locks/receipts are never
  refreshed. Source reads include stable-file checks; failures and budget gaps cannot align.

## Verification

`UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check` passed:
Ruff lint, formatting (**102 files at that gate**) and **1,167 tests**, Python 3.12.13/macOS.
`UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 uv run pytest -q tests/test_workspace.py tests/test_workspace_cli.py`
passed **96 tests**. No tests were skipped. Final documentation formatting and staged
whitespace checks are recorded in the implementation report.

Durable semantics and exact examples: `docs/workspace-integrity-contract.md`.
Phase 10 implementation evidence: `docs/implementation-reports/phase-10-implementation-report.md`.
Predecessor contracts remain `docs/derived-context-contract.md`, `docs/evidence-contract.md`
and `docs/architecture-integrity-contract.md`.

## Known limitations / findings

Equal pins/files/declarations do not prove API compatibility, consumer implementation use,
semantic truth, exhaustive coverage or product compliance. Claims stay `unverified`;
current dependency observations have no accepted historical revision pin. Dirty, unobservable
or generated dependencies and inventory gaps prevent positive claim alignment.

Repository observations are sequential, not atomic. No-origin identity is location dependent;
two same-origin checkouts cannot represent different logical workspace repos. Workspace indexes
are not durable cross-repo Phase 9 receipts or transitive generated-artifact revalidation.
Provider graphs and global authority/budget ranking are not merged. Publication is exclusive
but not a crash transaction; process loss may leave orphaned files.

Workspace bounds: manifest 256 KiB, lock 16 KiB, files 5 MiB, task 64 KiB, 128 checks,
16 context targets, 256 declared qualified endpoints, summed context budget 64 MiB. Explicit
reads and shared inventories each have separate 64 MiB/4,096-work ceilings. Exact path/output
restrictions, POSIX/macOS verification scope and predecessor limitations remain in the contracts.

Phase 4 final independent verification, Phase 7 fresh independent review, Phase 8 fresh
independent re-review and Phase 9 fresh independent re-review remain pending. Phase 10 independent
acceptance has not been established. No semantic compatibility/claim verification, generic
contradiction engine, persistence, LLM, cross-repo structural graph, source-body bundling or
CI enforcement is delivered.

## Next expected step

Independent Phase 10 review against the active plan, architecture, durable contracts,
code/tests and compiler/acquisition seams. Preserve earlier pending review statuses;
Phase 11 governance/CI work remains separately scoped.
