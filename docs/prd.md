# Context Integrity — Product Requirements Document

**Status:** Draft v2 — aligned with Codebase / Context Intelligence Engine  
**Date:** 2026-10-13  
**Related project:** Codebase / Context Intelligence Engine  
**Primary product mode:** Local-first / CI-capable context integrity platform  
**Audience:** Project owner, future contributors, implementation/review agents, prospective users

---

## 1. Executive Summary

Context Integrity is a platform for keeping software-development context accurate, authoritative, current, internally consistent, and task-appropriate over time.

Its core thesis is:

> **Context should be managed like code: indexed, typed, versioned, linted, tested, compiled, observed, and continuously improved.**

Modern AI coding workflows accumulate context across:

- source code;
- tests;
- schemas;
- architecture documents;
- ADRs;
- implementation plans;
- current-state files;
- release/review evidence;
- issue trackers;
- repository instructions;
- agent-specific rule files;
- prior decisions;
- generated summaries;
- cross-repository contracts.

The problem is not merely finding information. It is determining:

- which source is authoritative;
- whether a claim is still valid;
- what superseded it;
- whether two sources contradict one another;
- whether documentation matches code;
- whether current implementation matches intended architecture;
- whether a task is receiving too much, too little, stale, or irrelevant context;
- whether generated or derived context can still be trusted after upstream changes.

Context Integrity should provide a structured layer for:

- claims;
- sources;
- provenance;
- authority;
- validity;
- supersession;
- contradictions;
- invariants;
- context contracts;
- task-specific context compilation;
- drift detection;
- CI/governance;
- observability and evaluation.

### Key alignment principle

The Codebase / Context Intelligence Engine is the preferred upstream provider of deterministic repository facts. Context Integrity owns the semantic, policy, authority, and governance layer over those facts.

```text
Codebase / Context Intelligence Engine
- files
- symbols
- relations
- Git changes
- structural impact
- context candidates
- evidence provenance

                 ↓

Context Integrity
- claims
- authority
- validity
- supersession
- contradictions
- architectural intent
- context contracts
- drift judgments
- task context policy
- governance
```

Context Integrity must remain independently useful before that integration exists, but it should avoid building a competing long-term code parser/indexer unless required as an interim adapter.

---

# 2. Problem Statement

AI-assisted software engineering creates a new class of information-management problem.

A repository may simultaneously contain:

- delivered code;
- future plans;
- historical plans;
- outdated architecture descriptions;
- active ADRs;
- superseded ADRs;
- generated summaries;
- per-agent instructions;
- old migration notes;
- current release evidence;
- stale handoffs;
- local environment notes;
- code comments;
- schemas;
- tests.

All of these are "context," but they do not have equal authority.

A typical agent may read:

```text
README
AGENTS.md
architecture.md
old implementation plan
current implementation plan
review report
source files
```

and have no reliable formal way to distinguish:

```text
what is delivered
what is intended
what is historical
what is superseded
what is unverified
what is generated
what is binding
```

This leads to:

- context drift;
- contradictory instructions;
- repeated rediscovery;
- oversized prompts;
- architecture violations;
- stale documentation;
- inappropriate trust in plans or summaries;
- agents propagating old assumptions;
- high token cost;
- weaker models performing poorly because the harness gives them bad context.

---

# 3. Product Thesis

> **Software context is an evolving dependency graph of claims and evidence, not a pile of Markdown files.**

Context Integrity should provide the machinery to represent and continuously validate that graph.

Conceptually:

```text
Sources
  │
  ├── code
  ├── tests
  ├── schemas
  ├── docs
  ├── ADRs
  ├── plans
  ├── reviews
  ├── releases
  └── external systems
        │
        ▼
     Claims
        │
        ├── provenance
        ├── authority
        ├── validity
        ├── scope
        ├── dependencies
        └── supersession
        │
        ▼
   Integrity Engine
        │
  ┌─────┼───────────┐
  ▼     ▼           ▼
Drift  Compile   Governance
  │     │           │
  └─────┼───────────┘
        ▼
 Accurate task context
```

---

# 4. Relationship to the Codebase / Context Intelligence Engine

This is a foundational architectural boundary.

## 4.1 Codebase Intelligence Answers "What Is?"

Examples:

