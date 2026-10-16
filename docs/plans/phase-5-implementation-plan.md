# Context Integrity — Phase 5 Detailed Implementation Plan

**Phase:** 5 — Context Contracts
**Status:** Ready for implementation
**Date:** 2026-10-15
**Repository:** `jasonkli21/context-integrity`
**Inspected default branch:** `main`
**Inspected HEAD:** `4b60524bed350bbce5a64bcb3d9d803d139dcee2` (`Fix Phase 4 review findings`)
**Parent documents:** `docs/prd.md`, `docs/architecture.md`
**Current-state document:** `docs/current-state.md`
**Predecessor:** Phase 4 — Documentation / Instruction Drift
**Successor:** Phase 6 — Task Context Compiler
**Related project:** Codebase / Context Intelligence Engine; intentionally not integrated in this phase

---

# 1. Phase Objective

Phase 5 introduces **Context Contracts** as a first-class deterministic policy layer.

A context contract should let a repository declare, for a named task class:

- which kinds of context are required;
- which are optional;
- which are excluded;
- what bounded cardinality constraints apply;
- which source metadata dimensions a rule matches;
- and whether an explicitly supplied context package satisfies those rules.

The core Phase 5 question is:

> **Given a repository-defined context contract and an explicit set of current repository context sources, is the package complete and policy-compatible according to that contract?**

Phase 5 must **not** answer:

> **Which sources should I automatically retrieve, rank, deduplicate, budget, or assemble for this task?**

That is Phase 6.

The intended progression is:

```text
Phase 0–4
sources
  -> authority role
  -> lifecycle/supersession
  -> claims/provenance
  -> deterministic integrity findings

Phase 5
repository-defined context contract
  + explicit context package
  + current inventory metadata
  -> deterministic contract validation

Phase 6
contract
  + task
  + candidate retrieval
  + filtering/ranking/budget
  -> compiled context
```

The primary architectural invariant of this phase is:

```text
contract validation != context compilation
```

---

# 2. Product and Architecture Alignment

The original PRD defines Phase 5 as:

- define required context for task classes;
- define optional context for task classes;
- define excluded context for task classes;
- validate context package completeness.

The PRD's broader Context Contract concept also anticipates future:

- authority expectations;
- freshness requirements;
- dependency requirements;
- size budgets;
- verification/integrity rules.

The architecture places Context Contracts in **Layer 5**, immediately before the **Layer 6 Context Compiler**, and assigns the `contracts` module responsibility for:

- contract definitions;
- validation;
- task classification hooks.

This phase should implement the smallest durable deterministic contract core that Phase 6 can consume without prematurely implementing Phase 6 behavior.

## 2.1 Phase 5 Contract v1 Boundary

Contract v1 should support:

- stable contract identity;
- task-class metadata;
- stable rule identity;
- rule mode: required / optional / excluded;
- exact path selectors;
- source-kind selectors;
- authority-class selectors;
- lifecycle selectors;
- bounded source counts;
- validation against an explicit package of current inventoried sources;
- explainable rule results and findings.

Contract v1 should **not** support yet:

- automatic natural-language task classification;
- authority-policy winner selection;
- claim-semantic matching;
- semantic freshness/age windows;
- integrity-check gating;
- token/byte budgets;
- relevance ranking;
- automatic retrieval or package completion;
- code-symbol/entity selectors;
- external evidence-provider selectors;
- globs/regex selector languages;
- cross-repository contracts.

Those are intentional future schema/version extensions.

---

# 3. Current Delivered Baseline

Implementation must begin from actual repository state, not from an earlier Phase 4 implementation commit.

Reference HEAD inspected for this plan:

```text
4b60524bed350bbce5a64bcb3d9d803d139dcee2
Fix Phase 4 review findings
```

At inspected HEAD, the repository has:

- deterministic local source inventory;
- strict configuration schemas v1–v4;
- authority policies and source-role resolution;
- lifecycle and supersession;
- explicit claims and provenance;
- Phase 4 deterministic documentation/instruction integrity checks;
- local working-tree / explicit Git-range changed-path evidence;
- stable separate JSON v1 projections for inventory, authority, lifecycle, claims, and integrity;
- `scan`, `explain`, `authority`, `lifecycle`, `claims`, and `check` CLI surfaces;
- no `contracts.py` module and no delivered Context Contract domain model yet.

The current model already has a conceptual `ContextContract` in architecture documentation, but it is not implemented in code.

---

# 4. Verified Phase 4 Starting State — Do Not Re-Run Completed Work

