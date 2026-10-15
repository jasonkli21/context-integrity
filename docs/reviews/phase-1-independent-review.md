# Context Integrity — Phase 1 Independent Post-Implementation Review

**Reviewed revision:** `9efd5fbc509adffbc11a1100ac2bb31caf8f1b6e` (`implement phase 1`)
**Baseline parent:** `d5b62adc9de40416fd715983b2ec629378a4b5c0`
**Review target:** Phase 1 — Authority and Source-of-Truth Model
**Review outcome:** **NOT READY FOR PHASE 2**
**Fix-session target:** Luna XHigh
**Primary normative plan:** `docs/plans/phase-1-implementation-plan.md`
**Implementation evidence consulted:** `docs/implementation-reports/phase-1-implementation-report.md`

> **Luna XHigh handoff preamble:** This document is the complete implementation handoff for the Luna XHigh fix session. Implement the required findings in the listed order unless repository evidence requires a safer dependency order. Do not re-review the entire phase unless needed to understand a finding. Preserve Phase 1 scope and Phase 0 compatibility. Run each finding's targeted validation and the full repository quality gate. If a finding cannot be implemented as written, document the conflict precisely rather than silently changing its intended outcome.

---

# 1. Executive Assessment

## NOT READY FOR PHASE 2

The central Phase 1 architecture is otherwise strong: authority is question-specific rather than globally ranked; policies use ordered equal-precedence tiers; the resolver is pure; same-tier candidates remain peers; historical lifecycle exclusion is enforced before explicit eligibility; missing stronger tiers are modeled explicitly; configuration is strict and fail-closed; config revision consistency is checked across initial parse, inventory observation, and final observation; authority JSON uses an explicit projection; and the Phase 0 inventory schema is kept separate.

However, one **P1 authority-semantics defect** must be fixed before Phase 2:

- repository source metadata can currently relabel an ordinary inventoried document as `executable_truth`;
- the test suite explicitly codifies that behavior as valid;
- this permits `delivered_behavior` to report tier 0 as observed even though no executable evidence was observed;
- it removes the exact “missing executable truth” gap Phase 1 was designed to preserve until real executable evidence is supplied by a later evidence boundary;
- the same unconstrained override path also permits `historical` as an authority-class override even though Phase 1 explicitly does not support lifecycle overrides and already has `authority_eligible = false` for policy-independent exclusion.

This is partly an **implementation defect** and partly a **Phase 1 plan ambiguity/defect**: the plan required generic authority-class overrides but did not explicitly reserve `executable_truth` and `historical` from repository document metadata. The implementation chose the unsafe/semantically lossy interpretation and added a regression test for it.

Two additional P2 closeout items should be completed before Phase 2:

1. strengthen contract tests so the full built-in tier membership and whole-policy replacement semantics are pinned, rather than only the first class in each tier;
2. repair the Phase 1 implementation report's verification provenance, which still states that no implementation commit exists and changes remain in the working tree even though the reviewed implementation is now commit `9efd5fbc...`.

A small P3 `explain` wording issue is also included as an optional closeout improvement.

**Luna XHigh fix pass required:** yes.
**Phase 2 blocked:** yes, until F-001, F-002, and F-003 are resolved and the full gate passes.

---

# 2. Review Scope and Evidence

## Revision reviewed

- `9efd5fbc509adffbc11a1100ac2bb31caf8f1b6e`
- commit message: `implement phase 1`
- parent/baseline: `d5b62adc9de40416fd715983b2ec629378a4b5c0`

The commit is one commit ahead of the reviewed Phase 0 baseline.

## Canonical repository context consulted

In the review prompt's requested loading order, the review inspected:

- `AGENTS.md`
- `docs/current-state.md`
- `docs/plans/phase-1-implementation-plan.md`
- `docs/architecture.md`
- relevant Phase 0 plan behavior where needed to confirm inherited inventory semantics
- Phase 1 implementation under:
  - `src/context_integrity/models.py`
  - `src/context_integrity/authority.py`
  - `src/context_integrity/configuration.py`
  - `src/context_integrity/acquisition.py`
  - `src/context_integrity/classification.py`
  - `src/context_integrity/inventory.py`
  - `src/context_integrity/rendering.py`
  - `src/context_integrity/cli.py`
- Phase 1 tests under:
  - `tests/test_authority.py`
  - `tests/test_configuration.py`
  - existing Phase 0 rendering/regression tests
- `docs/implementation-reports/phase-1-implementation-report.md`
- `README.md` / current-state changes where they describe Phase 1 semantics

No ADR changed in the Phase 1 commit, and no Phase 1-specific ADR was required to understand the implementation.

## Commit change scope confirmed

The Phase 1 commit changes the expected Phase 1 modules and docs. `pyproject.toml`, the lockfile, repository implementation, evidence boundary, and other Phase 0 infrastructure were not changed. No new runtime dependency was introduced.

## Execution / environment evidence

The review attempted to create an executable local checkout of the exact revision so the repository gate could be run independently. The review environment could not resolve `github.com`, so cloning was not possible. No already-mounted repository checkout was available.

GitHub also reports no workflow runs and no commit status checks attached to `9efd5fbc...`.

Therefore:

- the implementation report's claim that `make check` passed with 221 tests is **implementation-session evidence only**;
- this independent review did **not** re-run `make check`;
- runtime claims below are marked according to code/test inspection rather than pretending independent execution occurred;
- F-003 requires the fix session to run the full gate and record accurate final verification provenance.

## Static evidence quality

The code and tests are sufficiently small and explicit to verify most core semantics statically. In particular:

- the resolver has no filesystem/Git/CLI I/O;
- config parsing and validation are centralized;
- the safe read primitive is reused;
- explicit rendering projections are directly inspectable;
- changed-file comparison confirms the Phase 0 golden fixtures were not modified;
- existing Phase 0 golden tests still assert byte equality against those unchanged files.

---

# 3. Findings Summary

