# Context Integrity — Architecture

**Status:** Draft v1  
**Date:** 2026-10-13  
**Parent requirements:** `docs/prd.md` — aligned Context Integrity PRD  
**Related project:** Codebase / Context Intelligence Engine  
**Scope of this document:** Context Integrity only. The two projects proceed independently until a later evidence-integration phase.

---

## 1. Purpose

This document turns the aligned Context Integrity PRD into a concrete software architecture.

Context Integrity exists to answer:

> **Does the current and assembled context accurately reflect the system's intended state, authority, lifecycle, and constraints?**

Its architecture must support a progression from a small local context inventory tool into a platform that can reason about:

- source identity;
- source classification;
- provenance;
- authority;
- lifecycle and supersession;
- structured claims;
- contradictions;
- derived-context dependencies;
- architectural invariants;
- context contracts;
- task-specific context compilation;
- CI/governance;
- cross-repository integrity.

The architecture deliberately does **not** make Context Integrity the long-term owner of low-level code parsing, symbol extraction, dependency graph construction, structural Git analysis, or code-context ranking.

Those capabilities belong to the separately developed Codebase / Context Intelligence Engine.

The integration boundary is therefore foundational:

```text
Codebase / Context Intelligence Engine
"What is observably true in code?"
              │
              │ revision-scoped evidence
              ▼
        Context Integrity
"What should be trusted, current,
authoritative, compatible, or required?"
```

The projects should align at interfaces and semantics, not share an implementation or database prematurely.

---

# 2. Architectural Drivers

The architecture is optimized for the following constraints, in priority order.

## 2.1 Correctness Before Intelligence

Context classification, authority, lifecycle, provenance, and deterministic integrity checks should not be delegated to an LLM when explicit rules or evidence can answer them.

Models may later assist with ambiguity.

They must not silently become the source of truth.

## 2.2 Evidence Before Judgment

Every integrity finding should be explainable through:

```text
finding
  ├── policy / architecture claim / contract
  └── evidence
       ├── source
       ├── revision
       ├── location
       └── derivation
```

The system should avoid opaque conclusions such as:

> "This document appears stale."

when it can instead say:

> `storage-architecture.md` asserts X; source revision Y exposes Z; ADR-0012 is the active authority for this claim class.

## 2.3 Authority Is Contextual, Not a Single Global Rank

The PRD contains a useful default authority order, but the implementation must not reduce authority to one universal numeric ranking.

For example:

- code may be strongest for **delivered behavior**;
- an accepted ADR may be strongest for **intended architectural policy**;
- an agent instruction may be strongest for **how an agent should operate**;
- an implementation plan may be strongest for **authorized future sequencing**.

Therefore `AuthorityClass` identifies a source's role. A later `AuthorityPolicy` determines precedence for a particular claim or task type.

## 2.4 Local-First and Read-Only by Default

Initial operation should require:

- no cloud;
- no database server;
- no model key;
- no network;
- no source upload.

Scanning and checking should be read-only unless an explicit future command is designed to mutate metadata.

## 2.5 Canonical Truth Must Remain Outside the Index

The Context Integrity store is primarily an index and integrity model.

Canonical truth remains in:

- repository files;
- Git history;
- accepted decisions;
- executable artifacts;
- external authoritative systems where explicitly configured.

A local database must never become authoritative merely because it cached or derived information.

## 2.6 Derived Context Is a Cache

Summaries, compiled context, extracted claims, classifications, and model-generated interpretations are derived artifacts.

They require:

- provenance;
- dependency tracking;
- versioning;
- invalidation.

They must not silently outrank primary sources.

## 2.7 Alignment Without Coupling

The Codebase Intelligence Engine and Context Integrity should align on concepts such as:

- repository identity;
- revision identity;
- evidence references;
- source locations;
- derivation metadata.

They should **not** initially:

- share a database;
- share process lifecycle;
- require one another to start;
- use one repository;
- force a common implementation language.

---

# 3. System Boundary

## 3.1 Context Integrity Owns

Context Integrity owns the semantics and workflows for:

- context-source identity;
- source type;
- authority class;
- lifecycle;
- source provenance;
- source dependencies;
- explicit supersession;
- structured claims;
- claim provenance;
- claim validity;
- authority policy;
- contradiction detection;
- documentation/instruction drift;
- architecture policy and invariant representation;
- context contracts;
- task-context policy;
- context compilation across source types;
- integrity findings;
- waivers/governance later;
- CI enforcement later;
- derived-context invalidation;
- integrity observability.