The current repository now records the Phase 4 review-fix state as verified:

- `docs/current-state.md` says Phase 4 is implemented/offline-verified and review findings F-001–F-003 are fixed and verified;
- `docs/implementation-reports/phase-4-implementation-report.md` records the post-fix verification: integrity tests **105 passed**, configuration/classification tests **117 passed**, and the full offline gate **532 tests passed**;
- text and JSON dogfood checks completed with zero findings and zero warnings;
- `docs/current-state.md` still lists **final independent verification** as a separate next step.

Treat that recorded verification as accepted predecessor evidence. **Do not re-run the Phase 4 baseline verification, re-implement review fixes, or perform the separate final independent verification as part of the Phase 5 implementation session.** Those are distinct completed/separate workflows, not Phase 5 work.

At Phase 5 start, only establish repository identity/state:

```bash
git status --short
git rev-parse HEAD
git log -5 --oneline
```

If HEAD has advanced beyond the inspected SHA, inspect and preserve accepted newer work. Do not reset the repository to this plan's reference commit.

If a concrete pre-existing breakage is discovered while implementing Phase 5, surface it and isolate it from Phase 5. Do not proactively repeat Phase 4 verification or broaden the task into predecessor cleanup merely to recreate already-recorded evidence.

Do **not** edit completed Phase 4 plans or reports to make historical evidence describe later reality.

---

# 5. Core User Journey

Phase 5 should enable a deterministic flow such as:

```text
Repository config defines contract:
  implementation-task

Contract says:
  required: current-state source
  required: implementation-plan source
  optional: architecture source
  excluded: historical/superseded source

User supplies package:
  docs/current-state.md
  docs/plans/phase-5-implementation-plan.md
  docs/architecture.md

Context Integrity:
  inventories current sources
  resolves the named contract
  matches each rule against supplied package sources
  checks cardinality/exclusions
  emits explainable rule results/findings
```

A failing example:

```text
Package:
  docs/current-state.md
  docs/reviews/old-review.md

Result:
  required active-plan rule missing
  excluded historical rule matched
```

The validator reports the state.

It does not automatically add the plan, remove the review, or construct a replacement package.

---

# 6. Product Boundary

## 6.1 In Scope

Phase 5 includes:

- first-class Context Contract domain models;
- strict domain validation at construction boundaries;
- configuration schema v5;
- repository-defined contracts;
- required / optional / excluded contract rules;
- deterministic selectors over existing source metadata;
- exact path selectors only;
- bounded cardinality rules;
- deterministic validation of an explicit package of inventoried source paths;
- rule-level match results;
- explainable contract findings;
- deterministic finding IDs and ordering;
- contract list/show/validate application services or pure functions;
- `context-integrity contracts ...` CLI surface;
- text output;
- separate contract-validation JSON v1 output;
- focused synthetic repository tests;
- Phase 5 implementation report;
- current-state update only after successful verification;
- README updates for user-facing contract configuration/commands;
- architecture updates only when a durable invariant is clarified or changed.

## 6.2 Explicitly Out of Scope

Do **not** implement:

- Phase 6 task-context compilation;
- automatic source retrieval;
- automatic package completion;
- automatic ranking;
- token budgeting;
- byte budgeting as selection behavior;
- redundancy optimization;
- automatic deduplication as a compiler feature;
- natural-language task classification;
- embeddings/vector search;
- LLM calls;
- Codebase Intelligence integration;
- AST/symbol/import/call-graph selectors;
- arbitrary code paths as context items unless already represented by the current inventory model;
- cross-repository contract evaluation;
- persistence/database state;
- contract inheritance/composition;
- globs;
- regular-expression selectors;
- semantic claim predicates in contract selectors;
- automatic authority-policy precedence resolution inside contract rules;
- time-based freshness windows;
- contract-driven execution of Phase 4 integrity checks;
- contradiction gating;
- severity-based process failure;
- CI enforcement;
- waivers/governance;
- automatic repairs or rewrites.

---

# 7. Why Contract Rules Should Use Existing Source Metadata First

Phase 5 should build on the implemented source model rather than create a parallel context-item taxonomy.

The current repository already has durable source dimensions:

```text
SourceRecord
- path
- kind
- authority_class
- lifecycle
- revision
```

Contract v1 selectors should therefore match these dimensions.

This gives Phase 5 useful behavior without inventing semantic parsing or relying on future Codebase Intelligence entities.

Later phases can extend the contract-item abstraction to structured code evidence while preserving the contract/rule semantics.

---