| ID | Severity | Category | Title | Fix required before Phase 2? |
|---|---|---|---|---|
| F-001 | **P1** | Authority semantics / plan defect | Repository metadata can synthesize reserved `executable_truth` (and pseudo-lifecycle `historical`) from ordinary document sources | **Yes** |
| F-002 | **P2** | Test contract | Built-in policy tests do not pin complete tier membership or full replacement semantics | **Yes** |
| F-003 | **P2** | Verification provenance / documentation | Phase 1 report is stale at the committed revision and does not bind final verification to the reviewed/fixed state | **Yes** |
| F-004 | **P3** | CLI semantics / documentation | `explain` still says authority precedence is “not inferred” without clarifying that resolution exists in a separate command | No |

---

# 4. Detailed Actionable Findings

## F-001

**Severity:** P1 — High
**Category:** Authority semantics / plan defect
**Fix required before Phase 2:** yes

### Affected files / symbols

- `src/context_integrity/configuration.py`
  - `parse_config`
  - source-metadata `authority_class` validation
- `src/context_integrity/classification.py`
  - `apply_authority_metadata`
- `src/context_integrity/authority.py`
  - behavior exposed by `resolve_authority`
- `tests/test_authority.py`
  - `test_executable_truth_can_be_observed`
  - metadata override tests
- `tests/test_configuration.py`
  - source metadata validation matrix
- `README.md`
- `docs/implementation-reports/phase-1-implementation-report.md`
- possibly `docs/current-state.md` only after fixes are verified
- **Do not rewrite the completed Phase 1 plan merely to erase the original ambiguity.** Record the corrected requirement in this review, tests, and verified implementation/report.

### Requirement / invariant

Phase 1 must preserve the distinction:

```text
observed document role
    !=
executable evidence
```

and, more specifically:

```text
delivered_behavior tier 0 = executable_truth
```

must remain unobserved in the Phase 1 document inventory unless actual executable evidence is supplied through an appropriate evidence/source boundary.

The architecture explicitly anticipates a later `EvidenceProvider` supplying executable truth. Phase 1 intentionally does not index ordinary source code.

Similarly:

```text
historical lifecycle
```

must not be simulated by assigning the `historical` authority class through a Phase 1 authority-only metadata override. Lifecycle override is explicitly out of scope, and `authority_eligible = false` already exists when a repository wants to exclude a source from authority candidacy without changing lifecycle.

### Observed behavior

`parse_config` currently accepts any `AuthorityClass` enum value for a source metadata override:

```python
override = AuthorityClass(...)
```

with no Phase 1 allowlist/reserved-class check.

`apply_authority_metadata` then replaces the effective source authority class with that value.

The repository test suite explicitly codifies the following as correct:

```python
path = "docs/verification/check.md"
authority_class = "executable_truth"
```

and asserts:

```text
highest_observed_tier == 0
missing_stronger_tiers == ()
```

for `delivered_behavior`.

This means a repository-local TOML declaration can turn a normal document source into observed `executable_truth` without any executable evidence.

The same parser also permits:

```toml
authority_class = "historical"
```

while leaving lifecycle unchanged.

### Why this is incorrect or risky

This defeats one of Phase 1's main semantic safeguards.

The point of modeling `executable_truth` before code/evidence integration is that the resolver can truthfully say:

```text
highest observed tier = verification_evidence
missing stronger tier = executable_truth
```

when executable evidence is unavailable.

The current override behavior allows config to erase that gap merely by relabeling a document. The output then says the strongest conceptual role is observed when it is not.

Even though the human disclaimer correctly says source-role precedence does not prove claim correctness, the **source role itself is now misrepresented**. This is not a claim-truth problem; it is an authority-role integrity problem.

Downstream, this is worse:

- Phase 3 could bind claims to a source carrying a fabricated `executable_truth` role.
- A later Codebase Intelligence / `EvidenceProvider` can supply genuine executable evidence, but the manually relabeled document would already occupy the same role/tier.
- Consumers would need a second trust dimension to distinguish real executable evidence from a document that self-declared the same class, forcing avoidable redesign.
- Allowing `historical` as an authority override also creates a backdoor semantic substitute for lifecycle, which Phase 2 is supposed to own.

### Required outcome

For Phase 1 source metadata, reserve authority classes that cannot be synthesized from document metadata.

At minimum:

- **reject `executable_truth` as a `source_metadata.authority_class` override in Phase 1**;
- **reject `historical` as a `source_metadata.authority_class` override in Phase 1**;
- continue to allow `executable_truth` in **policy tiers**;
- continue to reject `historical` and `unknown` as **active policy tiers**;
- `unknown` may remain a valid explicit source authority override, consistent with the implementation's conservative declassification behavior;
- use `authority_eligible = false` for policy-independent exclusion instead of a `historical` authority override;
- preserve the Phase 0 historical lifecycle overlay and its exclusion behavior;
- future executable evidence should enter through the intended executable/evidence seam, not by declaring a document to be executable truth.

If the implementation team has repository evidence showing a real Phase 1 requirement for a document to be explicitly promoted to `executable_truth`, do not silently retain the current behavior. Document the architectural conflict and define a provenance-bearing evidence type first.

### Recommended implementation direction

The smallest safe Phase 1 fix is in configuration validation.

Define the source-metadata override set intentionally rather than treating every enum member as valid metadata input.

Conceptually:

```text
allowed Phase 1 metadata overrides:
- verification_evidence
- decision
- architecture_product
- operating_instruction
- plan
- generated_derivative
- unknown

reserved from Phase 1 source metadata:
- executable_truth
- historical
```

The exact constant/helper placement can follow repository style.

Do not change `AuthorityClass` itself and do not remove `EXECUTABLE_TRUTH` from policies.

Do not add a new evidence subsystem in Phase 1.

### Plan defect / corrected requirement

The Phase 1 plan was underspecified here. It said source metadata could override authority class and separately said `executable_truth` is a valid policy class that may remain unobserved. It did not explicitly state that document metadata must not synthesize reserved evidence/lifecycle classes.

**Luna XHigh should follow this review's corrected requirement rather than the original Phase 1 plan wording for this issue.**