## 3.2 Context Integrity Does Not Own Long Term

Context Integrity should not become the primary implementation of:

- AST parsing;
- language-specific symbol extraction;
- call graphs;
- compiler semantics;
- repository dependency graphs;
- structural code search;
- structural Git diffs;
- code impact analysis;
- code-context ranking.

Those are expected to arrive through an `EvidenceProvider`.

## 3.3 Temporary Local Evidence

Before Codebase Intelligence integration, Context Integrity may use simple local evidence such as:

- file existence;
- file hashes;
- Git revision;
- path changes;
- explicit document links;
- simple text references.

These implementations must sit behind the same evidence boundary rather than spreading code-analysis assumptions throughout the domain.

---

# 4. High-Level Architecture

```text
                        Repository / Workspace
                                  │
             ┌────────────────────┼────────────────────┐
             │                    │                    │
             ▼                    ▼                    ▼
       Context files        Git metadata       External evidence
             │                    │                    │
             └──────────────┬─────┴────────────────────┘
                            ▼
                     Source Acquisition
                            │
                            ▼
                      Source Registry
             identity / revision / metadata
                            │
             ┌──────────────┼───────────────┐
             ▼              ▼               ▼
      Classification     Lifecycle       Provenance
             │              │               │
             └──────────────┼───────────────┘
                            ▼
                     Claim / Evidence Layer
                            │
              ┌─────────────┼──────────────┐
              ▼             ▼              ▼
         Authority       Integrity      Dependencies
          Policy          Engine         / Invalid.
              │             │              │
              └─────────────┼──────────────┘
                            ▼
                     Context Contracts
                            │
                            ▼
                     Context Compiler
                            │
               ┌────────────┼────────────┐
               ▼            ▼            ▼
              CLI           CI         Agent/tool

Future code evidence path:

Codebase Intelligence Engine
        │
        ▼
  EvidenceProvider
        │
        └──────────────► Claim / Evidence Layer
```

---

# 5. Architecture Layers

The system should evolve in layers. Later layers depend on lower ones; early phases should not imitate later capabilities with ad hoc shortcuts.

## Layer 0 — Source Acquisition

Answers:

- What candidate context sources exist?
- What repository/workspace do they belong to?
- What revision or content version was observed?

## Layer 1 — Source Classification

Answers:

- What kind of source is this?
- What role can it plausibly play?
- What classification rule produced that answer?

## Layer 2 — Lifecycle and Authority Metadata

Answers:

- Is this source active, historical, superseded, draft, or unknown?
- Which authority class does it belong to?
- Which policy governs precedence for a question?

## Layer 3 — Claims and Provenance

Answers:

- What assertions does the source make?
- What evidence supports each assertion?
- What source/version produced it?

## Layer 4 — Integrity Evaluation

Answers:

- Are active claims inconsistent?
- Is required evidence missing?
- Is a derived artifact stale?
- Does code evidence contradict architectural intent?

## Layer 5 — Context Contracts

Answers:

- What context must a class of tasks receive?
- What context must it exclude?
- What authority/freshness rules apply?

## Layer 6 — Context Compilation

Answers:

- Given a task and budget, what valid context should be assembled?

## Layer 7 — Operations and Governance

Answers:

- Should a PR fail?
- Who owns a policy?
- Is a waiver valid?
- What is the integrity trend?

---

# 6. Core Domain Model

The models below are conceptual contracts. Exact field names may evolve, but the distinctions should remain.

## 6.1 RepositoryRef

```text
RepositoryRef
- id
- name
- identity_basis
- vcs_kind
- canonical_remote?       # optional
```

`RepositoryRef.id` should be logical and stable enough to correlate evidence across runs.

The implementation must not assume an absolute local path is the repository identity.

## 6.2 SourceId

A `SourceId` identifies a source artifact within a repository.

Initial identity may be derived from:

```text
repository_id + normalized repository-relative path
```

A rename may initially create a new `SourceId`. Rename lineage can be added later.

## 6.3 SourceRecord

```text
SourceRecord
- id: SourceId
- repository: RepositoryRef
- path
- kind: SourceKind
- authority_class: AuthorityClass
- lifecycle: LifecycleState
- revision: SourceRevision
- classification: ClassificationResult
- media_type?
- size_bytes
- generated?
```

