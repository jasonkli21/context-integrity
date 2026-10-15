<!-- Retained external independent review, reviewed head 3ae38a6d.
The handoff instructions and unchecked checklist below are historical reviewer content.
Fix evidence is in ../implementation-reports/phase-2-implementation-report.md. -->

# Context Integrity Phases 0–2 — Sol High Review + Collective Pass / Sol Medium Fix Handoff

## Purpose

This file is both:

1. the independent Phase 2 review record for the reviewed implementation;
2. a follow-up collective audit of the delivered Phase 0–2 stack and its cross-phase seams; and
3. the complete handoff for a fresh **Sol Medium** session to address all review findings without additional prompting.

The fix session should treat repository code and executable tests as the delivered-behavior source of truth, each completed phase plan as the normative contract for that phase, `AGENTS.md`/architecture as durable cross-phase constraints, and this handoff as the accepted independent-review worklist.

---

## Review target

- **Repository:** `jasonkli21/context-integrity`
- **Reviewed Phase 1 baseline:** `36d150af6cf67b8bab41c528b4304fa83da51309` — `fix phase 1 review findings`
- **Reviewed Phase 2 head:** `3ae38a6dc1fec72b24a64e3a0ccd8f6c2f7195d5` — `phase 2 implementation`
- **Implementation range:** `36d150af6cf67b8bab41c528b4304fa83da51309..3ae38a6dc1fec72b24a64e3a0ccd8f6c2f7195d5`
- **Range shape:** exactly one commit ahead of the reviewed Phase 1 baseline; no intervening commit was found.
- **Review date:** 2026-10-14
- **Normative plan:** `docs/plans/phase-2-implementation-plan.md`
- **Implementation evidence:** `docs/implementation-reports/phase-2-implementation-report.md`
- **Current-state document:** `docs/current-state.md`

### Quality-gate status during this independent review

The implementation report records this implementation-session offline gate:

```bash
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check
```

with Ruff lint/format and **343 tests passing** on Python 3.12.13/macOS. The review environment still could not clone GitHub directly because its container DNS could not resolve `github.com`, so that exact offline command was not rerun locally by the reviewer.

However, the collective follow-up pass found independent GitHub Actions evidence for the exact reviewed head `3ae38a6dc1fec72b24a64e3a0ccd8f6c2f7195d5`:

- push workflow run `38686819388` completed successfully;
- checkout confirmed exact HEAD `3ae38a6d...`;
- Ruff lint passed;
- Ruff format check passed;
- pytest collected **343 items** and finished **343 passed in 2.15s**;
- CI used Python **3.12.3** on Ubuntu 24.04.

This is independent verification that the committed reviewed tree passed the repository CI gate. It is **not** the same as independently rerunning the implementation session's `UV_OFFLINE=1 make check` on macOS, because the CI environment installed dependencies with network access.

The fix session must still rerun the complete local/offline gate after making changes and record its exact final test count.

---

## Executive result

**PASS WITH FINDINGS — fixes required before Phase 3.**

Final finding count after the collective Phase 0–2 pass:

- **P0:** 0
- **P1:** 1
- **P2:** 4
- **P3:** 0
- **Total:** 5

The original Phase 2 pass found two P2 issues. The collective pass found one additional foundational Phase 0 defect plus two cross-phase evidence/governance defects.

The five findings are:

1. **F-001 — P2:** `lifecycle show` reports lifecycle-gate eligibility rather than the required combined policy-independent active-authority eligibility.
2. **F-002 — P2:** the Phase 2 implementation report falsely says no implementation commit exists.
3. **F-003 — P1:** inherited Git context can silently corrupt repository discovery/identity; `GIT_CEILING_DIRECTORIES` can downgrade a nested Git scan to non-Git, and merged/global `remote.origin.url` can supply a false canonical repository identity.
4. **F-004 — P2:** Phase 0/1 implementation reports do not fully record the actual committed delivery/review-fix chain required by their phase plans.
5. **F-005 — P2:** independent review records for completed phases are not persisted under `docs/reviews/`, contrary to the repository's canonical review workflow; the repository currently contains only the review-directory README.

No additional lifecycle graph, authority-resolution, configuration-consistency, source-read, or Phase 3 scope-creep defect was substantiated in the collective pass. In particular, a tentative concern about allowing the control-plane config to receive explicit ordinary authority metadata was **not** promoted to a finding because the Phase 1/2 contracts do not clearly prohibit deliberate explicit source-role overrides there.

---

## Canonical context for the fix session

Read in this order before editing:

1. `AGENTS.md`
2. `docs/current-state.md`
3. this handoff
4. `docs/plans/phase-0-implementation-plan.md`
5. `docs/plans/phase-1-implementation-plan.md`
6. `docs/plans/phase-2-implementation-plan.md`
7. `docs/architecture.md`
8. `src/context_integrity/repository.py`
9. `src/context_integrity/lifecycle.py`
10. `src/context_integrity/authority.py`
11. `src/context_integrity/configuration.py`
12. `src/context_integrity/rendering.py`
13. `src/context_integrity/cli.py`
14. `tests/test_repository.py`
15. `tests/test_lifecycle.py`
16. `tests/test_authority.py` and `tests/test_configuration.py` for regression protection
17. all three implementation reports under `docs/implementation-reports/`
18. `docs/reviews/README.md`
19. `README.md` only where user-facing semantics/provenance need alignment

Do not bulk-read historical reviews unless a concrete invariant requires them.

---

## Verified implementation summary

### Repository state and scope