The completed plan should remain historical planning evidence; do not rewrite it to make the omission disappear.

### Likely files to change

- `src/context_integrity/configuration.py`
- `tests/test_configuration.py`
- `tests/test_authority.py`
- `README.md`
- `docs/implementation-reports/phase-1-implementation-report.md`
- `docs/current-state.md` only after verification, if status changes

No architecture edit is required unless implementation discovers a broader evidence-role rule not already represented by `docs/architecture.md`.

### Tests to add or update

1. Replace `test_executable_truth_can_be_observed` with a regression proving Phase 1 metadata cannot synthesize executable truth.
2. Add config validation cases:

```toml
authority_class = "executable_truth"
```

=> configuration error.

```toml
authority_class = "historical"
```

=> configuration error.

3. Preserve a test showing `unknown` override remains valid if that is the chosen conservative behavior.
4. Preserve a test showing a normal override such as `verification_evidence` remains valid.
5. Preserve/strengthen `delivered_behavior` missing-tier behavior:
   - verification document observed;
   - no executable evidence;
   - highest observed tier = 1;
   - missing stronger tier includes tier 0 / `executable_truth`.
6. Preserve historical lifecycle + authority override ordering:
   - an actually historical source remains excluded as `historical_lifecycle`;
   - no metadata field may reactivate it.
7. Add/retain CLI exit-6 coverage for a config that attempts a reserved source-metadata class.

### Non-goals / do not change

- Do not remove `executable_truth` from `AuthorityClass`.
- Do not remove it from the `delivered_behavior` policy.
- Do not add code scanning.
- Do not add `EvidenceProvider` implementation.
- Do not add Phase 2 lifecycle states.
- Do not add claims.
- Do not reinterpret policy override semantics.
- Do not make `authority_eligible=false` mutate lifecycle.
- Do not change Phase 0 no-config inventory JSON.

### Documentation updates required

Update:

- `README.md`: clarify that repository source metadata can correct document authority roles but cannot manufacture `executable_truth` or lifecycle/historical semantics in Phase 1.
- `docs/implementation-reports/phase-1-implementation-report.md`: remove the claim that source class overrides may set historical; document the reserved-class validation and regression tests.
- `docs/current-state.md`: only after verification if a concise statement is needed.

Do not retroactively edit the completed Phase 1 plan.

### Verification

Targeted tests should include the exact new rejection scenarios plus existing authority tests.

Then run:

```bash
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check
```

Observable acceptance behavior:

- a config attempting `source_metadata.authority_class = "executable_truth"` fails closed with configuration error / CLI exit 6;
- a config attempting `source_metadata.authority_class = "historical"` fails closed;
- a policy tier containing `executable_truth` remains valid;
- `delivered_behavior` still reports missing executable truth when only verification evidence is observed;
- no-config Phase 0 goldens remain byte-identical.

### Downstream relevance

This prevents Phase 3+ from inheriting an authority class whose provenance is semantically untrustworthy, and keeps the later Codebase Intelligence / `EvidenceProvider` integration meaningful: actual executable evidence can occupy the existing tier without needing a second mechanism to distinguish it from manually relabeled documents.

---

## F-002

**Severity:** P2 — Medium
**Category:** Test contract
**Fix required before Phase 2:** yes

### Affected files / symbols

- `tests/test_authority.py`
  - `EXPECTED`
  - `test_exact_builtin_set`
  - `test_metadata_and_policy_merge`
  - custom policy replacement/addition tests
- possibly no production code changes

### Requirement / invariant

The review contract requires tests to pin:

- every built-in policy ID;
- every tier;
- all classes in every tier;
- tier order;
- built-in policy version;
- deterministic listing;
- complete replacement semantics when repository config redefines a built-in.

Equal-precedence tiers are a core Phase 1 semantic. Adding an extra class to a tier is not a cosmetic change.

### Observed behavior

`test_exact_builtin_set` currently constructs the actual policy matrix using:

```python
[t.classes[0].value for t in p.tiers]
```

It checks only the **first class** in each tier.

Therefore a regression such as:

```text
delivered_behavior
tier 0 = [executable_truth, decision]
```

would still satisfy the current exact-matrix assertion as long as `executable_truth` remained first.

The implementation itself is currently correct; the defect is that the core contract test would fail to catch an unauthorized equal-tier expansion.

Similarly, `test_metadata_and_policy_merge` proves that the custom first tier takes effect but does not directly assert that the effective overridden policy's entire tier list is exactly the repository definition with no inherited/trailing built-in tiers.

### Why this is incorrect or risky

Phase 1 deliberately distinguishes equal-precedence tier membership from ordering. An unexpected extra class in a tier changes authority semantics materially while preserving the first element.

The current test shape is therefore weaker than the semantic contract it claims to pin.

Whole-policy replacement is also a critical configuration rule; a future accidental merge/append implementation should fail a direct structural assertion, not merely happen to produce the same candidate for one fixture.

### Required outcome

Strengthen tests so they compare complete nested tier membership.

Recommended expected shape:

```python
EXPECTED = {
    "delivered_behavior": (
        ("executable_truth",),
        ("verification_evidence",),
        ("generated_derivative",),
    ),
    ...
}
```

and compare every tier/class exactly.

Also assert:

- `origin == "builtin"` for built-ins;
- `policy_version == "builtin-v1"`;
- deterministic effective policy ID listing;
- a repository override of a built-in has **exactly** the configured tiers and no inherited built-in tail.

Descriptions may be pinned if the project wants them treated as public contract, but that is not required to resolve this finding.

### Recommended implementation direction

Test-only change unless stronger tests reveal a production defect.

For replacement semantics, use a custom override whose tier structure is intentionally unlike the built-in, such as one or two tiers, and assert exact equality of the resulting nested tier structure.

### Likely files to change

- `tests/test_authority.py`

Potentially `src/context_integrity/authority.py` only if stronger tests expose an actual regression; current implementation appears correct.

### Tests to add or update

