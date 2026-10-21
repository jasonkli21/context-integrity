# Phase 8 Independent Review Fixes

**Date:** 2026-10-21
**Scope:** Address findings F8-001–F8-004 from the Phase 8 independent review.

## Changes

- Added a normalized file/symbol inventory to `EvidenceRelationBatch`. Generic batch validation
  now requires coverage to enumerate the file entities and requires each relation source and
  resolved target to exist in that inventory.
- Evaluation reports `source_entity_count`. An invariant with no observed source entity now has
  the `source_selector_unmatched` caveat and status `inconclusive`; a present source with no
  relations can still be `no_violation_observed` when global coverage is complete. Positive
  findings remain `violated` when unrelated evidence is incomplete.
- Compiled selector membership and indexed entities by path/symbol and relations by source/kind.
  Configuration is capped at 128 invariants and 16,384 selector values; evaluation is capped at
  250,000 index entries, selector visits and candidate relation checks. Exceeding the work budget
  raises `evaluation_budget_exceeded` and returns no partial result.
- Clarified endpoint, selector-applicability and work-budget semantics in the durable contract;
  corrected the historical integrity JSON v1 statement; added contract navigation; retained the
  supplied review in `docs/reviews/` and indexed it.

## Verification

Environment: macOS, Python 3.12.13.

- Focused `tests/test_architecture.py` and `tests/test_graph_adapter.py`: **115 passed**.
- `UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check`: Ruff passed,
  **83 files formatted**, **965 tests passed**.
- `git diff --check`: passed.

The findings are implemented and locally verified. Independent Phase 8 acceptance remains
pending a fresh review of this remediation commit.
