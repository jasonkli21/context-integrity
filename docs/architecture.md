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

Delivered Phase 7 compiler candidate path:

Codebase Intelligence Engine
        │
        ▼
  EvidenceProvider
        │
        └──────────────► Context Compiler

Phase 8 RelationEvidenceProvider -> Claim / Evidence Layer -> Integrity Engine
consumes structural imports/references for explicit forbid_relation invariants.
Impact consumers remain future work.
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

Phase 6 delivers deterministic inventory-source compilation from an explicit contract.
Phase 7 adds optional revision-scoped provider code candidates to the same selection core.

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
and does not run integrity checks as a side effect. The Phase 6 compiler and future
governance behavior remain separate layers.

Phase 6 adds strict configuration v6, retaining v1–v5: positive `budget_bytes` on a
contract, nonnegative rule `priority`, and optional rule `authority_policy` referencing
an effective built-in or configured policy. Older schemas reject these fields. Validator
matching/count behavior and its JSON v1 projection remain unchanged; compiler policy is
projected in the separate compiled-context schema.

Phase 7 configuration v7 adds contract kinds `source_code`, `test`, `schema` and `migration`.
Earlier configuration versions reject these kinds. Runtime provider selection, executable
paths, acquisition ceilings and change queries stay outside repository configuration.

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

Phase 6 implements a selection manifest with selected source records, structured per-source
and per-rule decisions, rule-scoped authority tiers/equal alternatives, budget accounting,
final Phase 5 validation, and unique source dependencies. Config revision, contract identity,
source identity/content revision, repository identity and compiled schema version retain its
derivation. Missing or unusable content SHA256/size prevents selection. Output has no source
bodies; it is derived and rebuildable. No atomic snapshot is claimed.

`complete` means the selected paths satisfy the bound contract, not semantic correctness or
integrity cleanliness. Compiled output carries `integrity_state` with `not_evaluated` by
default; callers may supply an existing deterministic Phase 4 overview, whose finding IDs,
severity and evidence references are retained. The selection core does not perform integrity
I/O or resolve contradictions.

The compiler selection boundary uses `CompilerCandidate`, an evidence-shaped item carrying
identity, location, size, lifecycle/authority inputs, revision and optional derivation/evidence
location. Phase 6 adapts inventory `SourceRecord` values into candidates. Phase 7 supplies
provider candidates with explicit origin, provider/version, rank/reasons and structural evidence.
Normalized provider `SourceRecord`s remain outside `manifest.sources`. Final compilation
validation evaluates the exact mixed source universe; standalone validation stays inventory-only.

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

Responsibilities, delivered in Phase 6:

- acquire candidates from the observed inventory;
- adapt inventory records to the compiler candidate/provenance boundary;
- apply explicit/default lifecycle selection and global contract exclusions;
- reuse subset-aware authority resolution within each rule;
- deduplicate and select required coverage before optional fill;
- enforce source-count maxima and byte budget;
- run the shared Phase 5 validator on final selected paths;
- emit structured decisions and dependency/provenance metadata.

Phase 7 adds body-free code candidates and subordinate structural relevance through
`EvidenceProvider`. The transport adapter belongs in `context_engine.py`; generic request,
batch, snapshot, descriptor and coverage types belong in `evidence.py`.

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

Phase 7 implements `context_candidates(request) -> batch` as a small Python Protocol.
Phase 8 adds a separate `RelationEvidenceProvider.relations(request) -> batch` protocol,
preserving existing replacement context providers. Other methods remain conceptual. See
[`evidence-contract.md`](evidence-contract.md) for the implemented evidence contract v1.

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

## 8.4 Phase 7 Transport and Coherence

The implemented adapter uses bounded local `ctx --version` and schema-v1 `ctx context`
CLI/JSON calls. No shell, shared database, Rust imports, installation or network is used.
Each invocation has a 30-second timeout and incremental 64 MiB stdout / 64 KiB stderr
limits (version stdout: 4 KiB). Errors expose sanitized codes and fail closed.
Resolved root and known HEAD/dirty metadata must match the requested repository observation.
Full UTF-8 bodies are byte-validated, SHA-256 hashed and discarded before domain compilation.
Unsafe paths and duplicate/colliding identities fail; individually lossy paths are omitted
with explicit coverage. Absolute roots and index-local IDs do not enter stable output.
Provider role mapping belongs to Context Integrity: source/test/schema/migration become
executable truth with unknown lifecycle. Other provider roles are skipped.