- full nested built-in matrix assertion;
- built-in origin/version assertion;
- deterministic sorted policy list assertion;
- exact whole-policy replacement assertion;
- keep equal-precedence custom-tier behavior test.

### Non-goals / do not change

- Do not change correct built-in policy semantics just to satisfy a new test.
- Do not convert tiers into scalar ranks.
- Do not impose ordering among classes inside one tier.
- Do not add generic property-testing infrastructure unless it materially simplifies the existing small suite.

### Documentation updates required

None unless a stronger test reveals a real semantic difference.

### Verification

Run:

```bash
uv run pytest tests/test_authority.py -q
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check
```

The test should fail if any extra class is inserted into a built-in tier or if replacement starts merging with the built-in.

### Downstream relevance

This locks the authority-policy contract before lifecycle and claims begin depending on it.

---

## F-003

**Severity:** P2 — Medium
**Category:** Verification provenance / documentation mismatch
**Fix required before Phase 2:** yes

### Affected files / symbols

- `docs/implementation-reports/phase-1-implementation-report.md`
- `docs/current-state.md` after the fix pass is verified
- final review/fix verification procedure
- no production code necessarily required

### Requirement / invariant

Implementation reports are evidence, not authority, but they must accurately identify what revision/state was implemented and verified.

The Phase 1 plan explicitly required:

- implementation commit(s);
- exact baseline;
- exact tests run;
- verification evidence;
- distinction between implemented / verified / deferred.

`AGENTS.md` likewise treats implementation reports as implementation evidence and requires `make check` after editing.

For Phase 1 closeout, the verified state should be tied to a concrete repository state rather than a now-stale working-tree description.

### Observed behavior

At reviewed commit `9efd5fbc...`, the report still says:

```text
Implementation commits: None created; changes remain in the working tree.
```

That is no longer true: the Phase 1 implementation is committed as `9efd5fbc...`.

The report says the full gate passed with 221 tests, but its wording describes a pre-commit working tree. The reviewed commit has no attached GitHub workflow run or status check.

The independent review environment could not clone the repository, so the reviewer could not independently bind the 221-test claim to the commit by rerunning the gate.

This does **not** prove the tests did not pass. It means the final immutable verification provenance is weaker than the report claims.

### Why this is incorrect or risky

The project is explicitly designed around context/provenance integrity. Its own phase report should not contain a known-false revision-state statement.

Starting Phase 2 with a baseline that says "verified" while its evidence refers to an uncommitted state makes later context archaeology harder:

- which tree was actually tested?
- did any edits occur between the 221-test gate and the commit?
- were documentation/current-state edits included in final verification?
- what exact state should Phase 2 treat as the closed Phase 1 baseline?

The implementation report itself notes that current-state was edited after the 221-test gate, reinforcing the need for a final post-fix gate.

### Required outcome

After F-001/F-002 are implemented:

1. run the complete repository gate on the final fix-pass tree;
2. update the Phase 1 report so its provenance is truthful;
3. identify `9efd5fbc...` as the original Phase 1 implementation revision reviewed here;
4. identify the independent review/fix pass and the exact final verification command/results;
5. remove any statement that changes "remain in the working tree" once that is no longer true;
6. update `docs/current-state.md` only after the full final gate passes.

If the report cannot know the SHA of the commit that will contain its own final edit, do **not** fabricate a self-referential SHA. Use truthful wording such as:

- original implementation revision;
- fix-pass base revision;
- exact verification state/branch/working-tree cleanliness at the time of the gate;
- subsequent commit recorded in a later closeout step if desired.

No new CI system is required by this finding.

### Recommended implementation direction

Keep this as a documentation/provenance correction, not an infrastructure project.

A useful report structure is:

```text
Original Phase 1 implementation revision: 9efd5fbc...
Independent review: docs/reviews/phase-1-independent-post-implementation-review.md
Fix pass: [truthful revision/state description]
Final verification:
  UV_CACHE_DIR=... UV_OFFLINE=1 make check
  <actual test/lint result>
Phase 0 goldens: unchanged / verified
```

### Likely files to change

- `docs/implementation-reports/phase-1-implementation-report.md`
- `docs/current-state.md`

### Tests to add or update

No new production test is required solely for this finding.

The fix pass itself must run the full gate after all code/test/doc changes that matter to Phase 1 closeout.

### Non-goals / do not change

- Do not add GitHub Actions solely for this finding.
- Do not claim this independent review ran the 221-test gate; it did not.
- Do not rewrite historical Phase 0 evidence.
- Do not change architecture for a provenance-documentation issue.

### Documentation updates required

Required, as above.

### Verification

Run:

```bash
git status --short
git rev-parse HEAD
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check
```

Then inspect the report/current-state and ensure they describe the actual verified state, not the pre-commit implementation session.

### Downstream relevance

Phase 2 needs an unambiguous Phase 1 baseline. This is exactly the kind of context drift the project exists to prevent.

---

## F-004

**Severity:** P3 — Low
**Category:** CLI semantics / documentation clarity
**Fix required before Phase 2:** no

### Affected files / symbols

- `src/context_integrity/rendering.py`
  - `render_explanation`
- `tests/test_authority.py`
  - explain-output assertions

### Requirement / invariant

`explain` should remain policy-independent and must not run a whole authority resolution.

But Phase 1 now **does** support question-specific authority resolution through:

```bash
context-integrity authority resolve POLICY_ID
```

The Phase 1 plan also asked `explain` to make clear that explicit authority eligibility affects Phase 1 authority resolution.

### Observed behavior

`render_explanation` currently ends with:

```text
Not inferred:
- active, superseded, expired, or invalid status; supersession relationships
- authority precedence, claim correctness, implementation delivery, or drift
```

That wording was appropriate for Phase 0, but in Phase 1 it is ambiguous: authority precedence is now resolvable by a separate command.

The metadata section shows:

```text
authority_eligible: false
reason: ...
```

but does not explicitly state that this field changes authority-resolution candidacy.

### Why this is incorrect or risky