- `ModelRouter` imports `ProviderRegistry`;
- `ProviderRegistry` has four implementations;
- a commit removed an abstraction edge;
- a schema changed;
- three repositories consume a contract;
- these files are structurally related to a task.

## 4.2 Context Integrity Answers "What Should Be Trusted / What Should Hold?"

Examples:

- an ADR is authoritative over a superseded design note;
- application services must depend on repository interfaces rather than persistence adapters;
- the current-state document is stale because code has moved past its claim;
- a generated summary depended on facts that have since changed;
- a phase plan is future intent, not proof of delivery;
- a task context must include authorization boundaries and omit historical plans.

## 4.3 Integration Principle

Context Integrity should consume evidence through a stable boundary such as:

```text
EvidenceProvider
- get_symbol(...)
- get_relations(...)
- get_change_set(...)
- get_impact(...)
- get_context_candidates(...)
```

The specific transport is not fixed.

Possible future implementations:

- local HTTP;
- Unix socket;
- file export;
- Rust/Python binding;
- MCP;
- embedded library.

## 4.4 Avoid Duplicate Engines

Context Integrity should not independently maintain a second long-term implementation of:

- AST parsing;
- code symbol identity;
- dependency graph construction;
- Git structural diffs;
- code impact analysis;
- code task-ranking.

Temporary implementations may exist before integration, but they should be replaceable adapters.

---

# 5. Goals

## 5.1 Core Goals

1. Model context as typed, versioned information.
2. Track provenance for claims.
3. Establish authority and precedence.
4. Detect stale, contradictory, or superseded context.
5. Relate documentation and architectural intent to implementation evidence.
6. Compile bounded task-specific context.
7. Make context quality inspectable.
8. Integrate with CI and agent workflows.
9. Work locally and cheaply.
10. Improve weaker/free model performance by improving context quality.

## 5.2 Long-Term Goals

1. Continuously maintain context integrity across multiple repositories.
2. Detect architectural drift before it compounds.
3. Revalidate derived context when dependencies change.
4. Provide machine-readable context contracts for agents.
5. Measure whether context improves task outcomes.
6. Support organizations as well as individual developers.
7. Integrate structural evidence, runtime evidence, and human decisions.

---

# 6. Non-Goals

Context Integrity is not:

- a coding model;
- a general vector database;
- a replacement for Git;
- a replacement for ADRs;
- a replacement for tests;
- an IDE;
- a full static analyzer;
- the owner of low-level code parsing once the Codebase Intelligence Engine is available;
- a requirement to centralize every project document;
- a requirement to use LLMs for all drift detection;
- a tool that treats generated summaries as authoritative by default;
- an excuse to retain all historical context forever.

---

# 7. Core Concepts

## 7.1 Source

A source is an origin of context.

Examples:

- source file;
- test;
- OpenAPI schema;
- ADR;
- PR review;
- release record;
- architecture document;
- implementation plan;
- issue;
- human decision;
- external system.

## 7.2 Claim

A claim is a structured statement derived from or asserted by a source.

Examples:

```text
"Firestore is the current production store."
"Phase 25 is implemented."
"ModelRouter must not instantiate provider clients."
"TripRepository owns travel persistence abstraction."
```

Claims are more useful than treating whole files as atomic truth.

## 7.3 Provenance

A claim should record:

- source;
- source version/revision;
- extraction method;
- author/origin where appropriate;
- time observed;
- dependencies.

## 7.4 Authority

Authority answers:

> If sources disagree, which one wins for this type of question?

A typical hierarchy may resemble:

1. code / executable schemas / migrations / tests for delivered behavior;
2. release/review/verification evidence for verified delivery;
3. accepted ADRs for durable design decisions;
4. architecture/product documents for intended design/scope;
5. active implementation plans for authorized future work;
6. historical/superseded documents for context only.

This is configurable and domain-specific.

Critically, this is **not one universal scalar ranking**. Different claim classes can have different governing authorities.

## 7.5 Validity

A claim may be:

- active;
- stale;
- expired;
- contradicted;
- superseded;
- unverified;
- historical.

## 7.6 Supersession

Context must support explicit replacement chains.

```text
ADR-0002
  superseded_by → ADR-0021
```

A newer file is not automatically more authoritative.

## 7.7 Dependency

Derived context depends on upstream context.

Example:

```text
Summary S
depends_on:
- architecture.md@abc
- storage.py@def
```

