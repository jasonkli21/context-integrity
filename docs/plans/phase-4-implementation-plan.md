# Context Integrity — Phase 4 Detailed Implementation Plan

**Phase:** 4 — Deterministic Documentation / Instruction Drift  
**Status:** Ready for implementation  
**Date:** 2026-10-15  
**Repository:** `jasonkli21/context-integrity`  
**Inspected HEAD:** `cce525db1eede17dc0158eee30b7a75a0a2d2397` (`fix claims diagnostics and domain invariants`)  
**Verified predecessor state:** Phase 3 implemented and review findings addressed; repository reports 426 passing tests  
**Parent documents:** `docs/prd.md`, `docs/architecture.md`  
**Current-state document:** `docs/current-state.md`  
**Predecessor:** Phase 3 — Claims and Provenance  
**Related project:** Codebase / Context Intelligence Engine; intentionally not integrated in this phase

---

# 1. Phase Objective

Phase 4 introduces the first **integrity evaluation** layer on top of the existing source inventory, authority, lifecycle, supersession, claims, and provenance stack.

The phase should let Context Integrity answer a bounded deterministic question:

> **Which current documentation or repository instructions require review because local source structure, explicit dependency policy, or Git/file evidence shows a concrete integrity risk?**

Phase 4 is intentionally not a general semantic contradiction engine. It should detect a small set of high-value documentation/instruction drift conditions that can be justified without an LLM, AST parser, code graph, database, or external service.

The target progression is:

```text
Phase 0–3
sources
  -> stable identity/revision
  -> classification
  -> authority role
  -> lifecycle/supersession
  -> explicit claims/provenance

Phase 4
deterministic evidence
  +
bounded integrity rules
  ->
explainable findings
```

The key architectural shift is:

```text
observation != finding
finding != proof of semantic incorrectness
finding != automatic mutation
```

A Phase 4 finding is a deterministic, inspectable review signal backed by revision-scoped evidence.

---

# 2. Why This Phase Now

The original PRD defines Phase 4 as:

- basic code/document dependency links;
- agent-instruction divergence;
- stale current-state detection;
- plan-vs-delivery distinctions;
- simple Git/file evidence until Codebase Intelligence integration exists.

The architecture already reserves:

- an `evidence` seam for deterministic observations;
- an `integrity` layer for composable rules;
- `IntegrityFinding` as a first-class domain concept;
- local temporary evidence such as file hashes, Git revisions, path changes, explicit links, and simple text references.

The current repository also deliberately dogfoods the problems Phase 4 is meant to address:

- `AGENTS.md` is the canonical instruction source;
- `CLAUDE.md` and `.github/copilot-instructions.md` point to `AGENTS.md`;
- `docs/current-state.md` names the current phase, active plan, status, and next step;
- phase plans are future/current normative requirements;
- implementation reports are delivery evidence rather than plans;
- plans do not prove implementation.

Phase 4 should formalize those relationships without turning repository-specific prose into a general-purpose semantic language.

---

# 3. Current Delivered Baseline

Implementation must begin from actual HEAD, not from an older Phase 3 implementation commit.

Reference HEAD inspected while preparing this plan:

```text
cce525db1eede17dc0158eee30b7a75a0a2d2397
fix claims diagnostics and domain invariants
```

At this point the repository reports:

- strict configuration schemas v1, v2, and v3;
- deterministic local inventory and stable source IDs;
- raw-byte source revisions distinct from Git HEAD;
- authority policies and equal-precedence tiers;
- lifecycle/supersession;
- explicit structured claims;
- claim declaration and dependency provenance;
- claim-scoped structured diagnostics;
- `scan`, `explain`, `authority`, `lifecycle`, and `claims` CLI surfaces;
- separate stable JSON v1 projections for inventory, authority, lifecycle, and claims;
- 426 passing tests after Phase 3 review fixes.

`docs/current-state.md` explicitly names the next expected step as:

```text
Phase 4 — Documentation / Instruction Drift
```

## 3.1 Baseline Verification Requirement

Before editing:

```bash
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check
git status --short
git rev-parse HEAD
```

Record the actual SHA and test count in the Phase 4 implementation report.

If HEAD has advanced beyond `cce525db...`, inspect the newer changes and use actual HEAD as the baseline. Do not reset accepted work to match this document.

---

# 4. Important Current-State Gap to Correct

The repository workflow treats `docs/implementation-reports/` as implementation/delivery evidence, but current source classification does not have a specific implementation-report rule.

Today an implementation report under `docs/implementation-reports/` is inventoried because it is under `docs/`, but it can fall through to a generic document kind rather than a verification kind.

Phase 4 needs a narrow correction:

```text
docs/implementation-reports/**
and clear *implementation-report* filenames
    ->
SourceKind.VERIFICATION_RECORD
AuthorityClass.VERIFICATION_EVIDENCE
```

Do **not** introduce a new `IMPLEMENTATION_REPORT` source kind unless implementation evidence shows the existing `VERIFICATION_RECORD` abstraction is insufficient. The architecture already has an appropriate verification role.

This classification correction is required because Phase 4 must distinguish:

```text
implementation plan
    !=
implementation evidence
```

without treating a plan as proof of delivery.

---

# 5. Product Boundary

## 5.1 In Scope

Phase 4 includes:

- a first `integrity` domain/evaluation module;
- deterministic `IntegrityFinding`-style models;
- stable finding rule IDs/codes;
- revision-scoped local file/Git evidence needed by Phase 4;
- Git changed-path evidence for:
  - working-tree changes;
  - an explicit local `BASE..TARGET` diff;
- configuration schema v4;
- optional explicit instruction canonicality policy;
- explicit document/instruction review dependencies on repository paths;
- deterministic instruction-source topology/reference checks;
- deterministic current-state navigation/staleness checks;
- explicit plan-vs-delivery-evidence checks within current-state evaluation;
- corrected implementation-report source classification;
- `context-integrity check`;
- text and separate integrity JSON v1 output;
- focused tests using synthetic repositories and small golden fixtures;
- Phase 4 implementation evidence;
- current-state update after verification.

## 5.2 Explicitly Out of Scope

Do **not** implement:

- general semantic contradiction detection;
- arbitrary natural-language equivalence checking;
- LLM/model calls;
- embeddings/vector search;
- automatic Markdown claim extraction;
- automatic claim validation;
- automatic claim invalidation;
- changing Phase 3 `ClaimValidity.UNVERIFIED`;
- claim authority selection;
- automatic document rewriting;
- automatic instruction rewriting;
- automatic current-state repair;
- AST parsing;
- symbol extraction;
- import/call/dependency graphs;
- architectural invariant evaluation;
- Codebase Intelligence integration;
- persistent indexes/databases;
- cross-run derived-artifact invalidation;
- context contracts;
- task-context compilation;
- CI enforcement policy;
- severity customization;
- waivers/governance;
- cross-repository integrity;
- external issue/PR/service integrations;
- remote Git fetches.

Phase 4 should create an integrity-evaluation seam that later phases can extend, not pull later phases forward.

---

# 6. Durable Semantics

The following are non-negotiable.

## 6.1 Findings Are Evidence-Backed Review Signals

A finding may say:

```text
docs/architecture.md should be reviewed because a declared upstream
source changed in the requested diff and the dependent document did not.
```

It must **not** say:

```text
docs/architecture.md is semantically wrong.
```

unless deterministic evidence actually proves that stronger statement.

## 6.2 A Changed Dependent File Does Not Prove It Is Correct

If an upstream source and its dependent document both changed in the same diff:

```text
no dependency-drift finding
```

is appropriate.

But this means only:

```text
the simple "upstream changed without dependent review" condition is absent
```

It does **not** mean the document now matches the code.

## 6.3 Plans Never Prove Delivery

A plan may establish intended work.

A plan must not satisfy a Phase 4 rule that requires delivery/verification evidence.

## 6.4 Findings Must Not Mutate Claim Validity

Phase 3 claims remain:

```text
validity = unverified
```

Phase 4 may emit a finding related to a source that a claim depends on, but it must not silently translate that finding into:

- stale;
- contradicted;
- invalid;
- superseded;
- verified.

Claim validity expansion belongs to a later explicit design.

## 6.5 Recency Is Not Authority

Phase 4 may use a later phase-numbered implementation report as a signal that `current-state.md` may lag delivery evidence.

It must not infer:

```text
newer file automatically supersedes older file
```

or:

```text
latest timestamp wins
```

## 6.6 Code Observation Remains Separate From Context Policy

Simple changed-path evidence is allowed.

Code parsing or structural interpretation is not.

---

# 7. Central Design: Integrity Evaluation Over Bounded Evidence

Introduce a module:

```text
src/context_integrity/integrity.py
```

Its job is to evaluate deterministic Phase 4 rules over:

- the inventory manifest;
- lifecycle/source roles;
- repository configuration;
- bounded source text where explicitly required;
- a local Git/file change set when available.

Conceptually:

```text
Repository discovery
  ↓
Inventory/config/lifecycle
  ↓
Phase 3 claims remain available but unchanged
  ↓
Local evidence
  ├── working-tree changed paths
  └── optional BASE..TARGET changed paths
  ↓
Integrity rules
  ├── instruction canonicality
  ├── current-state consistency
  ├── plan-vs-delivery evidence
  └── explicit dependent-source drift
  ↓
IntegrityOverview
  ├── findings
  ├── evaluation warnings
  └── evidence metadata
```