# 8. Configuration Schema v5

Introduce:

```text
schema_version = 5
```

Schema v5 retains all v4 behavior and adds:

```text
context_contracts
```

## 8.1 Backward Compatibility

After Phase 5:

```text
v1
- authority

v2
- v1
- lifecycle/supersession

v3
- v2
- explicit claims

v4
- v3
- instruction policy
- document drift dependencies

v5
- v4
- context contracts
```

Requirements:

- v1–v4 must continue to parse exactly as before;
- v1–v4 must reject v5-only keys;
- v5 must retain all earlier semantics;
- no silent schema upgrade;
- unknown keys fail closed;
- configuration errors remain sanitized;
- existing JSON projections remain unchanged.

---

# 9. Recommended Contract Configuration Shape

Use a repository-defined shape similar to:

```toml
schema_version = 5

[[context_contracts]]
id = "implementation-task"
task_class = "implementation"
description = "Context required for active implementation work."

[[context_contracts.rules]]
id = "current-state"
mode = "required"
kinds = ["current_state"]
lifecycles = ["unknown", "active"]
min_count = 1
max_count = 1

[[context_contracts.rules]]
id = "active-plan"
mode = "required"
kinds = ["implementation_plan"]
lifecycles = ["unknown", "active"]
min_count = 1

[[context_contracts.rules]]
id = "architecture"
mode = "optional"
kinds = ["architecture"]
authority_classes = ["architecture_product"]
lifecycles = ["unknown", "active"]
max_count = 2

[[context_contracts.rules]]
id = "historical-context"
mode = "excluded"
lifecycles = ["superseded", "historical", "expired", "invalid"]
```

A narrower exact-path rule is also valid:

```toml
[[context_contracts.rules]]
id = "canonical-instructions"
mode = "required"
paths = ["AGENTS.md"]
min_count = 1
max_count = 1
```

## 9.1 No Hidden Currentness Default

Contract rules should be explicit.

Do **not** silently treat:

```text
required -> active/unknown only
```

unless the rule says so.

If a contract wants only current sources, it should specify:

```toml
lifecycles = ["unknown", "active"]
```

This keeps historical/research contracts possible and avoids invisible policy.

## 9.2 Exact Paths Only

`paths` are exact normalized repository-relative paths.

Do not introduce:

- globbing;
- directory recursion;
- regex;
- suffix wildcard matching.

Later versions can add selector languages deliberately if needed.

---

# 10. Phase 5 Domain Model

Use shared models in `models.py` for stable domain contracts and a dedicated `contracts.py` module for validation behavior.

Recommended concepts:

```text
ContextRuleMode
ContextContractRule
ContextContract
ContextPackage
ContextRuleResult
ContractFinding
ContractValidationOverview
```

Exact names may vary if the implementation finds a cleaner shape, but the semantics below are normative.

## 10.1 `ContextRuleMode`

Fixed vocabulary:

```text
required
optional
excluded
```

## 10.2 `ContextContractRule`

Conceptually:

```text
ContextContractRule
- id
- mode
- paths[]
- kinds[]
- authority_classes[]
- lifecycles[]
- min_count?
- max_count?
```

### Selector semantics

Across dimensions:

```text
AND
```

Within one dimension:

```text
OR
```

Example:

```text
kinds = [architecture, decision_record]
authority_classes = [architecture_product, decision]
lifecycles = [active, unknown]
```

matches a source only when:

```text
kind is architecture OR decision_record
AND
authority class is architecture_product OR decision
AND
lifecycle is active OR unknown
```

A dimension omitted from a rule imposes no constraint for that dimension.

At least one selector dimension must be present.

### Domain validation

The model boundary itself must reject invalid direct construction, not only the TOML parser.

Validate:

- rule ID syntax;
- rule mode;
- tuple/list shape expected by the domain model;
- at least one selector dimension;
- safe normalized exact paths;
- unique values within every selector dimension;
- enum values;
- integer cardinalities only;
- nonnegative cardinalities;
- coherent min/max.

This incorporates the Phase 4 independent-review lesson that invariants belong at the domain boundary as well as config parsing.

## 10.3 Cardinality Semantics

Recommended defaults:

```text
required:
  min_count = 1 if omitted
  max_count = unbounded if omitted

optional:
  min_count = 0
  max_count = unbounded if omitted

excluded:
  min_count = 0
  max_count = 0
```

Rules:

- `required` may explicitly set `min_count >= 1`;
- `required` may set `max_count >= min_count`;
- `optional` must not require a positive minimum;
- `optional` may set a nonnegative maximum;
- `excluded` must not accept custom min/max that weaken exclusion semantics.

