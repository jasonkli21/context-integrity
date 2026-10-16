# Context Integrity — Phase 6 Detailed Implementation Plan

**Phase:** 6 — Task Context Compiler
**Status:** Ready for implementation
**Date:** 2026-10-16
**Repository:** `jasonkli21/context-integrity`
**Inspected default branch:** `main`
**Inspected HEAD:** `9a4ee1dd56fcec63799e6fa777eccb68ec9ae0b4` (`Fix Phase 5 contract review findings`)
**Parent documents:** `docs/prd.md`, `docs/architecture.md`
**Current-state document:** `docs/current-state.md`
**Predecessor:** Phase 5 — Context Contracts
**Successor:** Phase 7 — Codebase Intelligence `EvidenceProvider` integration
**Related project:** Codebase / Context Intelligence Engine; intentionally not integrated in this phase

---

# 1. Phase Objective

Phase 6 introduces the first **deterministic Task Context Compiler**.

The compiler turns the policy that Phase 5 can only *validate* into an automatically assembled, bounded, inspectable context selection.

The core Phase 6 question is:

> **Given an explicitly selected repository context contract, the current observed repository inventory, and an optional byte budget, which current context sources should be selected, which should be rejected or omitted, and why?**

The intended progression is:

```text
Phase 0–4
source inventory
  -> source role / authority
  -> lifecycle + supersession
  -> explicit claims / provenance
  -> deterministic integrity findings

Phase 5
configured contract
  + explicit user-supplied package
  -> deterministic package validation

Phase 6
configured contract
  + current inventory candidates
  + lifecycle / authority policy
  + deterministic selection
  + byte budget
  -> compiled context manifest
  -> Phase 5 validation of the selected package

Phase 7
Phase 6 compiler
  + code candidates / structural relevance from Codebase Intelligence
  -> mixed documentation + code task context
```

The primary architectural invariant of this phase is:

```text
context compilation selects from observed evidence;
it does not invent evidence, silently rewrite policy,
or become a second code-relevance engine.
```

---

# 2. Alignment with the PRD and Architecture

The aligned PRD defines Phase 6 as the **Task Context Compiler** with goals to:

- retrieve;
- authority-filter;
- deduplicate;
- remove superseded context;
- fit budget;
- produce task context.

The PRD's task-specific compilation pipeline is broader:

```text
Task
  -> classify requirements
  -> retrieve candidates
  -> validate authority
  -> remove superseded/stale context
  -> resolve contradictions
  -> apply required context contract
  -> rank / budget
  -> compiled context
```

The architecture similarly defines:

```text
Task
  -> Resolve context contract
  -> Acquire candidates
  -> Validate lifecycle
  -> Apply authority
  -> Resolve / surface contradictions
  -> Enforce required + excluded context
  -> Deduplicate / rank
  -> Fit budget
  -> CompiledContext + provenance/dependencies
```

The architecture also locks two constraints that matter directly here:

1. **Authority class is not a universal scalar rank.**
2. **The context compiler may consume relevance rankings but owns authority/lifecycle filtering itself.**

Phase 6 therefore must implement the deterministic policy/selection part of that pipeline without pretending that structural code relevance already exists.

## 2.1 Deliberate Phase 6 Interpretation

The current repository does **not** yet have:

- Codebase Intelligence candidates;
- code symbols/entities;
- semantic task relevance;
- general contradiction resolution;
- verified claim truth;
- learned ranking;
- embeddings/vector search;
- LLM task classification.

Those are not prerequisites to ship a useful first compiler.

Phase 6 should compile **repository context sources already present in the current inventory** and make every filtering/selection decision inspectable.

The compiler output is a **compiled context manifest**, not a new canonical source of truth and not a hidden source-body cache.

---

# 3. Current Delivered Baseline

Implementation must begin from the repository's actual current state.

Inspected HEAD:

```text
9a4ee1dd56fcec63799e6fa777eccb68ec9ae0b4
Fix Phase 5 contract review findings
```

`docs/current-state.md` records:

- Phase 5 — Context Contracts as the current delivered phase;
- Phase 5 implementation and offline verification complete;
- Phase 5 review findings F-001–F-003 fixed and verified;
- full gate at 632 tests;
- Phase 6 — Task Context Compiler as the next expected implementation step;
- a separately pending Phase 4 final independent verification that is **not Phase 6 work**.

At this baseline the repository already has:

- deterministic local source inventory;
- strict configuration schema versions v1–v5;
- source kinds and authority classes;
- question-specific authority policies;
- lifecycle and directional supersession;
- explicit claims and provenance;
- deterministic Phase 4 integrity findings;
- repository-defined Context Contracts;
- explicit package resolution and contract validation;
- separate stable JSON v1 projections for earlier surfaces;
- `scan`, `explain`, `authority`, `lifecycle`, `claims`, `check`, and `contracts` CLI surfaces;
- no `compiler.py` module yet;
- no delivered `CompiledContext` model;
- no automatic candidate selection/ranking/budgeting.

