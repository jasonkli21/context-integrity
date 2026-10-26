# Current State

**Last updated:** 2026-10-26
**Current phase:** Phase 11 — CI / Governance / Observability
**Active plan:** `docs/plans/phase-11-implementation-plan.md`
**Status:** Post-Phase 11 stabilization fixes through `56cd28a` are implemented and self-tested;
fresh independent stabilization/Phase 11 review and predecessor acceptance remain pending.
Audit provenance, dispositions and exact commits:
[`stabilization remediation report`](implementation-reports/stabilization-remediation-report.md).

## Delivered

- Phases 0–10 remain intact. Config v1–v8, compiled JSON v3, integrity JSON v2,
  derived receipt/result v1 and workspace/lock/check/context v1 remain unchanged.
- Explicit governance policy TOML v1/v2 composes typed repository/workspace/derived evaluations,
  declared severity/ownership, reviewed exact overrides and dated exact waivers. V2 waivers bind
  approval to effective severity, accountable owner and gate threshold; v1 waivers need renewal.
- Separate report v2 preserves native signals, evidence hashes, limitations and independent
  blocker/coverage factors. Exit 8 prioritizes definite blockers; 9 is fail-on-incomplete.
  Explicit warning policy permits completion while visibly retaining incomplete coverage.
- Governance Git ranges require the target commit to match a clean checked-out HEAD. Missing or
  mismatched endpoints, dirty paths and a changed checkout fail with exit 6 and no report. Strict
  inventory/config bytes and membership must also match target Git blobs; ignored/untracked config
  and edits hidden by index flags fail closed, with final rechecks. Working-tree/legacy checks stay
  live. Provider graphs explicitly remain observations without commit-certified analyzed bytes.
- Required compiler repair has sound capacity/cost pruning and a deterministic 250,000-unit work
  ceiling. Exhaustion retains an incomplete safe greedy package with a fixed warning. Legacy
  provider symbols retain qualified case/Unicode; reported sensitive-file exclusion counts survive
  as safety caveats. Production still consumes only `ctx context`/`ctx graph` schema v1.
- Evidence-scoped fingerprints exclude unrelated HEAD changes, roots, dates and claim bodies.
  Prior-report comparisons require the same diff base, evaluation config and compatible provider
  identity/capabilities/coverage; same-base target progression remains comparable. Comparisons are
  explicit, strictly validated and advisory. Scoped metrics are recomputable; no persistent
  monitoring or authenticated approval is claimed.
- Bounded no-follow stable inputs and exclusive output outside observed roots. No source bodies,
  raw claims, task strings, network/model/database requirement or automatic pin/waiver refresh.
  Existing quality CI remains unchanged; a pinned least-privilege PR recipe prints the bounded
  report, publishes an `if: always()` gate summary and documents trusted-policy and declared-coverage
  limits. It remains an example only.

## Verification

`UV_CACHE_DIR=/tmp/context-integrity-phase11-fix-uv-cache UV_OFFLINE=1 make check` passed:
Ruff lint, formatting (**115 files**) and **1,316 tests in 472.84s**, Python 3.12.13/macOS 27.0.1.
The broad focused suite passed **530 tests in 281.97s**; compiler/context-provider/evidence tests
passed **251 in 48.67s**, with later additions covered by the full gate or focused reruns.
Real-Git 28/32-file impossible-budget CLI probes returned incomplete in about one second.
An existing `ctx 0.1.0` release binary passed clean/dirty Rust/Python legacy context/graph smoke,
including qualified matches, safety exclusions and an architecture violation. Its exact-source
build provenance was not verified. These are implementation self-tests, not independent acceptance.

Canonical behavior: `docs/governance-contract.md`; policy/PR templates: `docs/examples/`.
Phase 11 delivery evidence: `docs/implementation-reports/phase-11-implementation-report.md`.
Review-fix evidence: `docs/implementation-reports/phase-11-review-fixes-report.md`.
Predecessor contracts remain `docs/workspace-integrity-contract.md`,
`docs/derived-context-contract.md`, `docs/evidence-contract.md`, and
`docs/architecture-integrity-contract.md`.

## Known limitations / acceptance debt

Phase 11 review fixes are implemented; independent Phase 11 re-review is still required. Phase 10
self-tests and direct report-bound/warning-isolation reproductions pass, but independent acceptance
is unavailable. Phase 4 final independent verification, Phase 7 fresh independent review, Phase 8
fresh independent re-review, Phase 9 fresh independent re-review and Phase 10 acceptance remain
pending. These implementation tests do not settle predecessor acceptance.
The supplied stabilization audits reviewed `b03d707`: RWA-001/002 and CI-BND-01/02 now have tested
local fixes, requiring fresh independent review. Earlier cumulative Phase 0–2 closure, the absent
Phase 3 independent artifact and Phase 5–6 index-level acceptance also remain unestablished here.
External-quality evaluation metrics and a protected-policy required-family floor remain separate
backlog. Engine's evidence-v1 conformance finding is upstream scope; no consumer migration is delivered.

Reports cover explicit rules/declared inputs, not semantic truth, exhaustive compliance or API
compatibility. Claims remain unverified. Observations are sequential; no-origin IDs are location
dependent and same-origin checkout collisions are rejected. Policy owners/review references are
unauthenticated declarations. A user-selected date is replay input, not a trusted clock.

Governance resource limits can refuse the report rather than publish partial evidence. Existing
Git/config/provider bounds remain; no global process sandbox is claimed. POSIX/macOS verified;
Windows and crash-atomic publication are not verified. No hosted dashboard, authenticated audit
trail, automatic remediation or Phase 12 reasoning is delivered.

## Next expected step

Before Phase 12 work, obtain fresh independent stabilization/Phase 6/7/11 review against the plans,
architecture, durable contracts and actual code, fix findings separately, verify predecessor
acceptance debt and complete a verified current-build Engine integration matrix.
No independent release/acceptance claim has been established by this implementation session.
