# Phase 5 Implementation Report — Context Contracts

**Date:** 2026-10-16
**Phase:** 5 — Context Contracts
**Status:** Implemented and offline-verified; independent review pending
**Plan:** `docs/plans/phase-5-implementation-plan.md`
**Actual baseline HEAD:** `4b60524bed350bbce5a64bcb3d9d803d139dcee2`
(`Fix Phase 4 review findings`)

## Starting state and predecessor evidence

Initial `git status --short`, `git rev-parse HEAD`, and `git log -5 --oneline` confirmed
that HEAD matched the plan's inspected revision. The only pre-existing working-tree item
was the supplied, untracked Phase 5 plan. It is included with its requirements preserved; header trailing whitespace was removed
to pass the staged whitespace check. No unrelated user edits were present.

Accepted Phase 4 predecessor evidence is the committed
`docs/implementation-reports/phase-4-implementation-report.md`, section
“Review-fix verification”: 105 integrity tests, 117 configuration/classification tests,
532 full-gate tests, and zero findings/warnings in text and JSON dogfood checks.
No Phase 4 baseline verification or review-fix implementation was repeated. The full gate
below verifies the changed Phase 5 implementation, including regression coverage; it is not
a recreation of predecessor evidence. The separately pending Phase 4 final independent
verification was not performed or claimed complete.

## Delivered behavior and acceptance mapping

- Frozen contract/rule models enforce identifier syntax, nonblank descriptions, typed tuple
  selectors/rules, distinct selector values and rule IDs, normalized safe exact paths,
  selector presence, enum types, integer counts excluding booleans, and coherent mode/count
  constraints. Repository configuration enforces distinct contract IDs.
- Strict schema v5 retains all v4 capabilities and adds `context_contracts`. Schemas v1-v4
  reject that key. Unknown contract/rule fields fail closed with sanitized config errors.
- `contracts.py` exposes deterministic discovery, explicit ID resolution, metadata-only
  matching, package resolution, and validation. Dimensions combine with AND, values with OR.
  There are no hidden currentness or authority winner policies.
- Required rules default to minimum 1 and no maximum. Optional rules default to minimum 0
  and no maximum. Excluded rules default to minimum/maximum 0. Explicit counts must preserve
  those semantics. Contract task classes are metadata, not inferred classifications.
- Package paths normalize before exact current-inventory lookup. Traversal, absolute paths,
  NULs, drive/backslash ambiguity, and trailing slashes are usage errors. No arbitrary path
  reads or candidate expansion occurs. Unique sources count once; duplicates warn, unresolved
  paths produce package findings, and empty packages evaluate normally.
- Every rule returns matched paths, count, effective bounds, and satisfaction. Findings cover
  unavailable sources, required shortfalls, overfilled rules, and excluded matches.
  Duplicate normalized input paths remain visible and warn without inflating counts.
- `contracts list`, `contracts show CONTRACT_ID`, and `contracts validate CONTRACT_ID` accept
  an optional repository path, text/JSON format, and output file. Validation accepts repeated
  `--source`. Findings return 0; unknown/invalid selection returns 2, repository failure 3,
  output failure 4, config failure 6. The CLI and renderers contain no matching/count policy.
- Independent contract-validation JSON v1 deliberately projects contract/config provenance,
  package resolution, resolved source IDs/revisions, rule results, findings, and warnings.
  List/show use separate deliberate JSON shapes. Source revisions retain content hashes.
  No absolute root, source bodies, timestamps, exception text, or generic dataclass dumps
  are introduced. Existing inventory/authority/lifecycle/claims/integrity projections stay
  unchanged.

## Configuration shape and commands

```toml
schema_version = 5
[[context_contracts]]
id = "implementation-task"
task_class = "implementation"
description = "Explicit implementation package"
[[context_contracts.rules]]
id = "instructions"
mode = "required"
paths = ["AGENTS.md"]
max_count = 1
```

Selectors also accept `kinds`, `authority_classes`, and `lifecycles` arrays. Omitted or
empty dimensions impose no constraint; at least one must be nonempty. Paths are literal,
not glob/regex expressions. Config input normalizes paths before model construction;
direct construction requires already-normalized paths. IDs use `[a-z][a-z0-9_-]*`.