## 3.1 Phase 5 Review-Fix Invariants That Phase 6 Must Preserve

The post-review Phase 5 state added important invariants:

1. Nonempty contracts cannot exist under configuration schemas v1–v4.
2. Contract validation requires the **exact configured contract** observed in the manifest.
3. The contract's `config_revision` must match the observed repository configuration digest.
4. Phase 4 integrity and Phase 5 contract responsibilities are now separated accurately in architecture documentation.

Phase 6 must not weaken or bypass those guarantees.

In particular:

```text
compiler input contract
must be the contract bound to
the exact observed manifest configuration
```

Do not accept an arbitrary caller-constructed lookalike contract as if it were repository policy.

---

# 4. Starting-State Workflow

At the start of the implementation session, do only enough predecessor work to establish the actual baseline:

```bash
git status --short
git rev-parse HEAD
git log -8 --oneline
```

Then read, in repository-instruction order:

1. `AGENTS.md`
2. `docs/current-state.md`
3. this Phase 6 plan
4. relevant Phase 5 implementation evidence
5. relevant sections of `docs/architecture.md`
6. relevant current source/tests
7. `docs/prd.md` only where product scope needs confirmation

If HEAD has advanced beyond the inspected commit:

- inspect newer changes;
- preserve accepted newer work;
- reconcile this plan against current reality;
- do **not** reset to the reference SHA.

Do not:

- rerun old review sessions;
- redo Phase 5 fixes merely to recreate evidence;
- perform the separately pending Phase 4 final independent verification;
- edit completed historical plans/reports to make them describe later reality.

A full `make check` at the end is still required because Phase 6 must preserve all earlier public behavior.

---

# 5. Core User Journey

A repository defines an implementation-oriented contract:

```toml
schema_version = 6

[[context_contracts]]
id = "implementation-task"
task_class = "implementation"
description = "Context for active implementation work."
budget_bytes = 120000

[[context_contracts.rules]]
id = "instructions"
mode = "required"
paths = ["AGENTS.md"]
min_count = 1
max_count = 1
priority = 100
authority_policy = "operating_instructions"

[[context_contracts.rules]]
id = "current-state"
mode = "required"
kinds = ["current_state"]
lifecycles = ["unknown", "active"]
min_count = 1
max_count = 1
priority = 90

[[context_contracts.rules]]
id = "active-plan"
mode = "required"
kinds = ["implementation_plan"]
lifecycles = ["unknown", "active"]
min_count = 1
max_count = 1
priority = 80
authority_policy = "future_work"

[[context_contracts.rules]]
id = "architecture"
mode = "optional"
kinds = ["architecture"]
lifecycles = ["unknown", "active"]
max_count = 2
priority = 50

[[context_contracts.rules]]
id = "historical"
mode = "excluded"
lifecycles = ["superseded", "historical", "expired", "invalid"]
```

The user runs:

```bash
uv run context-integrity compile implementation-task . \
  --task "Implement the next repository phase" \
  --format text
```

The compiler:

1. loads one coherent repository observation;
2. resolves the exact configured contract;
3. acquires current inventory sources as candidates;
4. applies explicit contract selectors;
5. applies Phase 6 lifecycle defaults only where the contract does not explicitly choose lifecycle;
6. applies any **rule-scoped** authority policy;
7. rejects candidates matching excluded rules;
8. deduplicates a source that satisfies multiple rules;
9. selects enough required context first;
10. adds optional context by deterministic priority while respecting cardinality and budget;
11. validates the final selected paths through Phase 5 contract validation;
12. emits a provenance-rich compiled manifest with selected and omitted candidates and selection reasons.

A failing/incomplete example must remain inspectable:

```text
budget too small for the only authoritative active plan
```

The compiler must **not** silently substitute a lower-authority plan merely because it is smaller.

Instead the result should state that required context could not be satisfied under the current policy/budget.

---

# 6. Product Boundary

## 6.1 In Scope

Phase 6 includes:

- first-class compiled-context domain models;
- deterministic candidate assembly from the current source inventory;
- exact bound-contract enforcement;
- configuration schema v6;
- backward-compatible v1–v5 configuration behavior;
- optional contract-level byte budget;
- rule-level selection priority;
- optional rule-scoped authority policy;
- lifecycle-aware candidate eligibility;
- deterministic excluded-context rejection;
- deterministic deduplication across overlapping rules;
- deterministic required-first selection;
- deterministic optional fill;
- source-size budget accounting;
- transparent candidate decisions/reasons;
- preservation of source revisions and config/contract provenance;
- final Phase 5 validation of the selected package;
- a top-level `compile` CLI command;
- text output;
- separate compiled-context JSON v1 output;
- focused synthetic repository/compiler tests;
- implementation report;
- README/current-state/architecture updates where the source of truth changes.

## 6.2 Explicitly Out of Scope

Do **not** implement:

- Phase 7 Codebase Intelligence integration;
- AST parsing;
- symbol extraction;
- code dependency graphs;
- code impact analysis;
- code relevance ranking;
- code-context retrieval;
- cross-repository compilation;
- natural-language task-class inference;
- automatic contract selection from task text;
- embeddings/vector search;
- LLM calls;
- learned ranking;
- model-based relevance;
- claim truth verification;
- general contradiction detection;
- automatic contradiction resolution;
- semantic architectural integrity;
- time-based freshness policies;
- persistence/database storage;
- compiled-context cache;
- background invalidation service;
- source-body materialization/bundling;
- prompt-template generation;
- automatic file rewriting;
- CI enforcement;
- severity-based process failure;
- waivers/governance;
- hosted/API/MCP surface.

Phase 6 may **surface** already-available integrity findings or ambiguity metadata, but it must not pretend to implement deferred semantic integrity engines.

---

# 7. Configuration Schema v6

Introduce:

```text
schema_version = 6
```

Schema v6 retains all v5 behavior and adds **compiler policy metadata** to existing context contracts.

## 7.1 Backward Compatibility

After Phase 6:

```text
v1
- authority

v2
- v1
- lifecycle / supersession

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

v6
- v5
- deterministic compiler policy metadata
```

Requirements:

- v1–v5 parse exactly as before;
- v1–v5 reject v6-only keys;
- v6 retains all prior semantics;
- no silent schema upgrade;
- unknown keys fail closed;
- errors remain sanitized;
- existing JSON projections remain unchanged.

## 7.2 Contract-Level Compiler Field

Add:

```text
budget_bytes: int | None
```

Semantics:

- optional;
- positive integer only;
- booleans are invalid;
- `None` means unbounded unless the CLI supplies an override;
- this counts observed source bytes, not estimated LLM tokens;
- it is a selection constraint, not proof that a downstream model will fit an exact token window.

Do **not** introduce a tokenizer dependency in Phase 6.

## 7.3 Rule-Level Compiler Fields

Add:

```text
priority: int = 0
authority_policy: str | None = None
```

Semantics:

### `priority`

- nonnegative integer;
- booleans invalid;
- higher value means earlier preference during deterministic selection;
- required rules remain required regardless of priority;
- priority decides deterministic allocation pressure when the budget cannot satisfy every desired item;
- priority is a policy preference, **not semantic relevance**.

### `authority_policy`

- optional stable authority policy ID;
- syntactically validated like existing policy IDs;
- when present, authority is resolved **within candidates matching that rule**, not over the entire repository;
- only the highest observed eligible policy tier for that rule is selectable;
- lower tiers remain inspectable as omitted candidates;
- lifecycle/explicit authority eligibility semantics must reuse the authority subsystem rather than reimplementing them in the compiler;
- an unknown referenced policy is a configuration/policy error, not a silent fallback.

## 7.4 Why Authority Must Be Rule-Scoped

A whole task package can legitimately need different authority semantics:

```text
instructions rule
  -> operating_instructions policy

active plan rule
  -> future_work policy

architecture rule
  -> architectural_intent policy
```

Using one global numeric source rank would violate the architecture.

Do not create:

```text
decision = 100
architecture = 80
plan = 60
...
```

and sort all sources globally.

---

# 8. Model Changes

Stable domain models belong in `models.py`; selection behavior belongs in a dedicated `compiler.py`.

Recommended concepts:

```text
CompilationStatus
CandidateDecisionKind
CompilationBudget
CompiledSourceDecision
CompiledDependency
CompiledContext
```

Exact names may vary if the implementation finds a cleaner shape, but the semantics below are normative.

## 8.1 `CompilationStatus`

Recommended values:

```text
complete
incomplete
```

`complete` means:

- final selected paths satisfy the configured contract under Phase 5 validation;
- no compiler-internal fatal policy inconsistency prevented selection.

`incomplete` means the compiler produced an inspectable result but could not satisfy the contract under the current candidates/policy/budget.

Do not turn ordinary incomplete compilation into a process failure in Phase 6.

## 8.2 `CandidateDecisionKind`

Recommended values:

```text
selected
excluded_by_contract
ineligible_lifecycle
ineligible_authority
lower_authority_tier
blocked_by_rule_max
blocked_by_budget
unverifiable_revision
redundant
not_selected
```

The implementation may consolidate categories, but the public result must distinguish materially different reasons.

## 8.3 `CompilationBudget`

Conceptually:

```text
CompilationBudget
- configured_bytes?
- requested_bytes?
- effective_bytes?
- used_bytes
- remaining_bytes?
```

Requirements:

- CLI override, if supplied, wins over contract default;
- negative/zero values are usage errors;
- arithmetic must be overflow-safe in ordinary Python integer semantics;
- total used bytes equals the unique selected sources' observed `size_bytes`;
- one source selected for multiple rules counts once.

## 8.4 `CompiledSourceDecision`

Conceptually:

```text
CompiledSourceDecision
- source
- decision
- matched_rule_ids[]
- contributing_rule_ids[]
- authority_context[]
- reason_codes[]
- size_bytes
```

The decision should make it possible to answer:

> Why was this file included or omitted?

Do not make message prose the only machine-readable explanation.

## 8.5 `CompiledDependency`

A compiled context is derived state and must be invalidatable.

At minimum retain:

```text
CompiledDependency
- source_id
- path
- source_revision
```

The compiled artifact also depends on:

```text
repository identity
configuration content SHA
contract ID
contract config revision
compiler schema/version
```

Do not claim an atomic snapshot. The existing repository observation remains sequential.

## 8.6 `CompiledContext`

Conceptually:

```text
CompiledContext
- repository
- task?
- task_class
- contract
- config_sha256
- status
- budget
- selected_sources[]
- decisions[]
- validation
- integrity_findings[]?   # only existing deterministic findings if surfaced
- dependencies[]
- warnings[]
- schema_version = 1
```

Requirements:

- selected source paths are repository-relative;
- source revisions retain content hashes;
- no absolute root in stable JSON;
- no timestamps in stable JSON;
- no source bodies in JSON;
- no arbitrary dataclass dumping;
- deterministic ordering;
- stable separate compiled-context schema version 1.

---

# 9. Bound Contract Reuse

Phase 5 currently validates binding inside `validate_contract`.

Phase 6 needs the same invariant before compilation.

Prefer extracting a small shared helper in `contracts.py`, for example:

```text
require_bound_contract(manifest, contract)
```

Then:

```text
validate_contract(...)
compile_context(...)
```

both use the same rule.

Requirements:

- preserve existing Phase 5 behavior and exceptions;
- do not weaken equality/revision checks;
- do not duplicate slightly different contract-binding logic;
- regression-test foreign, mutated, and stale-revision contract rejection.

The CLI should always resolve the requested contract from the observed manifest configuration.

---

# 10. Candidate Acquisition

Phase 6's candidate universe is:

```text
manifest.sources
```

This is intentionally limited.

Do not:

- recursively read arbitrary user paths;
- scan ordinary code files outside the current inventory model;
- fetch remote sources;
- query the Codebase Intelligence project;
- create synthetic sources merely to satisfy a contract.

Every candidate already has:

- source ID;
- repository-relative path;
- kind;
- authority class;
- lifecycle;
- revision;
- observed size;
- classification/provenance basis.

## 10.1 Revision Requirement

A selected compiled source must be dependency-trackable.

If a candidate does not have a usable content revision/hash, it should not silently become selected context.

Recommended behavior:

- mark it `unverifiable_revision`;
- keep it inspectable;
- allow final contract validation to show resulting incompleteness.

Do not fabricate a hash from path or Git HEAD.

---

# 11. Lifecycle Semantics

Phase 5 validation has **no hidden lifecycle filter**. Preserve that behavior.

Phase 6 compilation, however, must implement current-context selection.

Recommended compiler rule:

```text
If a rule explicitly declares `lifecycles`,
use exactly those lifecycle selectors.

If the rule omits `lifecycles`,
the compiler's default selectable lifecycle set is:
  unknown
  active
```

This is a compiler policy, not a change to Phase 5 validation.

Therefore:

- `draft`, `superseded`, `historical`, `expired`, and `invalid` are omitted by default;
- a research/history contract can still explicitly request historical or superseded context;
- recency never implies lifecycle;
- explicit supersession remains authoritative;
- no mtime/Git-date currentness heuristic is introduced.

Record lifecycle exclusion as a structured reason.

---

# 12. Authority Semantics

Authority is applied only where a rule explicitly references an `authority_policy`.

## 12.1 Reuse, Do Not Reimplement

The existing `resolve_authority` logic owns:

- lifecycle authority eligibility;
- explicit `authority_eligible = false`;
- policy membership;
- tier resolution;
- highest/lower candidate separation.

Phase 6 should refactor that logic into a reusable subset-aware pure function if necessary.

Recommended shape:

```text
resolve_authority_for_sources(
    manifest,
    policy,
    sources
) -> AuthorityResolution
```

Keep the existing public `resolve_authority(manifest, policy, ...)` behavior as a wrapper over all manifest sources.

Regression requirement:

> Existing authority command output and JSON must remain byte-for-byte compatible where golden fixtures exist.

## 12.2 Rule-Scoped Resolution Order

For a rule with `authority_policy`:

1. apply the rule's normal selectors;
2. apply compiler lifecycle eligibility;
3. resolve the configured authority policy over that rule's matching candidates;
4. make highest-tier candidates selectable;
5. mark lower-tier or ineligible candidates with explicit reasons.

Authority happens **before budget**.

Do not:

- choose a lower authority tier just because it is smaller;
- use path name, mtime, plan number, or Git time as an authority tiebreaker;
- declare equal-tier sources contradictory merely because there is more than one.

## 12.3 Equal Highest-Tier Candidates

Equal-tier ambiguity must be inspectable.

The compiler may choose deterministically among equal candidates when contract cardinality/budget requires it, but it must preserve metadata indicating that equally ranked alternatives existed.