A `SourceRecord` describes a source. It does not imply that every statement in the source is true.

## 6.4 SourceKind

Initial vocabulary should include at least:

```text
agent_instruction
readme
architecture
product_requirement
decision_record
current_state
implementation_plan
review
verification_record
release_record
handoff
generated_summary
schema
test
source_code
configuration
other_document
unknown
```

This vocabulary is about **what the artifact is**, not how authoritative it is.

## 6.5 AuthorityClass

Initial vocabulary:

```text
executable_truth
verification_evidence
decision
architecture_product
operating_instruction
plan
generated_derivative
historical
unknown
```

Important:

> `AuthorityClass` is not a global sort order.

Phase 1 should introduce policy that chooses precedence by claim/task type.

## 6.6 LifecycleState

```text
unknown
draft
active
superseded
historical
expired
invalid
```

Phase 0 should prefer `unknown` over unsupported inference.

In particular:

- "old-looking" does not automatically mean superseded;
- a newer document does not automatically supersede an older decision;
- supersession should eventually be explicit and directional.

## 6.7 SourceRevision

```text
SourceRevision
- content_sha256
- git_head?
- git_status?        # clean / modified / untracked / etc.
- observed_revision_basis
```

The content hash is essential because a dirty working tree means `HEAD` alone does not identify the observed content.

## 6.8 ClassificationResult

```text
ClassificationResult
- kind
- authority_class
- lifecycle
- basis
- matched_rules[]
- confidence
```

Initial `basis` examples:

```text
exact_filename
path_rule
directory_rule
extension_fallback
explicit_metadata       # later
manual_override         # later
model_suggestion        # much later, never silently authoritative
```

Classification must be explainable.

## 6.9 ProvenanceRef

```text
ProvenanceRef
- source_id
- source_revision
- location?
- extraction_method
- extractor_version?
```

Claims, findings, and derived artifacts should point back to provenance rather than embedding untraceable text.

## 6.10 Claim

Introduced in a later phase:

```text
Claim
- id
- subject
- predicate
- object/value
- claim_type
- scope
- provenance[]
- authority_resolution
- lifecycle
- dependencies[]
```

Claims are the unit on which contradiction and authority reasoning should ultimately operate.

## 6.11 Evidence

Evidence can come from a local source or an external provider.

```text
Evidence
- id
- kind
- repository
- revision
- subject/entity?
- fact
- provenance
- derivation
- confidence / strength
```

A deterministic parsed relation and an LLM-inferred relationship must have different derivation metadata.

## 6.12 SourceDependency

Later:

```text
SourceDependency
- dependent_artifact
- upstream_source_or_claim
- dependency_kind
- upstream_revision
```

This enables invalidating generated summaries or compiled contexts after source changes.

## 6.13 ContextContract

Phase 5 implements repository-defined contracts in strict configuration v5, retaining
schemas v1-v4. A contract has an ID, task-class identifier, description, typed rules, and
config content revision. Rules use required/optional/excluded modes and exact path, kind,
authority-class, and lifecycle selectors. Dimensions combine with AND; values within each
dimension combine with OR. Omitted/empty dimensions impose no constraint, and at least one
must be nonempty. Rules and contracts enforce their invariants at construction boundaries.

Validation resolves an explicitly supplied package against the current inventory, counts
unique normalized sources, and reports unavailable sources and duplicate inputs. Required
rules default to minimum 1, optional to minimum 0, and excluded to minimum/maximum 0;
source-count maxima are otherwise unbounded unless configured. There is no implicit
current-lifecycle filter or authority-policy winner selection. Matches use metadata only.

Validation produces rebuildable rule results and deterministic findings with contract/rule
identity. Finding identity excludes prose; the separate JSON v1 projection includes config
and resolved source content revisions. Contracts/rules are presented by ID and paths
lexically. Validation does not retrieve, rank, complete, rewrite, budget, or persist a package,
and does not run integrity checks as a side effect. Compiler and governance behavior remain
separate future layers.

The broader future contract may add:

```text
ContextContract
- id
- task_class
- required_context
- optional_context
- excluded_context
- authority_requirements
- freshness_requirements
- integrity_requirements
- budget_policy
```

## 6.14 IntegrityFinding

```text
IntegrityFinding
- id
- rule
- severity
- status
- message
- affected_entities
- evidence[]
- authority_context
- remediation_hint?
```

## 6.15 CompiledContext

