# Current State

**Last updated:** 2026-10-21
**Current phase:** Phase 9 — Derived Context Revalidation
**Active plan:** `docs/plans/phase-9-implementation-plan.md`
**Status:** Phase 9 review findings fixed and offline-verified; fresh independent re-review pending.
Phase 8 remediation's fresh independent re-review remains pending.

## Delivered

- Phases 0–8 inventory, question-specific authority, lifecycle/supersession, explicit
  claims, deterministic drift checks, contracts, mixed compilation and architectural
  integrity remain intact. Claims stay `unverified`. Config v1–v8, compiled JSON v3,
  integrity JSON v2 and the other existing projections retain their versions/behavior.
- Standalone strict derived receipt v1 records actual artifact/source SHA256, effective
  lifecycle/authority metadata, config absence/presence, declared derivation and pinned
  upstream receipt/artifact identities. Explicit dependencies may include non-inventory
  code. Constructors/decoder reject malformed/ambiguous fields and duplicate JSON keys.
- `derived capture` explicitly writes a new sidecar; `derived check` reobserves pinned
  inputs without refreshing them. Bounded memoized receipt DAGs propagate original source
  changes and uncertainty through unchanged intermediate artifacts. HEAD movement alone
  does not invalidate inputs; staged and unstaged edits are identified by content.
- Additive `compile --receipt-output` requires saved JSON and pins typed inventory/provider
  selections, effective contract/policies/budget, task digest, inventory selection universe,
  compiler status/version and validated provider snapshot/coverage fingerprints. Provider
  evidence is not re-queried: provider context remains inconclusive absent definite changes.
- Result v1 reports `unchanged_observed_inputs`, `review_required`, or `inconclusive`, with
  sorted reasons and explicit provenance caveats. Definite changes dominate while retaining
  uncertainty. Byte equality proves neither semantic correctness nor exhaustive provenance.
- Known inventory-classified handoffs and generated summaries require an explicit upstream
  receipt link for revalidation; compiler receipts fingerprint installed package Python source,
  and empty compiler selections are distinguished from empty manual declarations.
- New outputs are exclusive, repository-local, non-inventory paths with safe no-follow
  parents. Both compile payloads are prepared before publication; ordinary failures roll
  back. Cleanup/rollback failure is explicit. No hidden persistence, model/network call,
  provider installation, auto-refresh, auto-fix or authority promotion is introduced.

## Verification

`UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check` passed:
Ruff lint, formatting (**93 files**) and **1,071 tests**, Python 3.12.13/macOS.
`UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 uv run pytest -q tests/test_derived.py tests/test_derived_cli.py`
passed **106 tests**, including linked Git worktree edits, generated-source receipt linkage,
compiler implementation identity changes, empty compiler selection and graph budget reasons.
`git diff --check` passed. No tests were skipped.

Durable behavior: `docs/derived-context-contract.md`, `docs/evidence-contract.md`,
`docs/architecture-integrity-contract.md`. Phase 9 evidence and plan deviations:
`docs/implementation-reports/phase-9-implementation-report.md`.
Phase 8 remediation evidence: `docs/implementation-reports/phase-8-review-fixes-report.md`.

## Known limitations / findings

Receipts are unauthenticated local declarations, not semantic truth or authority. Manual
provenance closure is never proven. Provider ranking/coverage is not revalidated; inventory
selection fingerprints are conservative and can flag unselected document changes. Unknown
current inventory coverage is inconclusive. Observations are sequential, not atomic.

Files cap at 5 MiB; receipts at 1 MiB; DAGs cap at 128 receipt observations, 16 levels,
256 direct sources and 16 parents per receipt. Graph and metadata inventory each have
independent 64 MiB/4,096 observation ceilings. Receipt paths are printable ASCII; non-Git
identity retains existing location-dependent fallback. Cross-platform operation is not
claimed. Pair publication is not crash-atomic; process/power loss can leave orphaned files.

Phase 8 retains conservative global graph coverage, syntax/resolution limitations and
unknown/dirty snapshot caveats. No observed architecture violation is no compliance proof.
Phase 4 final independent verification, Phase 7 fresh independent review and Phase 8 fresh
independent re-review remain pending. Phase 9 independent acceptance has not been established.
No semantic claim verification, generic contradiction engine, persistence, LLM, cross-repo
policy, source-body bundling or CI enforcement is delivered.

## Next expected step

Fresh independent Phase 9 re-review against the active plan, durable contracts, code/tests and
material compiler/provider seams. Keep the earlier pending reviews explicit; Phase 10
cross-repository work remains separately scoped.