The CLI remains an adapter.

Do not put rule logic into `cli.py` or `rendering.py`.

---

# 8. Phase 4 Domain Model

Use shared models in `models.py` only when they are genuinely domain-wide.

Recommended concepts:

```text
FindingSeverity
IntegrityEvidence
IntegrityFinding
ChangeScope
ChangeSet
InstructionPolicySpec
DriftDependencySpec
IntegrityOverview
```

Exact names may vary if a cleaner implementation emerges.

## 8.1 `FindingSeverity`

Use a small fixed vocabulary:

```text
high
medium
low
```

Phase 4 severity is descriptive only.

Do not add:

- user-customized thresholds;
- waivers;
- enforcement status;
- ownership;
- CI gates.

Those belong to later governance work.

## 8.2 `IntegrityEvidence`

A finding should carry structured evidence rather than requiring message parsing.

Conceptually:

```text
IntegrityEvidence
- role
- path
- source_id?
- source_revision?
- detail?
- derivation
```

Examples of `role`:

```text
canonical_instruction
compatibility_instruction
current_state
active_plan
verification_record
dependent_document
changed_upstream
```

`detail` must remain bounded and must not contain source bodies.

## 8.3 `IntegrityFinding`

Conceptually:

```text
IntegrityFinding
- id
- rule_id
- code
- severity
- message
- affected_paths[]
- evidence[]
- remediation_hint?
```

Requirements:

- deterministic ID;
- deterministic ordering;
- repository-relative paths only;
- no timestamps in stable JSON;
- no absolute local root;
- no source body;
- no arbitrary exception text.

A suitable deterministic ID can hash:

```text
rule_id
+
code
+
sorted affected paths
+
stable rule-specific identity fields
```

Do not hash the human message as the primary identity input.

## 8.4 `ChangeSet`

Conceptually:

```text
ChangeSet
- scope
- base_revision?
- target_revision?
- changed_paths[]
- derivation
```

`scope` may be:

```text
working_tree
git_range
unavailable
```

The change set is descriptive.

It does not classify the semantic meaning of a code change.

## 8.5 `IntegrityOverview`

Conceptually:

```text
IntegrityOverview
- repository
- config_sha256
- change_set?
- findings[]
- warnings[]
- schema_version = 1
```

This is derived output and rebuildable.

---

# 9. Evidence Boundary

Expand `evidence.py` from its current placeholder into the minimum local evidence adapter needed for Phase 4.

Do not build the future Codebase Intelligence protocol yet.

Recommended responsibilities:

- validate and resolve local Git diff endpoints;
- obtain changed repository-relative paths;
- represent working-tree changed paths;
- safely read bounded text when a Phase 4 rule requires a literal reference check;
- attach derivation metadata.

It must not own:

- integrity policy;
- source classification;
- authority policy;
- current-state semantics;
- rendering.

---

# 10. Git Change Evidence

## 10.1 Default Working-Tree Scope

When `context-integrity check` is run without `--diff`:

- if Git is available, use the already observed working-tree status as the changed-path source;
- include modified, deleted, and untracked paths;
- preserve normalized repository-relative paths;
- do not refresh or mutate the Git index;
- do not make network calls.

A clean working tree produces:

```text
changed_paths = []
```

## 10.2 Explicit Diff Scope

Support:

```bash
context-integrity check --diff BASE..TARGET
```

Examples:

```bash
context-integrity check --diff main..HEAD
context-integrity check --diff abc123..def456
```

Phase 4 should support exactly a two-endpoint range.

Do not add:

- triple-dot merge-base semantics;
- remote fetch;
- GitHub APIs;
- revision expressions that are not needed.

Validation:

- require exactly one `..` separator;
- both endpoints nonblank;
- reject endpoint strings beginning with `-`;
- resolve each locally to a commit SHA;
- fail safely if either cannot be resolved.

Use argument-array Git invocation, never shell interpolation.

A requested explicit diff that cannot be evaluated is a fatal repository/evaluation error.

If no explicit diff is requested and Git is unavailable, non-Git integrity rules may still run; change-dependent rules are skipped with a structured warning.

## 10.3 Changed-Path Semantics

Use changed paths only.

Do not inspect code semantics.

Rename behavior should be deterministic. A simple and acceptable initial choice is to disable rename inference and treat rename-like changes as deletion + addition for Phase 4 path dependency purposes.

Document the choice and test it.

---

# 11. Configuration Schema v4

Introduce:

```text
schema_version = 4
```

Schema v4 retains all v3 behavior and adds Phase 4 drift policy.

## 11.1 Backward Compatibility

After Phase 4:

```text
v1
- authority only

v2
- v1
- lifecycle/supersession

v3
- v2
- explicit claims

v4
- v3
- instruction policy
- explicit drift dependencies
```

Older schemas must fail closed on v4-only keys.

Do not silently upgrade v1–v3 configuration.

## 11.2 Instruction Policy

Recommended shape:

```toml
schema_version = 4

[instruction_policy]
canonical = "AGENTS.md"
compatibility = [
  "CLAUDE.md",
  ".github/copilot-instructions.md",
]
```

Semantics:

- `canonical` is the intended repository-level canonical instruction source;
- `compatibility` lists repository-level compatibility/adaptor instruction files expected to refer back to the canonical source.

Validation:

- normalized repository-relative paths;
- canonical cannot equal a compatibility path;
- compatibility paths unique;
- configuration cannot name itself;
- no traversal/absolute/Windows ambiguity;
- unknown keys fail closed.

Do not add semantic instruction text to config.

## 11.3 Built-In Convention When No Policy Is Configured

To make Phase 4 useful without forcing configuration:

If root `AGENTS.md` exists and is inventoried as an agent instruction:

```text
effective canonical = AGENTS.md
```

Recognized repository-level compatibility candidates that exist:

```text
CLAUDE.md
GEMINI.md
.github/copilot-instructions.md
```

If no root `AGENTS.md` exists and no explicit instruction policy exists:

```text
skip canonicality evaluation
```

Do not assume that a repository using only `CLAUDE.md` is broken.

Nested/local `AGENTS.md` files are outside the automatic Phase 4 root-policy check. They may be legitimate additive local instructions.

## 11.4 Explicit Drift Dependencies

Recommended shape:

```toml
[[drift_dependencies]]
id = "architecture-core-model"
dependent = "docs/architecture.md"
upstream = [
  "src/context_integrity/models.py",
  "src/context_integrity/evidence.py",
]
reason = "Core domain/evidence changes require architecture review."
```

Requirements:

- stable explicit `id`;
- repository-wide unique drift dependency ID;
- safe `dependent` path;
- one or more unique safe `upstream` paths;
- nonblank reason;
- dependent cannot be `.context-integrity.toml`;
- upstream may refer to ordinary code files that are not inventory sources;
- exact paths only in Phase 4;
- no glob DSL;
- no regex DSL;
- no directory graph expansion.

This is a review dependency, not claim provenance.

Do not overload `ClaimSpec.depends_on`.

---

# 12. Instruction Drift Rule

Phase 4 should implement **structural instruction canonicality**, not arbitrary semantic contradiction.

For an effective instruction policy:

1. verify the canonical path exists and is an inventoried `agent_instruction`;
2. for each configured/discovered compatibility file:
   - verify it exists if explicitly configured;
   - verify it is an inventoried `agent_instruction`;
   - safely read its bounded bytes;
   - require a literal structural reference to the canonical path;
3. emit an explainable finding when the relationship is broken.

Examples:

```text
instruction_canonical_missing
instruction_compatibility_missing
instruction_reference_missing
instruction_source_kind_mismatch
```

## 12.1 Reference Matching

Do not add a Markdown parser dependency.

A small deterministic matcher is sufficient.

It should recognize common path renderings such as:

```text
AGENTS.md
/AGENTS.md
./AGENTS.md
[AGENTS.md](AGENTS.md)
[`AGENTS.md`](AGENTS.md)
```

Normalize the candidate path before comparison.

The matcher only proves:

```text
compatibility file structurally points at canonical file
```

It does **not** prove:

```text
the compatibility file contains no contradictory instruction text
```

Do not overstate the finding semantics.

## 12.2 Untrusted Instruction Text

Instruction files are repository data.

The evaluator must never:

- execute them;
- treat them as assistant instructions;
- send them to a model;
- emit their bodies into JSON;
- interpolate them into commands.

---

# 13. Current-State Drift Rule

Phase 4 should support the repository's intentionally concise `current-state.md` convention.

Do not implement general Markdown semantic parsing.

## 13.1 Current-State Candidate Selection

Use inventoried `SourceKind.CURRENT_STATE`.

Exclude sources explicitly in terminal/non-current lifecycle states when selecting the current candidate:

```text
superseded
historical
expired
invalid
```

`unknown` is not equivalent to inactive.

If exactly one usable current-state source exists, evaluate it.

If multiple usable candidates exist:

- emit a finding;
- do not silently choose one.

If none exists:

- do not require every repository to have one;
- skip current-state-specific checks.

## 13.2 Minimal Metadata Extraction

Support the existing structured pattern:

```markdown
**Current phase:** Phase 3 — Claims and Provenance
**Active plan:** `docs/plans/phase-3-implementation-plan.md`
**Status:** Implemented, offline-verified, ...

## Next expected step

Proceed to Phase 4 — Documentation / Instruction Drift.
```