```text
CompiledContext
- task
- contract
- selected_items
- excluded_items
- selection_reasons
- authority_resolutions
- integrity_state
- budget
- dependencies
```

A compiled context is derived output and therefore invalidatable.

---

# 7. Module Boundaries

The logical modules below are architectural ownership boundaries. They do not require separate Python packages on day one.

## 7.1 `acquisition`

Responsibilities:

- repository discovery;
- filesystem enumeration;
- Git-aware candidate discovery;
- source metadata;
- content hashing;
- safe handling of symlinks and unreadable files.

Does not own:

- authority policy;
- semantic claim extraction;
- integrity judgments.

## 7.2 `classification`

Responsibilities:

- source-kind classification;
- provisional authority-class assignment;
- provisional lifecycle classification;
- classification explanations;
- rule precedence.

Must remain deterministic in early phases.

## 7.3 `registry`

Responsibilities:

- source identity;
- source revisions;
- source lookup;
- deduplication;
- repository identity.

Initially in memory.

Later persisted.

## 7.4 `authority`

Responsibilities, beginning Phase 1:

- authority policies;
- precedence by claim/task type;
- source-role validation;
- authority resolution.

Must not be hard-coded into the scanner.

## 7.5 `lifecycle`

Responsibilities, beginning Phase 2:

- explicit active/draft/historical state;
- supersession edges;
- expiration;
- lifecycle validation.

Only `UNKNOWN` and `ACTIVE` lifecycle states are eligible for current authority or policy
evidence. `DRAFT` and terminal lifecycle states cannot establish current evidence.

## 7.6 `claims`

Responsibilities, beginning Phase 3:

- claim representation;
- extraction interfaces;
- claim provenance;
- claim dependency graph.

## 7.7 `evidence`

Responsibilities:

- common evidence types;
- evidence-provider abstraction;
- adapter normalization;
- deterministic vs inferred derivation metadata.

## 7.8 `integrity`

Responsibilities, beginning Phase 4:

- deterministic documentation and instruction integrity checks;
- dependency-based drift checks;
- changed-path evidence for local working-tree and explicit Git ranges.

Later responsibilities:

- contradiction rules;
- staleness;
- missing evidence;
- invalidated derived context;
- semantic architectural drift;
- contract drift.

## 7.9 `contracts`

Responsibilities, beginning Phase 5:

- context-contract definitions;
- validation;

Later responsibilities:

- task classification hooks.

## 7.10 `compiler`

Responsibilities, later:

- merge source and code candidates;
- filter invalid/superseded context;
- apply authority;
- deduplicate;
- rank;
- enforce budget;
- emit dependency/provenance metadata.

## 7.11 `storage`

Responsibilities, later:

- persistence of derived/index state;
- schema versioning;
- migration;
- cache invalidation.

It does not become canonical authority.

## 7.12 `interfaces`

Adapters:

- CLI;
- JSON;
- future CI;
- future API/MCP/plugin surfaces.

Interface concerns must not leak into domain policy.

---

# 8. Evidence Provider Architecture

The `EvidenceProvider` seam exists from the architecture's beginning even though Phase 0 does not need the Rust engine.

Conceptually:

```text
EvidenceProvider
- capabilities()
- repository_revision(...)
- find_entities(...)
- relations(...)
- changes(...)
- impact(...)
- context_candidates(...)
```

The exact method names and transport are intentionally deferred.

## 8.1 Required Semantics

A provider response should eventually carry:

- provider identity/version;
- repository identity;
- repository revision;
- entity/source identity;
- evidence location;
- derivation method;
- confidence/strength where relevant.

## 8.2 Provider Is Descriptive

A provider may say:

```text
TravelService depends_on DynamoTripStore
```

It should not decide:

```text
This violates ADR-0012.
```

That evaluation belongs to Context Integrity.

## 8.3 Context Integrity Does Not Blindly Trust Provider Ranking

If Codebase Intelligence returns a context candidate with score `0.94`, Context Integrity may use that as one relevance signal.

It still applies:

- authority;
- lifecycle;
- task contract;
- exclusions;
- integrity checks.

## 8.4 Integration Transport Is Deferred

Possible later transports:

- local HTTP;
- Unix socket;
- file export;
- Python/Rust binding;
- MCP;
- event/change feed.

No transport decision should affect Phase 0–6 architecture.

---

# 9. Source Provider vs Evidence Provider

These are different extension seams.

## SourceProvider

Provides context artifacts:

- local filesystem;
- future GitHub/Drive/issue tracker;
- future document stores.

Example:

```text
"docs/adr/0012-storage.md exists at revision X"
```

## EvidenceProvider

Provides structured observations about a system:

```text
"TravelService directly imports DynamoTripStore at revision X"
```

The local filesystem implementation can participate in both roles for simple evidence, but the interfaces should remain conceptually distinct.

---

# 10. Source Classification Architecture

Classification should be a pipeline of independent dimensions rather than one monolithic label.

```text
Source
  │
  ├──► Kind classifier
  ├──► Authority-class classifier
  └──► Lifecycle classifier
```

This avoids mistakes such as treating `docs/history/old-architecture.md` as merely "historical" and losing the fact that it is an architecture document.

A better result is:

```text
kind: architecture
authority_class: historical
lifecycle: historical
```

## 10.1 Rule Precedence

The eventual precedence should be:

1. explicit repository configuration;
2. explicit source metadata;
3. exact known filenames;
4. strong path conventions;
5. weaker filename/path heuristics;
6. extension/default fallback;
7. unknown.

Phase 0 implements only deterministic built-in rules.

Explicit config belongs in a later phase unless implementation reveals a strong need earlier.

## 10.2 Classification Must Be Inspectable

A user should be able to ask:

```bash
context-integrity explain docs/plans/phase-4.md
```

and see:

```text
kind: implementation_plan
authority_class: plan
lifecycle: unknown

matched:
- path segment "plans" -> implementation_plan
- kind implementation_plan -> plan authority

not inferred:
- active/superseded status
```

---

# 11. Authority Architecture

Authority is a policy problem, not a scanner problem.

A future authority decision may look conceptually like:

```text
AuthorityQuery
- claim_type
- task_class?
- candidate_sources[]

AuthorityResolution
- selected source(s)
- precedence rule
- conflicts
- unresolved?
```

Example policies:

```text
delivered_behavior:
  executable_truth > verification_evidence > generated_derivative

architectural_intent:
  decision > architecture_product > plan

agent_operating_rule:
  operating_instruction > architecture_product > plan
```

Phase 0 records `AuthorityClass` only.

It does **not** resolve precedence.

---

# 12. Lifecycle and Supersession Architecture

Lifecycle must eventually be explicit.

```text
Source A --superseded_by--> Source B
```

Rules:

- recency does not imply supersession;
- moving a file to `history/` may strongly indicate historical lifecycle but should not fabricate a supersession edge;
- deletion does not imply invalidity;
- a claim may become stale even if its source file remains active.

Phase 0 supports only provisional lifecycle classification.

---

# 13. Claims Architecture

Claim extraction should be introduced only after source identity/provenance are stable.

Initial claim sources should favor:

- explicit structured metadata;
- ADR fields;
- context-integrity-specific declarative files;
- deterministic parsers.

LLM-assisted extraction may be added later as:

```text
suggested claim
```

until verified.

A model extraction must record:

- source revision;
- model/provider;
- prompt/extractor version;
- confidence or verification status.

Claim identity and type identifiers are domain invariants and must be validated by the
claim model boundary, regardless of producer. Provenance must name its extraction method
and version explicitly; a producer must not inherit another producer's attribution by
default. Claim-scoped diagnostics carry the claim ID as structured data. A filtered claim
view includes only diagnostics for claims in that view, while repository observation
warnings remain separately scoped.

---

# 14. Integrity Engine Architecture

Integrity checks should be composable rules over structured inputs.

Conceptually:

```text
IntegrityRule
- id
- applicable_scope
- required_inputs
- evaluate(context) -> Finding[]
```

Categories:

```text
source_integrity
authority_integrity
lifecycle_integrity
claim_integrity
architecture_integrity
context_contract_integrity
derived_context_integrity
cross_repository_integrity
```

Phase 4 evaluates structural instruction references, narrow current-state navigation and
phase delivery evidence, and explicit exact-path document review dependencies. Local Git
changed-path observations belong to `evidence.py`; policy conclusions belong to
`integrity.py`. Explicit commit ranges scope change evidence, while source text describes
the current checkout. Text is bounded, descriptor-safe, and matched to inventoried raw-byte
hashes before evaluation. Failed or inconsistent text reads produce warnings rather than
fabricated conclusions.