The reviewed head is exactly one commit after the reviewed Phase 1 baseline. The Phase 2 commit changes the expected lifecycle/config/inventory/authority/rendering/CLI modules, adds `lifecycle.py`, lifecycle tests/goldens, the Phase 2 plan/report, and user-facing documentation. No database, LLM integration, claim extraction, contradiction engine, Context Intelligence dependency, daemon/server, or automatic source mutation was found.

### Lifecycle domain

`LifecycleState` contains exactly:

```text
unknown
draft
active
superseded
historical
expired
invalid
```

`lifecycle_authority_eligible` correctly treats only `unknown` and `active` as passing the lifecycle gate. Explicit `unknown` metadata is rejected.

### Configuration

The parser accepts schemas 1 and 2, keeps schema 1 authority-only, rejects Phase 2 keys from schema 1, permits lifecycle/supersession in schema 2, requires nonblank reasons, rejects unknown keys, rejects lifecycle management/supersession of `.context-integrity.toml`, and reuses repository-relative path normalization with additional Windows-path ambiguity checks.

The final config revision is re-read and compared against both the initially parsed hash and the observed config source hash, preserving the fail-closed Phase 1 consistency model across authority, lifecycle, and supersession.

### Supersession

Configured supersession is validated before endpoint observation for:

- source != target;
- one outgoing successor per source;
- allowed convergence;
- chains;
- cycle rejection;
- explicit-lifecycle conflicts.

Runtime resolution occurs only after inventory observation. A relation is activated only if both endpoints are observed. Missing source/target endpoints produce warnings and an unresolved relation alone does not make the source superseded. A valid relation makes only its source superseded; the target is not inferred active. Final edge records reference final effective endpoint records, which preserves correct chain state.

### Historical override behavior

Explicit non-historical lifecycle and valid supersession correctly remove only the historical path authority overlay and restore the kind-derived authority role unless an explicit Phase 1 authority-class override is present. Kind and top-level kind confidence are preserved.

### Authority integration

`resolve_authority` applies the gates in the intended order:

```text
lifecycle exclusion
  -> explicit authority_eligible = false
  -> not_in_policy
  -> candidate
```

State-specific lifecycle exclusion reasons are used. Built-in policy definitions remain structurally unchanged in the reviewed source, and Phase 1 equal-tier/missing-stronger-tier logic remains intact.

### Output and security

Inventory JSON remains an explicit schema-v1 projection with no graph fields. Authority JSON remains an explicit schema-v1 projection with no lifecycle graph fields. Lifecycle uses a separate explicit schema-v1 projection. Lifecycle paths/edges are sorted deterministically; JSON uses repository-relative paths and no default timestamp, absolute root, or source body.

Text rendering escapes repository-controlled paths and lifecycle/supersession reasons. Supersession validation is iterative rather than recursive and tests include a deep-chain case. The config remains strict TOML with no imports/includes, code execution, or network behavior.

### Test quality observed in source

The new lifecycle suite covers the principal product risks rather than only implementation internals, including:

- exact schema compatibility;
- explicit lifecycle state matrix;
- invalid/unsafe config paths;
- self/duplicate/cyclic supersession;
- chain and convergence behavior;
- missing endpoints;
- historical override restoration;
- lifecycle-aware authority exclusions;
- no recency/body/network/shell inference;
- deterministic lifecycle JSON goldens;
- terminal controls;
- CLI list/show/error/output behavior;
- no-config Git-date/filename non-inference;
- unobserved symlink endpoint safety.

The principal test gap is the exact combined-eligibility scenario described in F-001.

---

## Findings

### F-001 — P2 — `lifecycle show` does not implement the plan's combined active-authority eligibility semantics

**Type:** missing required behavior / CLI and machine-readable contract mismatch

#### Evidence

The normative Phase 2 plan, §21.2, defines the `lifecycle show` authority section as exposing:

```text
Authority:
  class: decision
  active authority eligible: no
  exclusion reason: superseded_lifecycle
```

and states explicitly:

> `active authority eligible` refers only to lifecycle eligibility + explicit global authority eligibility, not policy membership.

The reviewed implementation does not calculate that combined value.

`src/context_integrity/rendering.py::_lifecycle_entry_v1` emits only:

```python
"lifecycle_authority_eligible": lifecycle_authority_eligible(source.lifecycle)
```

It does not expose the source's explicit `authority_eligible` setting, the combined active-authority eligibility, or the corresponding exclusion reason.

`src/context_integrity/rendering.py::render_lifecycle_text(..., detail=True)` likewise prints only:

```text
lifecycle authority eligibility: <true|false>
```

based exclusively on `source.lifecycle`.

`src/context_integrity/cli.py::_lifecycle_output` uses these renderers for `lifecycle show`, so no later CLI layer repairs the semantics.

The actual authority resolver in `src/context_integrity/authority.py::resolve_authority` is correct: after lifecycle eligibility, it separately checks:

```python
entry is not None and entry.authority_eligible is False
```

and excludes such sources with `explicitly_ineligible`.

That creates a reproducible disagreement in inspection output. For example, with schema v2 metadata conceptually equivalent to:

```toml
schema_version = 2

[[source_metadata]]
path = "docs/adr/a.md"
lifecycle = "active"
authority_eligible = false
reason = "Do not use as active authority"
```

expected command semantics are:

```text
lifecycle gate: eligible
explicit global authority eligibility: false
active authority eligible: false
exclusion reason: explicitly_ineligible
```

but the current `lifecycle show` text reports lifecycle eligibility as `true`, and lifecycle JSON contains no field that communicates the explicit exclusion or the required combined result.

The test gap is visible in `tests/test_lifecycle.py`:

- `test_authority_lifecycle_matrix` proves the resolver handles explicit ineligibility correctly;
- `test_lifecycle_cli` exercises `show` using a superseded source and checks only `lifecycle authority eligibility: false`;
- no `lifecycle show` test covers `active`/`unknown` plus `authority_eligible = false`.

#### Why this is wrong

This violates the Phase 2 `lifecycle show` contract and the independent-review requirement that show expose lifecycle/explicit eligibility for active authority.

The problem is not cosmetic. `lifecycle show` is an inspection/explainability command. A consumer can inspect an explicitly active source and be shown a positive eligibility signal even though the same repository configuration globally excludes that source from every authority policy.

The command must not perform question-specific policy membership, but it **must** account for the policy-independent explicit eligibility flag.

#### Required fix

Introduce one narrow, deterministic representation of global active-authority eligibility that exactly mirrors the first two authority-resolver gates without invoking policy membership.

Required semantics:

```text
if lifecycle is draft/superseded/historical/expired/invalid:
    active_authority_eligible = false
    exclusion_reason = <state>_lifecycle
elif source_metadata.authority_eligible is false:
    active_authority_eligible = false
    exclusion_reason = explicitly_ineligible
else:
    active_authority_eligible = true
    exclusion_reason = none
```

`unknown` and `active` therefore pass the lifecycle component but can still be globally excluded by explicit authority metadata.

Implementation guidance:

- avoid calling `resolve_authority` from lifecycle inspection;
- avoid using `not_in_policy`, because show intentionally does not choose a policy;
- prefer a small pure helper shared with rendering and, if cleanly possible, authority resolution so these gates cannot drift again;
- preserve the existing lifecycle-only signal if useful, but do not present it as the required combined active-authority result;
- expose enough explicit data for a machine consumer to distinguish lifecycle gating from explicit global eligibility.

A clean lifecycle JSON source projection would expose the distinction explicitly, for example:

```text
lifecycle_authority_eligible: bool
explicit_authority_eligible: true | false | null
active_authority_eligible: bool
active_authority_exclusion_reason: string | null
```

Exact field names may differ if the implementation chooses a clearer contract, but semantics must be unambiguous. Because lifecycle JSON v1 is newly introduced in Phase 2 and currently under independent review, update its Phase 2 goldens deliberately rather than mutating older inventory/authority schemas.

Text `lifecycle show` should expose at least:

```text
authority_class: ...
active authority eligible: true|false
exclusion reason: <reason|none>
```

It may additionally show the lifecycle-only and explicit components for explainability.

Update README wording if necessary so it distinguishes:

- lifecycle-gate eligibility; and
- combined policy-independent active-authority eligibility.

#### Required tests

Add focused regression tests that prove both text and JSON behavior:

1. `active` + `authority_eligible = false`
   - lifecycle gate true;
   - explicit eligibility false;
   - combined active-authority eligibility false;
   - exclusion `explicitly_ineligible`.
2. `unknown` + `authority_eligible = false`
   - same combined result as above.
3. `active` + explicit `authority_eligible = true`
   - combined true;
   - no exclusion.
4. `active` + no explicit eligibility
   - combined true;
   - no exclusion.
5. `draft` + `authority_eligible = false`
   - combined false;
   - exclusion must be `draft_lifecycle`, proving lifecycle precedence remains stronger than explicit ineligibility.
6. A corresponding authority-resolution regression confirming the resolver still produces the same candidate/exclusion decisions after any helper refactor.
7. Update lifecycle JSON golden/key-set tests intentionally for the final projection.

#### Acceptance criteria affected

- Phase 2 plan §21.2 `lifecycle show` semantics.
- Phase 2 plan §35 Authority Integration: explicit authority eligibility still works end-to-end.
- Phase 2 plan §35 CLI / Output: `lifecycle show` works according to its specified meaning.
- Independent review rubric: lifecycle/explicit eligibility for active authority.

---

### F-002 — P2 — Phase 2 implementation report contains false delivery-commit provenance

**Type:** material implementation-report inaccuracy / context-integrity documentation defect

#### Evidence

The reviewed repository range is:

```text
36d150af6cf67b8bab41c528b4304fa83da51309
  -> 3ae38a6dc1fec72b24a64e3a0ccd8f6c2f7195d5
```

with exactly one implementation commit:

```text
3ae38a6dc1fec72b24a64e3a0ccd8f6c2f7195d5  phase 2 implementation
```

That commit contains `docs/implementation-reports/phase-2-implementation-report.md`.

However, the report header states:

```text
Delivery: Uncommitted working-tree changes on that baseline. No implementation commit created.
```

The report also describes `docs/plans/phase-2-implementation-plan.md` as a pre-existing untracked file. That can describe the implementation session's pre-commit chronology, but the delivery statement is now factually false as repository evidence: the Phase 2 implementation is committed at `3ae38a6d...`.

The Phase 2 plan §39 explicitly requires the implementation report to include **implementation commits**. The independent review rubric likewise requires checking the report's baseline and implementation commits against reality.

#### Why this is wrong

The implementation report is durable implementation evidence. A fresh session reading it should be able to identify exactly which committed tree constitutes the original Phase 2 delivery.

Saying that no implementation commit exists:

- contradicts Git history;
- weakens provenance between the reviewed baseline, implementation, and future review-fix commits;
- makes it harder to distinguish original Phase 2 behavior from independent-review fixes;
- violates the report requirement to record implementation commits.

This is particularly material in a repository whose product goal is context/provenance integrity.

#### Required fix

Update the report's delivery provenance to identify the actual original Phase 2 commit:

```text
3ae38a6dc1fec72b24a64e3a0ccd8f6c2f7195d5
phase 2 implementation
```