Provider completeness and contract completeness are independent. Material analysis,
acquisition, ranking or change-mapping gaps stay in provider coverage and warnings even
when the compiled package satisfies its contract. The provider acquisition budget defaults
to 1 MiB (maximum 16 MiB), separately from final package bytes. Other transports may replace
this adapter behind the same generic boundary when needed.

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
not satisfy this check. Phase 4 originally introduced integrity JSON v1 alongside the other
public projections; Phase 8 advances the integrity surface to v2 (see the
[Phase 8 boundary](#phase-8-architectural-integrity-boundary)).

Rules should prefer deterministic evaluation.

An LLM can be a specialized evaluator for rules that explicitly permit probabilistic reasoning.

---

# 15. Context Compiler Architecture

Phase 6 delivers deterministic local selection; Phase 7 adds optional Context Engine code
retrieval through EvidenceProvider. The explicit contract ID selects policy. Task text remains
opaque without a provider; provider mode uses a nonblank task as its relevance query. No task
classification, general contradiction resolution, source-body bundling, persistence, or
integrity gating is delivered.

Compiler lifecycle selection defaults to `unknown | active` unless a rule explicitly
selects lifecycle states. Phase 5 validation has no such implicit filter. Excluded matches
are globally rejected before authority resolution. Authority is resolved inside each rule's
matching lifecycle-eligible candidate subset. An explicit lifecycle selector defines that
rule's candidate universe for authority tier ranking; explicit `authority_eligible = false`
still excludes a source. Calls to the standalone authority resolver retain its active-lifecycle
gate.
Only that subset's highest eligible tier is selectable; budget cannot lower the tier. Equal
tier alternatives remain inspectable and lexical narrowing asserts no semantic preference.
For overlaps, every matching selection rule's lifecycle/authority restriction must hold;
selection through a different rule cannot bypass it. Maxima count all raw selector matches,
exactly as the final validator does.

Required selection first uses deterministic coverage/priority/path greedy ordering. If that
leaves required deficits, a deterministic exact feasibility search over eligible required
candidates repairs the package when possible, minimizing bytes and then selected paths while
respecting maxima and budget. If no feasible set exists, the best greedy inspectable package
is retained. Authority tiers have already filtered each rule and are not compared across
unrelated policies. For policy-equivalent groups, provider rank/path fills provider slots
in the lexical candidate sequence while inventory documents retain their positions. Optional
rules fill by priority descending and ID ascending with the same local relevance ordering. Source bytes count once and are checked before selection. CLI budget overrides the
contract budget, then defaults to unbounded. The final Phase 5 validator alone determines
contract completeness. Earlier JSON projections remain unchanged; compiled-context JSON v3
retains the integrity evaluation state and adds explicit provider/candidate provenance and coverage.

Broader pipeline (code relevance is delivered; general contradictions remain future work):

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
configuration_schema_version       # implemented through v8
evidence_contract_version          # implemented v1
compiled_context_schema_version    # implemented v3
derived_receipt_schema_version     # implemented v1
derived_result_schema_version      # implemented v1
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
- provider protocol/normalization logic.

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

Multi-repository support is a long-term requirement but was not a Phase 0 scope requirement.
The Phase 10 explicit workspace v1 supports declared local checks and per-repository context
indexes; graph federation and semantic cross-repository analysis remain future work.

The architecture should ensure:

- every source belongs to a repository identity;
- every evidence item belongs to a revision;
- IDs are not based solely on local absolute paths;
- source and evidence contracts can carry repository identity.

The workspace model is conceptually:

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
- additional evidence transports beyond the Phase 7 local CLI adapter;
- MCP/API surface;
- cross-repository structural graph and durable generated-artifact receipt formats;
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

Phase 7 implements the context-candidate subset in `evidence-contract.md`.
The broader alignment contract is:

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

The implemented integration contract is documented here:

```text
evidence-contract.md
```

That document describes implemented context and relation abstractions; impact consumers remain deferred.

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

Use `docs/current-state.md` for current verification and review status. Phase 8 architectural
integrity implements explicit repository-owned policy over descriptive relation evidence.
Phase 9 derived context revalidation and Phase 10 explicit workspace integrity are implemented;
independent review remains required. See current-state for verification and review gaps.
Fresh independent Phase 8 re-review remains separately pending.


## Phase 8 architectural integrity boundary

Strict config v8 adds typed `architecture_invariants`, each linked to an explicit architecture
claim with `must_not_depend_on`. Literal path/prefix/symbol selectors and unresolved target
names drive `forbid_relation`. `integrity.py` owns evaluation; the public Context Engine
schema-v1 graph adapter only validates and normalizes facts. Numeric graph identities are
removed before domain use. Provider acquisition reuses bounded subprocess controls.

Integrity JSON v2 retains Phase 4 checks and adds explicit policy, claim provenance,
provider/snapshot/coverage and grouped HIGH relation findings. Claims stay `unverified`.
Absence yields `no_violation_observed`, `inconclusive` with conservative global coverage gaps,
or `not_evaluated` without a provider. It never proves compliance. Dirty graph evidence lacks
provider content identity; separate bounded local hashes are observations, not graph byte
certification. The compiler and contracts remain separate. Durable semantics and limits:
[`architecture-integrity-contract.md`](architecture-integrity-contract.md).

## Phase 9 derived context boundary

Standalone receipt v1 records actual artifact/source bytes, effective inventory metadata,
config absence/presence, declared upstream receipts and typed compiler selection context.
It does not advance config v8, compiled JSON v3 or integrity JSON v2. `derived_models.py`
owns strict declarations/projectors; `derived.py` separates bounded observations from pure
comparison/status aggregation; `derived_output.py` owns explicit exclusive writes/rollback.
Existing acquisition and inventory accept optional smaller observation budgets; old command
defaults are unchanged.

Receipt DAGs retain exact receipt/artifact pins and propagate original changed/unknown input
reasons with bounded memoization. HEAD alone is explanatory, never an invalidation rule.
Compiler selection context conservatively fingerprints the inventory universe, effective
contract/policies, budget, task digest and the installed package's Python source fingerprint.
This implementation fingerprint is conservative and can flag unrelated package edits.
Selected provider candidates retain derivation;
local byte equality does not revalidate provider coverage/ranking, so provider context yields
inconclusive absent a definite change. No semantic verification, authority promotion, hidden
persistence, network/provider replay or automatic pin refresh is introduced. Ordinary output
failures roll back prepared pairs; independent filesystem names have no crash-atomic commit.
Exact semantics and limits: [derived context contract](derived-context-contract.md).

## Phase 10 workspace boundary

`workspace_models.py` keeps qualified repository/source/claim identities and typed rule results
separate from filesystem acquisition. `workspace_config.py` validates an explicit strict workspace
TOML v1 and consumer contract lock JSON v1. `workspace.py` binds aliases to discovered identities,
rejects duplicate/nested roots and same-origin checkout collisions, then evaluates explicit
contract pins, byte mirrors and paired unverified declarations. Matching bytes/declarations
never establish semantic compatibility or a cross-repository authority winner.

`workspace_output.py` projects separate check/context JSON v1 with repository-qualified evidence
and task digest only. Composition reuses each repository's configured contract/compiler and
explicit budget; selection completeness and check findings remain independent. Provider support
is disabled at this surface; no cross-repo graph, shared database or global ranking is inferred.
The consumer-owned lock is a narrow producer-revision acceptance receipt; it neither changes
Phase 9 receipt v1 nor supplies transitive generated-artifact revalidation.

All root ancestors and source components use no-follow descriptor traversal. Workspace reads
also check stable file metadata after hashing. Invocation-local qualified caches, separate
shared explicit/inventory budgets and conservative uncertainty bound observations. Saved output
is exclusive and outside every participating root. Observations/publication remain sequential,
without a multi-repo atomic snapshot or crash transaction. Exact grammar, limits, caveats and
valid fixtures: [workspace integrity contract](workspace-integrity-contract.md).