Findings are deterministic review signals with owned path/source/revision evidence. They
do not mutate authority, lifecycle, supersession, or claim validity. A changed dependent
suppresses only the simple upstream-without-dependent-change signal. Implementation report
existence supplies delivery evidence, never infallible proof; plans and generic reviews do
not satisfy this check. Integrity JSON v1 is separate from existing public projections.

Rules should prefer deterministic evaluation.

An LLM can be a specialized evaluator for rules that explicitly permit probabilistic reasoning.

---

# 15. Context Compiler Architecture

The context compiler is deliberately later because it depends on earlier integrity semantics.

Pipeline:

```text
Task
  │
  ▼
Resolve context contract
  │
  ▼
Acquire candidates
  │
  ├── document/source candidates
  └── code candidates from EvidenceProvider
  │
  ▼
Validate lifecycle
  │
  ▼
Apply authority
  │
  ▼
Resolve / surface contradictions
  │
  ▼
Enforce required + excluded context
  │
  ▼
Deduplicate / rank
  │
  ▼
Fit budget
  │
  ▼
CompiledContext + provenance/dependencies
```

The compiler must not hide unresolved high-severity integrity failures merely to fit a context budget.

---

# 16. Canonical State vs Derived State

This boundary is critical.

## 16.1 Canonical State

Examples:

- repository files;
- Git commits;
- accepted ADR text;
- explicit Context Integrity configuration;
- explicit supersession declarations;
- external authoritative records.

## 16.2 Derived State

Examples:

- source inventory;
- content hashes;
- inferred classification;
- extracted claims;
- code evidence cache;
- contradiction index;
- compiled context;
- generated summaries;
- rankings.

Derived state can be deleted and rebuilt.

The architecture should preserve this property.

---

# 17. Persistence

## 17.1 Phase 0

No database.

The scan builds an in-memory model and renders:

- human-readable output;
- optional JSON manifest.

## 17.2 Later

SQLite is the default candidate for a local index because:

- local-first;
- transactional;
- portable;
- easy to rebuild;
- no service dependency.

This is a direction, not a Phase 0 requirement.

## 17.3 No Shared Database with Codebase Intelligence

Even after integration, the default should be API/data-contract coupling rather than shared-table coupling.

Reasons:

- independent release cycles;
- different canonical models;
- easier replacement;
- clearer ownership;
- less schema lockstep.

---

# 18. Versioning

Machine-readable contracts require explicit versions.

At minimum:

```text
inventory_schema_version
configuration_schema_version       # later
evidence_contract_version          # later
compiled_context_schema_version    # later
```

Version fields should represent semantic schema versions, not application build versions.

Breaking schema changes require either:

- migration; or
- explicit rebuild when the artifact is derived.

---

# 19. Determinism

Default local scans should be reproducible.

Requirements:

- sort paths before output;
- normalize path separators to `/`;
- use repository-relative paths;
- avoid timestamps in canonical JSON by default;
- avoid absolute local paths in persisted machine-readable output;
- record content hashes;
- record Git HEAD separately from dirty working-tree content;
- do not use model inference in deterministic scan output.

Optional runtime metadata may be printed interactively without becoming part of the stable manifest.

---

# 20. Concurrency

No concurrency is required initially.

The architecture should prefer:

```text
correct sequential scan
        ↓
measured bottleneck
        ↓
bounded concurrency
```

rather than introducing worker pools prematurely.

When concurrency appears later:

- registry writes need deterministic identity;
- derived updates should be idempotent;
- change processing should be revision-scoped;
- duplicate work should be safe.

---

# 21. Error Model

Errors should be typed conceptually into:

```text
UsageError
ConfigurationError
RepositoryError
SourceReadError
ClassificationError
PersistenceError
ProviderError
IntegrityEvaluationError
```

Phase 0 should distinguish:

- fatal repository/configuration failures;
- per-file warnings that allow scanning to continue.

A single unreadable context file should not normally abort the entire inventory.

---

# 22. Security and Trust Boundaries

## 22.1 Repository Content Is Untrusted Input

Even local files may contain:

- malformed data;
- huge files;
- symlinks;
- unusual encodings;
- adversarial prompt text.

Scanning must not execute source content.

## 22.2 Symlinks

Phase 0 should not follow symlinks outside the repository root.

## 22.3 No Prompt Execution Semantics

Agent instruction files are data being inventoried.

The scanner must never "obey" repository prompt text as runtime instructions.

## 22.4 No Network by Default

Initial commands should make no network calls.

## 22.5 Sensitive Data

