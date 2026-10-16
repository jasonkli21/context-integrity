# Phase 7 Independent Review Fixes

**Date:** 2026-10-16
**Scope:** Address F-001–F-004 and the two documentation corrections in the Phase 7
independent review handoff.

## Changes

- Added provider-independent validation for relevance values, provider provenance, normalized
  source classification, provider state capabilities/change/warnings, and candidate bounds.
- Replaced provider and relevance `asdict()` serialization with explicit compiled-context v3
  projectors; retained the existing v3 golden output.
- Centralized supported config schema versions and enforce them in both TOML parsing and direct
  `RepositoryConfig` construction.
- Replaced impossible mutated-provider policy tests with actual provider lifecycle and authority
  cases, and made the replacement-provider test construct its normalized batch independently.
- Updated the README plan map and architecture diagram; clarified normalized provider and v3
  projection guarantees in the evidence contract.

## Verification

- `UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check` — Ruff lint/format
  passed; **850 tests passed** on Python 3.12.13/macOS.
- Focused `tests/test_evidence.py` and `tests/test_configuration.py` after final boundary cases —
  **111 passed**.
- Compiled-context v3 provider and inventory goldens remained unchanged.
- `git diff --check` passed.

The optional real Context Engine binary smoke was not repeated as part of these generic boundary,
renderer, configuration, and test-evidence fixes.