If either changes materially, the summary may require revalidation.

## 7.8 Context Contract

A context contract specifies what context a task or subsystem requires.

Example:

```yaml
task_class: "storage migration"
required:
  - current storage architecture
  - current persistence interfaces
  - active migration ADRs
  - migration tests
exclude:
  - superseded storage plans
authority:
  delivered_behavior: code
  future_target: active_adr
```

## 7.9 Integrity Finding

Examples:

- stale claim;
- contradiction;
- missing evidence;
- unauthorized source;
- superseded context included;
- architecture violation;
- derived context invalidated;
- task context incomplete;
- excessive context.

---

# 8. Context Layers

A mature system may distinguish:

```text
Layer 1 — Acquisition
Layer 2 — Structural evidence
Layer 3 — Semantic claims
Layer 4 — Authority / validity
Layer 5 — Integrity checks
Layer 6 — Context compilation
Layer 7 — Operations / CI
Layer 8 — Intelligence / optimization
```

The Codebase Intelligence Engine supplies much of Layer 2 for code.

---

# 9. Sources of Truth and Authority

Context Integrity should make source classification explicit.

Suggested classes:

| Class | Example | Typical role |
|---|---|---|
| Executable truth | code, schema, migration, test | delivered behavior |
| Verification evidence | release record, review | what was exercised |
| Decision | ADR | durable intended rule |
| Architecture/product | architecture doc, PRD | intended structure/scope |
| Operating instruction | AGENTS.md, repository policy | how tools/agents should operate |
| Plan | implementation plan | future work |
| Generated derivative | summary, handoff | convenience, not primary authority |
| Historical | superseded doc | background only |

Rules:

- plans do not prove implementation;
- summaries do not outrank their sources;
- security/privacy constraints may override normal convenience;
- explicit supersession is preferred over implied staleness;
- source authority may vary by claim type.

---

# 10. Claims and Provenance Model

Possible conceptual schema:

```text
Claim
- id
- subject
- predicate
- object/value
- type
- scope
- source_ref
- source_revision
- extracted_at
- authority_class
- validity
- confidence
- dependencies[]
- supersedes[]
- superseded_by[]
```

A first implementation may use simpler structures.

The long-term requirement is to avoid treating a Markdown document as an indivisible truth object.

---

# 11. Context Acquisition

Possible inputs:

- repository documents;
- ADRs;
- source files;
- tests;
- release evidence;
- PR/review artifacts;
- code intelligence evidence;
- Git metadata;
- external trackers later.

Acquisition should preserve source identity.

It should not flatten everything into embedding chunks with lost provenance.

---

# 12. Code Evidence via the Codebase Intelligence Engine

The preferred long-term architecture:

```text
Repository
   │
   ▼
Codebase / Context Intelligence Engine
   │
   ├── symbols
   ├── relations
   ├── structural diffs
   ├── cross-repo contracts
   └── context candidates
           │
           ▼
      Context Integrity
```

Required evidence characteristics:

- repository ID;
- revision;
- file path;
- source range;
- entity identity;
- derivation;
- parser/analyzer version where useful.

Context Integrity may annotate evidence with claims and policy semantics without mutating the underlying fact.

---

# 13. Drift Detection

"Drift" is not one phenomenon.

## 13.1 Documentation Drift

Example:

```text
Doc:
"ProviderRegistry owns all provider construction."

Code:
ModelRouter directly constructs OpenRouterProvider.
```

## 13.2 Architecture Drift

An invariant no longer holds.

## 13.3 Current-State Drift

`current-state.md` says Phase 20 is next, while release evidence shows Phase 30 is complete.

## 13.4 Instruction Drift

`AGENTS.md`, `CLAUDE.md`, and another agent rule file disagree.

## 13.5 Contract Drift

A shared schema changed, but a consuming repository did not update.

## 13.6 Derived-Context Drift

A generated summary still depends on a superseded source.

## 13.7 Authority Drift

A stale or low-authority source becomes de facto dominant because agents read it first.

---

# 14. Architectural Invariants

The system should support explicit invariants.

Simple deterministic example:

```yaml
name: application-storage-boundary
from: "application"
must_not_depend_on: "storage-adapter"
```

Semantic example:

```yaml
claim: >
  Application services access persistence through domain repository interfaces.
authority: ADR-0012
```