The tool should not print source contents during an inventory unless a later explicit command requests it.

Machine-readable manifests should contain metadata, not document bodies.

---

# 23. LLM Boundary

LLMs are optional enrichment providers.

They must not be embedded in core domain logic.

Potential later uses:

- ambiguous source classification;
- claim extraction;
- semantic contradiction assessment;
- remediation suggestions;
- context summarization.

Every model-derived artifact should be labeled with:

- derivation = model;
- model/provider;
- source dependencies;
- verification status.

A model-generated assertion is not authoritative because the model is strong.

---

# 24. CLI Architecture

The CLI is an adapter.

Conceptually:

```text
CLI
 ↓
Application use case
 ↓
Domain services
 ↓
Ports
 ↓
Filesystem / Git / storage adapters
```

The CLI should not contain:

- classification logic;
- authority rules;
- persistence logic;
- future provider protocol logic.

This allows future CI/API integrations to use the same application layer.

---

# 25. Suggested Initial Repository Layout

Keep the first implementation simple.

```text
context-integrity/
├── pyproject.toml
├── README.md
├── AGENTS.md
├── src/
│   └── context_integrity/
│       ├── __init__.py
│       ├── cli.py
│       ├── models.py
│       ├── repository.py
│       ├── acquisition.py
│       ├── classification.py
│       ├── evidence.py
│       └── rendering.py
├── tests/
│   ├── fixtures/
│   ├── test_acquisition.py
│   ├── test_classification.py
│   ├── test_rendering.py
│   └── test_cli.py
└── docs/
    ├── prd.md
    ├── architecture.md
    ├── current-state.md
    ├── adr/
    ├── reviews/
    ├── implementation-reports/
    └── plans/
        └── phase-0-implementation-plan.md
```

Do not over-modularize initially.

Refactor when responsibilities become real.

---

# 26. Initial Technology Direction

The architecture does not require a specific language, but the recommended initial implementation is:

- Python 3.12+;
- `pyproject.toml`;
- Typer for the CLI;
- standard-library dataclasses or Pydantic models;
- standard `hashlib`, `pathlib`, `subprocess`;
- Git CLI for repository enumeration/revision where available;
- pytest for tests;
- Ruff for lint/format;
- static type checking once the initial model stabilizes.

Rationale:

- Context Integrity's early work is policy/model iteration rather than a performance-sensitive parser;
- Python makes rule/evaluation experimentation inexpensive;
- the Rust project remains independently optimized for deterministic code intelligence;
- the future boundary is a data contract, not a shared language.

No web framework is needed.

No database is needed in Phase 0.

---

# 27. Testing Architecture

Testing should use layered fixtures.

## 27.1 Unit Fixtures

Small isolated cases:

- known filename;
- known directory;
- unknown file;
- historical directory;
- unreadable source;
- path normalization.

## 27.2 Repository Fixtures

Synthetic repositories containing:

- `AGENTS.md`;
- `docs/architecture.md`;
- ADRs;
- plans;
- reviews;
- releases;
- history;
- generic docs;
- ignored files;
- untracked files;
- symlinks.

## 27.3 Golden Output

Machine-readable JSON should have golden tests.

Human text output should test stable structural elements rather than brittle spacing where possible.

## 27.4 Future Integrity Fixtures

Later phases should add repositories with known contradictions and drift rather than relying only on mocks.

---

# 28. Observability

Phase 0 needs only lightweight diagnostics.

Useful fields:

- files considered;
- sources inventoried;
- files ignored;
- files unreadable;
- unclassified sources;
- Git availability;
- dirty working tree.

Later:

- rule timings;
- cache hits;
- provider latency;
- stale claims;
- unresolved contradictions;
- invalidation counts;
- context compilation metrics.

---

# 29. Cross-Repository Architecture

Multi-repository support is a long-term requirement but not a Phase 0 scope requirement.

The architecture should ensure:

- every source belongs to a repository identity;
- every evidence item belongs to a revision;
- IDs are not based solely on local absolute paths;
- source and evidence contracts can carry repository identity.

A future workspace is conceptually:

```text
Workspace
  ├── Repository A
  ├── Repository B
  └── Repository C
```

Context Integrity owns cross-repository **policy/integrity**.

Codebase Intelligence may own cross-repository **structural evidence**.

---

# 30. Architecture Invariants

The following should be treated as durable design rules.