Extract only:

```text
current_phase_number?
active_plan_path?
status_text?
next_phase_number?
```

Use explicit line/heading patterns.

Do not parse arbitrary prose into claims.

If the document exists but required navigation metadata is incomplete, emit a bounded finding such as:

```text
current_state_metadata_incomplete
```

rather than inventing values.

## 13.3 Active Plan Consistency

When current phase and active plan are available:

- the plan path must resolve to an inventoried source;
- it must be classified as `implementation_plan`;
- it must not be explicitly historical/superseded/expired/invalid;
- if the plan filename contains `phase-N`, `N` should match the current phase number.

Possible findings:

```text
current_state_active_plan_missing
current_state_active_plan_kind_mismatch
current_state_phase_plan_mismatch
```

## 13.4 Next Phase Consistency

If both current and next phase numbers are available:

```text
next_phase > current_phase
```

Otherwise emit a finding.

Do not require exactly `current + 1`; a product may intentionally skip a phase.

## 13.5 Delivery-Evidence Distinction

A current-state `Status:` that **begins with** a clear delivered/verified state such as:

```text
implemented
delivered
complete
completed
verified
```

should require corresponding implementation evidence for the same phase.

Avoid naive substring logic:

```text
"not implemented"
```

must not count as delivered simply because it contains the word `implemented`.

For Phase 4, matching delivery evidence is a non-terminal, non-historical source that:

- is classified as `verification_record`;
- has a filename matching the narrow phase implementation report convention:
  - `phase-N-implementation-report...`.

A plan is not sufficient.

A generic review is not automatically sufficient.

If a delivered status has no matching implementation report:

```text
current_state_delivery_evidence_missing
```

The finding means the navigation document lacks the repository's expected delivery evidence artifact. It does not independently prove the software was not implemented.

## 13.6 Current State Lagging Later Implementation Evidence

If a usable `current-state.md` declares Phase `N`, and a non-terminal implementation report exists for a strictly greater numeric phase:

```text
current_state_lags_verification_evidence
```

This is a review signal.

Do not automatically rewrite current-state or advance the phase.

Use numeric comparison, not lexicographic filename ordering.

---

# 14. Plan vs Delivery Is a First-Class Rule Boundary

The implementation must preserve this distinction everywhere Phase 4 evaluates phase state:

```text
implementation_plan
    -> intended/authorized work

verification_record / implementation report
    -> evidence that work was performed/verified
```

A later plan must not cause:

```text
current_state_lags_verification_evidence
```

A current-phase plan must not satisfy:

```text
current_state_delivery_evidence_missing
```

A review file should not silently substitute for the expected implementation report unless a later design explicitly broadens delivery evidence policy.

---

# 15. Explicit Document Dependency Drift Rule

For each configured `DriftDependencySpec`:

```text
dependent source D
upstream paths U1..Un
```

Given an available `ChangeSet`:

```text
if any upstream path changed
and dependent path did not change
    -> finding
```

Suggested code:

```text
document_dependency_changed
```

Evidence should include:

- dependency rule ID;
- dependent path and its observed source revision when available;
- changed upstream path(s);
- change-set derivation and revisions.

## 15.1 Missing Dependent

If the configured dependent is not an inventoried context source:

- keep configuration parseable if path syntax is valid;
- emit a finding;
- do not fabricate the source.

Suggested code:

```text
drift_dependent_missing
```

## 15.2 Upstream Missing From Working Tree

An upstream path may be:

- deleted in the diff;
- absent at target;
- ordinary code not inventoried.

That is not a configuration syntax error.

If the path is in changed-path evidence, evaluate it as changed.

If no change evidence mentions it, do not scan the entire repository to infer historical revisions.

## 15.3 Dependent Also Changed

If the dependent changed in the same change set:

- suppress the simple stale-review finding;
- do not emit a "passed/correct" claim.

---

# 16. Correct Implementation-Report Classification

Update candidate/classification behavior so implementation reports have the intended source role.

Recommended adjustments:

- candidate filename support for `*implementation-report*` when outside a normal context directory;
- classification path rule for `implementation-reports`;
- classification filename fallback for `*implementation-report*`.

The stronger directory rule should precede generic rules.

Expected result:

```text
SourceKind.VERIFICATION_RECORD
AuthorityClass.VERIFICATION_EVIDENCE
```

Do not infer lifecycle from report recency.

---

# 17. Integrity Rule Architecture

Rules should be composable and testable independently.

A lightweight internal shape is enough:

```text
rule_id
evaluate(inputs) -> tuple[IntegrityFinding, ...]
```

Do not build a plugin framework yet.

Recommended stable rule IDs:

```text
instruction.canonical_reference.v1
current_state.navigation.v1
current_state.delivery_evidence.v1
document_dependency.change_review.v1
```