A user reading `explain` can reasonably interpret "authority precedence [is] not inferred" as meaning the product still lacks authority resolution entirely.

The correct boundary is narrower:

- `explain` does not itself resolve a question-specific policy;
- `authority resolve` does;
- claim correctness/agreement and lifecycle/supersession remain genuinely uninferred.

### Required outcome

Make the wording command-local and explicit.

For example:

```text
Authority resolution:
- explicit authority eligibility affects Phase 1 authority resolution.
- question-specific precedence is not resolved by `explain`; use `authority resolve POLICY_ID`.

Not inferred:
- active/superseded/expired/invalid lifecycle or supersession relationships
- claim correctness or agreement
- implementation delivery or drift
```

Exact prose can differ.

Do not make `explain` accept a policy ID or run resolution.

### Recommended implementation direction

Small renderer/test change only.

### Likely files to change

- `src/context_integrity/rendering.py`
- `tests/test_authority.py`

### Tests to add or update

- explain with `authority_eligible=false` includes a policy-independent candidacy note;
- output clearly distinguishes "not resolved by this command" from "not implemented by the product";
- no authority policy lookup is performed by `explain`.

### Non-goals / do not change

- Do not add policy resolution to `explain`.
- Do not add Phase 2 lifecycle semantics.
- Do not expand inventory JSON.

### Documentation updates required

None beyond renderer/test unless README contains the same ambiguous wording.

### Verification

```bash
uv run pytest tests/test_authority.py -q
```

Manual smoke:

```bash
uv run context-integrity explain <metadata-target> --root <fixture>
uv run context-integrity authority resolve architectural_intent <fixture>
```

The two commands should have clearly distinct responsibilities.

### Downstream relevance

Low. This is primarily context hygiene and user-facing semantic clarity.

---

# 5. Non-Actionable Observations

These are deliberately **not** in the required fix queue.

## 5.1 Core resolver design is appropriate

`resolve_authority` is pure with respect to filesystem/Git/CLI concerns. It consumes structured inventory/policy state, checks historical lifecycle before explicit ineligibility, maps recognized authority classes to declared tiers, keeps all highest-tier candidates, retains lower candidates, reports missing stronger tiers, and sorts sources deterministically by repository-relative path.

No global scalar authority rank exists.

## 5.2 Config consistency design is stronger than a simple two-read check

The implementation:

1. safely reads/parses config;
2. inventories the config as a source;
3. compares the inventoried raw-byte hash to the parsed config hash;
4. safely reads/parses config again at the end;
5. fails if initial/final/inventory hashes disagree.

The tests include replacement, removal, symlink, appearance, and post-read mutation scenarios.

No fix is required here based on static review.

## 5.3 Full atomic repository snapshots are not required

The implementation correctly documents that scans are sequential and content-hash consistency does not make the whole repository atomic. Phase 1 only requires fail-closed consistency for the authority config itself.

## 5.4 Real repository implementation reports remain conservatively classified

The current classifier does not automatically interpret `docs/implementation-reports/*` as verification evidence; the implementation report itself documents this. Given the hard Phase 0 no-config compatibility requirement and Phase 1's explicit-metadata mechanism, this is an acceptable conservative limitation rather than a Phase 1 defect.

## 5.5 POSIX-only safe reads are inherited and documented

No Windows-safe-read expansion is required in Phase 1.

## 5.6 `unknown` authority-class metadata override may remain allowed

An explicit `unknown` override is a conservative declassification and does not synthesize stronger evidence or lifecycle. It should remain distinct from the reserved `executable_truth` and `historical` cases in F-001.

## 5.7 No future-phase leakage was found

The implementation adds no:

- claims;
- contradiction engine;
- active/superseded lifecycle;
- supersession graph;
- architecture drift;
- context contracts/compiler;
- LLM/model integration;
- persistence;
- Codebase Intelligence integration;
- MCP/server/daemon.

---

# 6. Acceptance-Criteria Audit

Statuses use the review prompt's required vocabulary:

- **verified** — supported by direct code/contract inspection;
- **partially verified** — implementation appears present, but a material test/provenance issue remains;
- **not verified** — the review environment could not independently establish the claim;
- **not implemented** — absent;
- **not applicable** — not required for this implementation.

## 6.1 Domain / Semantics

| Acceptance criterion | Status | Review evidence / finding |
|---|---|---|
| `AuthorityClass.EXECUTABLE_TRUTH` exists | verified | Present in `models.py`. |
| `.context-integrity.toml` represented as `SourceKind.CONFIGURATION` | verified | Exact classification rule + config candidate integration. |
| Authority policy is question-specific, not global | verified | Separate built-ins; resolver requires selected policy. |
| Policies contain ordered equal-precedence tiers | partially verified | Implementation is correct; F-002 requires stronger full-membership contract tests. |
| Multiple top-tier candidates are not contradictions | verified | Resolver returns all; no contradiction type/logic. |
| Historical lifecycle excludes active authority candidacy | verified | Historical check precedes eligibility/class lookup. |
| Missing stronger tiers are explicit | **partially verified** | Core resolver correct, but F-001 allows document metadata to fabricate `executable_truth` and erase the intended gap. |
| “Highest observed” is never represented as “correct truth” | verified | Model/output naming and mandatory text disclaimer preserve distinction. |
| No recency/mtime/Git-time authority inference | verified | Resolver never reads those values for precedence. |

## 6.2 Built-In Policies

| Acceptance criterion | Status | Review evidence / finding |
|---|---|---|
| `delivered_behavior` exact semantics | verified | Code definition correct; F-002 strengthens regression test. |
| `architectural_intent` exact semantics | verified | Code definition correct. |
| `operating_instructions` exact semantics | verified | Code definition correct. |
| `implementation_status` exact semantics | verified | Code definition correct. |
| `future_work` exact semantics | verified | Code definition correct. |
| Built-in policy version explicit/stable | verified | `builtin-v1`. |

## 6.3 Configuration