Evaluation may use:

1. deterministic code evidence from the Codebase Intelligence Engine;
2. explicit mappings;
3. optional model reasoning for ambiguous cases.

LLMs should not be required where static evidence is sufficient.

---

# 15. Contradiction Detection

Potential contradiction types:

- exact opposing values;
- competing "current" declarations;
- stale version references;
- implementation vs documentation mismatch;
- two active ADRs with incompatible rules;
- source-of-truth precedence conflict.

The engine should report:

- claims;
- sources;
- authority;
- evidence;
- suggested resolution path.

It should not silently pick a winner unless policy makes that deterministic.

---

# 16. Supersession and Lifecycle

Documents and claims need lifecycle.

Suggested status:

```text
draft
active
superseded
historical
expired
invalid
```

A key operational principle:

> When context becomes obsolete, delete, archive, expire, or explicitly supersede it. Do not merely add another newer document.

This keeps retrieval quality from degrading indefinitely.

---

# 17. Task-Specific Context Compilation

Context Integrity should be able to build a bounded context package.

Inputs:

- task;
- repository/repositories;
- task class;
- target entities;
- token/size budget;
- policy.

Sources:

- code context candidates from Codebase Intelligence;
- active ADRs;
- current architecture;
- relevant current state;
- required security rules;
- recent verification evidence;
- selected history.

Compilation stages:

```text
Task
 ↓
Classify requirements
 ↓
Retrieve candidates
 ↓
Validate authority
 ↓
Remove superseded/stale context
 ↓
Resolve contradictions
 ↓
Apply required context contract
 ↓
Rank / budget
 ↓
Compiled context
```

This is more than retrieval.

It is closer to compilation from a larger context graph into a task-specific artifact.

---

# 18. Context Contracts

Context contracts should become a defining concept.

A contract can express:

- required context;
- optional context;
- forbidden context;
- authority expectations;
- freshness;
- dependency requirements;
- size budget;
- verification rules.

Example:

```yaml
id: provider-integration-task

required:
  - provider interface
  - provider registry
  - active routing ADR
  - provider contract tests

must_exclude:
  - superseded provider plans

freshness:
  code: current_revision
  architecture: active_only

integrity:
  no_unresolved_high_severity_contradictions: true
```

The contract makes task context testable.

---

# 19. Context Budgeting

More context is not automatically better.

The platform should help answer:

- what must be present;
- what can be omitted;
- what is redundant;
- what is stale;
- what is low authority;
- what consumes excessive budget.

Budgeting can use:

- structural relevance from Codebase Intelligence;
- authority;
- freshness;
- task requirements;
- redundancy;
- token/byte cost.

This directly supports stronger performance from smaller/free models.

---

# 20. Generated Context and Derived Artifacts

Generated summaries, handoffs, and agent memories are useful but dangerous.

Requirements:

- label generated artifacts;
- record dependencies;
- record model/tool when useful;
- never make them silently authoritative;
- revalidate when dependencies change;
- expire when evidence is unavailable.

A generated summary is a cache, not primary truth.

---

# 21. Cross-Repository Context

Long-term Context Integrity must treat a product as more than one repository.

Potential cross-repo integrity checks:

- shared API drift;
- schema drift;
- permission contract mismatch;
- incompatible phase assumptions;
- duplicated authority statements;
- integration docs lagging implementation;
- one repo depending on a superseded contract.

The Codebase Intelligence Engine should supply cross-repo structural evidence where possible.

Context Integrity adds authority and semantic policy.

---

# 22. CI / Review Integration

Illustrative:

```bash
context-integrity check
context-integrity check --diff main..HEAD
context-integrity compile --task "..."
```

Possible CI output:

```text
HIGH — Architecture drift
TravelService now depends directly on DynamoTripStore.
Expected boundary: TripRepository.
Authority: ADR-0012.
Evidence: travel_service.py:8

MEDIUM — Documentation review required
storage-architecture.md depends on StorageRouter,
whose public interface changed in this PR.

LOW — Context redundancy
Two active files repeat the same current-phase claim.
```

Findings must remain inspectable.

---

# 23. Governance

Long-term organizational use may need:

- policy ownership;
- rule review;
- waivers;
- expiration;
- repository scopes;
- audit history;
- enforcement severity.

A policy change should itself be versioned and attributable.