The exact strings may differ, but they should be explicit and versionable.

Avoid one giant function with intertwined conditionals for every Phase 4 rule.

---

# 18. CLI

Add:

```bash
context-integrity check [PATH]
```

Options:

```text
--diff BASE..TARGET
--format text|json
--output PATH
```

Examples:

```bash
context-integrity check
context-integrity check .
context-integrity check --diff main..HEAD
context-integrity check --format json
context-integrity check --diff main..HEAD --format json --output integrity.json
```

## 18.1 Exit Behavior

Phase 4 is inspection, not CI governance.

On successful evaluation:

```text
exit 0
```

even if integrity findings exist.

Preserve existing fatal categories:

```text
2  requested item not found, where applicable
3  repository/evidence failure
4  output write failure
6  configuration failure
```

Do not introduce severity-based failing exits in Phase 4.

CI enforcement belongs to Phase 11.

## 18.2 Text Output

Example:

```text
Context Integrity Check

Repository: context-integrity
Change scope: working_tree
Findings: 2

HIGH  instruction_reference_missing
  CLAUDE.md does not reference canonical instruction source AGENTS.md.
  Evidence:
    canonical: AGENTS.md
    compatibility: CLAUDE.md

MEDIUM  document_dependency_changed
  docs/architecture.md may require review because declared upstream sources changed.
  Changed:
    src/context_integrity/models.py

Warnings: 0
```

Do not print source bodies.

Escape repository-controlled strings consistently with existing rendering safety.

---

# 19. Integrity JSON v1

Create a new stable machine-readable projection.

Do not modify:

- inventory JSON v1;
- authority JSON v1;
- lifecycle JSON v1;
- claims JSON v1.

Illustrative shape:

```json
{
  "schema_version": 1,
  "repository": {
    "id": "repo_...",
    "name": "context-integrity",
    "git_available": true,
    "git_head": "..."
  },
  "config_sha256": null,
  "change_set": {
    "scope": "working_tree",
    "base_revision": "...",
    "target_revision": null,
    "changed_paths": []
  },
  "findings": [
    {
      "id": "finding_...",
      "rule_id": "instruction.canonical_reference.v1",
      "code": "instruction_reference_missing",
      "severity": "high",
      "message": "...",
      "affected_paths": [
        "CLAUDE.md"
      ],
      "evidence": [
        {
          "role": "canonical_instruction",
          "path": "AGENTS.md",
          "source_id": "src_...",
          "revision": {
            "content_sha256": "...",
            "git_head": "...",
            "git_status": "tracked_clean",
            "observed_revision_basis": "raw_bytes"
          },
          "derivation": "inventory_source"
        }
      ],
      "remediation_hint": "..."
    }
  ],
  "warnings": []
}
```

Requirements:

- deterministic order;
- explicit schema version;
- repository-relative paths;
- no absolute root;
- no timestamps;
- no file bodies;
- no ANSI/control characters unescaped;
- no opaque dataclass dump;
- no exception stack/text leakage;
- stable newline termination.

---

# 20. Deterministic Ordering

Recommended ordering:

```text
findings:
  severity rank: high, medium, low
  then rule_id
  then affected paths
  then finding id

evidence:
  role
  path
  derivation

warnings:
  path
  code
  message

changed_paths:
  lexical normalized path
```

Severity ordering here is presentation ordering only.

It is not authority ranking.

---

# 21. Security and Trust Boundaries

Phase 4 expands read surfaces and Git input, so review this carefully.

## 21.1 Repository Text Is Untrusted

Current-state and instruction files may contain adversarial content.

The evaluator must not execute or obey it.

## 21.2 Use Existing Safe Read Boundary

Reuse descriptor-safe bounded reads where possible.

Do not reintroduce direct unsafe `Path.read_text()` for repository-controlled input inside the integrity engine.

## 21.3 Git Refs Are Arguments, Not Shell

Never interpolate `--diff` text into a shell command.

Validate endpoints and pass them as argument-list elements.

## 21.4 No Network

Git evidence must be local-only.

Do not fetch missing refs.

## 21.5 Sanitized Errors

Configuration and Git errors must not leak arbitrary repository contents.

## 21.6 Stable Output Privacy

Integrity JSON must not expose:

- absolute filesystem root;
- environment variables;
- source bodies;
- credentials/remotes beyond already-normalized repository identity semantics.

---

# 22. Implementation Shape

Expected touched/new files may include:

```text
src/context_integrity/models.py
src/context_integrity/configuration.py
src/context_integrity/classification.py
src/context_integrity/evidence.py
src/context_integrity/integrity.py        # new
src/context_integrity/rendering.py
src/context_integrity/cli.py

tests/test_integrity.py                   # new
tests/test_configuration.py
tests/test_classification.py
tests/test_repository.py or test_evidence.py
tests/test_cli.py
tests/fixtures/integrity-v1-*.json

README.md
docs/current-state.md
docs/implementation-reports/phase-4-implementation-report.md
docs/architecture.md                      # only for durable invariants actually introduced
```

Do not create extra modules merely to mirror every conceptual noun.

If the implementation naturally warrants a small `current_state.py` parser or `test_evidence.py`, that is acceptable. Prefer clear ownership over file-count minimization.

---

# 23. Recommended Implementation Sequence

## Step 0 — Baseline

- inspect actual HEAD;
- run offline full gate;
- record test count;
- inspect working tree;
- reread:
  - `AGENTS.md`;
  - `docs/current-state.md`;
  - this plan;
  - relevant architecture sections;
  - Phase 3 implementation report for accepted invariants.

## Step 1 — Correct Implementation-Report Classification

Add the narrow candidate/classification rules.

Test first because current-state rules depend on this semantic role.

## Step 2 — Add Phase 4 Domain Models

Add only the models needed by:

- v4 config;
- local change evidence;
- findings;
- integrity overview.

Keep claim models unchanged.

## Step 3 — Add Config v4

Implement strict parsing for:

- `instruction_policy`;
- `drift_dependencies`.

Preserve v1–v3 rejection behavior.

## Step 4 — Implement Local Change Evidence

Expand `evidence.py` with:

- working-tree change-set construction;
- explicit local `BASE..TARGET` change-set construction;
- safe ref resolution;
- deterministic changed paths.

Do not add structural code analysis.

## Step 5 — Implement Instruction Rule

Implement effective policy resolution:

- explicit v4 policy if present;
- otherwise root-`AGENTS.md` convention when applicable.

Add safe literal-reference evaluation.

## Step 6 — Implement Current-State Rules

Add targeted metadata extraction and:

- candidate uniqueness;
- active plan checks;
- phase/plan alignment;
- next-phase monotonicity;
- delivered-status implementation-report evidence;
- later-phase implementation-report lag finding.

Keep the parser narrow and explicit.

## Step 7 — Implement Drift Dependency Rule

Evaluate exact configured upstream/dependent paths against the change set.

## Step 8 — Add Rendering and CLI

Add:

```text
render_integrity_text
render_integrity_json
context-integrity check
```

Keep CLI orchestration thin.

## Step 9 — Focused Tests

Use synthetic repositories and table-driven cases.

Avoid combinatorial test explosion.

## Step 10 — Real-Repository Smoke

On the actual repository:

```bash
context-integrity check .
context-integrity check . --format json
```

Expected at accepted Phase 4 completion:

- no false positive for `AGENTS.md` / `CLAUDE.md` / Copilot compatibility;
- no false positive for a correctly updated current-state document;
- deterministic JSON on repeated runs with the same repository state.

Also use a disposable synthetic Git repository to smoke:

```bash
context-integrity check --diff <base>..HEAD
```

## Step 11 — Full Gate and Documentation

Run full offline gate.

Update:

- implementation report;
- current state only after verification;
- architecture only for durable invariants;
- README for user-facing Phase 4 commands/config.

Do not rewrite this completed plan to make later deviations disappear.

---

# 24. Testing Strategy

Testing should be focused on meaningful semantic boundaries.

## 24.1 Classification

Prove:

- `docs/implementation-reports/phase-4-implementation-report.md` -> verification record;
- a root `phase-4-implementation-report.md` candidate is recognized if supported;
- ordinary plans remain plans.

## 24.2 Config v4

Prove:

- valid v4 with existing v3 features;
- v1–v3 reject v4 keys;
- duplicate drift dependency IDs rejected;
- unsafe/duplicate paths rejected;
- canonical/compatibility self-conflict rejected;
- unknown keys rejected;
- sanitized fatal error behavior preserved.

## 24.3 Git Evidence

Prove:

- clean working tree;
- modified file;
- deleted file;
- untracked file;
- explicit valid diff;
- invalid/missing local ref;
- range input beginning with option-like values rejected;
- no network dependency;
- deterministic path ordering.

Do not exhaustively test Git itself.

## 24.4 Instruction Canonicality

Prove:

- current repo-style `CLAUDE.md` reference passes;
- `/AGENTS.md`, `./AGENTS.md`, Markdown link forms pass;
- missing canonical reference produces a finding;
- explicit compatibility file missing produces a finding;
- no root `AGENTS.md` + no explicit policy does not falsely fail a CLAUDE-only repository;
- repository content is not emitted into findings.

## 24.5 Current State

Prove:

- valid current-state + matching active plan + matching implementation report has no finding;
- "Implemented..." requires report;
- "not implemented" does not trigger delivered-status logic;
- later numeric phase report produces lag finding;
- `phase-10` compares numerically against `phase-9`;
- plan path missing;
- plan classified incorrectly;
- plan phase mismatch;
- next phase <= current phase;
- multiple usable current-state sources;
- historical/superseded current-state source does not win merely because it exists.

## 24.6 Plan vs Delivery

Explicit regression:

```text
current-state says implemented
matching phase plan exists
matching implementation report absent
```

must still produce:

```text
current_state_delivery_evidence_missing
```

## 24.7 Drift Dependencies

Prove:

- upstream changed, dependent unchanged -> finding;
- upstream and dependent both changed -> no simple drift finding;
- unrelated file changed -> no finding;
- deleted upstream in change set still counts;
- ordinary code path need not be an inventoried source;
- missing dependent -> finding;
- no change evidence -> structured warning/skip, not fabricated result.

## 24.8 JSON

Use one or two concise golden fixtures.

Prove:

- stable schema;
- deterministic ordering;
- no absolute root;
- no source body;
- no timestamps;
- revisions/evidence explicit;
- repeated render byte equality.

## 24.9 Regression Gate

Run the existing full suite.

Do not turn this phase into hundreds of near-duplicate tests. Table-driven cases are preferred.

---

# 25. Acceptance Criteria

Phase 4 is complete only if all of the following hold.

## Functional

- `context-integrity check` exists.
- It runs without network/model/database dependencies.
- Instruction canonicality checks are deterministic.
- Current-state navigation/staleness checks are deterministic.
- A plan cannot satisfy delivery-evidence requirements.
- Configured document dependencies can detect changed upstream paths without code parsing.
- Working-tree and explicit local diff evidence are supported.
- Implementation reports have the correct verification source role.
- Findings contain structured evidence.
- Integrity JSON v1 is deterministic.

## Architectural

- Context Integrity still owns policy/judgment.
- No Codebase Intelligence functionality is duplicated.
- `evidence.py` remains descriptive, not normative.
- `integrity.py` owns rule evaluation.
- CLI remains an adapter.
- claim validity remains unchanged.
- no persistence introduced.
- no semantic Markdown/LLM contradiction engine introduced.

## Compatibility

- v1–v3 configuration behavior remains strict.
- inventory/authority/lifecycle/claims public schemas remain v1 and are not polluted with integrity fields.
- Phase 0–3 commands continue to work.
- intentionally corrected implementation-report classification is documented if it changes an existing fixture.

## Security

- repository text is never executed;
- no unsafe direct source reads are introduced;
- diff refs are never shell-interpolated;
- no network fetch;
- no source bodies/absolute roots in stable JSON;
- errors remain sanitized.

## Evidence

- focused tests pass;
- full offline `make check` passes;
- real-repository smoke passes;
- implementation report records actual baseline, deviations, test commands/counts, and known limits.

---

# 26. Expected Phase 4 Limitations

The implementation report should explicitly retain these limitations.

Phase 4 cannot determine that:

- two arbitrary instruction files are semantically equivalent;
- a changed document was updated correctly;
- code behavior contradicts prose;
- a plan was actually implemented from code alone;
- a generated summary is stale across runs;
- a claim is semantically false;
- an architectural boundary was violated;
- a cross-repository contract drifted.

Those require later semantic/structural phases.

A correct Phase 4 implementation should be useful precisely because it is honest about what its deterministic evidence proves.

---

# 27. Forward Compatibility

## Phase 5 — Context Contracts

Phase 4 findings become useful inputs to contract integrity requirements.

Do not design contracts now.

## Phase 6 — Context Compiler

Compiler may later exclude or surface context based on integrity findings.

Do not compile task context now.

## Phase 7 — Codebase Intelligence Adapter

Replace/augment simple changed-path evidence with structured external evidence.

The Phase 4 evidence boundary should make this additive rather than a rewrite.

## Phase 8 — Architectural Integrity

Structured code relations can then be compared to architectural claims/invariants.

Do not emulate that with text matching now.

## Phase 9 — Derived Context Revalidation

Persistent dependency invalidation can build on revision-scoped evidence and dependency semantics.

Phase 4 diff checks are not a persistence substitute.

## Phase 11 — CI / Governance

Severity thresholds, failing exits, waivers, ownership, and policy enforcement belong there.

---

# 28. Definition of Done

Phase 4 is done when the repository can locally and deterministically surface concrete documentation/instruction drift risks while preserving the core product boundaries:

```text
evidence before judgment
plans do not prove delivery
findings do not silently mutate truth
code observation remains separate from context policy
```

At completion, `docs/current-state.md` should name Phase 4 as delivered and identify Phase 5 — Context Contracts as the next expected step.