A stricter implementation that treats unresolved equal-tier narrowing as incomplete is acceptable if clearly documented and tested.

What is not acceptable:

```text
silently pick lexical winner
and pretend it was semantically preferred
```

---

# 13. Excluded-Rule Semantics

A source matching any `excluded` contract rule is not selectable.

This is global across the compiled package.

If one source simultaneously matches:

```text
required rule A
excluded rule B
```

the compiler must:

- reject the source;
- surface the conflict;
- not weaken the excluded rule to make required context pass;
- allow final validation to report the package as incomplete.

Excluded context is removed before optional budget fill.

---

# 14. Deduplication

One source may satisfy multiple rules.

Select and budget it once.

Track all rule relationships:

```text
source X
  contributes_to:
  - required rule A
  - required rule B
  - optional rule C
```

Deduplication identity should use the already stable observed source identity/path semantics.

Do not deduplicate unrelated files by:

- body similarity;
- embeddings;
- filename stem;
- content hash alone.

Content-level redundancy optimization is later work.

---

# 15. Deterministic Selection Algorithm

Phase 6 needs a simple, reviewable selection algorithm rather than a speculative optimizer.

The following is the recommended normative algorithm.

## 15.1 Precompute Rule Candidate Sets

For every rule:

1. match current inventory sources with existing Phase 5 selector semantics;
2. apply compiler lifecycle eligibility;
3. reject globally excluded matches;
4. if the rule has an authority policy, reduce selectable candidates to the highest eligible observed tier;
5. retain every omitted candidate with a structured decision reason.

## 15.2 Required Selection Pass

Goal:

```text
satisfy each required rule's min_count
with unique sources
without violating max_count or budget
```

Use a deterministic greedy coverage algorithm.

At each step:

1. determine unsatisfied required rules;
2. consider currently selectable unselected candidates that help at least one unsatisfied rule;
3. reject a candidate if adding it would violate any applicable rule maximum;
4. reject/skip it if its size would exceed the effective byte budget;
5. rank remaining candidates by:
   - number of unsatisfied required rules they can satisfy, descending;
   - highest applicable rule priority, descending;
   - sum/aggregate applicable required priorities, descending;
   - strongest already-resolved rule-scoped authority tier where relevant;
   - repository-relative path, ascending as the final deterministic tiebreaker;
6. select the first candidate;
7. repeat until all required minimums are met or no progress is possible.

Do not use semantic text similarity.

## 15.3 Optional Fill Pass

After required minima are satisfied as far as possible:

1. consider candidates that contribute to optional rules;
2. order optional rules by:
   - priority descending;
   - rule ID ascending;
3. add eligible candidates in deterministic order while:
   - respecting excluded rules;
   - respecting all relevant max counts;
   - respecting authority results;
   - respecting unique-source deduplication;
   - respecting budget.

Optional context must never displace already-selected required context.

## 15.4 Extra Required Matches

A required rule's `min_count` is a minimum, not an instruction to include every possible match.

After its minimum is satisfied, extra matches should not be added merely because they match the required rule.

They may still be selected if they:

- satisfy another unsatisfied required rule;
- satisfy an optional rule;
- are otherwise explicitly required by contract cardinality.

This keeps packages bounded.

---

# 16. Budget Semantics

Phase 6 uses **observed source bytes**.

```text
candidate cost = source.size_bytes
package cost   = sum(unique selected source sizes)
```

Do not estimate tokens in this phase.

## 16.1 Budget Precedence

```text
CLI --budget-bytes
  overrides
contract budget_bytes
  otherwise
unbounded
```

The output must state the source of the effective budget.

## 16.2 Budget Failure

If required context cannot fit:

- do not select over budget;
- do not downgrade authority;
- do not silently drop the requirement;
- return an inspectable `incomplete` compiled result;
- surface which required rule remains unsatisfied and which candidates were blocked by budget.

Incomplete compilation is a product result, not a repository/usage exception.

## 16.3 Zero/Negative Budget

A supplied zero or negative CLI budget is invalid usage.

A configured zero/negative budget is invalid configuration.

Booleans must not be accepted as integers in domain/config construction.

---

# 17. Final Contract Validation

After selection, always run the existing Phase 5 validator against the selected repository-relative paths.

Conceptually:

```text
selected_paths
  -> validate_contract(manifest, bound_contract, selected_paths)
```

This is important because the compiler should not maintain a second divergent interpretation of:

- min/max cardinality;
- required/optional/excluded behavior;
- selector semantics;
- package identity.

The resulting validation should be part of `CompiledContext`.

Status:

```text
complete
  if validation has no contract findings

incomplete
  otherwise
```

Compiler-specific warnings/decisions can add detail but must not redefine contract validity.

---

# 18. Integrity Findings and Contradictions

The architecture says the compiler must not hide unresolved high-severity integrity failures merely to fit budget.

The current repository has only the deterministic Phase 4 integrity checks, not a general contradiction engine.

Recommended Phase 6 behavior:

- do **not** invent contradiction resolution;
- do **not** mutate claim validity;
- do **not** block compilation merely because Phase 4 findings exist;
- if existing deterministic integrity findings are evaluated as part of compile, surface them separately from contract validation;
- at minimum, never label a result `integrity_clean` or equivalent unless such a claim is actually supported.

If the implementation chooses to include existing `IntegrityFinding` objects in `CompiledContext`:

- keep them structurally separate from compiler/contract findings;
- preserve their evidence/revisions;
- do not let the byte budget erase them from machine-readable output;
- document that they are review signals, not semantic contradiction resolution.

Do not expand Phase 6 into Phase 8 architectural integrity.

---

# 19. Task Metadata

The compile command should accept optional opaque task text:

```text
--task "Implement Phase 6"
```

This is metadata only.

Phase 6 must not:

- infer a task class;
- choose a contract from task text;
- score source semantics against the task text;
- send task text to a model.

The explicit contract ID is the policy-selection mechanism in this phase.

Output should include:

- contract ID;
- contract task class;
- optional task text if supplied.

This establishes a forward-compatible task field without pretending semantic retrieval exists.

---

# 20. CLI Surface

Add a top-level command:

```bash
context-integrity compile CONTRACT_ID [PATH]
```

Recommended options:

```bash
--task TEXT
--budget-bytes INTEGER
--format text|json
--output PATH
```

Examples:

```bash
uv run context-integrity compile implementation-task .
uv run context-integrity compile implementation-task . --budget-bytes 80000
uv run context-integrity compile implementation-task . \
  --task "Implement Phase 6" \
  --format json \
  --output /tmp/compiled-context.json
```

## 20.1 Exit Behavior

Preserve the existing CLI philosophy.

Recommended:

```text
0  successful command, including an inspectable incomplete compilation
2  usage / unknown contract / invalid CLI budget
3  repository failure
4  output write failure
5  reserved existing warning behavior; do not repurpose casually
6  invalid/unsafe/inconsistent repository configuration
```

No CI-style failure on incomplete context in Phase 6.

## 20.2 Thin CLI

`cli.py` should:

- load repository/inventory;
- resolve the configured contract;
- parse the CLI override;
- invoke compiler domain logic;
- render;
- write output.

It should not contain selection/ranking policy.

---

# 21. Rendering and JSON v1

Add deliberate renderers, e.g.:

```text
render_compiled_context_text(...)
render_compiled_context_json(...)
```

Do not serialize dataclasses generically.

## 21.1 Compiled Context JSON v1

Recommended top-level shape:

```json
{
  "schema_version": 1,
  "repository": {},
  "task": {},
  "contract": {},
  "config_sha256": "...",
  "status": "complete",
  "budget": {},
  "selected_sources": [],
  "decisions": [],
  "validation": {},
  "dependencies": [],
  "warnings": []
}
```

Exact names may differ if consistent with existing projection conventions.

Requirements:

- explicit schema version;
- sorted deterministic arrays;
- repository-relative paths;
- source IDs/revisions;
- config revision;
- contract/rule IDs;
- structured reason codes;
- budget numbers;
- final contract findings;
- no absolute root;
- no runtime timestamp;
- no source bodies;
- no exception text;
- newline-terminated stable JSON;
- same input observation + same arguments => byte-identical JSON.

## 21.2 Existing Projections

Inventory, authority, lifecycle, claims, integrity, and contract-validation JSON must remain unchanged.

Do not add compiler fields to prior schema v1 outputs.

---

# 22. Recommended Module Changes

## 22.1 New `src/context_integrity/compiler.py`

Own:

- bound contract compile orchestration;
- candidate eligibility;
- excluded-rule decisions;
- rule-scoped authority resolution usage;
- deduplication;
- deterministic selection;
- budget accounting;
- final selected-package validation;
- compiled result construction.

Must not own:

- filesystem discovery;
- TOML parsing;
- rendering;
- CLI I/O;
- model calls;
- Codebase Intelligence transport.

## 22.2 `src/context_integrity/models.py`

Add:

- v6 compiler fields on contract/rule models;
- compiler result models/enums;
- construction-boundary invariants.

Keep models free of filesystem/rendering dependencies.

## 22.3 `src/context_integrity/configuration.py`

Add:

- schema v6;
- strict parsing for `budget_bytes`, `priority`, `authority_policy`;
- version gating;
- sanitized validation;
- cross-reference handling for authority policy IDs at the appropriate layer.

Preserve v1–v5 behavior.

## 22.4 `src/context_integrity/contracts.py`

Refactor only what is needed to share:

- bound-contract assertion;
- existing selector semantics.

Do not move compiler behavior into `contracts.py`.

## 22.5 `src/context_integrity/authority.py`

If needed, add a subset-aware pure authority resolver.

Keep:

```text
resolve_authority(manifest, policy)
```

backward compatible.

Do not change authority meaning to serve compiler convenience.

## 22.6 `src/context_integrity/rendering.py`

Add deliberate text/JSON projections for compiled context.