---

# 24. Observability

The system should expose its own context behavior.

Possible metrics:

- number of active claims;
- stale claims;
- unresolved contradictions;
- superseded sources still frequently retrieved;
- average task-context size;
- retrieval hit rates;
- context compilation latency;
- percentage of context by source type;
- invalidated derived artifacts;
- architectural drift findings.

---

# 25. Evaluation

The platform needs tests of both correctness and usefulness.

## 25.1 Deterministic Integrity Fixtures

Examples:

- conflicting source-of-truth declarations;
- superseded ADR;
- stale `current-state.md`;
- changed code edge violating invariant;
- invalid generated summary dependency.

## 25.2 Context Compilation Benchmarks

Tasks with expected:

- required files;
- required ADRs;
- prohibited historical docs.

Measure:

- recall;
- authority correctness;
- token efficiency;
- contradiction leakage.

## 25.3 Agent Evaluation

Compare:

- unfiltered repository context;
- naive retrieval;
- Codebase Intelligence bundle;
- Context Integrity compiled bundle.

Measure:

- task success;
- architectural mistakes;
- tokens;
- tool calls;
- stale assumptions.

---

# 26. Local-First / Cost Model

The platform should remain usable locally.

Default:

- local repository/doc parsing;
- embedded storage later;
- deterministic checks;
- optional local Codebase Intelligence service;
- optional LLM calls.

LLM usage should focus on ambiguity that deterministic systems cannot resolve.

This supports the broader goal of maximizing usefulness from free/cheap inference.

---

# 27. Security / Privacy

Requirements:

- local processing by default;
- no silent source upload;
- explicit network integrations;
- preserve repository privacy boundaries;
- sensitive sources can be excluded;
- external model calls must identify what is sent;
- derived artifacts should retain sensitivity/provenance where relevant.

Context correctness must never override security authorization.

---

# 28. Architecture

## 28.1 Logical Architecture

```text
                Sources
                  │
       ┌──────────┼──────────┐
       ▼          ▼          ▼
   Documents   Decisions   Code evidence
                              │
                     Codebase Intelligence
                              │
       └──────────┬───────────┘
                  ▼
             Acquisition
                  │
                  ▼
         Claim / Evidence Graph
                  │
      ┌───────────┼────────────┐
      ▼           ▼            ▼
 Authority    Integrity     Dependencies
      │           │            │
      └───────────┼────────────┘
                  ▼
          Context Compiler
                  │
         ┌────────┼────────┐
         ▼        ▼        ▼
       Agent      CI      Human
```

## 28.2 Separation of Concerns

### Codebase Intelligence

- syntax;
- symbols;
- code relations;
- Git structural changes;
- task code candidates.

### Context Integrity

- authority;
- lifecycle;
- claims;
- provenance across source types;
- semantic invariants;
- contradictions;
- context compilation policy.

---

# 29. Phased Roadmap

## Phase 0 — Context Inventory and Source Classification

Goal:

- scan repository context sources;
- classify files;
- identify obvious authority classes;
- provide reports only.

No code parser dependency required.

## Phase 1 — Authority and Source-of-Truth Model

Goal:

- configurable authority precedence;
- explicit current vs future vs historical classification;
- basic source metadata.

Deliver:

- authority config;
- source status;
- deterministic precedence checks.

## Phase 2 — Supersession and Lifecycle

Goal:

- mark context active/superseded/historical;
- build supersession chains;
- flag conflicting active sources.

## Phase 3 — Claim and Provenance Model

Goal:

- move beyond file-level truth;
- represent claims;
- connect claims to sources and versions.

Start with explicit or semi-structured claims before attempting broad LLM extraction.

## Phase 4 — Drift Checks for Documentation / Instructions

Goal:

- basic code/doc dependency links;
- agent-instruction divergence;
- stale current-state detection;
- plan-vs-delivery distinctions.

Can use simple Git/file evidence until Codebase Intelligence integration is available.

## Phase 5 — Context Contracts

Goal:

- define required/optional/excluded context for task classes;
- validate context package completeness.

## Phase 6 — Task Context Compiler

Goal:

- retrieve;
- authority-filter;
- deduplicate;
- remove superseded context;
- fit budget;
- produce task context.

At this stage, Context Integrity becomes directly useful for coding-agent workflows.