If the implementation chooses to require explicit counts instead of defaults, document and test that choice. Do not create ambiguous semantics.

## 10.4 `ContextContract`

Conceptually:

```text
ContextContract
- id
- task_class
- description
- rules[]
- config_revision
```

Requirements:

- contract ID is stable and validated;
- task class is a stable machine-readable identifier;
- description is nonblank;
- rule IDs are unique within the contract;
- contract IDs are unique repository-wide;
- task classes do not need to be globally unique in Phase 5;
- at least one rule is required.

`task_class` is metadata/hook input.

Phase 5 does **not** infer a task class from natural-language task text.

## 10.5 `ContextPackage`

A Phase 5 package is an explicit user-supplied set/list of repository context source paths evaluated against the **current inventory observation**.

Conceptually:

```text
ContextPackage
- requested_paths[]
- resolved_sources[]
- unresolved_paths[]
- duplicate_paths[]
```

Important:

- matching counts unique normalized sources;
- duplicate user inputs must not satisfy cardinality multiple times;
- unresolved/non-inventoried paths remain visible as package problems;
- the validator must not read arbitrary bodies merely because a path was supplied;
- package contents are not persisted.

## 10.6 `ContextRuleResult`

Each rule should produce inspectable results:

```text
ContextRuleResult
- rule_id
- mode
- matched_paths[]
- match_count
- min_count
- max_count
- satisfied
```

This is important even when there is no finding.

It gives Phase 6 a reusable validation seam without requiring message parsing.

## 10.7 `ContractFinding`

A contract finding should be separate enough to represent contract/rule identity explicitly.

Conceptually:

```text
ContractFinding
- id
- contract_id
- rule_id?
- code
- severity
- message
- affected_paths[]
```

Recommended codes:

```text
package_source_unavailable
required_context_missing
context_rule_overfilled
excluded_context_present
```

Optional duplicate-path handling may use a structured warning rather than a finding:

```text
duplicate_package_source
```

Requirements:

- deterministic ID;
- deterministic ordering;
- repository-relative paths only;
- no timestamps in stable JSON;
- no source bodies;
- no arbitrary exception text;
- messages are not identity inputs.

Severity remains descriptive only; no process-failure threshold is added.

## 10.8 `ContractValidationOverview`

Conceptually:

```text
ContractValidationOverview
- repository
- config_sha256
- contract
- requested_paths[]
- resolved_paths[]
- rule_results[]
- findings[]
- warnings[]
- schema_version = 1
```

This is derived output and fully rebuildable.

---

# 11. Why Authority Policy Resolution Is Deferred Inside Contract Rules

The repository already has question-specific authority policies, but current authority resolution is source-role based across the repository rather than claim/subject scoped.

A naive Phase 5 rule such as:

```text
authority_policy = architectural_intent
```

could incorrectly reject an architecture document merely because some unrelated active ADR exists at a stronger authority tier elsewhere in the repository.

Therefore Contract v1 should support:

```text
authority_classes = [...]
```

as explicit matching metadata, but should **not** silently invoke global authority winner selection as a selector.

Future claim/task-scoped authority integration can add this safely when semantics are strong enough.

This is a deliberate correctness boundary, not a missing shortcut.

---

# 12. Freshness Semantics in Phase 5

The PRD anticipates freshness requirements.

Phase 5 should provide only the deterministic freshness semantics already available from the inventory:

- selected sources are resolved from the current inventory observation;
- source revision/content hash remains inspectable in validation output where useful;
- lifecycle can be explicitly constrained by contract rules.

Do not add:

- wall-clock TTLs;
- "changed within N days";
- remote revision checks;
- Git age heuristics;
- automatic stale-claim inference.

A later contract schema version may add richer freshness policy.

---

# 13. Integrity Requirements in Phase 5

The PRD anticipates contract integrity rules such as:

```text
no unresolved high-severity contradictions
```

Phase 5 should **not** run or gate on the entire Phase 4 integrity engine as an implicit side effect of contract validation.

Reasons:

- Phase 4 findings are repository integrity review signals, not yet a governance state machine;
- semantic contradiction support does not exist yet;
- severity enforcement is intentionally deferred;
- hidden coupling would make contract validation depend on Git change scope.

Keep the APIs composable so Phase 6/11 can combine:

```text
contract validation
+
integrity state
+
compiler behavior
```

later.

---

# 14. Budget Policy in Phase 5