Preserve useful chronology rather than rewriting history. For example, it is acceptable to say the implementation session developed changes in a working tree and that those changes were subsequently committed as `3ae38a6d...`; do not leave the false statement that no implementation commit exists.

After implementing the independent-review fixes:

- add a concise independent-review/fix section to the Phase 2 report;
- record F-001 and F-002 resolution evidence;
- record the review-fix commit SHA(s) once actually available;
- record the exact post-fix offline gate and test count;
- distinguish the implementation session's original 343-test claim from the fix session's newly executed verification;
- do not claim this reviewer independently reran the original 343-test gate.

Do **not** edit the completed Phase 2 plan to retrofit post-review reality.

#### Required tests / verification

No new behavioral unit test is required solely for the prose correction, but the fix session must:

- verify the report names the correct original delivery commit;
- ensure it no longer says no implementation commit exists;
- run `git diff --check`;
- run the full offline quality gate after all fixes;
- update `docs/current-state.md` only after that gate succeeds.

#### Acceptance criteria affected

- Phase 2 plan §39 implementation report requirements: implementation commits.
- Phase 2 plan §35 Testing / Docs: implementation report maps verified delivered state accurately.
- Independent review rubric §26: implementation commits and factual report accuracy.


---

# Addendum — Collective Phase 0–2 Review Pass

This addendum was produced after the initial Phase 2-only review. It re-read the Phase 0, Phase 1, and Phase 2 plans/reports together; inspected current repository/discovery/config/authority/lifecycle code and tests at `3ae38a6d...`; verified the actual five-commit delivery chain; inspected the canonical review workflow; checked GitHub Actions for the delivered commits; and probed Git behavior independently with synthetic local repositories where useful.

The findings below are **additional** to F-001/F-002 and are part of the same mandatory Sol Medium worklist.

## F-003 — P1 — Inherited Git context can silently corrupt repository discovery and repository/source identity

**Owning phase:** Phase 0, with downstream impact on Phases 1–2 and future provenance/claims
**Type:** foundational identity/discovery correctness defect

### Contract and evidence

Phase 0 makes repository/source identity a foundational primitive. The Phase 0 plan requires that a path inside a Git worktree resolve to the Git repository root and that repository identity prefer a safely available normalized canonical Git remote, otherwise a local fallback. The Phase 0 implementation report further claims that inherited repository-location overrides are discarded.

`src/context_integrity/repository.py::git_command` currently strips several inherited variables:

```text
GIT_DIR
GIT_WORK_TREE
GIT_INDEX_FILE
GIT_COMMON_DIR
GIT_OBJECT_DIRECTORY
GIT_ALTERNATE_OBJECT_DIRECTORIES
```

but it leaves other discovery-affecting Git environment in place. In particular, `GIT_CEILING_DIRECTORIES` is inherited.

`discover_repository` performs:

```text
git rev-parse --show-toplevel
```

and treats stderr containing `not a git repository` as an ordinary non-Git path rather than a Git failure. Therefore an inherited ceiling between the requested nested directory and the actual repository root can make a real nested Git scan silently become a non-Git scan.

The reviewer reproduced the underlying Git behavior independently with a synthetic repository:

```text
repo/
  .git/
  sub/deep/
```

Normal:

```bash
git -C repo/sub/deep rev-parse --show-toplevel
# -> repo
```

With a ceiling below the actual repository root:

```bash
GIT_CEILING_DIRECTORIES=repo/sub \
  git -C repo/sub/deep rev-parse --show-toplevel
# -> fatal: not a git repository (or any of the parent directories): .git
```

Under the current `discover_repository` logic this becomes:

- `git_available = false`;
- the requested nested directory becomes the scan root;
- Git ignore semantics are lost;
- the repository ID changes to `local_fallback` for the nested path;
- source IDs change with it;
- the behavior is silent because the exact `not a git repository` stderr is treated as the normal non-Git case.

There is a second identity contamination path in the same module. The preferred remote lookup is:

```python
git config --get remote.origin.url
```

without `--local`. Git therefore reads merged configuration scopes. The reviewer independently reproduced that a **global** `remote.origin.url` is returned for a repository that has no local origin:

```bash
git config --global remote.origin.url https://example.com/shared.git

git -C repo-a config --get remote.origin.url
# -> https://example.com/shared.git

git -C repo-a config --local --get remote.origin.url
# -> no value
```

Two unrelated Git repositories with no local origin but the same inherited/global `remote.origin.url` are therefore assigned the same normalized remote identity by the current code. Because `RepositoryRef.id` hashes that remote and `SourceId` hashes `repository_id + relative_path`, same-path context sources in those unrelated repositories can receive the **same source ID**.

Existing repository tests cover `GIT_DIR`/`GIT_WORK_TREE`, worktree redirects, fsmonitor suppression, nested roots, and local/remote identity, but do not cover `GIT_CEILING_DIRECTORIES` or global-origin contamination.

### Why this is P1

Stable repository/source identity is the base provenance primitive for every later phase. This defect can silently produce:

- the wrong repository root;
- the wrong discovery mode and ignore semantics;
- the wrong repository identity basis;
- repository-ID collisions across unrelated repositories;
- source-ID collisions for equal relative paths.

Phases 1 and 2 attach authority/lifecycle/supersession results to those source records, and Phase 3 is expected to key claims/provenance to `SourceId + SourceRevision`. Proceeding into Phase 3 with a known silent identity contamination path would compound the defect into later provenance.

### Required fix

Keep the correction narrow and preserve Git's own security behavior.

