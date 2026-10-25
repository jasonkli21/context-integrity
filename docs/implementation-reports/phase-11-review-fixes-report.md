# Phase 11 independent-review fixes report

Date: 2026-10-24 Pacific. Implementation evidence, **not independent re-review or acceptance**.
Reviewed implementation baseline: `fdf59c84cbfabb30dbe1f525efe1cf5aafcf42ce` (`main`). This
report and the fixes are included in the single follow-up commit on that baseline; the resulting
commit is the repository `HEAD` reported with this task.

## Findings addressed

- **F11-001:** Governance resolves explicit Git ranges before evaluation and requires the target
  SHA to equal the checked-out `HEAD`. It rejects unknown/dirty status, tracked or untracked work,
  missing endpoints, target mismatches and checkout changes detected at the final status check
  with sanitized exit 6, independent of `on_inconclusive`; all explicit targets are rechecked
  after evaluation and before report construction, so one target cannot change while another is
  evaluated. No partial report is emitted. Detached `HEAD` and valid ref/SHA forms are covered.
  Legacy `integrity check --diff` is unchanged.
- **F11-002:** Report v2 comparisons require the same resolved base SHA for `git_range`, while
  allowing target progression on that base. Evaluation config hashes and provider presence,
  identity, contract version, capabilities and coverage summary must also match. Stable reason
  codes identify incompatible comparisons. Baselines never change the current gate.
- **G11-003:** Policy v2 waivers record the reviewed effective severity, accountable owner and
  `fail_on` threshold. A context mismatch becomes `stale_context` and cannot suppress the finding.
  Policy v1 without waivers remains accepted; existing v1 waivers fail closed as stale until
  renewed under v2. Evidence fingerprints remain independent of approval context. Governance
  report v2 exposes the context and treats report v1 baselines as unsupported/incomparable.
- **G11-004:** The PR example writes the bounded sanitized JSON report under the runner's temporary
  directory, prints it to the Actions step log, and emits an `if: always()` job summary with the
  gate outcome and validated aggregate counts. If no complete report exists, the summary identifies
  an input/infrastructure failure (or a skipped evaluation). A shell regression covers exits 0, 8
  and 9. No artifact upload or workflow activation was added.
- **G11-005:** The contract now explains that PR-head policy declarations are not authenticated,
  describes CODEOWNERS/required-review and branch-protection or base-controlled-policy options,
  and keeps the example on read-only `pull_request`. The repository's actual quality workflow
  remains unchanged and is not a governance gate.
- **D11-006:** README's repository map now points at the Phase 11 active plan.
- **G11-007:** The sample and contract state that a green result covers declared checks only. The
  starter policy has no architecture invariants, workspace target or derived target. A global
  required-family floor remains deferred and is documented as a protected-gate limitation.

## Architecture and compatibility choices

Explicit governance ranges are committed-checkout scopes, not historical evaluators: the range
target must equal a clean `HEAD` at both evaluation boundaries. Individual reads are stable, but
the overall observation remains sequential and is not an atomic filesystem transaction.

Waiver evidence identity and waiver authorization context remain separate. Policy/report schema
versions were advanced where serialized grammar changed. Policy v1 is still readable; its old
waivers require re-review. Report v1 is safely treated as incomparable rather than consumed as a
v2 baseline. Config v1–v8, integrity JSON v2, compiled JSON v3, derived receipt/result v1, and
workspace v1 contracts are unchanged.

No ADR was needed: these decisions refine the existing Phase 11 governance boundary and are
captured in the canonical [governance contract](../governance-contract.md) and
[architecture](../architecture.md). The original Phase 11 plan, review and implementation report
remain unchanged as historical evidence.

## Verification

- `UV_CACHE_DIR=/tmp/context-integrity-phase11-fix-uv-cache UV_OFFLINE=1 uv run pytest -q tests/test_governance.py`
  — **91 passed in 33.41s**.
- `UV_CACHE_DIR=/tmp/context-integrity-phase11-fix-uv-cache UV_OFFLINE=1 make check`
  — Ruff lint passed; format check passed (**115 files**); **1,258 passed in 178.53s**.
- `git diff --check` — passed after final source/doc changes; staged diff check remains before commit.
- `UV_CACHE_DIR=/tmp/context-integrity-phase11-fix-uv-cache UV_OFFLINE=1 uv run context-integrity governance --help`
  — passed; the governance command is listed.

Environment: macOS 27.0.0 arm64, Python 3.12.13, uv 0.11.13, pytest 9.1.1, Ruff 0.17.0.
No live GitHub Actions/fork execution, external Context Engine binary, Windows behavior, or
concurrent filesystem-race/crash behavior was verified. Independent Phase 11 re-review and prior
Phase 4/7/8/9/10 acceptance remain pending.

## Follow-up verification (2026-10-26)

The workflow example and canonical contract were updated to publish a bounded summary after the
gate step, including on exits 8 and 9. The full report remains available in the evaluation step log;
the summary includes only validated gate enums and aggregate integer counts. The workflow was not
run on GitHub Actions, and its example-only status is unchanged.

- `UV_CACHE_DIR=/tmp/context-integrity-phase11-fix-uv-cache UV_OFFLINE=1 uv run pytest -q tests/test_governance.py tests/test_integrity.py tests/test_workspace.py tests/test_workspace_cli.py tests/test_derived.py tests/test_derived_cli.py`
  — **398 passed in 134.90s**.
- `UV_CACHE_DIR=/tmp/context-integrity-phase11-fix-uv-cache UV_OFFLINE=1 make check`
  — Ruff lint passed; format check passed (**115 files**); **1,258 passed in 176.65s**.
- The added `base-a` ref/SHA and working-tree/range comparison assertions passed in
  `UV_CACHE_DIR=/tmp/context-integrity-phase11-fix-uv-cache UV_OFFLINE=1 uv run pytest -q tests/test_governance.py::test_compare_requires_same_git_base_but_allows_target_progression`
  (**1 passed in 5.49s**).
- The updated workflow YAML parsed locally. Its extracted summary step rendered allowed, blocked
  (exit 8), and no-report input-failure summaries. No live Actions run was performed.
- A fresh independent Phase 11 re-review is still required; passing implementation tests do not
  close Phase 10 acceptance or the listed Phase 4/7/8/9 review debt.