| Acceptance criterion | Status | Review evidence / finding |
|---|---|---|
| Optional `.context-integrity.toml` supported | verified | Absent config returns empty repository config; built-ins apply. |
| No config preserves Phase 0 behavior | verified | No-config path is additive-only; Phase 0 projection unchanged; original golden fixtures unchanged and exact-equality tests remain. |
| Schema version validated | verified | Exact integer type and value 1 required. |
| Repository policy replaces built-in by ID | verified | `dict.update` whole-object replacement; F-002 requests direct exact-structure test. |
| Repository policy can add custom ID | verified | Effective policy merge supports new IDs. |
| Invalid/duplicate tiers fail | verified | Tier and policy validation. |
| `historical` / `unknown` cannot be active policy tiers | verified | `AuthorityTier` rejects them. |
| Source authority-class override supported | **partially verified** | Feature works, but F-001 finds unsafe reserved-class scope. |
| Source authority eligibility supported | verified | Global policy-independent false exclusion. |
| Override reason required | verified | Nonblank `_text` required for metadata. |
| Stale metadata path emits structured warning | verified | Deterministic `authority_metadata_source_missing`. |
| Lifecycle override is not supported | **partially verified** | No lifecycle field is allowed, but F-001 notes `authority_class="historical"` is a semantic backdoor that should be rejected. |
| Config safely read and hashed | verified | Shared descriptor-safe bounded read + SHA-256. |
| Unsafe/invalid config fails with exit 6 | verified by code/tests | Independent CLI execution not performed, but exception mapping and tests are explicit. |

## 6.4 CLI / Output

| Acceptance criterion | Status | Review evidence / finding |
|---|---|---|
| `authority list` works | verified by code/tests | Command wiring + renderer explicit. |
| `authority show` works | verified by code/tests | Command wiring + renderer explicit. |
| `authority resolve` works | verified by code/tests | Command wiring + resolver/renderers explicit. |
| Text resolution states semantic limitation | verified | Mandatory `AUTHORITY_DISCLAIMER`. |
| Authority JSON schema version 1 | verified | Explicit top-level `schema_version: 1`. |
| JSON uses explicit projection | verified | Dedicated helper projections; no dataclass recursion. |
| JSON deterministic | verified by static inspection | Candidate/exclusion/warning ordering and `sort_keys=True` are deterministic. |
| JSON contains no absolute root/body | verified | Projection excludes both. |
| No-candidate resolution exits 0 | verified by code/tests | Resolver returns valid status; CLI does not convert to error. |
| Unknown policy exits 2 | verified by code/tests | `typer.BadParameter`. |
| Config error exits 6 | verified by code/tests | `load_inventory` maps `ConfigurationError` to exit 6. |

## 6.5 Integration / Regression

| Acceptance criterion | Status | Review evidence / finding |
|---|---|---|
| `scan` applies explicit authority-class metadata | verified | Inventory applies metadata after base classification. |
| `explain` shows explicit authority metadata/eligibility | verified, wording improvement F-004 | Fields/reason shown; command-boundary wording can improve. |
| Config source is inventoried | verified | Forced root config observation when needed. |
| Phase 0 no-config JSON goldens remain byte-identical | verified by static contract inspection | Original goldens unchanged; explicit projection unchanged; exact golden assertions retained. |
| Existing security/repository protections remain intact | verified by static inspection | New config reads reuse safe read boundary; repository module unchanged. |
| No database added | verified | No dependency/module change. |
| No LLM/model dependency added | verified | No dependency/module change. |
| No Codebase Intelligence dependency added | verified | Evidence boundary remains unintegrated. |
| No claim model/extraction added | verified | No claim types or body parsing. |
| No supersession graph added | verified | Lifecycle vocabulary remains Phase 0 subset. |

## 6.6 Testing / Docs

| Acceptance criterion | Status | Review evidence / finding |
|---|---|---|
| All built-in policies tested | **partially verified** | Tests exercise all policies, but F-002 shows exact tier membership is not fully pinned. |
| Config validation thoroughly tested | verified | Large invalid matrix + safe-read/race tests. |
| Authority golden JSON tests pass | **not independently verified** | Tests/goldens exist; review could not execute them. |
| Phase 0 regression suite passes | **not independently verified** | Existing tests retained; implementation report claims pass. |
| Full offline `make check` passes | **not verified** | Implementation report says 221 tests passed; no independent execution/CI evidence for reviewed commit. F-003. |
| README documents behavior/limitations | partially verified | Generally accurate; F-001 requires reserved-class correction. |
| Phase 1 report maps every acceptance criterion | partially verified | Mapping exists; provenance/state wording is stale. F-003. |
| Current-state updated only after verification | not independently verified | Report says current-state was edited after the 221-test gate; final committed-state verification should be re-established under F-003. |

---

# 7. Authority-Semantics Audit

| Semantic invariant | Assessment |
|---|---|
| No global rank | **Verified.** No scalar/global precedence map exists. |
| Equal-precedence tiers | **Verified in implementation.** F-002 strengthens the regression contract. |
| Highest observed vs strongest possible | **Defect under explicit metadata.** Base resolver is correct, but F-001 allows a document to be relabeled `executable_truth`, falsely making strongest possible appear observed. |
| Missing stronger tiers | **Correct in resolver, compromised by F-001.** |
| Same-tier behavior | **Verified.** All peers returned; deterministic path order is presentation only. |
| Historical exclusion | **Verified for actual historical lifecycle.** Historical check occurs first. |
| Unknown handling | **Verified.** Unknown remains valid inventory and becomes `not_in_policy`. |
| No claim-truth implication | **Verified.** Wording and model avoid winner/truth semantics. |
| No recency/supersession shortcut | **Verified.** Resolver does not read recency and no supersession model exists. |

## Key conclusion

The resolver is semantically correct **given trustworthy authority classes**.

F-001 is therefore located at the source-role trust boundary: Phase 1 currently allows config metadata to create an authority role that should be reserved for a different evidence domain.

---

# 8. Configuration-Security Audit