1. **Sanitize discovery-location environment that should not select a different repository boundary.** At minimum ensure inherited `GIT_CEILING_DIRECTORIES` cannot change Context Integrity's repository discovery semantics. Also inspect `GIT_DISCOVERY_ACROSS_FILESYSTEM` as the paired Git discovery control and neutralize it if it can change the selected repository boundary for the same requested path.
2. **Do not broadly disable Git system/global configuration** if doing so would bypass legitimate Git security such as `safe.directory`. Fix the specific identity leak instead.
3. Change the preferred remote lookup to repository-local scope, e.g. semantically equivalent to:

```bash
git config --local --get remote.origin.url
```

so a global/system/command-scope `remote.origin.url` cannot manufacture `git_remote` identity for a repository that does not define one locally.
4. Preserve current normalization and credential stripping for a genuine repository-local origin.
5. Preserve linked-worktree support and the existing worktree-redirect fail-closed checks.

If implementation discovers another inherited Git variable that demonstrably changes repository selection/identity, add it to the same narrow isolation boundary and test it. Do not turn this into a speculative rewrite of all Git environment handling.

### Required tests

Add regression tests in `tests/test_repository.py` and, where useful, one inventory-level assertion:

1. **Nested Git + inherited ceiling:** create a Git repo with a nested directory, set `GIT_CEILING_DIRECTORIES` between the nested path and actual root, and assert `discover_repository(nested)` still returns the real Git root with `git_available = true`.
2. Confirm the same scenario still uses Git candidate enumeration/ignore behavior rather than filesystem fallback.
3. **Global origin contamination:** create a Git repository with **no local origin**, supply a global `remote.origin.url` through an isolated test Git config/home, and assert Context Integrity uses `local_fallback`, not `git_remote`.
4. Create two unrelated no-origin Git repos under that same global origin and assert their `RepositoryRef.id` values differ.
5. Assert same-relative-path `SourceId` values differ across those repositories.
6. Existing genuine local-origin normalization tests must continue to pass and still produce `git_remote` identity.
7. Existing `GIT_DIR`/`GIT_WORK_TREE`, linked-worktree, redirect, fsmonitor, dirty/untracked, and Git-ignore tests must remain green.

### Documentation updates

Update the Phase 0 implementation report's review-fix/limitations section and README repository-identity wording after the fix so they state that the preferred remote is **repository-local origin configuration**, not an arbitrary merged Git configuration value.

Do not edit the completed Phase 0 plan retroactively.

---

## F-004 — P2 — Phase 0/1 implementation reports do not fully record the actual committed closure chain

**Owning phases:** Phase 0 and Phase 1
**Type:** durable implementation-evidence/provenance defect

### Evidence

The current Git history through the reviewed Phase 2 head is unambiguous:

```text
240dc93458ed11db901ede9cc264eb3e98a09594  initial commit
  -> d5b62adc9de40416fd715983b2ec629378a4b5c0  fix phase 0 independent review findings
  -> 9efd5fbc509adffbc11a1100ac2bb31caf8f1b6e  implement phase 1
  -> 36d150af6cf67b8bab41c528b4304fa83da51309  fix phase 1 review findings
  -> 3ae38a6dc1fec72b24a64e3a0ccd8f6c2f7195d5  phase 2 implementation
```

The Phase 0 plan §34 requires its implementation report to contain the implementation `commit(s)`. The current Phase 0 report explains that the initial report was prepared from a source copy without `.git` metadata and that the subsequent review-fix pass is recorded in one commit, but it does not name the actual committed delivery/fix SHAs now known from repository history.

The Phase 1 plan §27 similarly requires implementation commit(s). The Phase 1 report correctly names:

```text
baseline: d5b62ad...
Phase 1 delivery: 9efd5fb...
```

but then says the post-review corrections and updated report are in “one follow-up commit” without naming the actual closure commit:

```text
36d150af6cf67b8bab41c528b4304fa83da51309
```

F-002 already covers the more severe Phase 2 version of this problem, where the report incorrectly says no implementation commit exists at all.

### Why this matters

The implementation reports are the durable evidence layer for what was delivered and verified. A fresh agent should be able to move directly from a phase report to:

- original implementation commit;
- independent-review fix commit;
- final verified baseline consumed by the next phase.

Leaving those transitions implicit forces Git archaeology and weakens the exact provenance chain this project is intended to model.

### Required fix

Update historical reports **without rewriting implementation chronology**:

#### Phase 0 report

Record, with careful wording:

- original committed Phase 0/scaffold delivery: `240dc93458ed11db901ede9cc264eb3e98a09594` (`initial commit`);
- Phase 0 independent-review fix commit: `d5b62adc9de40416fd715983b2ec629378a4b5c0` (`fix phase 0 independent review findings`);
- clarify that the initial implementation session itself lacked `.git` metadata, but repository history now provides the committed delivery chain.

#### Phase 1 report

Retain:

- baseline `d5b62adc...`;
- original delivery `9efd5fbc...`;

and explicitly add:

- independent-review fix/final Phase 1 baseline `36d150af6cf67b8bab41c528b4304fa83da51309` (`fix phase 1 review findings`).

#### Phase 2 report

Resolve F-002 as already specified by naming original delivery `3ae38a6d...`, then record the new Sol Medium review-fix commit once it exists.

Do not alter completed phase plans to pretend the commit topology was known before delivery.

### Verification

No behavioral unit test is needed. Before committing, compare the report statements against:

```bash
git log --oneline --decorate --reverse 240dc93458ed11db901ede9cc264eb3e98a09594..HEAD
```

(or an equivalent log including the root commit) and ensure no report claims an uncommitted/follow-up state that is false for the durable repository history.

