# Phase 11 implementation report

Date: 2026-10-24 Pacific. Implementation/self-verification evidence, **not independent acceptance**.
Base and initial HEAD: `59b90c0808c3465cd38457e48ad79fa9bd2d36c9`, branch `main`, initially clean.
This exactly matches the supplied prompt/plan snapshot; no predecessor implementation changes
were silently assumed. The user supplied the companion plan during this session; it is preserved
under `docs/plans/phase-11-implementation-plan.md`. A temporary provisional plan was replaced by
that supplied document before implementation. No subagents, other chats or external services
were used. Work is intended as one commit titled **Implement Phase 11 local governance**;
the final session response identifies its exact review-target hash.

## Implemented

- Separate explicit strict bounded policy TOML v1, without configuration/schema migration.
  Required targets, ownership/severity/coverage choices, reviewed exact rule overrides and
  exact dated fingerprint waivers. Target kinds compose repository/workspace/derived checks.
- Typed adapters over `integrity_overview`, `Workspace.check` and `Checker.evaluate`. Native
  repository severities, workspace signals, derived effects, provenance hashes and caveats
  survive normalization. Unknown vocabulary, missing evaluation and unavailable evidence
  yield gaps. Workspace checks and subjects are evaluated independently.
- Versioned canonical SHA256 evidence fingerprints, excluding roots/date/unrelated HEAD and
  raw claims. Dirty provider observations and missing native/workspace evidence cannot be
  waived. Valid-through-expiration UTC matching, explicit expired/unused/ambiguous decisions,
  and independent coverage factors prevent waivers from clearing uncertainty.
- Additive `governance check POLICY`: explicit repeated repository diffs, single captured UTC
  date/`--as-of`, optional local provider, JSON/text, prior-report comparison, exclusive output.
  Exits 8/9 distinguish definite blockers from required gaps; blockers take precedence.
- Self-contained evidence-light report v1, scoped count metrics, strict validated advisory
  baseline comparisons, 8 MiB preflight before final serialization, and 4,096-observation /
  16,384-reference normalization caps. No raw claim/source/task payload or verbose legacy report.
  Baseline validation recomputes fingerprints, waiver decisions, severity ownership and metrics.
- Stable reads are an additive opt-in on derived `Reader`, used by governance only. Existing
  derived defaults/output v1 stay intact. The existing workspace formatting defect is fixed.
- Canonical grammar/limits/decision contract, executable golden, policy template and pinned
  least-privilege PR workflow example. Existing actual quality CI is unchanged.

Usage (copy/review the template at the checkout root first):

```bash
uv run context-integrity governance check governance.toml --diff app=BASE..HEAD --format json
uv run context-integrity governance check governance.toml --as-of 2026-10-24 \
  --compare-to previous.json --output /private/tmp/new-governance.json
```

Canonical contract: [`../governance-contract.md`](../governance-contract.md).
Examples: [`../examples/governance-policy.toml`](../examples/governance-policy.toml),
[`../examples/governance-pr.yml`](../examples/governance-pr.yml).

## Acceptance evidence matrix

| Requirement | Executable evidence in `tests/test_governance.py` |
| --- | --- |
| Native severity, ownership, override and legacy exits | `test_real_finding_legacy_and_threshold`; typed architecture provider matrix |
| Real PR range, dirty bytes, shell exit propagation | `test_real_pr_range_dirty_and_help`, `test_ci_shell_propagates_blocker` |
| Workspace pin/mirror/claim disagreement and qualified same paths | `test_workspace_real_signals_and_privacy` |
| Missing/unsafe sources, bad lock isolation, zero checks | `test_workspace_zero_checks_missing_and_failed_lock`, `test_workspace_unobservable_is_not_green` |
| Derived unchanged/review/caveats/transitive uncertainty | `test_derived_unchanged_changed_and_caveats`, `test_derived_upstream_uncertainty_and_definite_change` |
| Exact expiry, stale/cross-target/ambiguous waiver; HEAD stability | waiver boundary/material-change test, cross-target and ambiguous observation tests |
| Independent blocker+gap, explicit warning, missing evaluator, unknown vocabulary | blocker/missing-target test, warning matrix, required architecture/provider and unknown-code/schema tests |
| Strict grammar/type/path/date/duplicate/size bounds | table-driven parser/waiver/baseline/usage tests and normalization/report limit tests |
| Deterministic JSON/text/golden, no literals/roots, no overwrite/rollback | parity/output/golden tests, workspace privacy, failed-link and symlink tests |
| Advisory deltas, incompatible policy/scope/schema, forged baseline | comparison, invalid baseline, strict metrics and fingerprint/waiver corruption tests |
| Stable no-follow acquisition, read-only/offline | unstable receipt, policy/symlink tests, offline file-byte snapshot test |
| Phase 10 F10-001/F10-002 reproductions | `test_phase10_report_amplification_regression`, `test_phase10_warning_isolation_regression` |