| Area | Assessment |
|---|---|
| Safe read | **Verified.** Config uses `read_source_bytes` -> shared descriptor-safe `_read_source`. |
| Symlinks | **Verified.** Symlink config fails closed; replacement-by-symlink test exists. |
| Traversal | **Verified.** Metadata path normalization rejects `..`, absolute paths, Windows ambiguity. |
| Malformed config | **Verified.** Parse errors become generic `ConfigurationError`. |
| Strict validation | **Verified with semantic exception F-001.** Unknown keys/types/tiers are strict; reserved source-role semantics need tightening. |
| Config size | **Verified.** Reuses 5 MiB bounded read and growth defense. |
| No execution/network | **Verified.** `tomllib` data only; no include/import/fetch/exec path. |
| Config/inventory revision consistency | **Verified by code/test inspection.** Initial hash, inventoried hash, final hash must agree. |
| Fail-closed behavior | **Verified.** Present invalid/unsafe/inconsistent config does not fall back to built-ins. |
| Exit-code behavior | **Verified by code/tests; not independently executed.** Config maps to 6. |

No P0 security issue was found.

---

# 9. Backward-Compatibility Audit

## Phase 0 no-config JSON

**Assessment:** preserved by implementation design.

Evidence:

- inventory-v1 renderer still uses explicit key projection and does not serialize `authority_config` or `authority_metadata`;
- new internal fields have defaults and are omitted from Phase 0 JSON;
- config candidate special-casing affects only an actually present `.context-integrity.toml`;
- new config classification rule is exact-path only;
- original Phase 0 golden fixture files were not modified in the Phase 1 commit;
- existing tests still compare exact rendered bytes to those golden files.

Independent execution was unavailable, so final fix verification must rerun the suite.

## Existing rule IDs

No existing Phase 0 rule IDs were renamed. The config rule and metadata override rule are additive.

## Existing CLI behavior

`scan`, `explain`, and `version` remain structurally compatible. Config introduces a new deliberate exit-6 case when a policy config exists and is unsafe/invalid.

## Existing security protections

No regression found. The new config path reuses rather than bypasses the Phase 0 descriptor-safe source read.

## Intentional Phase 0 public-contract change

No Phase 0 inventory-v1 schema change was introduced.

---

# 10. Test-Quality Assessment

## Strong areas

The Phase 1 test suite is substantially better than a happy-path suite.

It covers:

- all five built-in policies behaviorally;
- multiple highest-tier candidates;
- no-recency behavior;
- no-candidate behavior;
- historical exclusion;
- explicit ineligibility;
- stale metadata warning;
- unknown authority override;
- config schema/type/key validation;
- duplicate normalized metadata paths;
- symlink/directory/oversized/unreadable config;
- config replacement/removal/appearance/symlink/race consistency;
- ignored config inventory;
- explicit authority JSON key sets;
- three authority golden scenarios;
- CLI exit codes;
- terminal-control escaping;
- Phase 0 byte-golden tests retained unchanged.

## Material gaps

### F-001 — one test currently enforces the wrong semantic

`test_executable_truth_can_be_observed` should not survive unchanged. It turns the core Phase 1 missing-evidence safeguard into a config-declared role.

### F-002 — exact built-in tier contract is under-pinned

The test only records `classes[0]` per tier. It must compare full nested tier membership.

### F-003 — test execution provenance is not independently bound to the commit

No CI/status exists for the reviewed commit and this review could not run the repository. The fix pass must provide final local gate evidence.

No other material test gap was found that warrants a separate finding.

---

# 11. Plan / Architecture Issues Discovered

## Plan defect / ambiguity: reserved source-metadata authority classes

The Phase 1 plan simultaneously established that:

- `executable_truth` exists so a stronger unobserved tier can be represented before code/evidence integration;
- a later `EvidenceProvider` may supply executable truth;
- repository source metadata can override authority class;
- lifecycle override is not supported.

It did not explicitly define which authority classes source metadata is allowed to synthesize.

The implementation interpreted that omission as “all enum values,” including `executable_truth` and `historical`.

That interpretation undermines the architecture.

Corrected Phase 1 requirement:

> Repository source metadata may correct document authority roles, but Phase 1 must not synthesize `executable_truth` or `historical` through an authority-only document metadata override. `executable_truth` remains valid in policy tiers for future executable evidence. Actual historical behavior remains a lifecycle concern, and policy-independent exclusion uses `authority_eligible=false`.

**Luna XHigh should follow the review's corrected requirement rather than the original Phase 1 plan wording for this issue.**

No other plan defect requiring architecture redesign was found.

---

# 12. Required Fix Set

## Required before Phase 2

### Fix order

1. **F-001 — Reserve `executable_truth` / `historical` from Phase 1 source metadata**
   - **Desired outcome:** ordinary document/config metadata cannot fabricate executable evidence or pseudo-lifecycle semantics.
   - **Likely files:** `configuration.py`, authority/config tests, README, Phase 1 report.
   - **Prerequisites:** none.
   - **Target validation:** reserved metadata classes fail closed; policy `executable_truth` remains valid; delivered-behavior missing tier 0 remains explicit.

2. **F-002 — Pin complete policy/replacement contracts**
   - **Desired outcome:** tests fail for any extra class/tier or accidental policy merge.
   - **Likely files:** `tests/test_authority.py`.
   - **Prerequisites:** F-001 test changes should be applied first so the final suite reflects corrected semantics.
   - **Target validation:** full nested policy matrix and exact replacement assertions.

3. **F-003 — Re-establish final verification provenance**
   - **Desired outcome:** Phase 1 report/current-state describe the actual reviewed/fixed state and final gate result truthfully.
   - **Likely files:** implementation report and current-state.
   - **Prerequisites:** F-001/F-002 complete.
   - **Target validation:** full offline `make check` after fixes; documentation matches actual revision/state.

## Optional / defer

4. **F-004 — Clarify `explain` authority wording**
   - **Desired outcome:** `explain` says policy resolution is not performed by that command, rather than implying authority resolution is not implemented.
   - **Likely files:** `rendering.py`, `tests/test_authority.py`.
   - **Target validation:** targeted explain-output test.
   - This can be implemented in the same fix pass because it is small, but it does not independently block Phase 2.

