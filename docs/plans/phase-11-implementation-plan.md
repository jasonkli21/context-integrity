# Context Integrity — Phase 11 Detailed Implementation Plan

**Phase:** 11 — CI, Governance, and Observability\
**Document role:** Proposed implementation plan; **not** evidence of delivery or independent acceptance\
**Repository:** https://github.com/jasonkli21/context-integrity\
**Inspected baseline:** `main` at [`59b90c0808c3465cd38457e48ad79fa9bd2d36c9`](https://github.com/jasonkli21/context-integrity/commit/59b90c0808c3465cd38457e48ad79fa9bd2d36c9), 2026-10-24 (Pacific)\
**Predecessor:** Phase 10 — explicit cross-repository integrity; review fixes committed, **independent verification/acceptance pending**\
**Successor:** Phase 12+ — optimization and richer intelligence

> **Baseline/acceptance gate.** On starting implementation, inspect the then-current `HEAD`, `AGENTS.md`, `docs/current-state.md`, the Phase 10 plan/contract and relevant code/tests. The current snapshot says the original Phase 10 delivery (`c24f15d`) passed 1,167 tests, but the later review-fix commit (`59b90c0`) **was not tested** in its fixes report. Re-run the Phase 10 reproductions and full gate and obtain/record independent acceptance before declaring Phase 11 integrated and complete. If Phase 10 changes, reconcile this plan openly rather than treating a past plan or fixes report as proof. Preserve unresolved Phase 4, 7, 8, and 9 independent review statuses; Phase 11 must not quietly close them.

## 1. Why Phase 11 exists

The preceding phases can inspect local repositories, evaluate deterministic drift, revalidate declared generated-context dependencies, and compare explicit cross-repository contracts/claims. Their CLI commands intentionally report findings without acting as CI enforcement. Phase 11 adds a **separate, explicit decision layer** so a team can ask:

1. Which observed findings are blocking for this pull request, under a named, owned policy?
2. Which *specific* previously reviewed findings have a valid, short-lived waiver, and why?
3. Did the requested checks actually run with sufficient evidence, or is the result inconclusive?
4. What changed in a comparable integrity report since a prior run?

The product outcome is a local-first, deterministic **policy-to-CI vertical slice**: an explicit policy file plus one command yields inspectable pass/fail/inconclusive decisions, versioned evidence-light JSON/text, meaningful exit codes, time-limited waivers, and comparable aggregate metrics. A GitHub Actions example consumes those exit codes without a network API in the product.

**Important separation:** An integrity signal is an observation; severity/ownership/waiver are governance decisions; the CI gate is an operational decision. Phase 11 must not present any of these as semantic truth, universal authority, or exhaustive repository compliance.

## 2. Source-of-truth and actual current architecture

Follow `AGENTS.md`'s hierarchy: code/tests prove delivery, `docs/architecture.md` and accepted ADRs define invariants, `docs/prd.md` expresses intent, the active plan defines planned scope, reports/reviews are historical evidence. There are no accepted ADRs in the inspected `docs/adr/` tree beyond its index/template; recheck at implementation time.

| Evidence | Current meaning / constraint |
| --- | --- |
| `docs/prd.md` §§22–25, 29 (Phase 11), 34–35 | PR checks, inspectable severity, policy ownership, scoped waivers/expiration, audit history, metrics/trends, low false-positive rate |
| `docs/architecture.md` Layer 7, §§16, 18–22, 28–30, 32–34 | Governance follows evidence, canonical state is external, no implicit network/DB/LLM, source inputs untrusted, explicit schema evolution and uncertainty |
| `docs/current-state.md` | Phase 10 delivered with pending independent acceptance; not a Phase 11 readiness certificate |
| `docs/workspace-integrity-contract.md` | Workspace check JSON v1, explicit qualified identities, `aligned_observed`/`review_required`/`inconclusive`, claims remain unverified |
| `docs/derived-context-contract.md` | Derived result JSON v1, `unchanged_observed_inputs`/`review_required`/`inconclusive`, local declared provenance only |
| `docs/architecture-integrity-contract.md` and `docs/evidence-contract.md` | Architecture relations are descriptive evidence; absent/provider-incomplete evidence cannot become a passing assertion |
| `src/context_integrity/models.py`, `integrity.py`, `rendering.py` | Existing `IntegrityFinding` has severity `high`/`medium`/`low`; ordinary `check` emits integrity JSON v2 and exits successfully even with findings |
| `src/context_integrity/workspace*.py` | Workspace findings have signals and coverage, **not** generic severity; report size capped at 8 MiB after Phase 10 fixes |
| `src/context_integrity/derived.py` | Receipt check returns typed reasons (`review`/`uncertainty`/`caveat`) and derived result JSON v1 |
| `src/context_integrity/cli.py`, `.github/workflows/ci.yml`, `pyproject.toml` | Typer commands, current exit conventions, existing quality-only CI, Python 3.12+/uv/pytest/Ruff; avoid a competing CLI/framework |

Do not modify or re-label existing inventory/config v1–v8, compiled JSON v3, integrity JSON v2, derived receipt/result v1, or workspace JSON/lock v1. The new policy and report schemas are independently versioned.

## 3. Three release journeys and acceptance outcomes

**J1 — PR gate for one repository.** A contributor changes a source that causes the existing `check --diff BASE..HEAD` evaluation to emit a high-severity architecture/instruction finding. Under a reviewed policy, `governance check` reports that specific finding as blocking and returns a dedicated policy-failure code. Running the original `check` still returns its legacy exit behavior. A clean, fully evaluated scope passes; absent required evidence does not silently pass.

**J2 — Workspace and generated-context safeguards.** A declared cross-repository `contract_pin` mismatch is mapped by policy to a blocking severity. Separately, a declared Phase 9 derived receipt with a changed observed dependency yields review-required status. Both appear under distinct subject identities. A merely `inconclusive` check remains visibly inconclusive and is handled by explicit coverage policy; it cannot be cleared by a finding waiver.

**J3 — Governance lifecycle and trend.** A reviewer adds a narrowly scoped waiver for a known finding fingerprint, with owner, reason, review reference, and expiration. The gate can pass with an explicit waived count. The same waiver stops matching when evidence materially changes or it expires. Comparing with an earlier compatible report shows count deltas and unresolved/waived totals, without inventing a persistent historical database or claiming an authenticated approval.

## 4. Scope and non-goals

### Required in this phase

1. Explicit, strict, versioned **governance policy v1** with policy identity, declared owner, target scopes, severity threshold, incomplete-evidence rule, optional exact rule overrides and tightly scoped expiring waivers.
2. A shared **typed adaptation layer** for existing repository `IntegrityOverview`, workspace check findings/coverage, and declared derived-receipt results. Reuse the real evaluators, do not parse terminal text or reinterpret provider graph internals.
3. A new CLI entrypoint such as `context-integrity governance check POLICY [--diff TARGET_ID=BASE..TARGET] [--as-of YYYY-MM-DD] [--compare-to PREVIOUS.json] [--format text|json] [--output PATH]`, operating offline. Exact names may change if better grounded in code, but the workflows and semantics below must survive.
4. Explicit CI exit behavior, complete/partial-coverage reporting, stable finding identity/fingerprint, controlled severity resolution, and valid/invalid/expired waiver treatment.
5. Deterministic, compact **governance report JSON v1** plus readable text; aggregate metrics and comparison with a deliberately supplied compatible historical report.
6. A portable, least-privilege pull-request workflow example and an offline test fixture; no implicit platform login, PR comment, auto-approval, or merge action.
7. Bounded security-sensitive input/output handling, strong tests, a durable governance contract, implementation report, and documentation staleness sweep.

### Intentionally out of scope

- A hosted dashboard, organization service, long-lived metric store, signed/cryptographically authenticated approvals, GitHub App/OAuth connection, comments/status API writing, live PR metadata, scheduled jobs or database migrations.
- Semantic compatibility checking, claim truth verification, LLM/embedding inference, new contradiction engine, transitive cross-repo receipt graphs, Codebase Intelligence internal database access, or auto-remediation.
- Treating current local findings as exhaustive security/compliance results, treating an expired/invalid waiver as a reason to mutate repository policy, or automatically inferring ownership/authority from GitHub usernames/recency.
- Silently enabling expensive/networked EvidenceProvider calls. Existing optional evidence integration remains explicitly requested and coverage-limited.
- Turning *all* older CLI commands into CI gates or rewriting old JSON schemas. The governance command composes existing checks without changing their contracts.

## 5. Versioned policy v1: concrete proposed contract

Use a deliberately explicit TOML file, e.g. `context-integrity-governance.toml`, supplied as a CLI argument. Do not add a hidden repository-wide policy discovery service or upgrade `.context-integrity.toml` to config v9. Resolve relative paths against the policy file's directory and use existing safe repository/file-read techniques. A representative declaration:

```toml
governance_schema_version = 1
policy_id = "context-integrity-main"
owner = "team:infra"                     # declared, not authenticated
fail_on = "high"                       # high, medium, low
on_inconclusive = "fail"              # fail or warn; selected deliberately

[[targets]]
id = "app"
kind = "repository"
root = "."
require_architecture = false           # true requires evaluated architecture coverage

[[targets]]
id = "product"
kind = "workspace"
manifest = "../workspace.integrity.toml"
review_severity = "high"              # explicit mapping; workspace has no severity

[[targets]]
id = "summary"
kind = "derived"
root = "."
receipt = "docs/generated/summary.receipt.json"
review_severity = "medium"

[[rule_policies]]
target = "app"
rule_id = "architecture.forbid_relation.v1"
severity = "high"
owner = "team:architecture"

# After running once, pin the exact observed fingerprint and reviewed evidence.
[[waivers]]
id = "WAIVER-123"
target = "app"
finding_fingerprint = "<64-hex-sha256>"
owner = "team:architecture"
reason = "Reviewed temporary exception"
review_ref = "https://github.com/example/repo/pull/123"
expires_on = "2026-11-01"
```

The example waiver digest is a placeholder, **not a valid committed configuration**. Provide valid sample fixtures in tests/docs. Treat `owner` and `review_ref` as reviewable declared metadata, not verified identity or external approval. Never fetch `review_ref` at runtime.

### Validation and trust requirements

- Reject unknown fields, duplicate keys/IDs, unsupported schema versions, malformed dates, booleans passed as integers, overlong/unsafe paths, unsafe symlinks, unbounded rules/waivers and unexpected target kinds. Set and test conservative limits (illustrative: 256 KiB policy, <= 16 targets, <= 128 rule policies, <= 256 waivers); justify any change.
- Targets are explicit and stable: repository root for `repository`, manifest for `workspace`, and receipt+root for `derived`. No root/manifest alias collision may silently conflate findings; actual discovered repo IDs are reflected in the report. A policy may restrict target kind combinations if required by the existing code; document such a restriction rather than silently skipping targets.
- For `repository`, preserve the intrinsic finding severity unless an exact `(target, rule_id)` policy override is declared, and show **both** observed and effective severity when overridden. For workspace/derived review signals, require an explicit target default `review_severity`, with optional exact rule/reason override. Never infer a universal ordering from authority classes, workspace aliases or provider relevance.
- Unmapped new codes and unknown target/result statuses must fail closed into an explicit policy/coverage error or inconclusive result; never drop them. Rule policy collisions are validation errors. Avoid wildcard waivers, free-form regex suppression, and broad `ignore all` options.
- A meaningful pass requires the declared target evaluations and explicitly required coverage. Zero workspace checks, disabled/unavailable required architecture evaluation, missing receipt, unsupported evidence, or any skipped target cannot be represented as a fully evaluated pass. Distinguish policy *coverage promises* from actual available evaluator signals; do not invent counters that code cannot establish.
- The policy file must be a canonical repository-owned, reviewable input. Include its SHA256 and version in every result; policy changes are attributable through normal Git history, not through an invented signature/audit service.

## 6. Finding normalization, gates and uncertainty

Create a small typed `GovernanceSubject`/`GovernanceFinding`/`GovernanceDecision` seam; keep acquisition, evaluation, rule decisions and rendering separate. Each finding needs a target identity; source kind and exact rule/reason; normalized repo-qualified paths/IDs; observed status/signal; observed/effective severity; evidence references/digests where actually available; policy owner; waiver decision; and explicit limitations.

| Existing evaluator | Normalize to governance without overstating evidence |
| --- | --- |
| `check` / `IntegrityOverview` | Existing `rule_id`, `code`, `severity`, evidence/path/claim/invariant and warnings. `architecture.evaluation_status` is not interchangeable with zero architecture findings. Preserve `--diff` semantics. |
| `workspace check` | Each declared check ID, `workspace.<kind>.v1`, `signal`, reasons and repo-qualified sides. `review_required`/`declared_disagreement` are definite review signals, not semantic API breakage or verified claim contradiction. `not_established` and incomplete coverage stay inconclusive. |
| `derived check` | One declared artifact subject with typed reasons. `review_required` reflects invalidation/revalidation need, `inconclusive` reflects uncertainty, `unchanged_observed_inputs` only the declared inputs. Do not convert caveats into proven findings. |

**Fingerprint semantics:** Use a versioned canonical fingerprint input comprising target kind/id, actual qualified repository identity, rule/diagnostic identity, affected normalized source/claim/artifact IDs, signal, and stable **evidence-state digest** sufficient to distinguish a materially changed observation. Hash canonical JSON with explicit ordering. Exclude absolute checkout paths, ephemeral timestamps, unrelated HEAD moves and rendered prose. Do **not** fingerprint solely on a generic rule ID/path or trust pre-existing finding `id` to be globally unique. Document when provenance is too incomplete for waiver eligibility. Keep raw claim values/content out of the public fingerprint preimage and report; use bounded digests where needed. Test determinism/collision boundaries and the exact waiver invalidation behavior.

**Gate aggregation (proposed):**

1. Evaluate every declared target first. Record definite findings, inconclusive subjects, unexpected exceptions and warnings separately. Do not drop a definite violation because some independent input is uncertain.
2. Resolve effective severity through policy. A definite finding at or above `fail_on` is blocking unless an exact, valid waiver matches that **same** target/evidence fingerprint.
3. A waiver requires exact target + fingerprint, nonempty reason/owner/review reference, valid expiration, and one unambiguous match. It cannot suppress an evaluation error, missing check, inconclusive result or report serialization failure. Expired/unused/ambiguous/mismatched waivers must be visible as diagnostics. Decide and document whether stale waivers themselves make the policy invalid; never silently treat them as valid.
4. Any incomplete required evaluation yields an explicit `inconclusive` gate factor, even when another finding blocks. `on_inconclusive = fail` blocks the CI gate; `warn` is an explicit policy exception with a conspicuous report status, **not** `complete` evidence.
5. Aggregate decisions must preserve both flags (`has_blocking_findings`, `has_incomplete_coverage`) and a final gate outcome. No policy setting can relabel unverified claims or locally aligned bytes as semantic correctness.

**Exit codes:** Reserve `0` for policy-allowed completion (including explicitly allowed warnings/waivers), `8` for evaluated blocking policy findings, and `9` for incomplete evidence that fails coverage policy without an evaluated blocker. Keep existing usage/config/repo/output/provider exit conventions (`2`/`6`/`3`/`4`/`7` respectively) wherever they apply. When both definite blocking findings and uncertainty exist, prefer `8` while reporting *both* flags. Do not change legacy `check`, `workspace check`, or `derived check` exit semantics. Print a complete report before returning policy-failure exits; errors in evaluation/policy validation must not be disguised as ordinary findings.

## 7. CLI and CI integration

Recommended command (adjust spelling for Typer conventions but document the actual CLI):

```bash
# Local/PR inspection. Pass a target-specific Git range explicitly.
context-integrity governance check context-integrity-governance.toml \
  --diff app=BASE..HEAD --format json

# Optional deterministic waiver test and comparison with a previous report.
context-integrity governance check context-integrity-governance.toml \
  --as-of 2026-10-24 --compare-to previous-governance.json --format text
```

Rules:

- The repeated `--diff TARGET_ID=BASE..TARGET` option is legal only for declared repository targets, unique per target. If absent, use the existing repository command's documented working-tree semantics. Do not silently use the runner's PR base or a shallow-clone guess. Workspace checks remain sequential current observations; Phase 9 receipts remain their own declared snapshots.
- Default to stdout and read-only operation. `--output` may create **one** new report outside participating repository roots, using safely validated no-follow/exclusive publication; no overwrite or append and no policy/receipt mutation. Render and bound the whole report before publication. In CI, redirect stdout to a trusted runner temp/artifact location if desired.
- Provide a `docs/examples/` GitHub Actions recipe: least-privilege `contents: read`, fetch sufficient Git history for explicit `BASE..HEAD`, pin external actions by commit, run the installed local CLI against a checked-in policy, and let nonzero exit codes fail the job. Do not run untrusted PR metadata as shell code, automatically post comments, use write-scoped tokens, or mark checks successful after catching exit 8/9.
- Do not make this project's existing `.github/workflows/ci.yml` gate the project itself using a speculative or non-shipped policy. Add an internal dogfood gate only if a real, reviewed fixture/policy exercises useful behavior without weakening the existing lint/format/test workflow.

## 8. Report JSON v1 and metrics/trend

Create an independent `governance_report_schema_version = 1` JSON contract. Suggested top-level fields:

```json
{
  "governance_report_schema_version": 1,
  "policy": {"id": "context-integrity-main", "sha256": "...", "owner": "team:infra"},
  "evaluation": {"as_of_utc_date": "2026-10-24", "subjects": [], "coverage": []},
  "gate": {"outcome": "fail", "has_blocking_findings": true, "has_incomplete_coverage": false},
  "findings": [],
  "waivers": [],
  "metrics": {"by_severity": {}, "blocking": 0, "waived": 0, "inconclusive": 0},
  "comparison": {"status": "not_requested"},
  "limitations": ["declared_scope_only", "no_semantic_proof"]
}
```

This is a **shape sketch**, not a full JSON schema; specify exact keys/enum meanings and write goldens before release. A report should include target scope, observed repo ID/snapshot/basis, check evaluation status, qualified finding fingerprint and evidence metadata, intrinsic/effective severity, owning policy rule and waiver ID, final decision, scoped uncertainty, deterministic counts, and no source/claim body text. Untrusted paths and messages require safe escaping; avoid leaking workspace absolute roots, task texts, tokens, environment variables or sensitive claim literals. Establish a practical serialized-output cap no larger than the existing workspace cap unless justified, including bound checks *before* huge string allocation.

Metrics v1 should derive strictly from report data: targets requested/evaluated/inconclusive, findings per severity and rule, blocking/waived/unwaived, coverage gaps, review-required derived artifacts, and workspace disagreements. Keep stable counts distinct from optional nondeterministic runtime timing. Do **not** claim global contradiction counts, retrieval quality or ecosystem-wide integrity from this narrow sample.

`--compare-to` may load only a strictly validated prior governance report v1, from a separately supplied local file. Compare counts and matched stable fingerprints only if policy identity/hash, declared scope/target repo IDs, schema and metrics definitions are compatible; otherwise report `comparison.status = "incomparable"` with reasons. A baseline is **observability-only**, never an automatic exemption or a mechanism that permits regressions because a finding pre-existed. No implicit persistence; the user/CI keeps historical JSON artifacts. Mention that a visual dashboard would be a later consumer of these versioned outputs, not a Phase 11 delivered service.

## 9. Time, security, determinism and resource controls

- Validate and bound policy, prior report and target counts, string sizes, waiver counts, evaluation work and output bytes. Do not allow repeated findings/waivers to amplify memory/serialization unboundedly (Phase 10 F10-001 lesson). Avoid quadratic fingerprint/waiver matching.
- Use a single UTC evaluation date for the whole invocation; `--as-of` is explicit test/replay input, otherwise derive UTC date once. Document expiration inclusivity (e.g. valid through `expires_on`, invalid on the next UTC date) and test boundary dates/leap days. The machine clock and a declared approver are **not** cryptographic trust anchors.
- Preserve symlink/non-follow traversal and stable reads for policy/baselines/outputs, as applicable. Defend against path traversal, repository rebinding, duplicated target IDs, mistaken same-origin worktree identities and TOCTOU as far as supported; report sequential snapshot limitations honestly.
- Never execute repository content, policy text, links or comments. No external network, model/API credentials, database, GitHub write API or source modifications. Keep error strings sanitized and stable; output must not include raw source bodies/claim values, even if older underlying JSON reports do.
- Deterministic canonical ordering for subjects, fingerprints, waivers, findings and counts. Separate volatile observation date/timing from stable fingerprinting; golden tests should pin date explicitly.
- No false pass from an empty target set, an unconfigured rule family presented as fully covered, missing required receipt/manifest, provider failure, budget-exceeded evaluation, or unknown output version. Preserve definite findings along with independent uncertainty.

## 10. Suggested implementation packages, in order

1. **Reconcile and baseline.** Review Phase 10 fixes/acceptance and current branch. Inventory exact existing evaluator APIs, exit codes and status/coverage fields; write a short design contract and adversarial test matrix. Promote any indispensable review invariant into a test/contract rather than relying on historical review prose.
2. **Typed policy and parsing.** Introduce e.g. `governance_models.py`, `governance_config.py`; strict TOML validation, deterministic normalized types, bounded path/read behavior, policy hash, test fixtures. Document v1 choices, not only an example.
3. **Evaluator adapters.** Introduce e.g. `governance.py`: invoke existing repository check/optional explicit local provider, workspace check and derived check; preserve their actual statuses/qualified identities and no-write assumptions. Create clear coverage obligations and typed failures.
4. **Rule decisions and waivers.** Normalize finding/fingerprint; resolve owner/severity, enforce target coverage, validate exact expiring waivers, aggregate results/exit selection. Test both definitive and uncertain signals in the same invocation.
5. **Rendering, output and metrics.** Introduce e.g. `governance_output.py`, JSON v1/text, bounded serializing/publication, privacy filtering, report comparison and deterministic metrics; golden fixtures. Do not project giant underlying reports verbatim.
6. **CLI and CI recipe.** Add additive Typer sub-app with precise help/exits; produce a portable workflow example and local PR-range reproduction.
7. **Docs and delivery evidence.** Add `docs/governance-contract.md`, phase implementation report, update README/doc map/architecture deferred decisions/current state where **delivered behavior** justifies it; perform staleness sweep without rewriting PRD/history. Run the full gate plus security/CLI smoke tests, then independent review in a separate session.

Do not add a framework, database or dependencies solely for this phase. Follow existing Python 3.12/uv/Typer/pytest/Ruff patterns. Refactor a shared safe file-read/output primitive only when doing so reduces duplicated security logic without destabilizing existing APIs.

## 11. Acceptance and adversarial test matrix

| Area | Minimum proof |
| --- | --- |
| Baseline | Current `HEAD` and Phase 10 acceptance status recorded; Phase 10 output-bound and warning-isolation reproductions rerun; old CLI/schema golden tests unchanged |
| Policy parsing | Unknown/duplicate fields, identifiers, target collisions, booleans, bad dates, overlong strings, malicious root/path, symlink, oversized policy/waiver counts fail deterministically |
| Repository gate | Existing high/medium/low findings mapped correctly; optional exact override visible; `--diff app=BASE..HEAD` uses real local Git diff; original `check` still non-gating |
| Workspace gate | Explicit pin mismatch, mirror divergence, claim disagreement, missing source, uncertainty; repo-qualified identity; no semantics inferred from hash equality; zero checks not a clean pass |
| Derived gate | Observed unchanged/review/inconclusive, stale transitive input, missing receipt, caveats and preserved provenance; no hidden receipt refresh |
| Waiver lifecycle | Exact valid match, changed evidence digest, other repo/target, ambiguous duplicate, expired on boundary, malformed/unused waiver, missing owner/review reference; uncertainty and errors cannot be waived |
| Coverage/gate | Definite failure + independent uncertainty both shown; `fail` vs explicit `warn`; required evaluator disabled/unavailable; no targets; unknown reason/schema fails closed; exit 0/8/9 vs 2/3/4/6/7 |
| Output/safety | Deterministic JSON/text, no literal claim value/root/token/raw task leakage; capped output, no partial stdout/file; no overwrite/no-follow output and input path safety; no repo writes/network |
| Trend | Compatible prior report counts, changed policy/scope/repo ID/schema, corrupt/oversized baseline, changed rule classification; baseline never suppresses current failure |
| Integration | Real disposable PR-like Git history, dirty worktree, repo and workspace fixtures, CI shell exit propagation, Windows limitations disclosed if POSIX tested only |

Run `make check`, focused governance tests, old workspace/derived/integrity suites, `git diff --check`, CLI help and representative end-to-end commands. Record platform/tool versions and **actual** counts in `docs/implementation-reports/phase-11-implementation-report.md`; do not prescribe guessed passing totals. Tests require no network/model keys/external database.

## 12. Review, documentation and release bar

Deliverables:

- Typed code/tests/fixtures plus `context-integrity governance check` and optional external CI recipe.
- `docs/governance-contract.md` with real policy grammar, fingerprint canonicalization/version, statuses, waiver lifecycle, privacy, metric schema, output behavior and trust bounds.
- Updated `README.md`, `docs/README.md`, targeted `docs/architecture.md` decisions/ADR if a genuinely durable choice was made; accurate `docs/current-state.md` and Phase 11 implementation report.
- An **independent** review under `docs/reviews/` with code-linked findings; fix and independently verify before acceptance. Do not replace the independent reviewer with an implementer self-assessment.

**Required handoff/staleness audit:** compare README command examples/status, doc navigation, PRD roadmap, architecture deferred list/Layers 7/28, all Phase 8–10 durable contracts, current-state review debt, CI example, JSON/version references, and actual code. Label each `current`, `stale: fix`, or `historical: retain`; fix active inaccuracies and preserve historical plans/reports as historical evidence. List residual deferred work and old review debt explicitly.

**Stop/reconsider the design if:** governance requires rewriting the integrity/workspace/derived outputs; it can only pass by ignoring unobservable evidence; waivers must be broad or based on unqualified file names; policy relies on an unauthenticated local approver as proof of approval; trend comparison needs implicit persistence; a new provider/network dependency becomes mandatory; or a claimed compliant state exceeds observed rule coverage. Record a focused ADR/architecture decision before expanding scope.

## 13. Independent review focus beyond this plan

The review must independently reconstruct product intent and code behavior, then challenge **the plan itself**: whether the chosen target set is sufficient for useful PR governance, whether default severity/coverage policy causes false passes or false failures, whether fingerprints actually guard changed evidence, whether an operator can game waivers or comparison, whether high-volume results remain bounded, and whether reported metrics mean what readers think they mean. It must inspect unexpected integration seams and security problems, not merely tick off the work packages above. The separate review prompt is deliberately non-exhaustive.

## 14. References and snapshot limits

Primary files: [`AGENTS.md`](https://github.com/jasonkli21/context-integrity/blob/59b90c0/AGENTS.md), [`docs/current-state.md`](https://github.com/jasonkli21/context-integrity/blob/59b90c0/docs/current-state.md), [`docs/prd.md`](https://github.com/jasonkli21/context-integrity/blob/59b90c0/docs/prd.md), [`docs/architecture.md`](https://github.com/jasonkli21/context-integrity/blob/59b90c0/docs/architecture.md), [`docs/workspace-integrity-contract.md`](https://github.com/jasonkli21/context-integrity/blob/59b90c0/docs/workspace-integrity-contract.md), [`docs/derived-context-contract.md`](https://github.com/jasonkli21/context-integrity/blob/59b90c0/docs/derived-context-contract.md), [`docs/reviews/phase-10-independent-review.md`](https://github.com/jasonkli21/context-integrity/blob/59b90c0/docs/reviews/phase-10-independent-review.md), and [`docs/implementation-reports/phase-10-review-fixes-report.md`](https://github.com/jasonkli21/context-integrity/blob/59b90c0/docs/implementation-reports/phase-10-review-fixes-report.md).

This is a design proposal grounded in a repository snapshot, **not** a statement that Phase 11 is already implemented or that Phase 10 is independently accepted. Reconcile the repository again immediately before work begins.