---

## F-005 — P2 — Completed independent-review evidence is absent from the canonical `docs/reviews/` surface

**Owning concern:** cross-phase repository context governance
**Type:** review-evidence retention / context-hygiene defect

### Evidence

`AGENTS.md` defines the canonical review workflow for a completed phase/significant implementation. Step 3 is:

```text
review findings are written under docs/reviews/
```

and the documentation lifecycle says `docs/reviews/` contains independent review findings.

`docs/reviews/README.md` likewise says:

> This directory contains independent post-implementation review findings.

At reviewed head `3ae38a6d...`, the `docs/reviews/` tree contains only:

```text
docs/reviews/README.md
```

There is no retained Phase 0 review artifact and no retained Phase 1 review artifact, despite:

- the Phase 0 implementation report recording independent findings F-001–F-003 and their fixes;
- the Phase 1 implementation report explicitly naming `context-integrity-phase-1-independent-post-implementation-review.md` and recording findings F-001–F-004;
- the repository now proceeding into a Phase 2 independent-review cycle.

The implementation reports contain useful **implementation-session summaries of review fixes**, but they are not a substitute for preserving the independent review evidence itself; `AGENTS.md` explicitly distinguishes reviews from implementation reports.

### Why this matters

This is a context-integrity failure in the repository's own development evidence. A fresh agent cannot inspect the independent review layer from canonical repository sources and must trust an implementation report's summary of a review that is absent.

That weakens:

- separation between implementation evidence and independent review evidence;
- auditability of why review-fix commits exist;
- future verification that a reported finding was represented accurately;
- the repository's stated “avoid context archaeology” goal.

### Required fix

Do **not** fabricate missing historical reviewer prose.

1. Persist this final Phase 0–2/Phase 2 review handoff in the repository under `docs/reviews/` as the canonical current review artifact, using a clear name such as:

```text
docs/reviews/phase-2-independent-review.md
```

The repository copy should contain the findings and fix requirements; model-specific handoff wording may be retained if useful, but avoid duplicating unrelated PRD/architecture prose.
2. For Phase 0 and Phase 1:
   - if the original independent-review artifacts are available to the fix session, add them under `docs/reviews/` with stable names;
   - if they are **not** available, create concise **reconstructed closure records** based only on the existing implementation reports + Git history, clearly labeled as reconstructed records and **not** as the original independent-review text.
3. A reconstructed record should contain only known facts:
   - reviewed phase/delivery commit;
   - known finding IDs/titles or exact summaries already preserved in the implementation report;
   - review-fix commit;
   - verification evidence;
   - explicit note that the original external review artifact was not retained in the repository.
4. Update `docs/reviews/README.md` with a short index/status note so future sessions can locate the phase review record directly.
5. Do not invent quotes, reviewer rationale, severities, or additional historical findings that are not supported by existing repository evidence.

### Verification

After the fix, a fresh session following `AGENTS.md` should be able to navigate:

```text
implementation report -> independent review record -> review-fix commit -> next-phase baseline
```

without relying on prior ChatGPT conversation history or external handoff files.

---

## Cross-cutting verification requirements

After implementing F-001 through F-005, verify all of the following rather than only the direct regressions.

### Repository/config compatibility

- schema v1 authority-only config remains valid;
- schema v1 still rejects lifecycle/supersession;
- schema v2 authority-only/lifecycle/supersession remain valid;
- unknown keys still fail closed;
- config revision race tests still pass for both schemas.

### Lifecycle/supersession semantics

- exactly seven lifecycle states remain;
- explicit `unknown` remains rejected;
- valid A -> B sets only A superseded;
- B is not inferred active;
- chains/convergence remain valid;
- self/duplicate/cyclic edges remain invalid;
- missing target does not supersede an otherwise unknown/active source;
- independent explicit `superseded` metadata remains effective with a missing target;
- explicit lifecycle/supersession continues to override historical heuristic correctly.

### Authority semantics

- lifecycle exclusion still precedes explicit ineligibility;
- explicit ineligibility still precedes `not_in_policy`;
- equal-precedence candidates remain all retained;
- missing stronger tiers are unchanged;
- built-in policies remain unchanged;
- no winner/correctness/agreement semantics are introduced.

### Output compatibility

- **do not change inventory JSON v1 keys**;
- **do not change authority JSON v1 keys merely to fix lifecycle show**;
- if lifecycle JSON v1 fields change for F-001, update only the Phase 2 lifecycle contract/goldens deliberately;
- preserve deterministic ordering, repository-relative paths, no default timestamps, no absolute root, no source body, and newline at EOF;
- keep repository-controlled text terminal-escaped.

### Scope

Do not introduce:

- claims or claim extraction;
- contradiction detection;
- architecture drift;
- context contracts/compiler;
- model/LLM calls;
- embeddings;
- persistence/database;
- Codebase Intelligence integration;
- mutation commands;
- automatic time-based expiry;
- lifecycle inference from filename, Git date, mtime, or body text.

---

## Files likely to change

F-001 likely requires narrow changes in:

- `src/context_integrity/rendering.py`
- one of `src/context_integrity/lifecycle.py` or another small domain helper location if a shared global-eligibility helper is introduced
- possibly `src/context_integrity/authority.py` if the resolver is refactored to share the exact gate helper without circular coupling
- `tests/test_lifecycle.py`
- lifecycle JSON fixtures under `tests/fixtures/` if the lifecycle projection changes
- `README.md` if wording needs to distinguish lifecycle-only vs combined active-authority eligibility

F-002 requires:

- `docs/implementation-reports/phase-2-implementation-report.md`