```bash
uv run context-integrity contracts list .
uv run context-integrity contracts show implementation-task . --format json
uv run context-integrity contracts validate implementation-task . --source AGENTS.md
uv run context-integrity contracts validate implementation-task . --format json --output /tmp/contracts.json
```

## Files changed

- `src/context_integrity/models.py`: contract, rule, package, result, finding and overview
  models; repository-config contract collection/invariants.
- `src/context_integrity/configuration.py`: strict v5 parsing and config revisions.
- `src/context_integrity/contracts.py`: pure discovery, resolution and validation.
- `src/context_integrity/rendering.py`: deliberate contract projections and escaped text.
- `src/context_integrity/cli.py`: thin contracts adapter and output handling.
- `tests/test_contracts.py`: 94 focused model/config/domain/rendering/CLI cases.
- `tests/fixtures/contracts-v1.json`: small deterministic validation golden.
- `tests/test_configuration.py`: unsupported-version case advances from 5 to 6.
- `README.md`: contract setup, commands, semantics, outputs and boundaries.
- `docs/architecture.md`: durable implemented contract/compiler separation and semantics.
- `docs/plans/phase-5-implementation-plan.md`: preserve the supplied normative plan; normalize header trailing whitespace only.
- `docs/current-state.md`: verified delivered Phase 5 navigation/status.
- This implementation report.

## Verification

Environment: Python 3.12.13/macOS; no network, credentials, model, or database required.

```bash
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 uv run pytest tests/test_contracts.py -q
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check
git diff --check
git status --short
```

Results:

- Focused contract suite: **94 passed**.
- Full Phase 5 gate: Ruff lint and formatting passed; **626 tests passed**.
- Existing golden comparisons passed across inventory, authority, lifecycle, claims and
  integrity; all earlier tracked JSON fixtures remain **byte-identical** to baseline.
- New validation JSON golden passed, including explicit projection keys, privacy, newline
  termination, content revisions, and repeatability checks. Reordering package input retains
  deterministic results and finding IDs. IDs are independent of message prose.
- CLI integration covers text/JSON and output files on all three commands, empty and passing
  packages, findings with exit 0, missing contracts, unsafe paths, and fatal exit categories.
- Additional real executable smoke via `UV_CACHE_DIR=/tmp/context-integrity-uv-cache
  UV_OFFLINE=1 uv run python` created a disposable local repository, ran
  `context-integrity contracts list/show/validate`, and asserted: passing package zero
  findings; failing package `required_context_missing` + `excluded_context_present`, exit 0;
  text and JSON output; repeated passing JSON byte-identical. Temporary files were removed.
- `git diff --check` passed. Final diff inspection found no new runtime dependencies,
  earlier-projection changes, body-reading selectors, or compiler behavior.

## Decisions, deviations and limitations

No scope deviation from the plan. Rule results and contract definitions sort by ID rather
than declaration order, one of the plan's permitted choices. Selector values and paths sort
lexically for output. Findings are initially medium severity and sort by contract/rule/code/
affected-paths/ID; warnings sort by path/code/message. Identity hashes structured semantic
fields, not prose. Normalized requested paths retain input multiplicity (sorted); resolved
sources are unique. List JSON includes full rule definitions so discovery remains inspectable.
All contract tests live together in one focused module rather than being spread across
existing test modules. No built-in contract or repository config was added merely to supply
demo data; CLI smoke uses a disposable repository.

Validation proves compliance with declared metadata/count rules, not semantic completeness,
claim correctness, source agreement, or validity. It observes current inventory sources,
not arbitrary code files; missing sources remain problems rather than prompting retrieval.
Source/config revisions describe sequential observations, not an atomic snapshot. Historical
context is allowed if the contract permits it. Source-role authority classes do not establish
claim/task-scoped precedence. Independent architectural review remains a separate session.

Phase 6+ deferrals: task classification, retrieval, package completion, ranking, budgeting,
compiler deduplication/selection, code/AST/symbol evidence, Codebase Intelligence integration,
claim-semantic predicates, time-based freshness, integrity gating, inheritance/composition,
glob/regex selector languages, LLMs/embeddings, persistence, cross-repository behavior,
automatic rewriting, and CI/severity enforcement.