## Phase 7 — Codebase Intelligence Adapter

Goal:

Integrate the external Codebase / Context Intelligence Engine.

Consume:

- symbol graph;
- structural evidence;
- change sets;
- impact;
- code context candidates.

Replace any temporary duplicate repository-analysis paths.

## Phase 8 — Architectural Integrity

Goal:

- connect architecture claims/invariants to structural evidence;
- detect dependency/boundary violations;
- generate explainable findings.

Example:

```text
Expected:
ModelRouter -> ProviderRegistry -> Provider

Observed:
ModelRouter -> OpenRouterProvider
```

## Phase 9 — Derived Context Revalidation

Goal:

- track dependencies of summaries/handoffs/generated context;
- invalidate/review them when upstream evidence changes.

## Phase 10 — Cross-Repository Integrity

Goal:

- product/system-wide claims;
- contract drift;
- integration alignment;
- cross-repo task context.

Leverage cross-repository evidence from Codebase Intelligence.

## Phase 11 — CI / Governance / Observability

Goal:

- pull-request checks;
- severity;
- policy ownership;
- waivers;
- dashboards/metrics;
- integrity trend.

## Phase 12+ — Optimization and Intelligence

Potential:

- LLM-assisted claim extraction;
- semantic contradiction classification;
- automatic context repair suggestions;
- learned context ranking;
- runtime evidence;
- issue/PR/observability integration;
- team knowledge systems.

These are explicitly later.

---

# 30. Integration Milestones with Codebase Intelligence

The projects should not block one another.

## Stage A — Independent

Context Integrity:

- documents;
- authority;
- claims;
- supersession.

Codebase Intelligence:

- files;
- symbols;
- graph;
- changes.

## Stage B — Evidence Export

Codebase Intelligence exports:

```text
repository revision
symbols
relations
changes
evidence locations
```

Context Integrity consumes them read-only.

## Stage C — Context Compilation

Codebase Intelligence proposes code candidates.

Context Integrity merges them with:

- ADRs;
- architecture;
- current state;
- policy;
- history.

## Stage D — Integrity Feedback

Context Integrity may request targeted evidence:

```text
"Show paths from application services to persistence adapters."
```

The intelligence engine answers structurally.

## Stage E — Multi-Repo

Both share repository/workspace identities.

No requirement that they share a database.

---

# 31. Open-Source Landscape

The product intentionally combines ideas already explored by multiple OSS projects.

## 31.1 Repository / Agent Context Systems

### Repomix

Packs code into AI-friendly output.

Relevant lesson:

- simple packaging creates immediate utility;
- context size is a product concern.

### Aider Repo Map

Uses structural graph ranking to select code context under a budget.

Relevant lesson:

- graph structure improves context selection.

### Serena

Provides semantic symbol retrieval/editing to coding agents.

Relevant lesson:

- high-level code primitives are more useful than raw line access.

### CodeGraphContext

Provides local graph-based code context through CLI/MCP.

Relevant lesson:

- code graph functionality alone is no longer unique.

### Potpie

Provides a broad context graph spanning code, history, and SDLC inputs.

Relevant lesson:

- the ecosystem is moving toward persistent context graphs.

These systems overlap heavily with the separate Codebase Intelligence Engine.

## 31.2 Context / Rule Consistency

Rule-synchronization systems show value in keeping agent instructions derived from canonical sources.

Overlap:

- instruction drift;
- source-of-truth consistency.

Context Integrity goes broader by modeling authority, claims, code evidence, supersession, and task compilation.

## 31.3 Documentation Drift

Documentation drift tools commonly link docs to code or use model-assisted alignment checks.

Overlap:

- code-document dependency;
- staleness;
- CI checks.

Context Integrity expands toward:

- claim-level provenance;
- authority;
- semantic contradictions;
- context contracts;
- cross-repository context;
- derived artifact invalidation.

---

# 32. Differentiation

The platform should not define itself as:

> "RAG for your repo."

Nor:

> "A code graph."

Nor:

> "A documentation drift linter."

The intended long-term differentiation is:

> **A context correctness and compilation system that treats software knowledge as versioned claims with provenance, authority, dependencies, and lifecycle, then uses deterministic code evidence plus explicit policy to keep task context and architectural understanding aligned with reality.**

Key differentiators:

1. claim-level provenance;
2. explicit authority;
3. supersession/lifecycle;
4. derived-context dependencies;
5. context contracts;
6. task-context compilation;
7. deterministic code evidence via separate Codebase Intelligence;
8. architectural drift over structured evidence;
9. cross-repository integrity;
10. evaluation of context quality itself.

---

# 33. Monetization Possibilities

Not an early constraint.

Potential future paid value:

- organizational policy/governance;
- hosted CI integrity history;
- shared context graph;
- enterprise integrations;
- cross-repo architecture analytics;
- access controls;
- audit;
- compliance;
- team context quality dashboards.

A combined offering with the Codebase Intelligence Engine could form a broader software-context platform.

---

# 34. Risks

## 34.1 Overlap with Fast-Moving OSS

Mitigation:

- integrate rather than duplicate where appropriate;
- preserve modular provider interfaces;
- focus on authority/integrity semantics.

## 34.2 Claim Extraction Becomes LLM-Dependent

Mitigation:

- start explicit;
- use structured docs/frontmatter;
- deterministic metadata;
- treat model extraction as suggestions.

## 34.3 False Positives

Architecture drift is often contextual.

Mitigation:

- evidence-first findings;
- severity;
- explicit policy;
- waivers;
- confidence;
- human review.

## 34.4 Context System Becomes Another Source of Stale Context

Mitigation:

- version everything;
- dependency invalidation;
- revalidation;
- no silent derived truth.

## 34.5 Integration Coupling

Mitigation:

- separate evidence provider contract;
- no shared DB requirement;
- revision-scoped APIs.

---

# 35. Success Metrics

## Integrity

- stale context detected before agent use;
- reduction in unresolved conflicting active sources;
- percentage of authoritative claims with provenance;
- derived artifacts revalidated after dependency changes.

## Context Quality

- smaller task contexts;
- improved expected-context recall;
- fewer superseded docs included;
- lower agent architectural error rate.

## Operational

- low-friction local setup;
- fast incremental checks;
- CI findings actionable rather than noisy.

## Integration

- Context Integrity can consume Codebase Intelligence evidence without owning parser/indexer internals;
- both projects can evolve independently.

---

# 36. Immediate Next Steps

1. Use `docs/architecture.md` as the durable architectural interpretation of this PRD.
2. Implement Phase 0 according to `docs/plans/phase-0-implementation-plan.md`.
3. Do **not** refactor around a Rust engine that does not yet exist.
4. Keep repository/code evidence behind an adapter boundary.
5. In the Codebase Intelligence project, define evidence/provenance fields early enough to support future consumers.
6. Before the first integration phase, write a shared `evidence-contract.md` based on implemented models.
7. Reconcile both PRDs when either project reaches its first stable MVP.

---

# 37. Summary

Context Integrity's mission is:

> **Keep software-development context trustworthy over time.**

The separate Codebase / Context Intelligence Engine answers:

> **What does the software system structurally look like, what changed, and what code context is relevant?**

Context Integrity answers:

> **Which of those facts and surrounding documents are authoritative, current, compatible, required, or in conflict?**

Together, the long-term system becomes:

```text
        Software System
              │
              ▼
  Codebase Intelligence Engine
      observable code facts
              │
              ▼
       Context Integrity
  authority + intent + validity
              │
       ┌──────┼────────┐
       ▼      ▼        ▼
      CI    Agents   Humans
```

The core product principle remains:

> **Context should be managed like code: indexed, typed, versioned, linted, tested, compiled, observed, and continuously improved.**

The major alignment rule is that **code intelligence is a first-class upstream dependency boundary rather than a capability Context Integrity should own itself.**

---

# Appendix A — Representative References

- Repomix — https://github.com/yamadashy/repomix
- Aider repository map — https://aider.chat/docs/repomap.html
- Serena — https://github.com/oraios/serena
- CodeGraphContext — https://github.com/CodeGraphContext/CodeGraphContext
- Potpie — https://github.com/potpie-ai/potpie
- agentsync — https://github.com/obielin/agentsync
- docdrift — https://github.com/NicoSchwandner/docdrift
- doc-drift — https://github.com/driki/doc-drift

These are comparables and inspiration sources. The goal is not to avoid their coverage; it is to build a broader, more integrated context-integrity model while preserving clean boundaries with specialized code-intelligence infrastructure.