The broader contract concept anticipates size/token budgets.

Do not implement package selection or rejection based on token/byte budget in Phase 5.

Budgeting is part of Phase 6 context compilation.

A contract v1 rule may bound **source count** only because count is directly part of deterministic completeness/exclusion semantics.

Do not introduce a tokenizer dependency.

---

# 15. `contracts.py` Responsibilities

Add:

```text
src/context_integrity/contracts.py
```

Responsibilities:

- expose effective repository contracts from configuration;
- resolve a contract by ID;
- normalize/resolve explicit package paths against current inventory;
- match a source against a rule;
- evaluate cardinality;
- emit rule results;
- emit deterministic contract findings/warnings;
- return a contract-validation overview.

It must not own:

- filesystem enumeration;
- config parsing;
- source classification;
- source-body reads;
- authority policy definitions;
- Phase 4 integrity rules;
- context ranking;
- context retrieval;
- token budgeting;
- rendering;
- CLI behavior.

Prefer pure functions over stateful service classes unless implementation evidence requires otherwise.

---

# 16. Matching Semantics

For each selected, resolved `SourceRecord`, a rule matches when every configured selector dimension matches.

Pseudo-logic:

```text
match(source, rule):
    if rule.paths and source.path not in rule.paths:
        return false
    if rule.kinds and source.kind not in rule.kinds:
        return false
    if rule.authority_classes and source.authority_class not in rule.authority_classes:
        return false
    if rule.lifecycles and source.lifecycle not in rule.lifecycles:
        return false
    return true
```

No selector should perform source-body inspection.

## 16.1 Required Rule

If:

```text
match_count < min_count
```

emit:

```text
required_context_missing
```

If a maximum exists and:

```text
match_count > max_count
```

emit:

```text
context_rule_overfilled
```

## 16.2 Optional Rule

Absence is valid.

If a maximum exists and it is exceeded:

```text
context_rule_overfilled
```

## 16.3 Excluded Rule

If any selected source matches:

```text
excluded_context_present
```

The validator must not silently remove it.

---

# 17. Package Source Resolution

User-supplied source paths must pass the same safe repository-relative normalization semantics used elsewhere.

For each package path:

- normalize safely;
- map to an inventoried source by exact normalized path;
- count unique resolved sources once;
- preserve unresolved paths for reporting;
- preserve duplicates as warnings/diagnostics if supplied repeatedly.

A supplied path that is not in the inventory should produce a bounded finding such as:

```text
package_source_unavailable
```

rather than causing arbitrary file reads or expanding inventory candidate rules inside the contracts module.

This means Phase 5 validates **current Context Integrity source items**, not all code files in the repository.

Broader code context arrives through later compiler/evidence integration.

---

# 18. Contract Finding Identity and Ordering

Stable IDs should be derived from stable semantic fields such as:

```text
contract_id
rule_id or package-level scope
code
sorted affected paths
```

Do not hash:

- prose message text;
- timestamps;
- absolute paths;
- process-specific state.

Recommended finding ordering:

```text
severity presentation rank
contract_id
rule_id
code
affected_paths
finding_id
```

Recommended rule-result ordering:

```text
contract rule declaration order
```

or stable rule-ID order.

Pick one and document/test it.

Configuration serialization should not accidentally depend on TOML dictionary insertion details.

---

# 19. CLI Surface

Add a `contracts` command group.

Recommended commands:

```bash
context-integrity contracts list [PATH]
context-integrity contracts show CONTRACT_ID [PATH]
context-integrity contracts validate CONTRACT_ID [PATH] --source SOURCE ...
```

Common options:

```text
--format text|json
--output PATH
```

Examples:

```bash
context-integrity contracts list .
context-integrity contracts show implementation-task .
context-integrity contracts validate implementation-task . \
  --source docs/current-state.md \
  --source docs/plans/phase-5-implementation-plan.md \
  --source docs/architecture.md

context-integrity contracts validate implementation-task . \
  --source docs/current-state.md \
  --format json \
  --output contract-validation.json
```

## 19.1 Contract Selection

Phase 5 validation selects a contract by **explicit contract ID**.

Do not automatically select a contract from `task_class` or natural-language task input yet.

`task_class` is retained as stable metadata for future task-classification/compilation hooks.

## 19.2 Empty Package

Allow validation of an empty package.

This is useful because it deterministically demonstrates which required rules are unsatisfied.

## 19.3 Exit Behavior

Contract violations are findings, not CI governance.

On successful evaluation:

```text
exit 0
```

even when findings exist.