## 22.7 `src/context_integrity/cli.py`

Add the thin `compile` command.

---

# 23. Tests

Testing should be focused, synthetic, deterministic, and not excessive.

Prefer one main new module:

```text
tests/test_compiler.py
```

plus small targeted additions to existing config/authority/contract tests.

## 23.1 Domain / Config Tests

Cover:

- schema v6 accepted;
- v1–v5 reject v6-only fields;
- v5 contract behavior unchanged;
- positive `budget_bytes`;
- invalid 0/negative/bool budget;
- nonnegative integer priority;
- bool/negative priority rejected;
- authority policy ID syntax;
- direct model construction enforces invariants.

## 23.2 Bound Contract Regression

Cover:

- exact configured contract accepted;
- foreign ID rejected;
- mutated contract rejected;
- stale `config_revision` rejected;
- compiler and validator use the same binding rule.

## 23.3 Lifecycle Tests

Cover:

- omitted lifecycle selector defaults compiler eligibility to `unknown`/`active`;
- explicit historical lifecycle can be selected;
- superseded source excluded by default;
- no mtime/Git-date freshness inference.

## 23.4 Authority Tests

Cover:

- rule-scoped policy uses matching candidate subset;
- highest eligible tier selected;
- lower tier retained as omitted reason;
- explicit `authority_eligible=false` respected under policy;
- lower tier not substituted because of budget;
- equal highest-tier candidates are transparently represented;
- existing authority output behavior unchanged.

## 23.5 Contract/Selection Tests

Cover:

- required minima;
- optional fill;
- excluded rule overrides required match;
- rule max counts;
- source satisfying multiple required rules selected once;
- one source counts once toward byte budget;
- deterministic selection under input/source ordering changes;
- no arbitrary noninventory source retrieval.

## 23.6 Budget Tests

Cover:

- contract default budget;
- CLI override semantics at domain layer;
- unbounded mode;
- required candidate exactly fits budget;
- one byte over budget blocked;
- required context becomes incomplete when budget insufficient;
- optional context never displaces required context;
- lower authority source not used as a budget fallback.

## 23.7 Provenance / Revision Tests

Cover:

- selected source revision retained;
- config revision retained;
- dependency list contains unique selected sources;
- candidate without usable content revision cannot silently become selected;
- no absolute root/source body in stable JSON.

## 23.8 Final Validation Tests

Cover:

- complete compiled selection yields zero contract findings;
- incomplete selection preserves Phase 5 findings;
- excluded conflict remains visible;
- compiler doesn't reinterpret validator semantics.

## 23.9 CLI Tests

Cover:

- text;
- JSON;
- output file;
- unknown contract;
- valid/invalid budget;
- optional task metadata;
- complete and incomplete exit 0;
- output failure;
- config failure.

## 23.10 Golden Test

Add a small:

```text
tests/fixtures/compiled-context-v1.json
```

Keep it deliberately small.

Assert:

- byte-identical repeatability;
- deterministic ordering;
- explicit projections;
- privacy/no absolute root;
- source revisions;
- structured decisions;
- budget;
- validation;
- newline termination.

Do not create a giant fixture.

---

# 24. Verification Strategy

During implementation:

1. run the narrow compiler/config tests while iterating;
2. run directly affected authority/contract tests when refactoring shared logic;
3. run the full gate once the implementation is stable.

Recommended final commands:

```bash
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 \
  uv run pytest tests/test_compiler.py tests/test_contracts.py tests/test_authority.py tests/test_configuration.py -q

UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check

git diff --check
git status --short
```

If practical, add one disposable executable CLI smoke test that:

- creates a tiny local repository/config;
- compiles a passing package;
- compiles an incomplete budget-constrained package;
- verifies repeated JSON is byte-identical;
- removes temporary artifacts.

Do not spend the phase on broad redundant test permutations.

---

# 25. Documentation Updates

## 25.1 Required

After successful implementation/verification:

- add `docs/implementation-reports/phase-6-implementation-report.md`;
- update `docs/current-state.md`;
- update `README.md` with compile usage and boundaries;
- update `docs/architecture.md` where Phase 6 is now delivered rather than future;
- retain this plan as historical normative planning evidence.

## 25.2 Architecture Sections to Reconcile

At minimum inspect/update:

- Layer 6 — Context Compilation;
- `ContextContract`;
- `CompiledContext`;
- module boundary `compiler`;
- Section 15 — Context Compiler Architecture;
- versioning if compiled-context JSON v1 is now delivered;
- architecture invariants if implementation clarifies them;
- evolution-by-phase status language if needed.

Do not rewrite the architecture merely to mirror code details.

## 25.3 Current State

Only after verification, move current state to something like:

```text
Current phase: Phase 6 — Task Context Compiler
Status: Implemented and offline-verified; independent review pending
Next expected step: independent Phase 6 review, then Phase 7 EvidenceProvider integration
```

Preserve any genuinely unresolved predecessor review item unless separately completed.

## 25.4 Documentation Staleness Sweep

Before finishing, inspect:

- `README.md`;
- `docs/README.md`;
- `docs/current-state.md`;
- `docs/architecture.md`;
- `docs/prd.md`;
- `AGENTS.md`;
- relevant plan/report index files.

Fix only statements that became false because of Phase 6.

Do not casually modernize historical Phase 0–5 plans/reports.

---

# 26. Implementation Report Requirements

The Phase 6 implementation report should record:

- actual starting HEAD;
- working-tree state;
- files changed;
- delivered compiler semantics;
- configuration v6 shape;
- authority/lifecycle behavior;
- selection algorithm;
- budget semantics;
- JSON schema/output;
- CLI examples;
- tests run and exact counts;
- full gate result;
- deviations from this plan;
- known limitations;
- deferred Phase 7+ behavior;
- any documentation staleness corrected.

If a plan decision is changed during implementation, document **why**.

---

# 27. Acceptance Criteria

Phase 6 is complete only when all of the following are true.

## 27.1 Correctness

- compiler consumes an exact manifest-bound configured contract;
- candidate universe is current inventory only;
- required/optional/excluded semantics remain consistent with Phase 5;
- lifecycle filtering is deterministic and explicit;
- rule-scoped authority does not become a global scalar rank;
- lower authority is not silently selected to satisfy budget;
- excluded sources cannot be selected;
- deduplication counts one source once;
- required context is selected before optional context;
- byte budget is never exceeded;
- final Phase 5 validation determines complete vs incomplete;
- every selected source retains revision/provenance;
- derived output is rebuildable.

## 27.2 Determinism

- source ordering does not change the compiled result;
- repeated stable JSON is byte-identical;
- messages are not the sole identity/decision mechanism;
- no timestamp/mtime/randomness enters selection.

## 27.3 Backward Compatibility

- config v1–v5 behavior preserved;
- v1–v5 reject v6-only keys;
- earlier CLI surfaces preserved;
- earlier JSON v1 projections unchanged;
- existing authority/contract semantics unchanged.

## 27.4 Privacy / Safety

- no absolute root in stable compiled JSON;
- no source bodies in compiled JSON;
- no remote calls;
- no credentials/model/database required;
- no arbitrary filesystem reads introduced by compile candidate acquisition.

## 27.5 Scope

- no Codebase Intelligence integration;
- no semantic code relevance;
- no LLM/embedding ranking;
- no general contradiction engine;
- no persistence;
- no CI enforcement.

## 27.6 Verification

- focused compiler/shared tests pass;
- full offline `make check` passes;
- `git diff --check` passes;
- implementation report exists;
- current-state/README/architecture accurately describe delivered behavior.

---

# 28. Known Design Risks to Watch During Implementation

These should be actively checked rather than papered over.

## 28.1 Plan vs Product Gap: "Compiled Context" Without Source Bodies

This plan treats v1 `CompiledContext` as a provenance-rich **selection manifest**.

That is consistent with the architecture's `selected_items` abstraction and avoids adding a second source-body storage/cache layer.

If implementation evidence shows that the product contract clearly requires materialized source bodies in Phase 6, stop and make that architectural decision explicit rather than quietly adding bodies to stable JSON.

## 28.2 Greedy Selection Can Be Locally Optimal Only

The recommended algorithm is deterministic and reviewable, not globally optimal.

Do not add an optimization solver.

But tests should include overlapping required rules so obvious avoidable failures are caught.

## 28.3 Equal Authority Is Not Semantic Equivalence

Do not claim one same-tier source is "better" without explicit policy/evidence.

Keep alternatives inspectable.

## 28.4 Phase 4 Integrity Is Not a General Integrity Oracle

Do not label compiled context globally "valid" merely because Phase 4 checks are quiet.

Contract completeness and semantic correctness are different concepts.

## 28.5 Sequential Repository Observation

Source/config bytes are observed sequentially.

Preserve current consistency checks and disclaimers.

Do not describe the output as an atomic repository snapshot.

---

# 29. Phase 7 Seam

Phase 6 should leave a clean future seam for:

```text
Codebase Intelligence Engine
  -> EvidenceProvider
  -> code/structural candidates + relevance
  -> compiler
```

Phase 7 should be able to add code candidates without replacing:

- contract semantics;
- lifecycle/authority policy ownership;
- deduplication structure;
- budget accounting;
- compiled-context provenance;
- rendering/CLI contract.

Do not build the provider now.

A good Phase 6 design makes future relevance an **input to selection**, not a rewrite of authority or lifecycle policy.

---

# 30. Definition of Done

Phase 6 is done when a fresh local user can:

1. configure a v6 context contract;
2. explicitly invoke that contract;
3. receive a deterministic, bounded selected context manifest;
4. inspect why each relevant source was selected or omitted;
5. see incomplete required context rather than a silently degraded package;
6. reproduce the same result from the same repository observation;
7. consume stable JSON with source/config provenance;
8. do all of this offline, without a model, database, or Codebase Intelligence service.

That is the correct foundation for Phase 7.