## Actual verification

All project verification commands below use:
`UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1`.
Environment: macOS/Darwin 27.0.0 arm64, Python 3.12.13, uv 0.11.13, pytest 9.1.1,
Ruff 0.17.0. No network/model credentials/database required.

- Initial `make check`: Ruff lint passed; formatting failed on pre-existing `workspace.py`
  formatting. Corrected with repository Ruff formatter; no workspace behavior change.
- Baseline `uv run pytest -q`: **1,167 passed in 160.21s**.
- Baseline `uv run pytest -q tests/test_workspace.py tests/test_workspace_cli.py`:
  **96 passed in 74.97s**.
- Fresh final `uv run pytest -q tests/test_governance.py`: **82 passed in 35.64s**.
- Final `make check`: lint passed, **113 files** formatted, **1,249 passed in 179.75s**.
- `uv run context-integrity governance check --help`: passed; actual options documented.
- `git diff --check` and final `git diff --cached --check`: passed. The staged change
  contains 23 task files. Only documentation changed after the final full test gate.

Development iterations are not substituted for the final gate. The first governance run had
65 passes/1 failure from a drift fixture missing its required `reason`; the fixture was corrected.
A combined targeted run over governance/workspace/derived/integrity/CLI/architecture/contracts
had **554 passes/1 failure in 228.17s**: its already-loaded code used an earlier report shape
while the golden had advanced. Fresh governance and the final full gate use the final schema.
An initial combined command named nonexistent `tests/test_contracts_cli.py` (no tests ran);
contract CLI tests actually reside in `tests/test_contracts.py`. One unqualified `uv run python
--version` hit the restricted default cache; the documented temporary-cache command succeeded.
These are resolved development/tooling issues, not unresolved verification blockers.

## Deliberate plan reconciliations

1. Policy-owned override severity requires both reason and review reference, beyond the proposed
   example. They are declarations, not proof of authenticated approval.
2. Policy paths reject parent traversal (place the policy at a common parent). Existing workspace
   manifest root semantics remain compatible. `repository_id` is an optional explicit binding;
   all successfully observed identities appear in reports and conflicting checkout bindings fail.
3. All targets are required. There is no optional-target mechanism that silently excuses skipped
   work. `on_inconclusive=warn` is explicit and reports `allow_with_incomplete`, never complete.
4. Per-subject discovery/config/provider exceptions become visible gaps, preserving other target
   blockers rather than terminating early with 3/6/7. Legacy commands retain those original
   exits. Policy/baseline/report/resource failure remains fatal 6; publication remains 4.
5. Workspace checks run individually, reusing typed caches and budgets, so an invalid lock cannot
   abort later independent checks. Missing native/workspace evidence adds gaps and cannot be waived.
6. Arbitrary policy reason prose is represented by hash; original explanation remains in the
   supplied policy. Reports carry reviewed metadata, pinned/observed digests and related IDs,
   avoiding accidental source-like prose/secret disclosure. No raw legacy claim projector is used.
7. The report uses one `observations` array with typed effects, including definite findings and
   uncertainty/caveats, rather than duplicating large evidence in separate finding/result arrays.
   Subject scope carries declared non-native severity and architecture requirements for inspection.
