# Post-Phase-11 evaluation evidence

This report records a small offline retrieval evaluation over authored Rust/Python fixture
files. It is not a product acceptance review and selected-file recall is not task success.

## Reproduction

```sh
CARGO_TARGET_DIR=/tmp/context-integrity-post-phase11-engine-target \
  cargo build --locked --offline --bin ctx
PYTHONDONTWRITEBYTECODE=1 uv run python scripts/post_phase11_evaluate.py \
  --ctx /tmp/context-integrity-post-phase11-engine-target/debug/ctx \
  --engine ../context-engine \
  --output docs/reviews/post-phase-11-e2e-results.json
```

The runner regenerates the JSON results. This Markdown file is the reviewed evidence summary;
it also records verification and source findings checked separately from the retrieval run.

## Additional verification

| Repository / command | Result |
|---|---|
| Integrity: `UV_CACHE_DIR=/tmp/context-integrity-postphase11-uv-cache UV_OFFLINE=1 make check` | Ruff passed, 119 files formatted, 1,321 tests passed in 191.55s |
| Engine: `CARGO_TARGET_DIR=/tmp/context-integrity-post-phase11-engine-target cargo test --locked --offline --test evidence` | 11 integration tests passed in 4.69s |
| Engine: `CARGO_TARGET_DIR=/tmp/context-integrity-post-phase11-engine-target cargo test --locked --offline --test cli git_filter_` | 2 filter-safety tests passed in 1.04s |
| Engine: `CARGO_TARGET_DIR=/tmp/context-integrity-post-phase11-engine-target cargo test --locked --offline --bin ctx expected_file_recall_benchmark -- --nocapture` | 1 benchmark test passed; six authored tasks, production 12/12 expected files, path-and-symbol search 6/12, path order 0/12, path lexical 2/12, production without role scoring 10/12 |

The Engine evidence integration tests exercise four live feed types (structure, candidates,
changes, workspace), 21 malformed golden documents, and five mutated live documents through
the independent decoder. The six-task Engine unit benchmark is an existing self-authored test;
the eight-task results below are a separate evaluation against keyword grep and path-order
controls. Neither sample establishes real developer task success.

Host: macOS 27.0.1 arm64; Python 3.12.13, uv 0.11.13, Rust/Cargo 1.99.1, Git 2.39.5.
Each `ctx` command has a 120-second timeout; evidence candidates are capped at 200, and the
authored fixture has 21 files (the JSON records total content bytes and runner hash).

Integrity source SHA: `52303037d413b180ec6a923b9ceb1f43b4a7bfeb`<br>
Engine source SHA: `34a9e3d25d7a336977d114562db40fadd130979a`<br>
Engine checkout clean: `False`<br>
ctx version: `ctx 0.1.0`<br>
ctx binary SHA-256: `0e4180bfe91ebd36d4321edc661616b895f357173a5b9de70d0994ba6352f1d2`<br>
Fixture commit: `dcc4316764ff9808f6805fbdb185eced0730bbdf`<br>
Pre-registered task count: `8`<br>
Oracle SHA-256: `14069062ac0306534be99ae85a9a998b35b60119b8b4f846a26ad620e9908c00`<br>
Semantic result SHA-256: `8f9e33e91d6b9197495f8edd25624717eced736f47a5524fc02395fb8daa66a3`

## Aggregate results

| Strategy | Recall | Recalled / expected | Extra | Files | Content bytes |
|---|---:|---:|---:|---:|---:|
| ctx | 0.833 | 10 / 12 | 2 | 12 | 914 |
| keyword_grep | 0.750 | 9 / 12 | 2 | 11 | 917 |
| path_order | 0.000 | 0 / 12 | 9 | 9 | 708 |

## Scenario results

| Scenario | Category | Expected | ctx selected | Recall | Extra | Bytes |
|---|---|---|---|---:|---:|---:|
| path_only_python | exact_path_only | src/parser/token_rules.py | tests/test_token_rules.py | 0 / 1 | 1 | 63 |
| symbol_only_python | symbol_only | src/session/manager.py | src/session/manager.py | 1 / 1 | 0 | 82 |
| symbol_only_rust | symbol_only | src/transport.rs | src/transport.rs | 1 / 1 | 0 | 146 |
| misleading_documentation | misleading_docs | src/keys.py, tests/test_keys.py | src/keys.py, tests/test_keys.py | 2 / 2 | 0 | 144 |
| multiple_plausible_implementations | multiple_plausible_files | src/compat/old_policy.rs, src/policy/current.rs | src/compat/old_policy.rs, src/policy/current.rs | 2 / 2 | 0 | 137 |
| irrelevant_lexical_hits | irrelevant_lexical_hits | src/worker.py, tests/test_worker.py | src/queue_metrics.py, src/worker.py | 1 / 2 | 1 | 129 |
| budget_pressure | budget_pressure | src/index.rs, tests/index_test.rs | src/index.rs, tests/index_test.rs | 2 / 2 | 0 | 137 |
| unsupported_language_coverage | incomplete_or_unsupported_analysis | src/unsupported/manifest.go | src/unsupported/manifest.go | 1 / 1 | 0 | 76 |

## Comparison counts

| Baseline | Recall W/T/L | Extra W/T/L | Bytes lower/tied/higher |
|---|---|---|---|
| keyword_grep | 2 / 5 / 1 | 1 / 6 / 1 | 1 / 5 / 2 |
| path_order | 7 / 1 / 0 | 6 / 2 / 0 | 1 / 0 / 7 |

## Interpretation and boundaries

The runner freezes eight task IDs, expected path sets, and byte budgets before invoking Engine.
Full recall occurred in 6 / 8 tasks. It records recall, extraneous files, selected file count,
and raw UTF-8 content bytes against a simple path-and-body keyword grep and a lexical path-order
budget control. All task command output containing source bodies is discarded after extracting
bounded metadata.

Each task also exports evidence-v1 candidates twice. The check requires a best-effort worktree
observation with the fixture commit and clean state, verifies that invocation scope changes,
compares normalized candidate semantics, and rejects body or absolute-root leakage. Evidence
coverage remains explicitly incomplete. This is producer evidence only; Context Integrity still
consumes legacy `ctx context` and `ctx graph` schema v1.

The fixture set is small and synthetic. The baselines are deliberately simple; ties and losses
are retained. The measurements do not establish real developer task success, better retrieval
quality, semantic API compatibility, complete analysis, or independent Phase 11/predecessor
acceptance.

## Existing handoff findings checked against current sources

- Evidence-v1 remains an opt-in Engine producer feed; the Integrity adapter still consumes `ctx
context`/`ctx graph` schema v1. No production migration is present.
- The handoff's earlier eight-scenario report and runner were absent at the starting Integrity
SHA, so their reported results were not treated as current verified evidence. This report
records a fresh, reproducible eight-task retrieval evaluation.
- The handoff's non-Unix Engine safe-read risk has changed: current Engine source fails closed
on non-Unix reads. Native Windows runtime verification remains outstanding; no portability pass
is claimed here.
- The latest Engine commit after the handoff baseline is documentation-only. Its current report
  also confirms the filter-safety limitation in code/tests: if any clean/process filter is
  configured, Engine skips `git status` and reports `git_dirty=null` rather than invoking it.
  The disposable evaluation fixtures disable ambient system/global Git config; this does not
  resolve that upstream limitation. No Engine product changes were authorized or made.
- Current-state's independent Phase 11/stabilization and predecessor acceptance debt remains
open. This evaluation does not change those dispositions.

Full per-scenario metadata and exact aggregate counts are in `post-phase-11-e2e-results.json`.
