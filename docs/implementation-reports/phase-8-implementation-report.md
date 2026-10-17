# Phase 8 implementation report

**Date:** 2026-10-16
**Scope:** Architectural Integrity
**Disposition:** Implementation evidence; fresh independent Phase 8 review remains required.

## Commit context

Started on `main` at `cdee5befa78ccac3bbc4825ad7e0a943e406596a`
(`Fix Phase 7 independent review findings`). The sole initial untracked file was the supplied
`docs/plans/phase-8-implementation-plan.md`; its requirements are retained, with trailing whitespace normalized for the final diff check.
The implementation, tests, documentation and this report are delivered in one commit,
`Implement Phase 8 architectural integrity`, whose parent is that starting commit. The final
commit ID is reported with the delivery; a report cannot embed its own containing commit hash.

The live sibling Context Engine was inspected only for the public graph contract. Its observed
HEAD was `2634ba783c3927de03f9c3eb4df5e7a95e026a0d`, newer than the prompt's reference.
No sibling files were changed. An already-present release `ctx 0.1.0` binary was used for optional
smokes; no correspondence between that executable's build and sibling HEAD is asserted.

## Material changes

- `models.py` / `configuration.py`: strict config v8, immutable typed selectors/invariants,
  claim linkage and direct-construction validation, architecture result models and typed finding
  extensions. Schemas v1–v7 retain valid behavior and reject the new key.
- `relations.py`: separate relation request/provider/batch/state/coverage protocol, body-free
  entity/target/relation values, bounded strings, safe paths, typed points/ranges, ordering and
  unresolved-coverage validation. No numeric provider identity exists in these values.
- `graph_adapter.py`: public Context Engine graph schema-v1 decoder, root/snapshot checks,
  unique/referenced-ID validation, symbol/range/path validation, graph/file accounting,
  deterministic normalization and sanitized coverage categories.
- `context_engine.py` / `evidence.py`: relation capability alongside unchanged context-provider
  protocol, shared bounded subprocess runner, finite deadline validation, graph acquisition and
  separate bounded local hash observations. Context provider states still require `context`
  snapshots; relation states require `graph` snapshots.
- `integrity.py`: explicit `forbid_relation` judgment, claim provenance context, stable grouped
  HIGH findings and coverage-aware result states; all Phase 4 checks remain in the same workflow.
- `rendering.py` / `cli.py`: explicit integrity JSON v2 projection, readable rule/evidence/status
  output, `check` provider/executable options, provider exit 7 and preserved findings exit 0.
- New `test_architecture.py`, `test_graph_adapter.py` and two integrity v2 goldens; intentional
  schema-boundary updates to existing config/contracts/integrity tests. Legacy claim aggregation,
  Phase 4 findings and Phase 7 compilation regressions remain covered.
- Durable architecture-integrity contract, architecture/evidence/README navigation and verified
  current-state update. Historical plans/reports were not rewritten.

## Exact policy semantics

Each invariant references a configured `architecture_invariant` claim with predicate
`must_not_depend_on`. Only `forbid_relation`, `imports` and `references` are supported.
Both selector sides must be nonempty. Exact normalized paths, literal slash-terminated directory
prefixes and qualified symbols select resolved entities; only exact `target_names` select
unresolved names. Families on a side combine with OR; source, kind and target combine with AND.
There is no glob/regex DSL or name-to-path conversion. Prefixes respect directory boundaries.
Claims supply intent/provenance; executable selectors are never extracted from claim prose.

One HIGH finding is emitted per invariant/claim/relation-kind/stable-source/stable-target edge.
Entity descriptors include kind, path, qualified symbol, symbol kind/language and definition range.
Different definitions stay distinct; repeated syntax occurrences of the same edge retain sorted
ranges under one finding. Exact duplicate normalized facts collapse. Finding IDs hash the rule
version and semantic edge key, excluding prose, provider numeric IDs, checkout roots and order.

Claims remain independently `unverified`. Missing claim provenance dependencies produce visible
warnings/context and do not disable explicit config policy. Evaluation does not alter inventory,
authority, lifecycle, supersession, contracts or compilation.

## Evidence surface and interpretation

The replaceable `RelationEvidenceProvider.relations(request)` seam is independent of
`EvidenceProvider.context_candidates(request)`. The Context Engine implementation runs
`ctx --version` followed by `ctx graph ROOT --format json`, consuming only the public schema-v1
DTO. Containment is checked and discarded; imports/references retain stable entity/name targets,
resolution, source path/range, language and derivation. Numeric graph IDs remain decode-local.
Graph summary, file symbol status, relation-file status, unresolved/unsupported counts and fixed
warning categories become typed coverage. Arbitrary provider diagnostics and stderr are discarded.