F-003 likely requires narrow changes in:

- `src/context_integrity/repository.py`
- `tests/test_repository.py`
- possibly one inventory-level regression test if needed to prove Git-ignore/discovery mode is preserved
- `README.md` repository-identity wording
- `docs/implementation-reports/phase-0-implementation-report.md`

F-004 requires provenance corrections in:

- `docs/implementation-reports/phase-0-implementation-report.md`
- `docs/implementation-reports/phase-1-implementation-report.md`
- plus the Phase 2 report work already required by F-002

F-005 requires durable review evidence under:

- `docs/reviews/`
- `docs/reviews/README.md`

After all fixes and verification:

- `docs/current-state.md` should be updated to record independent review findings as addressed/verified and name the next expected step.

Do not edit `docs/plans/phase-2-implementation-plan.md` to rewrite history.

---

## Tests / commands to run

Run targeted tests while editing, then the complete gate.

Suggested targeted commands:

```bash
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 uv run pytest tests/test_repository.py -q
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 uv run pytest tests/test_lifecycle.py -q
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 uv run pytest tests/test_authority.py tests/test_configuration.py -q
```

For F-003, add focused synthetic Git tests for inherited discovery controls and global-origin contamination; do not modify the developer's real global Git configuration in tests. Use isolated temporary HOME/config or controlled environment variables/fixtures.

Add a direct CLI smoke scenario for F-001 using schema v2 with `lifecycle = "active"` and `authority_eligible = false`, then inspect both:

```bash
uv run context-integrity lifecycle show docs/adr/a.md .
uv run context-integrity lifecycle show docs/adr/a.md . --format json
uv run context-integrity authority resolve architectural_intent .
```

The first two must communicate policy-independent active-authority ineligibility and `explicitly_ineligible`; the authority resolver must agree without the lifecycle command performing policy membership.

Then run:

```bash
git diff --check
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check
```

Record the exact final test count and Python version in the implementation report.

---

## Constraints / do not change

The Sol Medium fix session must:

1. inspect the current code before editing;
2. address **all findings F-001 through F-005** in this handoff;
3. fix F-003 first because repository/source identity is the highest-severity foundation;
4. preserve reviewed Phase 0/1/2 public contracts except where a finding explicitly requires a correction;
5. not pull Phase 3 claims/provenance implementation forward;
6. add regression tests for every behavior fix;
7. keep Git-environment remediation narrow rather than globally disabling Git security/config behavior;
8. run targeted tests after each behavioral fix, then the full offline gate;
9. update all affected implementation reports with accurate committed provenance;
10. persist the independent review layer under `docs/reviews/` without fabricating missing historical prose;
11. update `docs/current-state.md` only after verification;
12. not edit completed phase plans to rewrite history;
13. report any intentionally unfixed finding and why; the expected result is zero unresolved F-001–F-005 findings;
14. keep the change reviewable — no broad cleanup or speculative abstraction.

Do not:

- redesign authority policy;
- change repository identity algorithms beyond what F-003 requires to remove external contamination;
- add claim extraction;
- add a database;
- integrate Context Intelligence;
- add LLM/model calls;
- infer lifecycle from dates/body text;
- mutate user sources automatically;
- change old inventory/authority JSON schemas unnecessarily;
- hide missing endpoints;
- weaken config fail-closed behavior;
- disable Git `safe.directory` or other Git security globally as a shortcut;
- invent Phase 0/1 review text that is not present in canonical evidence.

### Sol Medium execution order

Use this sequence unless current code inspection reveals a safer dependency order:

1. **F-003 repository identity/discovery** — implement + repository tests.
2. Run `tests/test_repository.py` and relevant acquisition/inventory tests.
3. **F-001 lifecycle show eligibility** — implement + lifecycle/authority tests and lifecycle golden updates if required.
4. Run lifecycle/authority/config targeted tests.
5. **F-002/F-004 provenance corrections** — update Phase 0/1/2 reports against actual Git history.
6. **F-005 review evidence retention** — add current review and honest historical closure records/recovered artifacts.
7. Update README only for behavior/provenance wording actually changed.
8. Run `git diff --check`.
9. Run the complete offline `make check`.
10. Only after successful verification, update `docs/current-state.md` and record exact final test count/environment.

---

## Documentation updates after fixes

### Phase 0/1/2 implementation reports

Apply F-004 to Phase 0/1, then update Phase 2 to contain:

- baseline `36d150af6cf67b8bab41c528b4304fa83da51309`;
- original Phase 2 delivery `3ae38a6dc1fec72b24a64e3a0ccd8f6c2f7195d5`;
- independent review outcome and findings F-001 through F-005;
- concise description of each fix;
- review-fix commit(s), once available;
- exact post-fix quality-gate command/result/test count;
- any lifecycle JSON v1 contract adjustment made for F-001;
- confirmation that Phase 0 inventory and Phase 1 authority compatibility tests remain unchanged/passing.

### README

Update repository-identity wording for F-003 so "normalized origin remote" explicitly means a **repository-local** origin and inherited/global Git configuration cannot manufacture canonical identity.

If the lifecycle output contract changes, make the wording precise:

- `lifecycle_authority_eligible` (if retained) is only the lifecycle gate;
- `active_authority_eligible` is lifecycle gate + explicit global `authority_eligible`;
- policy membership is intentionally not resolved by `lifecycle show`.

### Current state

Only after the full post-fix gate succeeds, update the status from independent review pending to reviewed/fixed/verified, with the final test count and next expected step (Phase 3 planning/implementation, if otherwise ready).

---

## Review checklist

### Repository state