Preserve existing fatal categories where applicable:

```text
2  requested contract/item not found or invalid CLI selection
3  repository failure
4  output write failure
6  configuration failure
```

Do not add severity-based failing exits in Phase 5.

---

# 20. Text Output

Illustrative output:

```text
Context Contract Validation

Contract: implementation-task
Task class: implementation
Selected sources: 3
Findings: 1

Rules
  PASS  current-state       required  matches=1  min=1  max=1
  FAIL  active-plan         required  matches=0  min=1
  PASS  architecture        optional  matches=1  max=2
  PASS  historical-context  excluded  matches=0

HIGH  required_context_missing
  Contract rule active-plan requires at least 1 matching source; found 0.

Warnings: 0
```

Do not print source bodies.

Repository-controlled strings must be escaped/sanitized consistently with existing rendering behavior.

---

# 21. Contract Validation JSON v1

Create a separate stable machine-readable projection.

Do not modify existing public JSON v1 shapes.

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
  "config_sha256": "...",
  "contract": {
    "id": "implementation-task",
    "task_class": "implementation",
    "description": "Context required for active implementation work."
  },
  "package": {
    "requested_paths": [
      "docs/current-state.md"
    ],
    "resolved_paths": [
      "docs/current-state.md"
    ],
    "unresolved_paths": [],
    "duplicate_paths": []
  },
  "rules": [
    {
      "id": "current-state",
      "mode": "required",
      "matched_paths": [
        "docs/current-state.md"
      ],
      "match_count": 1,
      "min_count": 1,
      "max_count": 1,
      "satisfied": true
    }
  ],
  "findings": [],
  "warnings": []
}
```

Requirements:

- deterministic order;
- explicit schema version;
- repository-relative paths;
- no absolute root;
- no timestamps;
- no source bodies;
- no arbitrary exception strings;
- no generic dataclass dump that accidentally changes public schema;
- stable newline termination.

If source revision metadata is included for matched package items, keep it bounded and use the existing stable revision projection style.

---

# 22. Contract List / Show Output

`contracts list` should make configured contracts discoverable without validating a package.

Minimum text information:

```text
id
task_class
rule count
description
```

`contracts show` should expose:

```text
contract identity
rule identity
rule mode
selectors
cardinalities
```

If JSON is supported for list/show, use a deliberate stable shape.

Do not reuse the validation JSON schema for semantically different output merely for convenience.

---

# 23. Security and Trust Boundaries

Phase 5 should not expand dangerous read or execution behavior.

## 23.1 Repository Content Remains Untrusted

Contract configuration and source metadata are repository input.

Do not execute source text.

## 23.2 No Source-Body Reads for Matching

Contract v1 selectors rely on inventory metadata only.

Do not call bounded text readers merely to evaluate path/kind/authority/lifecycle selectors.

## 23.3 Safe Paths

Reuse the durable safe normalized repository-relative path invariant.

Reject:

- absolute paths;
- traversal;
- backslash/drive ambiguity where configuration currently rejects it;
- config self-reference only when semantically necessary, not as a blanket rule without reason.

## 23.4 Sanitized Errors

Invalid config should continue to return the repository's sanitized configuration error rather than leaking arbitrary TOML/repository text.

## 23.5 No Network / External Services

No network, model, database, or remote Git requirement may be added.

---

# 24. Expected Implementation Shape

Expected touched/new files may include:

```text
src/context_integrity/models.py
src/context_integrity/configuration.py
src/context_integrity/contracts.py          # new
src/context_integrity/rendering.py
src/context_integrity/cli.py

tests/test_contracts.py                    # new
tests/test_configuration.py
tests/test_cli.py
tests/test_rendering.py
possibly tests/test_models.py
possibly a concise contracts JSON golden fixture