---

# 13. Global Fix-Pass Constraints

Luna XHigh must preserve all of the following:

- remain within Phase 1;
- do not add claims;
- do not add contradiction detection;
- do not add active/superseded lifecycle inference;
- do not add supersession graphs;
- do not add persistence;
- do not add LLM/model calls;
- do not add Codebase Intelligence integration;
- do not add ordinary source-code indexing;
- do not implement `EvidenceProvider` yet;
- keep `executable_truth` in the domain enum and policy tier model;
- prevent Phase 1 document metadata from fabricating reserved evidence/lifecycle roles;
- preserve Phase 0 inventory JSON v1 byte compatibility;
- preserve existing Phase 0 rule IDs;
- preserve safe-read and Git-root protections;
- preserve config revision consistency;
- preserve all same-tier candidates as peers;
- preserve no-recency behavior;
- preserve `authority_eligible=false` as authority-only metadata;
- preserve actual historical lifecycle exclusion before eligibility/class lookup;
- keep fixes minimal and test-backed;
- do not perform unrelated cleanup;
- do not rewrite the completed Phase 1 plan to hide the discovered plan ambiguity;
- update reports/current-state only after verification.

---

# 14. Expected Post-Fix Verification

## Targeted semantic/config tests

At minimum, add/run tests proving:

- source metadata `executable_truth` is rejected;
- source metadata `historical` is rejected;
- source metadata `unknown` remains valid if intentionally retained;
- source metadata `verification_evidence` remains valid;
- policy tiers may still contain `executable_truth`;
- policy tiers still reject active `historical` / `unknown`;
- delivered behavior with only verification evidence reports:
  - highest observed tier 1;
  - missing stronger tier 0 / `executable_truth`;
- same-tier candidates remain peers;
- actual historical lifecycle remains excluded;
- `authority_eligible=false` remains exclusion-only and does not mutate lifecycle;
- config errors still exit 6;
- no source body / absolute root leaks into authority JSON.

## Contract tests

Prove:

- every built-in ID;
- complete nested tier membership;
- built-in version;
- deterministic listing;
- custom policy addition;
- exact whole-policy replacement with no merge/inheritance.

## Phase 0 regression

Prove:

- no-config inventory goldens remain byte-identical;
- existing rule IDs remain;
- existing scan/explain/version behavior remains compatible;
- safe-read/Git redirect/deleted/disappearing-source regressions still pass.

## Full gate

Always finish with:

```bash
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check
```

Expected outcome:

- Ruff lint/format pass;
- all tests pass;
- all required findings have regression tests where applicable;
- invalid config fails closed;
- config revision consistency tests still pass;
- authority JSON remains deterministic;
- delivered-behavior missing executable truth is explicit without genuine executable evidence;
- multiple same-tier candidates remain peers;
- historical sources remain excluded;
- no Phase 2+ semantics were introduced.

## Manual CLI smoke

Use a small synthetic repo/config:

```bash
uv run context-integrity authority list .
uv run context-integrity authority show delivered_behavior .
uv run context-integrity authority resolve delivered_behavior .
uv run context-integrity authority resolve delivered_behavior . --format json
```

Also confirm a config attempting:

```toml
[[source_metadata]]
path = "docs/verification/check.md"
authority_class = "executable_truth"
reason = "should be rejected in Phase 1"
```

fails closed with configuration exit code 6.

If F-004 is implemented, smoke `explain` and confirm its wording distinguishes command-local non-resolution from product-level unimplemented semantics.

---

# 15. Downstream Readiness

## Current state

**Phase 1 is not ready to serve as the Phase 2 baseline at commit `9efd5fbc...`.**

The blocker is narrow, not architectural collapse:

- the policy/resolver model is good;
- the config security boundary is good;
- the public JSON separation is good;
- the Phase 0 compatibility design is good;
- but source-role metadata currently has too much semantic power.

## After required fixes

After F-001, F-002, and F-003 pass targeted validation and the full repository gate:

**Phase 1 should provide a sound foundation for Phase 2 — Lifecycle and Supersession.**

In particular:

- Phase 2 can add richer lifecycle decisions without changing authority tier semantics;
- actual lifecycle can continue filtering candidates before authority selection;
- Phase 3 can bind claims to source authority without inheriting document-fabricated executable truth;
- a future `EvidenceProvider` can supply genuine `executable_truth` into the existing policy model;
- multiple evidence types can occupy one equal-precedence tier;
- repository policies remain independent of persistence/transport.

No architectural reconsideration is required beyond the corrected reserved-class rule in F-001.

---

# 16. Final Questions

## Is the Phase 1 implementation trustworthy enough to begin Phase 2 — Lifecycle and Supersession, or are there correctness, security, semantic, or architectural defects that must be fixed first?

**Not yet.**

The central resolver/config architecture is largely trustworthy, but F-001 is a real authority-semantics defect: a Phase 1 repository document can be manually relabeled `executable_truth`, causing the system to report the strongest delivered-behavior tier as observed without actual executable evidence. This breaks the intended missing-evidence boundary and would pollute future claim/evidence reasoning.

F-002 and F-003 are also required closeout work so the corrected contract is pinned and the Phase 1 baseline is verified/provenanced accurately.

After those required fixes and a clean full gate, Phase 2 can proceed without redesigning the authority model.

## If this review document is handed directly to Luna XHigh with no additional prompt, does it contain everything necessary to implement and verify every required fix without reopening the Phase 1 design from scratch?

**Yes.**

For each required finding this document specifies:

- the defect;
- affected modules/tests/docs;
- the invariant being violated;
- the required outcome;
- the corrected requirement where the Phase 1 plan was ambiguous;
- the expected implementation seam;
- tests to add/change;
- non-goals;
- documentation updates;
- targeted validation;
- the final full-gate requirement;
- downstream constraints.

Luna XHigh should not need a separate planning prompt.