- [x] Correct Phase 2 implementation range identified.
- [x] Full Phase 0 -> Phase 2 commit chain identified.
- [x] Push CI found for Phase 0 review-fix, Phase 1 review-fix, and Phase 2 delivery commits.
- [ ] Repository discovery/identity is isolated from inherited Git context — **F-003**.

### Lifecycle

- [x] Seven-state model.
- [x] Eligibility matrix for lifecycle gate.
- [x] Explicit unknown rejected.

### Configuration

- [x] v1 compatibility by source/test inspection.
- [x] v2 lifecycle support.
- [x] v2 supersession support.
- [x] strict validation.
- [x] config revision consistency preserved in code/tests.

### Supersession

- [x] directional.
- [x] target not automatically active.
- [x] unique outgoing.
- [x] DAG/cycle rejection.
- [x] chains.
- [x] converging predecessors.
- [x] missing endpoints safe.
- [x] control-plane config protected.

### Classification

- [x] explicit lifecycle overrides heuristic.
- [x] historical authority restoration correct.
- [x] lifecycle provenance separated through rule matches/origin.
- [x] existing Phase 0/1 rule behavior appears preserved; no reviewed old rule IDs were intentionally renamed.

### Authority

- [x] lifecycle gate integrated in resolver.
- [x] Phase 1 built-in policies structurally unchanged.
- [x] equal-tier semantics unchanged.
- [x] missing-stronger-tier semantics unchanged.
- [ ] lifecycle **show** does not yet include explicit global eligibility in its advertised active-authority eligibility result — **F-001**.

### Output

- [x] inventory v1 remains explicit/no graph fields.
- [x] authority v1 remains explicit/no graph fields.
- [x] separate lifecycle v1 exists.
- [x] no source body/absolute root/default timestamp found in lifecycle projection.
- [ ] lifecycle show text/JSON does not yet satisfy combined active-authority eligibility semantics — **F-001**.

### Security

- [x] config path normalization/restrictions inspected.
- [x] control-plane lifecycle/supersession endpoints rejected.
- [x] terminal escaping present for new repository-controlled text paths/reasons.
- [x] no new network/code-execution/model behavior found.
- [x] unresolved edge cannot silently deactivate a source by inspected resolver logic/tests.

### Scope

- [x] No Phase 3+ functionality pulled forward materially.

### Verification / evidence

- [x] Exact Phase 2 head independently passed GitHub push CI: Ruff + **343 tests** on Python 3.12.3/Linux.
- [ ] Exact offline `UV_OFFLINE=1 make check` independently rerun after fixes — **fix session must rerun locally**.
- [x] All three implementation reports inspected.
- [ ] Phase 2 implementation report delivery provenance accurate — **F-002**.
- [ ] Phase 0/1 closure commit provenance complete — **F-004**.
- [ ] Independent review records retained under `docs/reviews/` — **F-005**.
- [x] `docs/current-state.md` inspected; it correctly marks independent Phase 2 review as pending at the reviewed commit.

---

## Definition of done for Sol Medium

The fix session is complete only when all of the following are true:

1. **F-003 is fixed first:** nested Git discovery cannot be silently changed by inherited `GIT_CEILING_DIRECTORIES` (and paired discovery controls found relevant during implementation).
2. A global/system/command-scope `remote.origin.url` cannot manufacture repository `git_remote` identity for a repo with no repository-local origin.
3. Two unrelated no-origin repositories exposed to the same global origin produce distinct repository IDs and distinct same-path source IDs.
4. Genuine repository-local origins still normalize to stable `git_remote` identity; linked worktrees and redirect protections remain correct.
5. F-001 is fixed in lifecycle-show text and machine-readable inspection semantics.
6. `active_authority_eligible` (or equivalent) means exactly lifecycle eligibility plus explicit global authority eligibility, not policy membership.
7. The precedence of lifecycle exclusion over `explicitly_ineligible` is regression-tested.
8. Actual authority resolution behavior remains unchanged and agrees with lifecycle inspection on the policy-independent gates.
9. F-002 is fixed and the Phase 2 report records original delivery `3ae38a6d...` plus the new review-fix commit once created.
10. F-004 is fixed: Phase 0 and Phase 1 reports name their actual original-delivery/review-fix commits without rewriting chronology.
11. F-005 is fixed: the current independent review is retained under `docs/reviews/`, and prior review evidence is recovered or honestly reconstructed without invented reviewer prose.
12. Any lifecycle JSON v1 change is explicit, documented, deterministic, and limited to the new Phase 2 schema; old inventory/authority schemas remain unchanged.
13. Phase 0 no-config inventory golden tests pass unchanged except for tests intentionally added around repository identity/discovery that do not alter stable contract bytes for unaffected fixtures.
14. Phase 1 no-config/schema-v1 authority golden tests pass unchanged.
15. All existing lifecycle/supersession security and missing-endpoint tests pass.
16. `git diff --check` passes.
17. The full offline gate passes:

```bash
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check
```

18. The affected implementation reports contain the post-fix command, exact test count, and accurate fix/commit evidence.
19. `docs/current-state.md` is updated only after successful verification and points to a trustworthy Phase 0–2 baseline for Phase 3.
20. No Phase 3+, database, LLM, Context Intelligence, mutation, or automatic inference scope has been introduced.
21. No finding F-001 through F-005 remains intentionally unresolved unless the session discovers a genuine contract conflict; if so, stop that specific fix path and document the conflict rather than silently redefining the phase contract.

Once these conditions hold, Phase 2 and the cumulative Phase 0–2 foundation are ready for final Sol High verification and then Phase 3 can begin from a trustworthy identity/authority/lifecycle/provenance baseline.
