# Context Integrity — Phase 10 Independent Review

**Review date:** 2026-10-24 (Pacific)
**Repository:** https://github.com/jasonkli21/context-integrity
**Target:** [`c24f15d411d94a3ea61f6ed8efaa042f27acc41b`](https://github.com/jasonkli21/context-integrity/commit/c24f15d411d94a3ea61f6ed8efaa042f27acc41b)
**Verified baseline / parent:** `61ca15782dadff319c6d4ed2422d1d6e82fffd2a`
**Mode:** Independent source review, full offline gate, focused tests, and disposable-repository adversarial probes. No product-code changes or GitHub review submission.

## 1. Verdict and risk summary

**FIX THEN RE-REVIEW.** Phase 10 substantially implements the promised *explicit, local* cross-repository vertical slice. The exact target passes the independently rerun gate (**1,167 tests**) and workspace suite (**96 tests**). The three checks have useful, narrow semantics; identity, source qualification, strict lock decoding, per-repo context compilation, conservative missing-source treatment, and legacy interfaces are supported by code and tests. The implementation does not pretend hashes establish API compatibility or claim truth.

Two **independently reproduced implementation defects** remain:

| ID | Severity | Finding | Acceptance |
| --- | --- | --- | --- |
| **F10-001** | **High** | Repeated claim checks amplify bounded config values into unbounded-size reports | **Blocker:** bound projection/memory work |
| **F10-002** | **Medium** | An unrelated failed explicit read contaminates a later claim's inventory coverage and signal | **Blocker:** isolate warning scopes |

Separately, **G10-001** is a plan-level freshness gap: a clean, *committed* edit to a claim's dependency can coexist with `declarations_agree` and `aligned_observed`. The implementation honestly records `dependency_history_not_pinned`; this is **not** evidence of verified claim freshness and is not treated as a violation of the documented narrow comparison rule. **G10-002** concerns sensitive literal claim values in ostensibly body-free output. These deserve clear consumer-facing safeguards but should not be confused with the two demonstrated code defects.

Acceptance confidence is **high for the two reproduced code paths and the test gate**, moderate for the remainder of the local POSIX safety surface, and limited for concurrency, malicious-scale Git enumeration, external provider integration and actual schema semantics. No semantic/atomic/cross-repo-graph assurance is claimed.

## 2. Scope, evidence and exact verification

The submitted link's visible label named `61ca157…`, but its destination was `c24f15d…`. `git log` and the supplied prompt resolve this: `61ca157…` is the explicitly named **pre-Phase-10 baseline**, whereas `c24f15d…` is the actual Phase 10 delivery. I reviewed **`c24f15d…`**, with no post-target changes imported. `main` and `origin/main` pointed there. `git status --porcelain=v1` was empty after review. The temporary clone was not edited for fixes; transient adversarial fixtures were created elsewhere.

`git diff --stat 61ca157..c24f15d`: **21 files**, 3,759 insertions, 73 deletions, including four new workspace modules, shared acquisition/inventory hooks, CLI, plan, workspace contract, report, goldens and two test files. `git diff --check 61ca157..c24f15d` passed with no output. No dependency-lockfile or CI-workflow change is in this commit.

**Authority and intended behavior independently checked before grading against the plan:** complete `AGENTS.md`; `docs/prd.md` §§4, 17–21, 29–30; `docs/architecture.md` §§2, 6, 14–22, 29–34 and Phase 8–10 addenda; `docs/derived-context-contract.md`, `docs/evidence-contract.md`, `docs/architecture-integrity-contract.md`. `docs/adr/` contains only an index/template; there are no accepted ADR files to reconcile. Then I read `docs/plans/phase-10-implementation-plan.md`, the attached independent review prompt, `docs/implementation-reports/phase-10-implementation-report.md` and the material tests/fixtures. The report's test claims were treated as implementation-session assertions until independently rerun.

**Affected code inspected:** `workspace_models.py`, `workspace_config.py`, `workspace.py`, `workspace_output.py`; shared `acquisition.py`, `inventory.py`, `repository.py`, `configuration.py`, `claims.py`, `contracts.py`, `compiler.py`, `derived_models.py`, `derived_output.py`, `cli.py`, and relevant rendering/model/provider contracts. Phase 8 graph normalization and the Context Engine adapter were checked at their architectural boundary and documented contracts, not exhaustively re-reviewed internally: Phase 10 deliberately does not invoke them.

**Commands/results — Linux, Python 3.12.14, uv 0.13.4, pytest 9.1.1:**

```text
git rev-parse HEAD
  c24f15d411d94a3ea61f6ed8efaa042f27acc41b
git status --porcelain=v1
  (empty)
git diff --check 61ca15782dadff319c6d4ed2422d1d6e82fffd2a c24f15d411d94a3ea61f6ed8efaa042f27acc41b
  (passed, no output)
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check
  Ruff lint passed; formatting passed (103 files); 1,167 passed in 16.12s; 0 skipped
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 uv run pytest -q tests/test_workspace.py tests/test_workspace_cli.py
  96 passed in 5.49s; 0 skipped
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 uv run context-integrity workspace --help
  exit 0; check and compile commands present
```

The first offline gate was blocked because its cache lacked pinned Ruff; dependencies were installed into the disposable checkout with `uv sync --frozen`, then the commands above passed offline. That one-time bootstrap used package downloads; **the tested CLI itself did not require network, model or provider**. The author's macOS/Python 3.12.13 results are distinct from these Linux results.

Independent `CliRunner` probes exercised actual JSON `workspace check` for aligned pin/mirror/claim rules, committed dependency drift, and JSON `workspace compile` with two targets. In the normal fixture, `check` returned `aligned_observed` and all three findings `aligned`; `compile` returned context schema v1, two complete targets, task digest with **no raw task text**, and accurately retained review status after a producer change. The other independent probes are described under individual findings. No production file was altered.

## 3. Observed architecture and trust boundary

| Surface | Delivered and traced | Meaning/limit |
| --- | --- | --- |
| Workspace input | Strict bounded TOML v1 (`workspace_config.py:48–116`), 2–8 explicit aliases/expected IDs; root discovery and collision checks (`workspace.py:231–262`) | No implicit discovery, no absolute-root exposure; no-origin identity is location-dependent; same-origin clones intentionally collide |
| Qualified references | Repo alias + observed repository ID + repo-relative path or claim ID (`workspace_models.py:23–44`, output projectors) | Same-named paths and claim IDs in two repos do not merge |
| Consumer lock | Strict JSON v1 decoder, duplicate-key rejection, ID/path binding, producer raw-byte SHA comparison (`workspace_config.py:120–147`, `workspace.py:174–205`) | Editable consumer declaration, **not** signed attestation; does not prove consumer implementation use |
| Mirror | Descriptor-safe, stable raw-byte observations; exact SHA equality/mismatch (`workspace.py:64–101,265–295`) | No schema/semantic compatibility claim |
| Claims | Existing configured `ClaimRecord`s, source/dependency revisions, conservative dirty/unavailable handling (`workspace.py:135–172,298–319`) | Values are exact declarations and stay `unverified`; no historical accepted dependency pins |
| Context | Local `resolve_contract`/`compile_context` for each target (`workspace.py:208–228`); full per-repo decisions/revisions, independently chosen budgets (`workspace_output.py:137–255`) | Index only, no source bodies, global authority rank, provider query or workspace receipt |
| Output | Separate check/context JSON v1; complete escaped JSON also embedded in text; descriptor-relative exclusive saved outputs outside roots (`workspace_output.py:270–294`) | No rewrite of locks/receipts; observations sequential, output not a durable freshness receipt |

Existing single-repo config v1–v8, compiled JSON v3, integrity JSON v2, and derived receipt/result v1 remain separate. The suite covered old commands and targeted tests confirmed compiled-v3 task behavior and integrity-v2 schema. Phase 9 receipts are **not** silently extended across roots. Normative policy stays in Context Integrity; Codebase Intelligence's repository-scoped, descriptive relation/provider interfaces were not promoted into cross-repo proof. No winning repository is chosen by order, alias, recency or provider rank.

## 4. Prioritized findings

### F10-001 — High — Repeated checks permit disproportionate report/memory amplification

**Class:** Implementation defect; additionally exposes a missing output resource bound in the plan.
**Location:** [`configuration.py:161–179`](https://github.com/jasonkli21/context-integrity/blob/c24f15d411d94a3ea61f6ed8efaa042f27acc41b/src/context_integrity/configuration.py#L161-L179), [`workspace.py:135–172`](https://github.com/jasonkli21/context-integrity/blob/c24f15d411d94a3ea61f6ed8efaa042f27acc41b/src/context_integrity/workspace.py#L135-L172), [`workspace_output.py:40–56`](https://github.com/jasonkli21/context-integrity/blob/c24f15d411d94a3ea61f6ed8efaa042f27acc41b/src/context_integrity/workspace_output.py#L40-L56), [`workspace_output.py:90–133`](https://github.com/jasonkli21/context-integrity/blob/c24f15d411d94a3ea61f6ed8efaa042f27acc41b/src/context_integrity/workspace_output.py#L90-L133), [`workspace_output.py:270–275`](https://github.com/jasonkli21/context-integrity/blob/c24f15d411d94a3ea61f6ed8efaa042f27acc41b/src/context_integrity/workspace_output.py#L270-L275).

**Reproduction, executed in new independent Git fixture roots:** Replace each repo's explicit claim `value` with a 100,000-character string. The unchanged three-check manifest renders **210,179 bytes** versus **10,179 bytes** before replacement. Add 19 further uniquely ID'd `claim_match` checks referencing that same pair: still valid manifest, **22 total checks**, and JSON expands to **4,134,165 bytes** with `status=aligned_observed`. No new source data was observed for these repeated references. The full 128-check allowance and two near-5-MiB configuration values permit on the order of **1 GiB** serialized repetition before accounting for other fields. That maximum is an extrapolation from documented limits and the measured linear duplication, **not** an attempted 1-GiB execution.

**Expected:** The advertised finite workspace observation/budget model should also bound materialized reports or refuse oversized results safely, especially for local untrusted repository configuration. **Observed:** `ClaimRecord.value` has no small length bound; every finding emits the entire value twice, JSON is materialized at once by `canonical_json`, and there is no output-byte/projection-work cap. Reading each config under 5 MiB and limiting checks to 128 does not bound output to a practical size.

**Impact:** An otherwise valid workspace can cause high memory use, enormous stdout/files and disruptive agent/CI consumers without breaching any input cap. The repeated values can also amplify sensitive declared metadata in logs. **Root cause:** Bounds are on inputs/observations, not on multiplicity in the projection.

**Smallest safe fix:** Define a conservative overall projection-byte/work ceiling and preflight it **before building the giant JSON**, or introduce a bounded, deduplicated claim-evidence representation under a deliberately versioned output contract. Do not silently truncate equality evidence and call the report complete. Emit a sanitized typed error/explicit uncertainty if the bound prevents evaluation, with no partial file. **Regression:** One large claim + many distinct duplicate-pair checks, exact bound/over-bound behavior for text/JSON/stdout/file, no emitted secret snippets or partial output, and unchanged small goldens.

### F10-002 — Medium — Unrelated rule warning changes later claim's result

**Class:** Implementation defect; unexpectedly couples independent observations.
**Location:** [`workspace.py:64–100`](https://github.com/jasonkli21/context-integrity/blob/c24f15d411d94a3ea61f6ed8efaa042f27acc41b/src/context_integrity/workspace.py#L64-L100), [`workspace.py:103–172`](https://github.com/jasonkli21/context-integrity/blob/c24f15d411d94a3ea61f6ed8efaa042f27acc41b/src/context_integrity/workspace.py#L103-L172), [`inventory.py:139–158`](https://github.com/jasonkli21/context-integrity/blob/c24f15d411d94a3ea61f6ed8efaa042f27acc41b/src/context_integrity/inventory.py#L139-L158).

**Reproduction, executed:** In the synthetic two-repo fixture, name the pin check `a_pin`, the claim check `z_claims`, and remove `api/spec/api.json` (which is unrelated to the claim's declaration and `docs/architecture.md` dependency). Because checks are sorted by ID, `a_pin` first appends a `candidate_metadata_failed` warning to the shared `RepositoryContext.warnings`. The later inventory snapshots that warning as `manifest.warnings`; `Workspace.claim()` therefore adds `claim_inventory_incomplete`. Result:

```text
With unrelated missing a_pin:  z_claims = not_established
  reasons: claim_inventory_incomplete, claims_unverified, dependency_history_not_pinned
Remove just the a_pin rule:   z_claims = aligned
  reasons: declarations_agree, claims_unverified, dependency_history_not_pinned
```

**Expected:** Removing/adding an unrelated check must not change evidence completeness for a fully observed claim. The missing pin should still report its own review signal; legitimate inventory warnings should still affect claims. **Observed:** The claim's signal depends on an unrelated check and its lexicographic ID. This is a false *inconclusive* rather than false *aligned*, but it makes coverage and per-rule conclusions unreliable. Context target `coverage`/warning lists can be similarly polluted.

**Root cause:** Explicit observations, Git-discovery warnings and inventory warnings mutate/consume one shared list, without scoping warning provenance to the operation that generated it.

**Smallest safe fix:** Give each inventory an operation-local warning collector (or snapshot baseline and return only warnings produced by Git discovery + that inventory); leave explicit-source warnings attached only to their own findings. Avoid merely suppressing all warnings: missing inventory dependencies must still block claims. **Regression:** Reorder/rename rules; add/remove missing unrelated mirror/pin; assert claim signal, claim coverage and target inventory coverage invariant, while the missing rule remains a review finding.

## 5. Independent plan adequacy and gap review

I reconstructed five actual end-user journeys from the PRD/architecture, without treating Phase 10's proposed narrow plan as the ultimate product definition:

1. **API producer update → consumer review:** The lock detects exact producer-byte movement. It cannot show whether the consumer actually uses that lock; the caveat `consumer_implementation_not_verified` is honest. **Valid deferral** of cross-repo code usage analysis and full compatibility checking, not a claimed proof.
2. **Two repos mirror a schema:** Equal/different bytes are observable and correctly qualified. **Valid deferral** of semantic schema parsing; equal bytes establish only the declared exact mirror invariant.
3. **One product policy declared in two repos:** Exact value comparison works, but a dependency revision can move after the declaration and leave a green comparison. **G10-001 — Plan gap**, discussed below. The original plan knowingly chose current declarations over historic validity; the user-facing status still invites overinterpretation.
4. **Agent builds cross-repo task context:** The index preserves per-repo selected sources, required/excluded decisions, policies, budgets and task hash. It does not use workspace checks to gate selections, and task text does not drive semantic relevance while providers are disabled; those separations are visible. **Valid deferral** of multi-repo ranking, body bundling and provider graph fusion. A future consumer must inspect both `selection_complete` and `checks_status`, not only `status`.
5. **Agent handoff saved for reuse:** Output is root-free and explicitly not a fresh cross-repo Phase 9 receipt. Mutable pins and sequential observation remain documented. **Valid deferral** of a signed/durable cross-repo DAG, but handoff consumers must not treat a saved index as current evidence without rerunning it.

**G10-001 — Medium plan gap, not a rule-engine misimplementation: dependency history is unpinned.** An independently constructed test changed `api/docs/architecture.md` **and committed it**, leaving `api` Git-clean and the configured claim unchanged. The `claim_match` still signaled `aligned`, with reasons `declarations_agree`, `claims_unverified`, `dependency_history_not_pinned` (the separate mirror correctly signaled review). This follows [`workspace.py:165–172,298–317`](https://github.com/jasonkli21/context-integrity/blob/c24f15d411d94a3ea61f6ed8efaa042f27acc41b/src/context_integrity/workspace.py#L165-L172) and the explicit v1 contract; it is *true declaration equality*, not freshness. Nevertheless, an agent consuming top-level `aligned_observed` could miss the dependency-history limitation. The smallest near-term improvement is an explicit structured `claim_dependency_freshness: not_established` (or equivalent per-check dimension and machine-readable top-level limitation) that cannot be confused with alignment; a future optional accepted dependency-revision pin can graduate this to checkable freshness. Test a clean committed dependency edit, not only dirty worktrees. Do **not** silently turn all equal claims into semantic truth or re-version Phase 9 receipts.

**G10-002 — Medium plan/privacy gap: structured claim literals remain verbatim.** The allowlisted claim projector includes `declaration.value` and other arbitrary user-maintained strings, even though source bodies and task text are withheld. A CLI probe with `value = "ACCESS_TOKEN_SENSITIVE_VALUE"` confirmed that literal appears in JSON. This is intentional and documented in `docs/workspace-integrity-contract.md:239–243`, not a covert network transmission or a false claim that *all* source-derived strings are absent. Still, an exported report can carry credentials/prompt-injection-like metadata into an agent log. Consider an opt-in redacted/digest-only projection or a prominent CLI documentation warning; regression-test no task/raw source-body echo and explicit metadata handling. Preserve the ability to diagnose claim mismatches without defaulting to indiscriminate string dumping.

**Implemented deviations/strengths:** New workspace outputs are stricter than the plan's tentative requirement: saved files must be outside **every** participating root. Constructor/schema boundaries, duplicate-key rejection, source/lock identity binding, no-follow source reads and conservative empty-check status are sound. No accepted ADR was bypassed. No material evidence supports treating the intentional lack of cross-repo structural graphs, signed locks, global authority, semantic analysis, generated-artifact DAGs, CI enforcement or auto-refresh as Phase 10 implementation defects; these are **valid deferrals** conditioned on truthful output naming and caveats.

## 6. Adversarial scenario matrix

“Probe” below means a reviewer-built disposable fixture/CLI run. “Suite” means the project's test assertion was inspected and **independently rerun**; it is weaker than a separate novel fixture. “Unverified” means no independent execution establishing the broader property.

| Scenario | Result | Evidence / qualification |
| --- | --- | --- |
| Valid two-repo pin, byte mirror, paired claim | **Pass — probe** | Actual CLI JSON baseline `aligned_observed`; all three checks `aligned` |
| Committed upstream claim dependency revision with clean Git state | **Gap — probe** | Claim still `aligned`, unconditional `dependency_history_not_pinned`; G10-001 |
| Source staged/unstaged edit, reversion with same HEAD | **Pass — suite** | `test_dirty_contract_content_unchanged_head` and related workspace assertions |
| Repeated same claim with large declaration value | **Fail — probe** | 100K-character pair ×20 yields 4,134,165-byte JSON; F10-001 |
| Failed unrelated explicit check before claim inventory | **Fail — probe** | Claim signal changes solely with pin presence/ID; F10-002 |
| Wrong expected ID, same-origin checkout, nested/root alias | **Pass — suite** | `test_repository_binding_and_boundaries`, `test_sibling_roots_and_local_identity` |
| Sibling `../` roots; no-origin identity | **Pass — suite** | Accepted, with nonportable identity limitation |
| Same relative filename/claim ID in both repos | **Pass — suite/probe** | Qualified source/claim observations retained; no namespace collision |
| Lock wrong producer/path; duplicate key, unknown version, oversize | **Pass — suite** | Strict parser and binding tests; mutable-lock authenticity is outside threat model |
| Empty, equal, differing, missing, unreadable, symlinked/oversize file | **Pass — suite** | Exact-byte and conservative source-state tests; no schema meaning implied |
| Claim value/scope mismatch, superseded/missing dependency, unknown inventory | **Pass — suite** | Incomparable/uncertain handling; clean historic edits remain G10-001 |
| Definite missing source plus independent unobservable source | **Pass — suite** | Review precedence with both reasons retained |
| Empty checks / no context targets | **Pass — suite** | No global compliance; compile requires targets |
| Two context targets; one insufficient budget or provider-backed requirement | **Pass — suite/probe** | Independent status, selection completeness and checks status retained |
| Sensitive task literal | **Pass — probe** | Raw task absent; digest present. Config claim literal still disclosed under G10-002 |
| Stable source reads, unsafe output parents, no overwrite, rollback | **Pass — suite** | POSIX synthetic tests; no general atomic-snapshot proof |
| Input permutations / repeated deterministic JSON / text parity | **Pass — suite** | Golden fixtures, declaration-order and text-parity tests; full adversarial property fuzzing unverified |
| Full 128 checks with near-5-MiB values; memory ceiling | **Unverified high-scale execution** | Measured linear amplification + allowed bounds establish F10-001 without intentionally allocating ~1 GiB |
| Repository changes during multi-repo observation; manifest root swap race | **Unverified** | Sequential/not atomic by contract; stable per-file reads only |
| Cross-repo Context Engine graph or semantic API conformance | **Not implemented — valid deferral** | Existing provider is repository-scoped; no invented cross-repo proof |
| Legacy config v1–v8, compiled v3, integrity v2, Phase 9 receipts | **Pass — suite** | Full gate and explicit CLI/config compatibility tests; no exhaustive old-receipt migration matrix rerun separately |

## 7. Documentation staleness sweep

**Current navigation largely agrees with delivery.** `README.md`, `docs/README.md`, `docs/current-state.md`, `docs/workspace-integrity-contract.md`, the Phase 10 implementation report, and the Phase 10 plan point to the right phase and explicit schema v1. `AGENTS.md`, `CLAUDE.md`, `.github/copilot-instructions.md` and `docs/ai/README.md` preserve singular canonical instructions and history/implementation separation. `docs/plans/README.md`, `docs/implementation-reports/README.md` and `docs/reviews/README.md` correctly explain artifact roles. No stale assertion was found claiming Phase 10 is wholly absent in the active status pages. The report's macOS gate count is preserved as historical author evidence, while the independent Linux rerun is recorded here.

| Location | Observation | Minimal correction / acceptance impact |
| --- | --- | --- |
| `docs/architecture.md:1614–1638` | Still describes a workspace as “future” in the conceptual §29, although a narrowly declared workspace is now delivered in the later Phase 10 addendum | Qualify “future” as “original architecture concept; explicit v1 now delivered, graph federation later.” **Low, nonblocking** |
| `docs/workspace-integrity-contract.md:248–258`; Phase 10 implementation report “bounds” | Accurately limits read work but does not mention projection amplification under repeated checks | Add output bound/guard and clarify size guarantee when F10-001 is fixed. **Blocker to the fix's documentation**, not an independently stale Phase 10 status claim |
| `docs/workspace-integrity-contract.md:185–195,226–246` | `dependency_history_not_pinned` and literal claim metadata are documented, but machine consumers may read only the aggregate alignment status | Add prominent structured freshness distinction and safe-export metadata warning (G10-001/002). **Nonblocking** if Phase 10 contract remains explicitly narrow |
| `docs/current-state.md:6,60–63` | Correctly says Phase 10 independent review pending and Phase 4/7/8/9 independent work not closed | Keep pending status until fixes/re-review; update review navigation once this independent handoff is accepted. **No staleness defect** |
| `docs/evidence-contract.md:123–124`, `docs/architecture-integrity-contract.md:151–152`, `docs/derived-context-contract.md:219–221` | Older scoped boundaries say no cross-repo *provider*, *Phase 8 rule*, or *Phase 9 chain* support; those statements remain true even after workspace v1 | Preserve precise historical/surface-specific language; **no rewrite needed** |
| `docs/prd.md` and prior plans/reviews | Broad Phase 10 vision and historical expectations exceed this deliberately bounded delivered slice | Preserve as product intent/history; do not falsify past plans or equate them with delivery |

The checked-in golden fixtures do match the executed baseline tests. `docs/reviews/README.md` does not yet index a Phase 10 review because none had been committed at the target; that absence is not implementation staleness. No documentation or repository file was edited by this review.

## 8. Residual risks and explicit unverified areas

- **Mutable trust:** Consumer locks and workspace manifests are unsigned local declarations. The lock binds producer ID/path/hash but neither authenticates the producer nor proves consumer code usage; same-origin checkouts are deliberately rejected. A matching pin is a byte/revision observation only.
- **Freshness:** No transitive cross-repo Phase 9 receipt or historical claim dependency pin. The report is a sequential index, not an atomic snapshot or durable freshness certificate. Source files can change after checking; no end-of-command reobservation occurs. Per-file stability checks reduce, but do not eliminate, races.
- **Coverage:** Unknown Git metadata and inventory warnings are exposed; however F10-002 shows a scope-isolation bug. Dependency and provider evidence remain limited. Per-repo provider-backed code contexts can be incomplete because workspace provider calls are intentionally disabled.
- **Privacy:** Raw tasks, source bodies, absolute roots and stderr were absent in observed output; original structured claim fields are not redacted (G10-002). No upload or LLM call is part of the workspace command.
- **Unverified tests:** No separate multi-threaded filesystem race stress, scale-to-maximum 1-GiB report execution, non-POSIX platform run, real multi-repo API schema migration, real Context Engine integration, or formal parser fuzzing. Git listing and existing compiler feasibility search retain inherited limits/complexity. These are not silently claimed as passed.
- **Prior reviews:** `61ca157` reports Phase 9 fixes and 1,071 offline tests, but Phase 9 **fresh independent re-review remains pending**. So do Phase 8 fresh re-review, Phase 7 fresh independent review and Phase 4 final independent verification. This review neither closes those findings nor penalizes Phase 10 for truthfully reporting them.

## 9. Prioritized fix handoff for a separate session

1. **F10-001 (blocking):** Add a deterministic, pre-render projection output/work bound. Avoid materializing arbitrary repeats into a giant string before noticing oversize. Define sanitized error/no-partial-output semantics; prove 128 repeated pairs and near-limit values cannot exhaust memory. Preserve small-case check/context v1 structures and existing exit conventions; version any incompatible schema change deliberately.
2. **F10-002 (blocking):** Separate warning channels for explicit file observations, repository discovery and inventory acquisition. Preserve real inventory-incomplete uncertainty; ensure per-claim/target status is invariant to unrelated check IDs/order/presence. Add targeted regression fixtures with missing pin/mirror and fully healthy claims.
3. **G10-001 (plan gap / recommended):** Make declaration equality and historical dependency freshness separable for machine consumers. Keep claims `unverified`, do not fabricate historical pins or upgrade Phase 9 receipt v1. Test a clean committed dependency edit under unchanged explicit claims.
4. **G10-002 (recommended):** Document that claim literals can contain secrets; consider a bounded redacted/digest-only export option for downstream handoffs. Keep rule comparison lossless internally; test secret-like values without raw task or arbitrary source-body output.
5. Update workspace contract/current-state/review index as appropriate **after** fixes and independent verification. Do not expand into semantic compatibility engines, cross-repo graph IDs, signing, governance, automatic lock rewrite or generated-artifact DAGs under the guise of this fix pass.

**Re-review acceptance:** Repeat full `make check`, 96+ focused tests and a new test for each F10 finding. Independently rerun the two precise counterexamples, confirm bounded JSON/text/file behavior and unrelated-rule invariance, inspect any schema/exit/docs changes, and verify no regression to pin/mirror/claim, context selection and legacy receipts. Treat plan-gap remediation separately and honestly if deferred.

## 10. Final acceptance checklist

| Phase 10 promise / inherited invariant | Result at `c24f15d` |
| --- | --- |
| Explicit strict workspace manifest v1, identity binding, duplicate/nested checks | **PASS** — code + test gate |
| Qualified source/claim refs and safe per-repo file observations | **PASS** — code + test gate |
| Strict consumer lock v1, producer path/ID binding, byte pin drift detection | **PASS** — code + test gate |
| Mirror bytes equality/difference and missing/unsafe evidence distinction | **PASS** — code + test gate |
| Claim type/subject/predicate/scope/value comparison, unverified validity | **PASS for literal comparison**, but **FAIL independent warning isolation** (F10-002) |
| Reliable coverage/reasons under mixed unrelated checks | **FAIL** — F10-002 |
| Finite resource consumption for all accepted valid workspace inputs | **FAIL** — F10-001 output amplification |
| Context v1 per-repo contracts, exclusions, budgets, qualified decisions and digest-only task | **PASS** — code + tests; no global relevance/atomic claim |
| Safe new-file-only saved output, no root writes, sanitized errors/exits | **PASS in exercised POSIX tests**; high-scale and concurrent races unverified |
| Legacy config v1–v8, compiled v3, integrity v2, receipt/result v1 compatibility | **PASS in full suite**, no deliberate migration |
| Source-derived metadata sensitivity handled for exported reports | **PLAN GAP / LIMITED** — G10-002 |
| Claim freshness after clean committed upstream change | **NOT ESTABLISHED** — G10-001, expressly documented caveat |
| Product-wide semantic compatibility, cross-repo structural graphs, transitive derived receipts, CI enforcement | **VALID DEFERRALS**, not delivered or claimed |
| Independent acceptance of Phase 10 | **FAIL pending separate fix/re-review** |

**Overall recommendation: FIX THEN RE-REVIEW.** Do not mark Phase 10 accepted on the strength of 1,167 passing tests alone. Its core architecture is useful and largely faithful to the narrow plan, but the two independently reproduced implementation defects should be corrected before using these outputs as reliable agent handoff/CI inputs.