Subprocesses reuse `shell=False`, closed stdin, process-group cleanup, finite timeouts and bounded
stdout/stderr. The default bounds remain 30 seconds, 64 MiB stdout, 64 KiB stderr and 4 KiB version
stdout. Local post-graph hashing reuses safe acquisition, discards bodies and conservatively reserves
5 MiB per attempted file within 64 MiB. Null hashes expose unreadable/unattempted observations.
These hashes are explicitly local observations, not certification of the provider's analyzed bytes.

A prohibited observed edge yields `violated` even with coverage gaps. Without a matching edge,
reported incompleteness yields `inconclusive`; otherwise the result is `no_violation_observed`.
The latter means only that no prohibited relation appeared in the acquired evidence without
reported gaps. It is **not** proof of architecture compliance. Missing provider selection yields
`not_evaluated`, with a warning, while Phase 4 checks continue. Findings always exit 0; provider
failures exit 7. Config errors remain exit 6.

## Deliberate choices and limitations

- Integrity output advances to v2 globally, including legacy-only checks. Old integrity goldens
  were intentionally replaced; earlier inventory/claim/contract/compiler schema versions stay intact.
- Coverage is deliberately global and conservative. Unrelated gaps can make an otherwise unviolated
  invariant inconclusive. No attempt is made to prove missing evidence irrelevant using graph absence.
- Dirty/unknown graph snapshots remain incomplete because public graph JSON has no content fingerprint.
  Local hashes are separate sequential observations; there is no atomic snapshot or provider-byte proof.
- Upstream imports can remain unresolved; references use conservative, largely same-file syntax
  resolution. No compiler, type, dispatch or exhaustive static-analysis guarantee is made. Unsupported
  languages/files, parse recovery, scan warnings and unsupported candidates remain visible limitations.
- Symbol definition movement can change finding identity. No cross-edit entity lineage is promised.
- Occurrences remain bounded by graph acquisition rather than an additional per-finding truncation layer.
- Process/source safety is locally verified on POSIX/macOS, not independently verified cross-platform.
- No new dependencies, parser, network, database, LLM, CI threshold, waiver, persistence, automatic fix,
  cross-repository policy or Phase 9 revalidation was added. Independent architectural acceptance is
  not claimed; existing Phase 4 final verification and Phase 7 independent review remain pending.

## Verification

Environment: macOS (`darwin`), Python **3.12.13**, pytest **9.1.1**.

Commands and results:

```text
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 uv run pytest -q tests/test_architecture.py tests/test_graph_adapter.py
108 passed in 3.46s

UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check
Ruff: All checks passed!
Ruff format: 80 files already formatted
pytest: 958 passed in 77.34s (0:01:17)

git diff --check
git diff --cached --check
git diff HEAD^ HEAD --check
passed (including newly tracked plan/report whitespace after normalization)

git status --short
inspected before commit; only Phase 8 delivery changes
```

Earlier full regression passes (953 tests before the finite-timeout cases) and focused runs were
followed by the final full gate above after the last code change. Tests are offline and use generated
schema-v1 fixtures/fake executables, not an installed Context Engine requirement. They exercise config
version/linkage/selector failures, relation domain invariants, malformed/dangling/duplicate graph IDs,
unsafe paths/ranges, snapshot mismatches, sanitized process/timeout/output failures, stable IDs and
ordering, no body/root/ID output leakage, no-provider visibility, CLI output files and preserved domains.

Optional smoke command:

```text
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 uv run python /tmp/phase8_smoke.py
```

The temporary script created a small committed Python repository with an explicit import/reference
boundary and invoked `check --evidence-provider context-engine --context-engine-bin` using the existing
sibling release binary. `CONTEXT_ENGINE_CACHE_DIR` pointed to an isolated `/tmp` directory. Both clean
and dirty observations returned exit 0, **2 findings**, `violated`, and explicit incomplete coverage.
Assertions checked absence of absolute checkout root and source bodies. Nothing was installed/built.

## Documentation staleness sweep and next step

Targeted `rg` searches checked README, architecture, evidence contract, current-state and runtime
sources for v7 ceilings, integrity-v1-only descriptions, deferred relation consumers and future-only
Phase 8 language. Corrections updated the README integrity version, architecture provider diagram,
protocol/transport/current-phase descriptions and version ceiling, and evidence capability/version
language. Current-state was updated only after the full gate passed. PRD roadmap and historical
Phase 0–7 evidence/plans were preserved according to their roles.

Next: fresh independent Phase 8 review against the supplied plan, architecture, evidence and
architecture-integrity contracts, actual code/tests and downstream seams. This implementation report
is evidence of changes and local verification, not independent acceptance.
