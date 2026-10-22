# Phase 9 Review Fixes — Implementation Evidence

Date: 2026-10-21. Role: implementation evidence, **not independent acceptance**.
Review baseline: `eedc972a53bb568291bda7a876189aefe6c1ad3f`.
The submitted independent review is retained at
[`docs/reviews/phase-9-independent-review.md`](../reviews/phase-9-independent-review.md).

## Findings addressed

- **F9-001:** Revalidation now marks an inventory-classified `handoff` or
  `generated_summary` used as a plain dependency with `unlinked_derived_dependency`
  uncertainty unless its artifact path is explicitly represented by an upstream receipt.
  `current_state` is excluded. Declared `compiled_context` receipts are inconclusive when
  they lack typed compiler-selection provenance. The contract, README and AI handoff guide
  explain the receipt-link workflow.
- **F9-002:** The existing compiler identity field now records the release label plus a
  SHA256 fingerprint over sorted installed package Python source files. Code changes without
  a release bump produce `compiler_implementation_changed`; an unavailable fingerprint is
  inconclusive. Older receipt v1 pins with release labels alone conservatively require review.
  The fingerprint contains no source text and does not change receipt schema v1.
- **F9-003:** Empty-dependency uncertainty is scoped to declared provenance. A complete
  compiler-selected package with no selected source remains checkable from its pinned
  contract and inventory universe. Empty manual declarations remain inconclusive.
- **F9-004:** Graph reads distinguish shared-budget exhaustion (`*_budget_exceeded`) from a
  per-file size limit (`*_too_large`). Both remain inconclusive, preserving review precedence
  when a definite change is also observed.

## Files changed

- `src/context_integrity/derived.py`
- `src/context_integrity/acquisition.py`
- `tests/test_derived.py`, `tests/test_derived_cli.py`
- `docs/derived-context-contract.md`, `docs/architecture.md`, `README.md`, `docs/ai/README.md`
- `docs/reviews/phase-9-independent-review.md`, `docs/reviews/README.md`
- `docs/current-state.md`

## Verification

- `UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 uv run pytest -q tests/test_derived.py tests/test_derived_cli.py` — **106 passed**.
- `UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check` — Ruff lint and formatting passed; **1,071 tests passed** on Python 3.12.13/macOS.
- `git diff --check` — passed.

Phase 9 independent acceptance remains pending until a fresh independent review compares the
resulting fix commit against the original findings. Phase 8 independent re-review remains
separately pending.