1. **Code evidence and context policy are separate concerns.**
2. **Context Integrity owns normative interpretation; Codebase Intelligence owns structural observation.**
3. **Authority class is not a universal scalar rank.**
4. **Canonical sources remain outside derived indexes.**
5. **Derived artifacts always retain provenance/dependencies.**
6. **Plans never prove implementation.**
7. **Generated summaries never become authoritative by default.**
8. **Recency never silently implies supersession.**
9. **Deterministic checks precede LLM reasoning when sufficient.**
10. **Provider/model-derived facts are labeled by derivation.**
11. **Machine-readable outputs use repository-relative paths.**
12. **Dirty working-tree content is identified by content hash, not HEAD alone.**
13. **The Rust engine is optional until the explicit integration phase.**
14. **No shared database is required between the two projects.**
15. **The context compiler may consume relevance rankings but owns authority/lifecycle filtering itself.**

---

# 31. Decisions Locked for Phase 0

Phase 0 should treat these as decided:

- local-first;
- read-only;
- single repository per invocation;
- no database;
- no LLM;
- no Codebase Intelligence dependency;
- deterministic built-in classification rules;
- repository-relative paths;
- content hashes;
- Git-aware discovery when available;
- JSON + human-readable output;
- explainable classification;
- unknown is a valid result;
- no semantic authority resolution;
- no supersession graph;
- no claim extraction.

---

# 32. Decisions Intentionally Deferred

Do not resolve these before implementation provides evidence:

- SQLite schema;
- explicit repository configuration syntax;
- claim DSL;
- policy DSL;
- evidence transport to Rust engine;
- MCP/API surface;
- exact cross-repository workspace format;
- embedding/vector use;
- LLM provider;
- learned ranking;
- web UI;
- team/hosted architecture;
- waiver/governance model;
- stable rename lineage;
- automatic document repair.

---

# 33. Evolution by Phase

The intended architectural progression is:

```text
Phase 0
Source identity + inventory + provisional classification

Phase 1
Authority policy

Phase 2
Lifecycle + supersession

Phase 3
Claims + provenance

Phase 4
Documentation / instruction drift

Phase 5
Context contracts

Phase 6
Context compiler

Phase 7
Codebase Intelligence EvidenceProvider integration

Phase 8
Architectural integrity

Phase 9
Derived-context revalidation

Phase 10
Cross-repository integrity

Phase 11
CI / governance / observability

Phase 12+
Semantic optimization / richer intelligence
```

Each phase should extend the existing domain model rather than introduce a second parallel architecture.

---

# 34. Relationship to the Separate Rust Project

The two projects should proceed independently.

The alignment contract at this stage is conceptual:

```text
Context Integrity expects future evidence to have:

- repository identity
- revision identity
- entity or subject
- fact / relation / change
- source location
- derivation
- provider version
```

The Rust project should not import Context Integrity policy types.

Context Integrity should not import Rust parser internals.

When both systems have stable models, create a shared design document:

```text
evidence-contract.md
```

That document should be based on implemented abstractions, not speculative types.

---

# 35. AI-Development Organization

Because the project itself is about context integrity, the repository should dogfood strong context hygiene from the beginning.

## 35.1 Canonical Agent Instructions

`AGENTS.md` is the single canonical repository instruction source.

Model-specific compatibility files should point to it rather than duplicate its content.

Local `AGENTS.md` files should be added only when a subtree has genuinely different invariants.

## 35.2 Minimal Context Path

An implementation agent should normally read:

1. `docs/current-state.md`;
2. the active phase plan;
3. relevant architecture sections;
4. relevant ADRs;
5. target code/tests;
6. the PRD only when broader product intent is necessary.

Historical reviews and implementation reports are not part of the default context set.

## 35.3 Durable Knowledge Promotion

When a review or AI session discovers a durable lesson, promote it to the correct canonical layer:

```text
behavioral invariant       -> test
system architecture        -> architecture.md
specific durable decision  -> ADR
future implementation      -> phase plan
current navigation/status  -> current-state.md
delivery evidence          -> implementation report
review finding             -> review
```

Do not require future agents to mine old session artifacts for important invariants.

---

# 36. Immediate Next Step

Implement Phase 0 according to:

`docs/plans/phase-0-implementation-plan.md`

Do not build Phase 1 authority resolution during Phase 0 merely because the enums already exist.

The purpose of Phase 0 is to validate the foundational source model on real repositories before the architecture becomes more semantic.
