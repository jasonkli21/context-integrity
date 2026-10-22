# Context Integrity — Phase 9 Independent Review

**Review date:** 2026-10-21 (Pacific)
**Target:** [`eedc972a53bb568291bda7a876189aefe6c1ad3f`](https://github.com/jasonkli21/context-integrity/commit/eedc972a53bb568291bda7a876189aefe6c1ad3f)
**Verified parent/baseline:** `917a9d318824d4fa67a7206dd3784068dabc7a21`
**Review mode:** Independent source inspection, full offline suite, and separately constructed adversarial runtime probes. **No repository changes or GitHub review submission.**

## 1. Verdict and risk summary

**Verdict: FIX, THEN INDEPENDENT RE-REVIEW.** The core Phase 9 implementation is substantial and well bounded. The actual target commit passes the full test gate independently (**1,067 tests**) and the Phase 9-focused tests (**102 tests**). Direct source edits, artifact edits, transitive *explicit receipt* chains, provider uncertainty, strict decoding, and no-overwrite output handling have credible coverage. Existing config and JSON contracts were not deliberately advanced.

However, a high-impact agent-workflow counterexample remains: a handoff that names an already-generated summary as an ordinary file dependency reports `unchanged_observed_inputs` after that summary's primary source changes. The tool already identifies the intermediary as `generated_derivative` but does not treat the missing receipt link as material uncertainty. The result is literally true for the declared summary *bytes*, but dangerously easy to interpret as a usable revalidation of the handoff. This gap exists in both the plan's usability assumptions and the implementation.

| Severity | Count | Findings |
| --- | ---: | --- |
| Critical | 0 | — |
| High | 1 | F9-001: unlinked derived-source dependency yields false operational freshness |
| Medium | 2 | F9-002: compiler logic changes can evade version/selection checks; F9-003: empty valid compile is misclassified as incomplete provenance |
| Low | 1 | F9-004: exhausted byte budget is mislabeled `unobservable` |

**Confidence:** High for the four identified paths (three independent probes, one static code/version trace); high for test gate results; moderate for exhaustive security and performance assurance. Provider replay, concurrency stress, non-POSIX filesystem behavior and actual model-semantic validation were **not** independently exercised and are not claimed to pass.

## 2. Scope and verification provenance

### Baseline and examined material

- Checked out the **exact target** in a separate temporary clone, not the evolving `main` branch. `git rev-parse HEAD` returned `eedc972a53bb568291bda7a876189aefe6c1ad3f`; `git status --short` was empty before/after verification; recent history is `eedc972` → `917a9d3` → `9f78278` → `cdee5be` → `c29c14b`.
- `git diff --stat 917a9d3..eedc972`: **18 changed files**, including `derived.py`, `derived_models.py`, `derived_output.py`, CLI, bounded acquisition/inventory hooks, contract/current-state/architecture docs, implementation report, and two test files.
- Instructions and product: `AGENTS.md`, `docs/current-state.md`, `docs/README.md`, full in-repo `docs/plans/phase-9-implementation-plan.md`, supplied independent review prompt, `docs/prd.md` (especially §20 and roadmap), `docs/architecture.md` (canonical/derived and Phase 9 sections), `docs/evidence-contract.md`, `docs/architecture-integrity-contract.md`, `docs/derived-context-contract.md`.
- Implementation and relevant surrounding contracts: `src/context_integrity/{derived.py,derived_models.py,derived_output.py,cli.py,acquisition.py,inventory.py,compiler.py,models.py,configuration.py,contracts.py,authority.py,repository.py,evidence.py,classification.py,__init__.py}`; `tests/test_derived.py`, `tests/test_derived_cli.py`, their fixtures, provider-adapter test support, and related compiler tests.
- Documentation/navigation: root `README.md`, `AGENTS.md`, `CLAUDE.md`, `.github/copilot-instructions.md`, `docs/{README.md,ai/README.md,current-state.md,prd.md,architecture.md,evidence-contract.md,architecture-integrity-contract.md,derived-context-contract.md}`, `docs/{plans,implementation-reports,reviews}/README.md`; Phase 9 report and Phase 8 review/fix state. Phase 8 remediation's **fresh independent re-review is still pending**; its implementation report alone does not establish acceptance.
- No separate Phase 9 implementation prompt was committed at this target. The in-repo plan and attached review prompt were available. The review does not presume a hidden implementation prompt was inspected.

### Commands actually executed

```text
git rev-parse HEAD                             -> eedc972a53bb568291bda7a876189aefe6c1ad3f
git status --short                             -> empty
git log -5 --oneline                          -> eedc972, 917a9d3, 9f78278, cdee5be, c29c14b
git diff --stat 917a9d3..eedc972             -> 18 changed files
git diff --check 917a9d3..eedc972            -> no findings

UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 \
  uv run pytest -q tests/test_derived.py tests/test_derived_cli.py
                                             -> 102 passed in 4.40s

UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check
                                             -> Ruff passed; format check passed
                                             -> 91 files formatted; 1,067 passed in 10.81s
```

The first offline attempt could not find locked `ruff` in the local cache. The locked dependencies were then installed into the **temporary checkout**, after which the focused and full suites completed offline. Runtime here was **Linux/Python 3.12.14**, whereas the author report claims macOS/Python 3.12.13; do not conflate the two execution environments. The author's own counts and test claims were not accepted as evidence until rerun.

Three additional **independent, transient temp-directory probes** were executed without changing repository files:

1. A generated-summary/ordinary-dependency handoff (F9-001).
2. A complete compiled result whose contract legitimately selects zero sources (F9-003).
3. A Reader with one byte remaining in the 64 MiB graph budget (F9-004).

The source-change-to-compiler-version gap (F9-002) was established by static code/commit-history trace; it was not tested by modifying the reviewed package. No path outside temporary test fixtures was written for adversarial verification.

## 3. Observed implementation and architecture alignment

| Area | Observed delivery | Boundaries / qualifications |
| --- | --- | --- |
| Receipt contract | Independent `derived_receipt_schema_version=1`, `derived_result_schema_version=1`; strict dataclasses, exact keys, duplicate-key rejection, canonical JSON, SHA256 byte pins and repo identity | Locally writable declarations, **not** signed/authenticated attestations; printable ASCII paths only |
| Manual workflow | `derived capture ARTIFACT ROOT --depends-on PATH --upstream-receipt RECEIPT --receipt-output FILE`; `derived check RECEIPT ROOT --format text\|json [--output FILE]` | No auto-extraction of source dependencies or automatic parent-receipt linking |
| Statuses | `unchanged_observed_inputs`, `review_required`, `inconclusive`; deterministic reason codes; definite changes dominate uncertainty | Unchanged pins do **not** mean truthful text or complete provenance |
| Compiler integration | `compile --format json --output ... --receipt-output ...`; artifact remains compiled-context **schema v3**; pins selected typed inventory **and provider** decisions | No provider replay; any provider context causes inconclusive without a stronger observed change |
| Selection context | Config hash (including absence), contract/policy hashes, selected source bytes, whole inventoried document-universe fingerprint, task digest, effective budget, compiler version | Does not rerun selection; does not reliably identify unversioned compiler-code changes (F9-002) |
| Transitive graph | Explicit receipt-edge/artifact pins; memoization, cycle and identity checks; original upstream reasons propagate | No transitivity when a derivative is listed merely as an ordinary file (F9-001) |
| I/O / resources | Descriptor-relative no-follow reads; 5 MiB sources, 1 MiB receipts, 64 MiB/4,096 graph read budgets, 128 receipts/16 levels, exclusive root-local outputs, ordinary-error rollback | Sequential, not atomic repository snapshots; pair publication not power-loss atomic; global Git enumeration not fully bounded |
| Compatibility | Config v1–v8, inventory v1, claim/contract surfaces, compiled v3 and integrity v2 preserved; Context Engine remains optional via public adapter | No DB, CI waiver/enforcement, cross-repository policy, semantic model call, LLM validation or automatic pin renewal |

The architecture is appropriately narrow: canonical input documents are still canonical, generated artifacts remain rebuildable caches, selected provider code is descriptive evidence rather than authority, no new global authority scalar is introduced, and the Phase 10/11/12 capabilities have not been dragged forward. Phase 9's first-class compiler receipt is built from typed `CompiledSourceDecision`s, which is materially better than assuming `CompiledContext.dependencies` is the only relevant provenance source (even though the current compiler already includes provider-selected sources in that tuple).

## 4. Findings (ordered by severity)

### F9-001 — High — Ordinary file pins bypass known derived-context transitivity

**Class:** Implementation defect + plan/usability gap + documentation gap.
**Evidence:** [`derived.py:187–199`](https://github.com/jasonkli21/context-integrity/blob/eedc972a53bb568291bda7a876189aefe6c1ad3f/src/context_integrity/derived.py#L187-L199), [`derived.py:228–275`](https://github.com/jasonkli21/context-integrity/blob/eedc972a53bb568291bda7a876189aefe6c1ad3f/src/context_integrity/derived.py#L228-L275), [`derived.py:428–467`](https://github.com/jasonkli21/context-integrity/blob/eedc972a53bb568291bda7a876189aefe6c1ad3f/src/context_integrity/derived.py#L428-L467), [`derived-context-contract.md:20–26`](https://github.com/jasonkli21/context-integrity/blob/eedc972a53bb568291bda7a876189aefe6c1ad3f/docs/derived-context-contract.md#L20-L26).

**Independent reproduction (executed):** In a temporary non-Git repository:

1. `AGENTS.md` has policy v1. `docs/generated/summary.md` summarizes it; `docs/handoff.md` relies on that summary.
2. Capture A for `docs/generated/summary.md`, explicitly dependent on `AGENTS.md`, with receipt `docs/a.json`.
3. Capture B for `docs/handoff.md` using **only** `--depends-on docs/generated/summary.md`, with receipt `docs/b.json` (a natural way to name the handoff's immediate input). Do not add `--upstream-receipt docs/a.json`.
4. Change `AGENTS.md` to policy v2, leaving summary and handoff bodies unchanged.

Observed:

```text
B declared source authority: generated_derivative
A: review_required          [declared_inputs_not_semantic_validation, source_changed]
B: unchanged_observed_inputs [declared_inputs_not_semantic_validation]
```

**Expected:** The checker cannot assume the generated summary's upstream context is current. With no linked parent receipt, the downstream handoff should at minimum be **inconclusive with a named unlinked-derived-source reason**; when a matching receipt is linked, the upstream `review_required` must propagate (already supported).

**Actual/impact:** The capture path classifies the summary as an inventory source and stores its `generated_derivative` authority; evaluation tests its unchanged byte hash and metadata only. The existing `--upstream-receipt` mechanism works when used, but the general `--depends-on` path does not require it or warn. An agent can receive a seemingly successful check for a stale chain. This is **not** an assertion that the program falsely compared the immediate file hash: that comparison is correct. The failure is at the Phase 9 *derived-workflow* guarantee and at the missing material uncertainty despite an observed derivative classification.

**Minimal fix:** When a declared dependency has a strongly identified *generated artifact kind* (notably `HANDOFF` or `GENERATED_SUMMARY`) but no linked upstream receipt, require a receipt for an unchanged status or emit `unlinked_derived_dependency` **uncertainty** with the affected relative path. Avoid guessing receipt filenames. **Do not blanket-require receipts for every `generated_derivative` authority class:** that class also includes `current_state`, whose legitimate use must not be broken by a global rule. Consider an explicit override for genuinely source-of-record generated files, with a retained caveat. Similarly, `--kind compiled_context` with `provenance_scope=declared` should not silently be treated as equivalent to the first-class compiler receipt.

**Regression:** Build the same A→B fixture twice: (a) file-only B is inconclusive, (b) B with A's receipt propagates `source_changed` and `upstream_review_required`; include an ordinary canonical document as a control that remains unchanged. Test typed result and CLI JSON.

### F9-002 — Medium — Compiler implementation changes are not pinned reliably

**Class:** Plan defect + implementation completeness/coverage gap.
**Evidence:** [`derived.py:328–358`](https://github.com/jasonkli21/context-integrity/blob/eedc972a53bb568291bda7a876189aefe6c1ad3f/src/context_integrity/derived.py#L328-L358), [`derived.py:468–521`](https://github.com/jasonkli21/context-integrity/blob/eedc972a53bb568291bda7a876189aefe6c1ad3f/src/context_integrity/derived.py#L468-L521), [`__init__.py:3`](https://github.com/jasonkli21/context-integrity/blob/eedc972a53bb568291bda7a876189aefe6c1ad3f/src/context_integrity/__init__.py#L3), [`compiler.py`](https://github.com/jasonkli21/context-integrity/blob/eedc972a53bb568291bda7a876189aefe6c1ad3f/src/context_integrity/compiler.py).

**Counterexample (statically established, not dynamically mutated):** Create a first-class compiler receipt and keep the artifact, selected files, config, contract, task, budget and inventoried docs constant. Change selection ordering or eligibility logic in `compiler.py` (or an equivalent relevant library module) but leave the package version at `0.0.1`. The current receipt fingerprints no compiler implementation files or build identity: it records `__version__` alone and its checker compares that one string. Hence there is no `compiler_version_changed`, `selection_context_changed` or other review reason for this change. This is realistic here: `__version__` has remained `0.0.1` since the initial commit while the compiler evolved through multiple phase commits. The `selection_not_replayed` caveat is truthful but does not supply a material uncertainty status.

**Expected:** A change in the meaning of a saved compile should be detectable or treated as unverified; its original selected bytes cannot certify that today's tool would make the same decision. The request explicitly called out relevant compiler/selection code as context inputs.

**Minimal fix:** Capture a reproducible implementation/build fingerprint that actually changes with compiler-relevant code, or explicitly mark the implementation comparison **inconclusive** if only an unverified `0.0.1` release label is available. Keep this separate from config v8 and compiled JSON v3. Do not require a full selection replay; a stable semantic-build identity is sufficient for this narrow gap.

**Regression:** In a temporary editable installation/repository fixture, produce a compiler receipt; modify a meaningful compiler decision branch without bumping package version; the new check must report review/uncertainty. A change to unrelated code should remain either unaffected or have a documented conservative result.

### F9-003 — Medium — A valid empty compiled package is always inconclusive

**Class:** Implementation defect + test gap.
**Evidence:** [`derived.py:424–427`](https://github.com/jasonkli21/context-integrity/blob/eedc972a53bb568291bda7a876189aefe6c1ad3f/src/context_integrity/derived.py#L424-L427), [`derived.py:340–358`](https://github.com/jasonkli21/context-integrity/blob/eedc972a53bb568291bda7a876189aefe6c1ad3f/src/context_integrity/derived.py#L340-L358), [`derived-context-contract.md:72–82`](https://github.com/jasonkli21/context-integrity/blob/eedc972a53bb568291bda7a876189aefe6c1ad3f/docs/derived-context-contract.md#L72-L82).

**Independent reproduction (executed):** A schema-v8 contract with one `optional` rule whose path selector matches no source compiles successfully. `compile --format json --output docs/compiled.json --receipt-output docs/receipt.json` exits 0. The receipt has `dependencies=[]`, compilation `status=complete`, `known_incomplete=false`, and a pinned complete inventory-selection/contract context. `derived check` exits 0 but returns:

```text
inconclusive
[declared_inputs_not_semantic_validation, provenance_incomplete, selection_not_replayed]
```

**Expected:** An intentionally empty yet fully observed compiler-selected package should not be treated as having *missing declared provenance* solely because it selected no source. Its inventory-selection fingerprint and contract are meaningful coverage. Other real gaps (provider, inventory warnings, unknown implementation fingerprint per F9-002) must still trigger appropriate uncertainty.

**Cause/fix:** The generic `not receipt.dependencies and not receipt.upstream_receipts` test is applied to **both** `declared` and `compiler_selection` scopes. Scope the empty-declaration uncertainty to manual declarations; for compiler selection decide from actual compilation status, coverage and available selection context. Add a zero-selected complete-compile golden/test alongside the existing no-dependency manual test.

### F9-004 — Low — A near-exhausted graph byte budget receives the wrong reason code

**Class:** Implementation defect + diagnostic regression gap.
**Evidence:** [`derived.py:96–122`](https://github.com/jasonkli21/context-integrity/blob/eedc972a53bb568291bda7a876189aefe6c1ad3f/src/context_integrity/derived.py#L96-L122), [`acquisition.py:245–249`](https://github.com/jasonkli21/context-integrity/blob/eedc972a53bb568291bda7a876189aefe6c1ad3f/src/context_integrity/acquisition.py#L245-L249).

**Independent reproduction (executed):** With a real 9-byte temp file and `Reader.bytes = MAX_GRAPH_BYTES - 1`, the next `Reader.read('data.txt')` returns `state='unobservable'` and logs `source_too_large`, despite the file being below the intrinsic 5 MiB limit. The reader passes a one-byte residual budget as the file limit; acquisition treats the file as oversized; the reader loses the distinction.

**Expected:** `budget_exceeded`/`source_budget_exceeded`, not a false implication that the input cannot be observed for file-specific reasons. **Safety impact is low:** status is still inconclusive, not unchanged. Fix by differentiating a lower global residual budget from the per-file ceiling, and test the one-byte/zero-byte boundary plus mixed definite-change precedence.

## 5. Plan gaps found independently

1. **Derived-input closure (must fix for Phase 9):** The plan models explicit parent receipts but lets an agent list the *same derived artifact* merely as an ordinary source. It does not require a provenance-completeness warning for known generated-role inputs. F9-001 is the concrete false-operational-freshness example that passes the originally intended direct byte-hash tests.
2. **Compiler semantic inputs (must address in Phase 9 or explicitly downgrade status):** Task and budget are captured, and the inventory universe is fingerprinted, but the effective compiler logic itself is reduced to a human-maintained package version. A frozen version string is not a reproducible implementation fingerprint. F9-002 is distinct from the intentionally deferred provider replay.
3. **Empty output semantics (narrow implementation fix):** A compiler has a selection-universe assertion even when it chooses zero sources; a manual handoff with no dependencies does not. The current status logic treats both as the same missing-declaration situation (F9-003).
4. **Manual task/prompt scope (known limitation, not a blocker on its own):** `derived capture` records a producer and optional version but no model prompt/task or generation parameters. Reusing the same summary for a **different task** can still show unchanged declared files. The receipt should remain plainly task-agnostic unless an optional task digest is introduced in a future backward-compatible version.
5. **Canonical/derived boundary:** An observed `generated_derivative` authority class is informative classification, not an authentication of creation or a global authority ranking. The corrective design should use narrowly identified summary/handoff kinds (and explicit receipts) to signal provenance uncertainty, not promote or condemn arbitrary sources. In particular, `current_state` sharing that authority class is **not** sufficient to mark it broken.
6. **Valid deferrals:** Provider re-query/ranker replay, LLM factual truth, automatic dependency extraction, cross-repo lineage (Phase 10), CI enforcement/waivers (Phase 11), semantic verification and auto-repair (Phase 12+) remain outside this delivery. A check that has provider evidence correctly reports `provider_not_revalidated`, and a locally forgeable receipt should not be mistaken for an attestation.

## 6. Adversarial-case matrix

`Independent` means a separately authored runtime fixture in this review; `Suite` means executed existing tests plus source trace; `Static` means source reasoning without an independent mutating experiment.

| Scenario | Expected | Observed | Status / evidence |
| --- | --- | --- | --- |
| Unchanged declared direct source and artifact | Unchanged observed inputs, scoped caveat | As expected | Suite; `test_roundtrip_sorted_actual_bytes` |
| Staged edit at identical HEAD | Review | As expected | Suite; `test_real_git_worktree_journey` |
| Unstaged edit, unrelated HEAD change, byte reversion | Change/revert behavior by bytes | As expected | Suite; `test_dirty_staged_reverted_unrelated_head` |
| Artifact modified | Review | As expected | Suite; direct pin comparison |
| Source deleted/renamed, symlinked, unreadable, oversized | Review or inconclusive; never unchanged | As expected | Suite; `test_non_safe_observations`, `test_unreadable_and_simultaneous_change` |
| Config absent→present, valid→invalid, source lifecycle/supersession change | Review and/or uncertainty with retained byte cause | As expected | Suite; config and metadata tests |
| Explicit A→B receipt chain; A primary source changed | B review with original reason | As expected | Suite; `test_transitive_diamond_memoization`, CLI chain |
| B cites generated A **as plain file**, no parent receipt | B inconclusive because known derived linkage is missing | **B unchanged** | **Independent failure F9-001** |
| Changed/tampered or foreign upstream receipt; cycle, conflicting ID | Review or inconclusive; no silent adoption | As expected | Suite; untrusted/graph tests |
| Provider-selected code, provider not replayed | Inconclusive; direct code change dominates | As expected | Suite; public fake provider adapter |
| Newly eligible inventoried document added after compile | Review | As expected | Suite; compiler receipt context test |
| Compiler implementation changes without `__version__` bump | Review/uncertainty or honest non-coverage | Not pinned; unchanged remains possible | **Static F9-002** |
| Valid compiler-selected empty package | No false missing-source uncertainty | **Inconclusive** | **Independent failure F9-003** |
| Graph byte budget leaves 1 byte before reading a small file | Budget-specific uncertainty reason | **`unobservable`** | **Independent failure F9-004** |
| Unknown/future receipt version, duplicate keys/IDs, escape path | Reject/no unsafe read | As expected | Suite; strict models and CLI tests |
| Pair-output partial link/write failure | No success/overwrite; rollback or explicit retained-partial error | As expected | Suite; output publication failure tests |
| Crash during two-name publication, concurrent mutation across observations | No false atomicity claim | **Not tested**; explicitly disclosed limit | Unverified |
| Large hostile DAG worst-case memory/reason fan-out; Windows/other filesystems | Bound work / fail conservatively | **Not independently stress-tested** | Unverified |

## 7. Documentation staleness sweep

The core canonical files generally reflect delivery accurately. The **important omissions** are in workflow guidance and compiler-version coverage—not in claims that Phase 9 is still deferred.

| File / line at target | Assessment | Proposed precise update | Priority |
| --- | --- | --- | --- |
| `docs/derived-context-contract.md:20–26` | Describes repeatable `--depends-on` and `--upstream-receipt`, but does **not warn** that citing a generated derivative only as an ordinary file suppresses its upstream staleness (F9-001). | Add: “For an input known to be generated, also link its receipt. A plain `--depends-on` hashes only that file; it does not revalidate the file's own dependencies.” Once fixed, document the new `unlinked_derived_dependency` uncertainty reason. | **High** |
| `README.md:748–767` | Correct command examples, but the one-handoff example does not illustrate a two-level handoff/summary graph. | Add a short A→B example or prominent link to the derived contract's parent-receipt warning; avoid duplicating the full schema. | Medium discoverability |
| `docs/ai/README.md:108–115` | Correct advice to keep handoffs short, but no link to the now-shipped receipt workflow. | Add one sentence: “When a handoff is generated from other context, record its declared inputs and any upstream derived receipts; see `../derived-context-contract.md`.” | Low |
| `docs/derived-context-contract.md:108–110` and `docs/architecture.md:1868–1872` | Recording an “implementation version” is technically true, but may imply meaningful detection of algorithm changes; `__version__` is currently a static `0.0.1` marker (F9-002). | Clarify that current version equality **does not prove compiler-logic equality** and name the additional implementation/build fingerprint or uncertainty convention after fixing. | Medium |
| `docs/derived-context-contract.md:142–147` | General claim that empty provenance means uncertainty is accurate for manual capture but over-broad for complete, intentionally empty compiler selections (F9-003). | Distinguish manual `declared` source closure from `compiler_selection` with a pinned contract and complete inventory universe. | Medium |
| `docs/reviews/README.md:~20–25` | Phase 9 is not indexed **because the independent review file was not yet present in the target commit**. This is not historical drift. | When adding this handoff to the repository, link the reviewed `eedc972` commit and fix/re-review evidence once available. Do not call fixes accepted until separately verified. | Handoff follow-up |

**No material Phase 9 status drift found** in `docs/current-state.md:1–70`, `README.md:11–20`, `docs/README.md:54–67`, `docs/architecture.md:1833–1874`, or the updated `docs/architecture-integrity-contract.md:147–153`. Config v8, compiled v3, integrity v2, and derived receipt/result v1 are clearly distinguished. `docs/prd.md` Phase 9 roadmap language is product intent, not a stale delivery assertion. Historical plans and implementation reports properly remain historical. `AGENTS.md` remains canonical; `CLAUDE.md` and `.github/copilot-instructions.md` are pointers rather than competing rules. `docs/plans/README.md`, `docs/implementation-reports/README.md` and `docs/ai/README.md` are generally role-correct; none requires an indiscriminate phase-number rewrite. Phase 8 pending re-review and earlier independent verification gaps are accurately retained in current-state; do not silently close them.

## 8. Remaining risks and unverified areas

- **Unauthenticated receipts:** A malicious writer capable of replacing receipt and artifact bytes can forge matching observations. This is an explicit trust boundary, not a detected new exploit or a request for cryptographic signing in Phase 9.
- **Manual declaration scope:** Omitted primary sources, untracked prompts and newly relevant authority are not exhaustively discoverable. F9-001 is actionable because the dependency is *already observably classified as derived*; unknown hidden semantic dependencies cannot be magically inferred.
- **Provider semantics:** Without replay of validated provider candidate/ranker coverage, results remain inconclusive. That conservative behavior passed targeted tests; real Context Engine was not installed/run.
- **Observation races:** Reads and inventory scans are sequential; no cross-file transaction/snapshot guarantee. Double-observation/coherence stress tests were not added during this review.
- **Operating systems/resources:** No Windows or special-filesystem check, crash-recovery experiment, or worst-case near-limit DAG memory profile was run. The existing bounded read/path validation and rollback tests passed but do not prove every race or DoS boundary.
- **Prior reviews:** The Phase 8 fix commit `917a9d3` is the verified parent, but a separate fresh Phase 8 independent acceptance was still pending in the reviewed docs.

## 9. Prioritized implementation handoff

1. **P0 — Fix F9-001: unlinked derived inputs.** Define a conservative stable reason for a known generated **summary/handoff** source used as an ordinary file pin without an upstream receipt. Either require an explicit parent link at capture or allow capture but force check `inconclusive`; do not infer or trust a sidecar by filename alone. Avoid sweeping in `current_state` solely because its authority class is `generated_derivative`. Apply analogous honesty to generic `--kind compiled_context` declared captures. **Acceptance:** Independent A→B scenario is no longer unchanged; properly linked A→B propagates cause; canonical/current-state-only controls stay unchanged; no schema/authority promotion.
2. **P1 — Fix F9-002: compiler algorithm identity.** Add a deterministic build/implementation fingerprint or explicit inability-to-confirm status. Keep receipt/version separation and no secret/raw code in output. **Acceptance:** Changing compiler selection semantics without bumping `__version__` produces review/uncertainty; equivalent builds and unaffected canonical inputs remain stable; old receipt v1 handling is deliberately versioned or conservatively handled.
3. **P1 — Fix F9-003: valid zero-selection compile.** Scope empty-dependency uncertainty to declared workflows or calculate compiler completeness from the typed selection universe/contract. **Acceptance:** A complete no-provider empty compile does not get `provenance_incomplete`; manual zero-dependency capture remains inconclusive; an incomplete compile/provider or inventory gap still returns inconclusive.
4. **P2 — Fix F9-004: budget reporting.** Preserve whether a read failed because the global remaining byte budget was below the file size. **Acceptance:** Per-file oversized and global-budget-exhausted cases have distinct stable reason codes; both remain uncertain and simultaneous definite changes retain review precedence.
5. **Documentation:** Update just the identified contract/README/AI handoff passages; index the review when incorporated. Keep current-state truthful until fixes are tested and independently re-reviewed. Do not edit the PRD or rewrite historical plans simply to match this handoff.

**Post-fix verification in a clean checkout:**

```bash
git rev-parse HEAD
git status --short
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 \
  uv run pytest -q tests/test_derived.py tests/test_derived_cli.py
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check
git diff --check
git status --short
```

Add the four targeted regression cases above rather than relying exclusively on the implementation session's existing 102-test matrix. Then perform a fresh independent review of **the fix commit** and explicitly compare with this handoff.

## 10. Final acceptance checklist

- [x] Exact commit/parent verified; detached checkout clean and no later commit mixed in.
- [x] Instructions, PRD/architecture/contracts, typed compiler/provider seam, receipt graph, CLI, tests and navigation docs inspected.
- [x] Focused 102 tests, full 1,067 tests, lint/format and commit whitespace check passed independently.
- [x] Dirty/HEAD, transitive, malformed, provider, config, safe-output paths reviewed; independent counterexamples attempted.
- [ ] **F9-001**: known derived source cannot silently bypass upstream revalidation by using ordinary file dependency syntax.
- [ ] **F9-002**: compiler logic identity is pinned or the unknown status is honest.
- [ ] **F9-003**: intentionally empty complete compiler output has correct scoped result.
- [ ] **F9-004**: global graph byte-budget reason remains accurate.
- [ ] Identified user-facing guidance updated; new regression tests pass; a new independent review accepts the fix revision.
- [ ] Outstanding Phase 8 independent re-review is handled separately; it is not implicitly accepted here.

**Final decision:** The implementation meets many mechanical Phase 9 requirements, but the observed F9-001 downstream-generated-source gap is material for the intended agent-handoff workflow. **Fix then re-review; do not mark Phase 9 independently accepted at `eedc972`.**