8. Unsupported integer baseline versions are explicitly incomparable; malformed v1 is input error.
   Scope comparison also requires observed scope, repository change mode and workspace manifest
   hash. This conservative choice refuses misleading trends after changing declared checks.
9. No internal dogfood policy was declared reviewed or wired into actual CI. The supplied policy
   is a template, with installation instructions; hosted dashboards/authenticated audit are deferred.

The original supplied plan remains planning evidence. Implementation never certifies independent
correctness. Phase 10 is a **provisional predecessor baseline**, despite passing self-tests and
new direct reproductions. Independent acceptance/release remains pending.

## Changed-file inventory

- Runtime: `src/context_integrity/governance_models.py`, `governance_config.py`,
  `governance_adapters.py`, `governance.py`, `governance_output.py`; additive `cli.py` command;
  stable-read option in `derived.py`; formatting-only `workspace.py`.
- Verification: `tests/test_governance.py`, `tests/fixtures/governance-report-v1.json`.
- Requirements/contracts/navigation: supplied `docs/plans/phase-11-implementation-plan.md`,
  `docs/governance-contract.md`, `README.md`, `docs/README.md`, `docs/architecture.md`,
  `docs/current-state.md`, `docs/architecture-integrity-contract.md`,
  `docs/derived-context-contract.md`, `docs/workspace-integrity-contract.md`.
- Examples/evidence: `docs/examples/governance-policy.toml`, `docs/examples/governance-pr.yml`,
  this report, `docs/implementation-reports/README.md`.
- No runtime dependencies, lockfile, original PRD, actual CI workflow, predecessor schema/goldens,
  source receipts/locks, unrelated repositories or duplicated AI instructions changed.

## Staleness sweep

| Source | Result |
| --- | --- |
| README status/commands/roadmap | stale: fixed active governance/CI guidance; broader roadmap retained |
| Architecture Layer 7/interfaces/deferred list | stale: fixed local governance boundary; authenticated/hosted operations still deferred |
| Current-state | stale: updated only after actual verification; preserves predecessor review debt |
| Docs map/report index | stale: added contract/evidence links |
| Phase 7 evidence contract | current: provider contract unchanged; no rewrite |
| Phase 8 architecture contract | stale: clarified separate governance and workspace surfaces |
| Phase 9 derived contract | current command semantics; added separate governance link |
| Phase 10 workspace contract | stale CI-deferred wording replaced with separate governance link |
| PRD §§22–25/29/34–35 | current long-term intent; hosted dashboards/audit remain future scope; no edit |
| Supplied plan, historical plans/reviews/reports | historical/planning: retain; no retrospective acceptance rewrite |
| CI recipe/policy/schema examples | current: templates only, explicit PR SHA argv, pinned existing actions, nonzero propagation, golden v1 |

No known pending documentation fix remains. Independent review may identify additional changes.

## Security, limitations and unresolved acceptance

Owners/reviews/date are declarations, not trusted approval. Policy review/branch protection is an
external operational obligation; PR-controlled policy can weaken a gate if teams do not review it.
Review-reference links are never fetched. Source/body/task/claim values are absent, but hashes
and user-declared identifiers/owners/references are still metadata, not a secrecy boundary.

Observations and publication are sequential, non-atomic; concurrent repository replacement is
not an atomic-snapshot guarantee. Limits refuse reports rather than truncate; existing Git/config/
provider ceilings are not a global CPU/memory sandbox. Same-origin checkouts collide and no-origin
identity is location dependent. Provider executable selection is explicit and trusted; governance
does not certify its behavior. POSIX/macOS tested; Windows and crash recovery are not verified.

Byte/declaration equality never proves semantics or freshness history; claims remain unverified.
There is no database, hosted dashboard, authenticated audit trail, auto-remediation, network API,
transitive workspace receipt graph or Phase 12 inference. Old commands remain non-gating.

**Acceptance blockers:** independent Phase 11 review and Phase 10 acceptance are pending.
Phase 4 final verification, Phase 7 fresh review, Phase 8 fresh re-review and Phase 9 fresh
re-review remain separately pending. Passing self-tests do not close them. No push, PR,
external comment, release or deployment was requested or performed.