README.md
docs/current-state.md
docs/implementation-reports/phase-5-implementation-report.md
docs/architecture.md                       # only for durable clarifications
```

Do not create a module per data class.

Do not create a generic policy framework merely because contracts may later grow.

---

# 25. Recommended Implementation Sequence

## Step 0 — Confirm Starting Revision Without Re-Running Phase 4

- inspect actual HEAD and working tree;
- confirm `docs/current-state.md` and the Phase 4 implementation report contain the recorded review-fix verification;
- treat the recorded 532-test Phase 4 gate and focused verification as accepted predecessor evidence;
- do **not** rerun Phase 4 baseline verification or the separate final independent verification;
- if HEAD advanced, inspect the delta and preserve accepted newer work.

Read, in order:

1. `AGENTS.md`;
2. `docs/current-state.md`;
3. this Phase 5 plan;
4. relevant sections of `docs/architecture.md`;
5. relevant sections of `docs/prd.md` for Context Contracts / roadmap;
6. current `models.py`, `configuration.py`, `authority.py`, `lifecycle.py`, `integrity.py`, `cli.py`, `rendering.py`;
7. Phase 4 implementation report only for accepted predecessor behavior and recorded verification evidence.

## Step 1 — Add Contract Domain Models

Add:

- rule mode;
- rule model;
- contract model;
- package/result/finding overview models as needed.

Put invariants in the model constructors.

Add focused direct-construction tests before parser wiring.

## Step 2 — Add Configuration v5

Extend strict parser:

- allow `context_contracts` only in v5;
- parse nested rules;
- validate IDs, enums, exact paths, cardinality;
- reject unknown keys;
- reject duplicate contract IDs;
- reject duplicate rule IDs per contract;
- preserve all v1–v4 behavior.

## Step 3 — Implement Pure Contract Matching

Create `contracts.py` with:

- source/rule matcher;
- package resolution;
- cardinality evaluation;
- deterministic rule results;
- deterministic findings.

No rendering or CLI logic here.

## Step 4 — Add Contract Discovery

Expose list/show behavior from parsed repository contracts.

Do not add built-in generic contracts merely to populate the list unless a compelling product requirement emerges.

## Step 5 — Add Validation Rendering

Implement text and contract-validation JSON v1.

Keep existing renderers/projections unchanged.

## Step 6 — Add CLI

Add `contracts list/show/validate` as a thin adapter.

Reuse existing inventory/config/repository error handling patterns.

## Step 7 — Focused Tests

Add compact synthetic fixtures covering semantic boundaries.

Avoid combinatorial explosion across every selector permutation.

## Step 8 — Real / Disposable Smoke

Because the repository may not yet contain a v5 config, use either:

- a small disposable repository with a v5 contract; or
- a deliberately added repository contract only if there is a real dogfooding reason.

Exercise:

```bash
context-integrity contracts list
context-integrity contracts show <id>
context-integrity contracts validate <id> --source ...
context-integrity contracts validate <id> --source ... --format json
```

## Step 9 — Full Gate and Compatibility Check

Run:

```bash
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check
git diff --check
```

Confirm existing stable JSON golden fixtures are unchanged.

## Step 10 — Documentation

Create/update:

- `docs/implementation-reports/phase-5-implementation-report.md`;
- `README.md` for v5 contract config and commands;
- `docs/current-state.md` only after Phase 5 verification;
- `docs/architecture.md` only if implementation establishes a durable rule not already captured.

Do not rewrite completed phase plans/reports to make historical statements appear current.

---

# 26. Focused Testing Strategy

Testing should prove semantics, not maximize test count.

## 26.1 Model Invariants

Prove direct construction rejects:

- invalid contract ID;
- invalid task class;
- duplicate rule IDs;
- invalid rule ID;
- no selector dimensions;
- duplicate selector values;
- unsafe exact paths;
- invalid cardinalities;
- optional rule with positive minimum if disallowed by chosen model;
- excluded rule with weakened max/min;
- max less than min.

## 26.2 Config v5

Prove:

- valid v5 retaining earlier features;
- v1–v4 reject `context_contracts`;
- unknown contract/rule keys reject;
- duplicate contract IDs reject;
- duplicate rule IDs reject;
- enum values reject when invalid;
- unsafe paths reject;
- invalid count types reject (`bool` must not be accepted as `int` accidentally);
- errors remain sanitized.

## 26.3 Matching Semantics

Use a small matrix to prove:

- path OR within paths;
- kind OR within kinds;
- dimensions combine with AND;
- omitted dimensions do not constrain;
- authority class filter works;
- lifecycle filter works;
- no source-body semantics are involved.

## 26.4 Required / Optional / Excluded

Prove:

- required minimum satisfied;
- required minimum missing;
- required maximum exceeded;
- optional absent is valid;
- optional maximum exceeded;
- excluded absent is valid;
- excluded matched produces finding.

## 26.5 Package Resolution

Prove:

- normalized selected path resolves;
- unresolved/non-inventoried path is visible and does not satisfy a rule;
- duplicate supplied source does not count twice;
- empty package is valid input and exposes missing required rules;
- path traversal/absolute path is rejected safely.

## 26.6 Determinism

Prove:

- same repository/config/package -> same finding IDs;
- rule-result ordering stable;
- finding ordering stable;
- JSON repeated runs byte-identical for the same observed state.

## 26.7 CLI

Prove:

- list/show/validate happy paths;
- unknown contract -> exit 2;
- findings still -> exit 0;
- config failure -> exit 6;
- output write failure -> exit 4;
- text and JSON paths;
- repeated `--source` behavior.

## 26.8 Compatibility

Prove:

- v1–v4 config behavior remains;
- inventory JSON v1 unchanged;
- authority JSON v1 unchanged;
- lifecycle JSON v1 unchanged;
- claims JSON v1 unchanged;
- integrity JSON v1 unchanged.

Do not create dozens of near-duplicate fixtures when table-driven tests cover the same semantic boundary.

---

# 27. Acceptance Criteria

Phase 5 is complete only when all of the following are true.

## A. Domain contract

- Context Contract is a first-class typed domain model.
- Contract/rule invariants are enforced outside the parser too.
- Contract rules support required/optional/excluded modes.
- Selector semantics are explicit and deterministic.
- Cardinality semantics are explicit and deterministic.

## B. Configuration

- schema v5 is implemented strictly;
- v1–v4 compatibility remains;
- older schemas reject v5-only keys;
- invalid contracts fail closed with sanitized errors.

## C. Validation

- explicit package paths resolve against current inventory;
- required context can be proven present/missing;
- optional context can be bounded without becoming required;
- excluded context can be detected;
- unresolved package sources are reported;
- duplicates do not inflate counts;
- validator does not mutate/complete the package.

## D. Phase boundary

- no automatic retrieval;
- no ranking;
- no token budget;
- no natural-language task classifier;
- no Codebase Intelligence integration;
- no LLM;
- no database;
- no CI enforcement.

## E. Interfaces

- contracts are discoverable;
- a contract can be shown;
- an explicit package can be validated;
- text output is useful and bounded;
- contract-validation JSON v1 is stable and private-path safe.

## F. Compatibility / quality

- existing machine-readable projections remain stable;
- full offline gate passes;
- focused tests cover the semantic boundaries above;
- no unnecessary runtime dependency is introduced.

## G. Documentation

- Phase 5 implementation report records actual baseline, changes, tests, deviations, limitations;
- README documents user-facing v5 contract syntax/CLI;
- current-state reflects Phase 5 only after verified delivery;
- durable architectural semantics are promoted appropriately;
- historical docs are not rewritten merely because they describe an earlier state.

---

# 28. Definition of Done for the Implementation Report

The Phase 5 implementation report should explicitly record:

- actual starting HEAD;
- accepted Phase 4 predecessor verification evidence (do not rerun it solely for the report);
- final Phase 5 test count;
- files changed;
- exact v5 config semantics delivered;
- exact rule matcher semantics;
- exact CLI commands delivered;
- JSON schema/output decisions;
- any deviation from this plan and why;
- known limitations;
- explicit deferrals to Phase 6+;
- verification commands and results;
- whether existing JSON goldens remained byte-identical.

Do not claim broader Context Contract capabilities that were intentionally deferred.

---

# 29. Deferred Phase 6+ Hooks

Phase 5 should leave clean seams for, but not implement:

## Phase 6 — Task Context Compiler

Will need to consume:

```text
ContextContract
ContextRuleResult / validation semantics
current source inventory
candidate sources
```

and add:

- candidate acquisition;
- lifecycle/authority filtering;
- required/excluded enforcement while selecting;
- deduplication;
- ranking;
- budget fitting;
- compiled context provenance/dependencies.

## Phase 7 — Codebase Intelligence Adapter

Will add structured code context candidates/evidence.

Contract selectors may later need a generalized context-item abstraction rather than only `SourceRecord`.

Do not invent that abstraction prematurely if the current source model cleanly supports Phase 5.

## Later Contract Versions

Potential additions:

- claim/subject selectors;
- authority-policy semantics scoped to a claim/task;
- richer freshness;
- integrity requirements;
- token/byte budgets;
- contract composition;
- cross-repo scope;
- code-symbol/entity selectors.

Each should require an explicit schema/version decision.

---

# 30. Final Implementation Guidance

Prefer the smallest implementation that makes Context Contracts real, deterministic, inspectable, and reusable by Phase 6.

The important outcome is not a large policy DSL.

It is a trustworthy boundary:

```text
repository-defined contract
+
explicit current package
->
structured, deterministic validation result
```

If implementation pressure starts turning Phase 5 into retrieval/ranking/compilation, stop and preserve that work for Phase 6.
