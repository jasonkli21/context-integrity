# Phase 4 Implementation Report

Date: 2026-10-15. This report records implementation evidence, not independent review.

## Baseline and commit

- Actual baseline: `cce525db1eede17dc0158eee30b7a75a0a2d2397`.
- Baseline offline `make check`: Ruff passed, **426 tests passed**.
- Initial working tree: only untracked `docs/plans/phase-4-implementation-plan.md`, supplied
  before this implementation. Preserved without edits and included with the implementation.
- Implementation commit: resolve with
  `git log -1 --format=%H -- docs/implementation-reports/phase-4-implementation-report.md`.
  Code, tests, plan, and delivery documentation are committed together in one commit.

## Delivered behavior and acceptance mapping

- `classification.py` and candidate selection recognize implementation reports as
  verification records / verification evidence, with no recency-based lifecycle inference.
- `models.py` adds immutable drift config, change-set, evidence, finding, and overview values.
  Findings hash rule/code/dependency ID/affected paths rather than human messages or bodies.
- Strict configuration v4 retains authority, lifecycle/supersession, and explicit claims.
  Instruction policy validates paths, uniqueness, collisions, and config self-reference.
  Drift rules validate identifiers, nonempty unique exact upstream paths, dependent paths,
  and reasons. Older schema versions reject the new keys; failures remain sanitized.
- `evidence.py` observes modified/deleted/untracked status or resolves exactly two local
  commits for `BASE..TARGET`. Option-like or malformed endpoints fail safely. Git uses
  argument arrays, existing environment protections, no lazy fetch, no external diff or
  text conversion, and disabled rename inference for ranges (delete plus add).
- `integrity.py` has separately callable instruction, current-state, and dependency
  evaluators with explicit versioned rule IDs. Instruction checks recognize literal root
  references, including slash/dot/link forms. The default root policy requires inventoried
  `AGENTS.md`; explicit policy can require missing compatibility sources.
- Current-state checks detect incomplete/ambiguous navigation, missing/wrong/unusable
  plans, numeric phase mismatches, invalid next phases, missing phase implementation
  evidence for delivered statuses, and lag behind later numeric reports. Plans and reviews
  do not satisfy report evidence. Terminal/historical sources do not count as usable.
- Exact upstream changes without dependent changes produce review findings, including
  deleted or non-inventoried code upstreams. Missing dependents produce findings. No Git
  permits other rules and emits an unavailable-evidence warning.
- Safe bounded text reads compare raw-byte hashes with the inventory before interpreting
  narrow metadata or references. Unsafe/inconsistent/non-UTF-8 text produces warnings.
  Configuration is checked again after evaluation. No source bodies are rendered.
- `check` supports path, diff, text/JSON, and output files. Findings return 0; fatal repository,
  output, and config failures return 3, 4, and 6. Separate integrity JSON v1 has deterministic
  paths, source revisions, change revisions, warnings, and newline termination.
- README and architecture document the public behavior and durable interpretation boundary.
  Current-state advances to Phase 4 only after the full implementation gate passed.

## Verification

Commands run from the repository root (all `uv` commands used the shown offline prefix):

```bash
git status --short
git rev-parse HEAD
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 uv run ruff check . --fix
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 uv run ruff format .
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 uv run pytest tests/test_integrity.py -q
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 uv run pytest tests/test_integrity.py -k test_dependency_explicit_range_and_claim_validity -q
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 uv run context-integrity check .
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 uv run context-integrity check . --format json
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check
git diff --check
git status --short
```

- Focused Phase 4 suite: **83 passed** (initial 79, then four additional cases covering ranges and
  claim validity, policy consistency, bounded metadata, and sanitized evidence failure).
- Full gate: Ruff lint and format pass; **510 tests passed**.
- An intermediate run exposed the expected classification rule-list assertions requiring
  the newly added rule; those expectations were updated. No baseline failure was hidden.
- Existing inventory, authority, lifecycle, and claims JSON v1 goldens are byte-identical.
  A small new integrity JSON golden checks stable IDs/provenance and privacy.
- Actual checkout text and JSON smoke: zero findings, zero warnings; canonical instruction
  topology passes. JSON contains only relative paths and no source bodies or timestamps.
- Disposable Git fixture explicit-diff CLI smoke: two local commits with a changed code
  upstream produce exactly `document_dependency_changed`, resolved commit SHAs, and exit 0.
  Automated range tests also cover clean, modified/deleted/untracked, invalid ranges/refs,
  rename-as-delete/add, and stable path ordering.

## Design choices, deviations, and limitations

No scope deviation from the normative Phase 4 plan. Minimal model names follow its suggested
shape. All initial findings use descriptive medium severity; thresholds remain deferred.
Numeric phase metadata is bounded to nine digits to avoid unbounded integer parsing of
untrusted text. A dependent cannot list itself upstream (a vacuous review dependency);
config may be an upstream path, but cannot be the dependent or instruction-policy endpoint.

The literal matcher establishes structural references only. It does not prove instruction
agreement. The metadata convention is narrow, not a general Markdown parser. Implementation
report existence does not establish software correctness. Both upstream and dependent
changing suppresses only this simple review signal. Explicit ranges describe path changes;
source text/revisions still describe the current checkout. Reads are sequential observations,
not an atomic repository snapshot. Unavailable text/evidence remains a warning, not a pass
assertion. Runtime dependencies are unchanged.

No Codebase Intelligence integration, AST/symbol/import/call graph, LLM, database, network
integration, semantic contradiction detection, automatic rewriting, claim-validity mutation,
or CI governance was added. Independent architectural review remains a separate session.
