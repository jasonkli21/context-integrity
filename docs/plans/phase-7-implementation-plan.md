# Context Integrity — Phase 7 Detailed Implementation Plan

**Phase:** 7 — Codebase Intelligence `EvidenceProvider` Integration
**Status:** Ready for implementation
**Date:** 2026-10-16
**Repository:** `jasonkli21/context-integrity`
**Inspected default branch:** `main`
**Inspected Context Integrity HEAD:** `ce97e04c07ede75e91ad137b97ba1079ff0030bb` (`Fix Phase 6 review findings`)
**Related repository:** `jasonkli21/context-engine`
**Inspected Context Engine HEAD:** `5e3ae18d1510501e177aac2d9021fc01d8534435` (`fix: address phase 6 review findings`)
**Parent documents:** `docs/prd.md`, `docs/architecture.md`, `docs/current-state.md`, `AGENTS.md`
**Predecessor:** Phase 6 — Task Context Compiler
**Successor:** Phase 8 — Architectural Integrity

---

# 1. Phase Objective

Phase 7 introduces the first deliberate integration between Context Integrity and the separate Codebase / Context Intelligence Engine.

The goal is not to merge the projects, share storage, or move policy into the Rust engine. The goal is to let Context Integrity consume **revision-scoped, descriptive code evidence** through a replaceable provider boundary and use that evidence as additional candidates in the existing task-context compiler.

The core Phase 7 question is:

> **Given a Context Integrity contract, the current Context Integrity repository observation, and a task-specific set of ranked code candidates from a compatible Codebase Intelligence provider, can Context Integrity compile one deterministic mixed documentation + code context package while preserving its own authority, lifecycle, exclusion, provenance, and budget semantics?**

The intended progression is:

```text
Phase 0–5
inventory + authority + lifecycle + claims + integrity + contracts

Phase 6
repository context sources
  + deterministic contract-aware compiler
  -> bounded documentation/context manifest

Phase 7
Phase 6 compiler
  + revision-coherent external code evidence
  + provider ranking/provenance
  -> mixed documentation + code compiled context

Phase 8
provider structural evidence
  + explicit architectural invariants/policy
  -> architectural integrity findings
```

The primary architectural invariant is:

```text
Codebase Intelligence describes observable code facts and relevance.
Context Integrity decides what those facts mean for authority, lifecycle,
contracts, integrity, and governance.
```

Provider ranking may influence relevance **only after** Context Integrity policy has established eligibility. It must never override contract exclusions, lifecycle rules, authority policy, cardinality, or byte budget.

---

# 2. Alignment with the PRD, Architecture, and Current Repository

The original PRD defines Phase 7 as the **Codebase Intelligence Adapter** and names symbol/structural evidence, changes, impact, and code context candidates as the upstream evidence family.

The architecture deliberately keeps the exact provider methods and transport deferred, while fixing the durable responsibility split:

- Context Engine: structural/descriptive evidence;
- Context Integrity: normative interpretation;
- no shared database;
- no parser internals imported into Context Integrity;
- provider/model facts retain derivation;
- the compiler may consume relevance but owns authority/lifecycle filtering.

The newer Phase 6 design and post-review state narrow the immediate Phase 7 seam further in a useful way:

- `CompilerCandidate` already exists as an evidence-shaped compiler boundary;
- inventory `SourceRecord` is only one candidate origin;
- compiler decisions already retain optional evidence location/derivation;
- compiled results already carry an explicit integrity-evaluation state;
- Phase 7 is explicitly named as the place where other candidate origins enter the compiler.

The current Context Engine now has a concrete, versioned local surface that can support the first adapter without speculative infrastructure:

```text
ctx context [PATH]
  --task TASK
  --budget BYTES
  [--change BASE..HEAD]
  --format json
```

Its schema-v1 context output already carries, among other fields:

- repository/root context;
- Git HEAD / dirty state;
- task text;
- ranker version (`file-ranker-v1` in the inspected implementation);
- byte-budget accounting;
- change-aware ranking metadata when requested;
- coverage/incompleteness signals;
- ranked selected file paths;
- file language/role;
- UTF-8 content-byte size;
- score components and reason codes;
- matched-symbol evidence;
- graph/change distances;
- full selected file content.

Phase 7 should consume the stable external JSON contract, not Context Engine internals or its SQLite store.

## 2.1 Deliberate Phase 7 Interpretation

The original roadmap mentions consuming the broader evidence family. Do **not** implement unused graph/diff/impact policy plumbing merely to check roadmap boxes.

Phase 7 should establish a provider contract that can grow to additional capabilities, but the required end-to-end capability for this phase is:

```text
context_candidates
```

with optional change-aware ranking through the existing Context Engine `--change` input.

Phase 8 can extend the provider contract with relation/impact queries at the moment Context Integrity has a real architectural-integrity consumer for them.

This interpretation follows the repository's current architecture rule: avoid speculative abstractions and add provider methods when current requirements justify them.

---

# 3. Current Delivered Baseline

Implementation must start from the repository as it exists, not from the Phase 6 plan alone.

## 3.1 Context Integrity baseline

At inspected HEAD `ce97e04c07ede75e91ad137b97ba1079ff0030bb`:

- Phase 6 is implemented, independently reviewed, and its findings F-001–F-004 have been fixed;
- full offline verification recorded **721 tests**;
- strict repository configuration supports schemas v1–v6;
- contracts are exact-config-bound;
- the compiler uses deterministic required-first selection plus feasibility repair;
- contract exclusions and rule-scoped authority are enforced before budget fallback;
- `CompilerCandidate` exists as a provider-ready selection item;
- `CompilerCandidate.from_source(...)` adapts inventory `SourceRecord` values;
- compiled-context JSON is schema v2;
- integrity state is explicit and `not_evaluated` by default;
- compilation still acquires candidates only from `manifest.sources`;
- Context Integrity inventory intentionally indexes context/document candidates, not ordinary code;
- `validate_contract(...)` still resolves package paths only against `manifest.sources`;
- no provider transport, provider contract, code retrieval, or code relevance exists.

`docs/current-state.md` explicitly identifies the next work as:

```text
Phase 7 — Codebase Intelligence EvidenceProvider integration
```

The separately pending Phase 4 final independent verification remains separate work and must not be folded into Phase 7.

## 3.2 Context Engine baseline

At inspected Context Engine HEAD `5e3ae18d1510501e177aac2d9021fc01d8534435`:

- Phase 5 provides deterministic task-context ranking and full-file bundles;
- Phase 6 provides a validated persistent analysis cache while reconstructing current graphs through the existing domain path;
- JSON surfaces remain versioned and adapter-oriented;
- Context Engine's own integration document says it owns descriptive files/symbols/relations/changes/impact/context ranking while Context Integrity owns claims/authority/validity/supersession/policy/drift/governance;
- Context Engine does **not** own Context Integrity policy semantics.

Phase 7 must consume this external behavior without coupling to Context Engine's cache schema, Rust types, index-local IDs, or implementation modules.

---

# 4. Starting-State Workflow

At the beginning of implementation:

```bash
git status --short
git rev-parse HEAD
git log -10 --oneline
```

Read in this order:

1. `AGENTS.md`
2. `docs/current-state.md`
3. this Phase 7 plan
4. `docs/architecture.md` sections on evidence providers, compiler, versioning, determinism, security, and the Phase roadmap
5. Phase 6 implementation + review-fix evidence only where needed
6. current `models.py`, `evidence.py`, `compiler.py`, `contracts.py`, `configuration.py`, `cli.py`, `rendering.py`
7. relevant tests
8. `docs/prd.md` only for product-scope confirmation

For the sibling Context Engine, inspect only the minimum external contract needed:

1. `docs/current-state.md`
2. `docs/integrations/context-integrity.md`
3. the current `ctx context` CLI definition
4. its schema-v1 context JSON renderer / DTOs

If either repository has advanced beyond the inspected SHAs:

- inspect the newer state;
- preserve accepted newer work;
- reconcile this plan against actual interfaces;
- do not reset either repository to the reference commits.

Do not modify the Context Engine repository as part of this phase unless the user explicitly expands scope.

---

# 5. Core User Journey

A repository can define a Phase 7 contract such as:

```toml
schema_version = 7

[[context_contracts]]
id = "implementation-task"
task_class = "implementation"
description = "Current policy and relevant code for implementation work."
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
min_count = 1
max_count = 1
priority = 90

[[context_contracts.rules]]
id = "code"
mode = "required"
kinds = ["source_code"]
min_count = 1
max_count = 8
priority = 80

[[context_contracts.rules]]
id = "tests"
mode = "optional"
kinds = ["test"]
max_count = 4
priority = 70

[[context_contracts.rules]]
id = "historical"
mode = "excluded"
lifecycles = ["superseded", "historical", "expired", "invalid"]
```

The user runs:

```bash
uv run context-integrity compile implementation-task . \
  --task "Add provider snapshot validation to compilation" \
  --evidence-provider context-engine \
  --format text
```

Optional change-aware ranking:

```bash
uv run context-integrity compile implementation-task . \
  --task "Review the impact of the persistence changes" \
  --evidence-provider context-engine \
  --evidence-change BASE..HEAD \
  --format json
```

The flow is:

```text
observe Context Integrity repository state
  -> resolve exact configured contract
  -> acquire normal inventory candidates
  -> ask EvidenceProvider for ranked code candidates
  -> verify provider contract + repository/revision coherence
  -> normalize provider candidates into Context Integrity-owned types
  -> discard provider source bodies after hashing/validation
  -> combine inventory + provider candidates
  -> apply Context Integrity lifecycle/authority/exclusions
  -> use provider rank only as a subordinate relevance tie-break
  -> required-first selection + feasibility repair
  -> optional fill
  -> final contract validation across the same candidate universe
  -> compiled-context v3 with provider provenance/coverage, no source bodies
```

If the provider is requested and its output is malformed, incompatible, from the wrong repository/snapshot, or otherwise unsafe to trust, compilation should fail with a typed provider error rather than silently dropping back to documentation-only behavior.

If the provider returns a valid but incomplete analysis/shortlist, compilation may continue, but that incompleteness must remain visible in provider coverage/warnings.

---

# 6. Product Boundary

## 6.1 In Scope

Phase 7 includes:

- a versioned Context Integrity `EvidenceProvider` domain contract;
- provider descriptor/capability metadata;
- a typed context-candidate request/result boundary;
- provider repository/snapshot coherence checks;
- Context Engine CLI + schema-v1 JSON adapter;
- safe subprocess invocation without shell execution;
- explicit provider timeout/output/error handling;
- provider full-content validation + SHA-256 derivation, followed by body discard;
- normalized code/test/schema/migration candidate roles;
- configuration schema v7 for code-evidence contract kinds;
- backward-compatible v1–v6 repository configuration behavior;
- mixed inventory + provider compilation;
- contract validation against the exact mixed candidate universe used by compilation;
- provider ranking as a lower-order relevance signal only;
- provider coverage/incompleteness surfaced in compiled output;
- provider identity/version/ranker/derivation retained as provenance;
- optional change-aware Context Engine ranking through `--evidence-change`;
- compiled-context JSON schema v3;
- text rendering for provider provenance/coverage;
- deterministic candidate IDs/orderings;
- focused provider, mixed-compiler, rendering, CLI, and compatibility tests;
- a durable `docs/evidence-contract.md` describing the implemented boundary;
- README/current-state/architecture/docs navigation updates where the source of truth changes;
- a Phase 7 implementation report.

## 6.2 Explicitly Out of Scope

Do **not** implement:

- architectural-integrity rules or findings (Phase 8);
- generic contradiction resolution;
- claim truth verification;
- importing Context Engine Rust modules or internal data structures;
- reading Context Engine SQLite tables directly;
- a shared database;
- a Python/Rust FFI binding;
- HTTP/MCP/server transport;
- background provider daemons;
- provider auto-install/download;
- network calls;
- cross-repository compilation;
- cross-repository identity reconciliation;
- symbol-lineage semantics;
- compiler/type-checker-grade code truth;
- a second parser/indexer in Context Integrity;
- LLMs, embeddings, or learned ranking;
- semantic natural-language task classification;
- automatic contract selection;
- token budgeting or tokenizers;
- source-body persistence or source-body output in compiled manifests;
- automatic policy/document repair;
- CI enforcement, waivers, or governance;
- Phase 7 implementations of `relations()`, `impact()`, etc. with no current consumer merely for speculative completeness.

---

# 7. Configuration Schema v7

Introduce:

```text
schema_version = 7
```

The provider itself is a runtime integration and should **not** require host-specific executable paths in repository configuration.

Schema v7 exists to expand the contract vocabulary for provider-backed code evidence while preserving earlier schema behavior.

## 7.1 New `SourceKind` values

Add the missing architecture-aligned kinds needed for normalized code evidence:

```text
source_code
test
schema
migration
```

`configuration` already exists.

Do not broaden the normal Phase 0 inventory acquisition to scan all code. These values are for normalized external evidence and future sources, not permission to turn Context Integrity into a second code scanner.

## 7.2 Schema gating

Requirements:

- schemas v1–v6 parse exactly as before;
- v1–v6 continue rejecting unsupported schema versions/unknown keys;
- contracts using the new provider-backed kinds require schema v7;
- v7 retains all v6 fields/semantics;
- no silent schema upgrade;
- no provider executable/path is stored in `.context-integrity.toml` in Phase 7;
- existing v1–v6 machine-readable projections remain unchanged.

A small helper should centralize the version gate rather than scattering checks around the parser.

---

# 8. Evidence Provider Domain Contract

The generic boundary belongs in Context Integrity's evidence/domain layer. Provider-specific subprocess/JSON logic belongs in a separate adapter module.

Recommended concepts (exact names may vary):

```text
EvidenceProvider
EvidenceProviderDescriptor
EvidenceCapability
EvidenceContextRequest
EvidenceRepositorySnapshot
EvidenceCoverage
EvidenceContextCandidate
EvidenceContextBatch
EvidenceProviderError
```

Avoid a large trait/framework hierarchy. One `Protocol` or small abstract boundary is sufficient.

## 8.1 Provider descriptor

Conceptually:

```text
EvidenceProviderDescriptor
- id                  # e.g. "context-engine"
- version             # executable/provider version
- contract_version    # Context Integrity evidence contract, v1
- capabilities[]      # at least context_candidates
- derivation          # adapter/ranker identity
```

Provider identity/version must be data, not only log prose.

## 8.2 Request

Conceptually:

```text
EvidenceContextRequest
- repository_root     # runtime-only; never stable output
- repository_ref
- task
- acquisition_budget_bytes
- change_range?
```

The request should make the provider query explicit and deterministic.

Provider-backed compilation requires a nonblank task because the current Context Engine context ranker requires task text. Do not silently substitute contract IDs/task classes as semantic queries.

## 8.3 Repository snapshot

Conceptually:

```text
EvidenceRepositorySnapshot
- provider_repository_root   # runtime validation only
- git_head?
- git_dirty?
- provider_schema_version
- command
```

The absolute provider root may be used to validate that the provider observed the requested repository, but it must not enter stable Context Integrity JSON.

## 8.4 Candidate

Conceptually:

```text
EvidenceContextCandidate
- provider_candidate_id
- path
- source_kind
- content_sha256
- size_bytes
- provider_rank
- provider_score
- provider_score_components
- provider_reasons[]
- matched_entities[]
- graph_distance?
- change_distance?
- provider_derivation
```

Do not carry source bodies past adapter normalization.

## 8.5 Coverage

Preserve enough upstream incompleteness to avoid overstating what the provider observed.

At minimum retain normalized equivalents of material Context Engine context-coverage signals, including where available:

- analysis incomplete;
- paths may be lossy;
- task terms truncated;
- graph traversal truncated;
- ranking roots omitted;
- fallback candidates omitted;
- content-load failures;
- content-load safety limiting/omissions;
- selection candidates omitted;
- skipped candidates omitted;
- change mapping ambiguity/unavailability when `--change` is used.

Do not map every current Rust DTO field into a permanent Context Integrity field if it has no integrity value. Keep the evidence contract compact but honest.

---

# 9. Context Engine CLI Adapter

Implement one provider adapter around the stable executable/JSON surface.

A reasonable module boundary is:

```text
src/context_integrity/evidence.py
  generic provider/evidence types and validation

src/context_integrity/context_engine.py
  Context Engine executable invocation + JSON normalization
```

Do not create a package hierarchy solely for one adapter unless current code organization clearly benefits from it.

## 9.1 Invocation

Expected external command shape:

```text
ctx context ROOT
  --task TASK
  --budget PROVIDER_ACQUISITION_BUDGET
  --format json
  [--change BASE..HEAD]
```

Requirements:

- never use `shell=True`;
- pass arguments as an argv sequence;
- support an explicit executable override from the Context Integrity CLI;
- otherwise resolve `ctx` through the local environment/PATH;
- no auto-install, download, or network fallback;
- use a finite timeout;
- bound accepted stdout/stderr sizes and sanitize user-visible failures;
- provider nonzero exit is a typed provider failure;
- do not echo arbitrary repository/provider stderr into stable JSON;
- optionally call `ctx --version` through the same bounded safe subprocess boundary to identify provider version.

## 9.2 Provider acquisition budget

The Context Engine `context` command requires its own content-byte budget. This is an **evidence-acquisition ceiling**, not the final Context Integrity contract budget.

Use a bounded default appropriate to the current provider contract (the inspected Context Engine supports up to 16 MiB) and optionally expose an advanced CLI override such as:

```text
--evidence-budget-bytes N
```

Requirements:

- final Context Integrity budget remains authoritative for the compiled package;
- provider acquisition budget must not be mislabeled as the contract budget;
- provider omissions caused by its acquisition ceiling remain visible in coverage;
- do not dynamically lower provider authority/policy because a smaller file fits better.

## 9.3 Envelope validation

Fail closed unless the output is the expected external contract:

```text
schema_version == 1
command == "context"
```

Validate required field types/ranges and reject malformed/unsafe data with a sanitized `EvidenceProviderError`.

Do not deserialize arbitrary JSON directly into broad internal models and trust missing/default values.

## 9.4 Repository and revision coherence

Provider results must describe the same repository observation closely enough to combine safely.

Validate:

1. provider root resolves to the requested repository root;
2. provider Git HEAD matches Context Integrity's observed HEAD when both are available;
3. provider dirty state matches Context Integrity's repository dirty state when both are known;
4. a non-Git repository may still provide content-hash-scoped candidates;
5. a mismatch is a provider failure, not a warning-and-continue condition.

Do not persist the absolute root after validation.

Because neither project claims an atomic filesystem snapshot, also bind every candidate to its own content hash.

## 9.5 Full-content handling

The current Context Engine context JSON contains full selected content. Context Integrity needs it only to establish a candidate content revision because the current provider surface does not expose a per-file hash.

For each accepted code candidate:

1. require `content` to be a string;
2. UTF-8 encode it;
3. require encoded byte length to equal provider `content_bytes`;
4. compute SHA-256;
5. construct the normalized revision/candidate;
6. immediately discard the body;
7. never include body text in `CompiledContext`, warnings, provider errors, logs, goldens, or implementation reports.

If Context Engine later adds explicit content hashes, the adapter can move to that field without changing the provider domain boundary.

## 9.6 Safe paths

Reject or omit unsafe provider paths:

- absolute paths;
- traversal;
- backslashes/drive ambiguity where Context Integrity requires POSIX repository-relative identity;
- NULs;
- lossy paths that cannot be represented faithfully in the stable Context Integrity path model.

A lossy provider path should produce explicit provider coverage/warning evidence, not a fabricated normalized identity.

---

# 10. Provider Role Normalization

The provider is descriptive. It must not get to choose Context Integrity authority/lifecycle semantics.

Normalize supported Context Engine file roles in the Context Integrity adapter:

```text
Context Engine role     Context Integrity kind   Authority class
---------------------   ----------------------   -----------------
source                  source_code              executable_truth
test                    test                     executable_truth
schema                  schema                   executable_truth
migration               migration                executable_truth
```

For Phase 7, skip provider documentation/configuration/generated/vendor/unknown roles unless the implementation has a concrete need and a clearly documented mapping.

Rationale:

- Context Integrity already owns document acquisition/policy;
- avoiding provider document candidates prevents duplicate document truth paths;
- generated/vendor/unknown evidence should not silently become task context.

Set provider code candidate lifecycle conservatively to:

```text
unknown
```

The provider observed the file in the current snapshot, but it does not own semantic lifecycle policy. The existing compiler default already treats unknown/active as current-eligible.

## 10.1 Synthetic `SourceRecord` adapter

A provider-backed candidate may be represented as a Context Integrity `SourceRecord` **only as a normalized evidence adapter**, not as proof it came from the local context inventory.

Recommended properties:

- stable source ID derived from Context Integrity repository identity + normalized path;
- provider-normalized `SourceKind`;
- Context Integrity-owned authority class mapping;
- lifecycle `unknown`;
- content SHA-256 derived from validated provider bytes;
- provider Git HEAD when available;
- file-level Git status `tracked_clean` only when repository cleanliness proves it; otherwise `unknown`;
- classification basis explicitly says provider-derived;
- provider provenance remains separately available on `CompilerCandidate`.

Do not mutate `manifest.sources` and then claim ordinary inventory discovered the code file.

---

# 11. Compiler Candidate Evolution

Extend `CompilerCandidate` rather than create a parallel compiler path.

Recommended additions:

```text
CandidateOrigin
- inventory
- evidence_provider

CompilerCandidate
- existing identity/path/kind/authority/lifecycle/revision/size
- origin
- provider_id?
- provider_version?
- relevance_rank?
- relevance_score?
- relevance_reasons[]
- graph_distance?
- change_distance?
- existing evidence_location / derivation
```

Exact field names may vary, but the following must remain answerable:

> Where did this candidate come from, what revision does it describe, why did the provider consider it relevant, and why did Context Integrity select or reject it?

## 11.1 Candidate IDs and deduplication

Requirements:

- IDs deterministic across repeated identical observations;
- sort provider candidates independently of provider emission order before compiler use;
- reject duplicate provider paths with conflicting revisions/metadata;
- do not allow provider evidence to silently shadow an inventory source at the same path;
- if an overlap is accepted at all, require identical content revision and a deliberate merge rule;
- provider origin must remain visible after deduplication.

Prefer skipping provider document/config roles so overlap is naturally rare.

---

# 12. Contract Matching and Validation Across Mixed Candidates

Phase 5 public validation behavior must remain intact.

Today:

```text
validate_contract(manifest, contract, paths)
```

resolves paths only from `manifest.sources`.

Phase 7 needs compilation validation against the **same mixed candidate source records the compiler actually selected**, without pretending those records are canonical inventory.

Refactor toward a shared internal evaluator, for example:

```text
validate_contract(...)
  -> inventory-only wrapper; behavior unchanged

validate_contract_sources(
  manifest,
  contract,
  available_sources,
  selected_paths,
)
  -> same rule semantics over an explicitly supplied source universe
```

Requirements:

- `require_bound_contract(...)` remains mandatory;
- Phase 5 `validate_contract(...)` output and semantics remain unchanged;
- rule matching still means AND across dimensions / OR within dimension;
- no hidden lifecycle filter is introduced into validator semantics;
- duplicate/unavailable path behavior remains deterministic;
- compiler final status is based on validation against the exact candidate universe it compiled from;
- provider candidates do not become globally visible to unrelated `contracts validate` commands unless explicitly supplied through a future interface.

Do not fake provider membership by mutating the canonical `InventoryManifest` in a way that could leak into other use cases.

---

# 13. Mixed-Candidate Selection Semantics

All Phase 6 policy remains in force.

Selection order conceptually becomes:

```text
candidate acquisition
  -> global contract exclusions
  -> lifecycle eligibility
  -> rule-scoped authority
  -> content revision/size validity
  -> required coverage / rule priority
  -> provider relevance tie-break where applicable
  -> deterministic path tie-break
  -> budget/cardinality constraints
  -> feasibility repair
  -> optional fill
  -> final mixed-candidate contract validation
```

## 13.1 Provider ranking is subordinate

Provider rank/score must never:

- bypass an excluded rule;
- make historical/invalid context current;
- bypass an authority policy;
- choose a lower authority tier over a higher one;
- violate rule maxima;
- exceed Context Integrity budget;
- turn a provider omission into proof no other evidence exists.

Recommended ordering for otherwise policy-equivalent candidates:

```text
1. required-rule coverage
2. contract rule priority
3. provider relevance rank (when present)
4. provider score only if needed and semantically stable
5. repository-relative path
```

Do not compare authority tiers across unrelated policies.

Do not make a numeric provider score a global truth/authority rank.

## 13.2 Inventory candidates without provider rank

Do not invent relevance scores for inventory documents.

Contract priorities should express policy differences between documentation and code. Provider rank is a local relevance signal for provider-backed candidates, not a reason to silently demote unranked required policy sources.

## 13.3 Feasibility repair

The Phase 6 required-set feasibility repair must continue to consider every policy-eligible candidate in the combined candidate universe and respect:

- rule maxima;
- unique byte accounting;
- provider/inventory deduplication;
- authority/lifecycle eligibility;
- final contract minima.

If relevance is used in repair tie-breaking, correctness/minimal feasible cost remains more important than provider preference.

---

# 14. Provider Coverage and Compilation Semantics

Keep two concepts separate:

```text
contract completeness
!=
provider analysis completeness
```

`CompilationStatus.COMPLETE` should continue to mean the selected package satisfies its bound Context Integrity contract over the acquired candidate universe.

A separate provider state should say whether upstream evidence was incomplete/truncated/ambiguous.

Do not silently change `complete` to mean "all code truth known."

Recommended compiled provider metadata:

```text
CompiledProviderState
- provider descriptor
- query/ranker derivation
- repository revision
- change range?
- coverage status
- normalized coverage counters/flags
- warnings[]
```

If provider evidence is valid but incomplete, compilation can still be `complete` while the provider state is explicitly incomplete.

---

# 15. Compiled Context Model and JSON v3

Provider-backed selected items require deliberate provenance evolution.

Advance the separate compiled-context JSON contract to:

```text
schema_version = 3
```

Do not change earlier inventory/authority/lifecycle/claims/integrity/contract-validation JSON versions.

## 15.1 Required v3 additions

At minimum expose:

- evidence-provider descriptor(s);
- provider query/ranker derivation;
- provider revision/coverage state without absolute roots;
- candidate origin;
- provider relevance rank/reason evidence on decisions;
- provider-derived source revisions;
- dependencies for selected provider candidates;
- optional change-awareness metadata;
- warnings/incompleteness;
- existing Context Integrity authority/lifecycle/contract decisions.

## 15.2 Privacy and determinism

Stable compiled JSON must still contain:

- no source bodies;
- no absolute repository roots;
- no runtime timestamps;
- no raw unbounded provider stderr;
- deterministic ordering;
- repository-relative paths only;
- content hashes for selected dependencies;
- provider/ranker versions as explicit semantic provenance.

## 15.3 Inventory-only regression

An ordinary compile with no provider should preserve Phase 6 behavior semantically.

The v3 projection may add explicit origin/provider-state fields, but it must not change:

- selected paths;
- authority/lifecycle decisions;
- budget arithmetic;
- contract findings;
- Phase 6 feasibility behavior.

Keep a focused golden/regression demonstrating this.

---

# 16. CLI Surface

Extend `compile` minimally.

Recommended options:

```text
--evidence-provider context-engine
--context-engine-bin PATH
--evidence-budget-bytes N
--evidence-change BASE..HEAD
```

Exact naming may vary if the existing Typer style suggests a cleaner choice.

Requirements:

- no provider option => Phase 6 acquisition behavior;
- only recognized providers accepted;
- provider-backed compilation requires nonblank `--task`;
- executable override is runtime-only, never stable output except sanitized provider identity/version;
- `--evidence-change` is valid only with a provider that advertises/supports change-aware context;
- provider errors map to a distinct typed exit category (recommended exit 7 if unused);
- complete/incomplete contract status remains exit 0 as in Phase 6;
- CLI orchestrates; it does not contain provider parsing or selection policy.

---

# 17. Error Model

Add a typed provider failure category consistent with architecture:

```text
EvidenceProviderError / ProviderError
```

Differentiate internally where useful:

- provider executable unavailable;
- provider timed out;
- provider process failed;
- output exceeded safety bound;
- malformed JSON;
- unsupported provider schema/command;
- repository mismatch;
- revision mismatch;
- unsafe/lossy candidate path;
- candidate content/size mismatch;
- duplicate/conflicting candidate identity.

User-facing messages must remain sanitized and should not embed arbitrary source content, command output, or absolute paths in stable machine-readable results.

---

# 18. Testing Strategy

Testing should remain focused, deterministic, and offline.

The normal test suite must **not require a real sibling Context Engine binary**.

## 18.1 Evidence contract/model tests

Cover:

- provider descriptor invariants;
- capability validation;
- repository snapshot validation;
- safe candidate IDs;
- content revision validation;
- provider coverage model invariants;
- deterministic ordering.

## 18.2 Configuration v7 tests

Cover:

- v1–v6 unchanged;
- v6 rejects provider-only contract kinds;
- v7 accepts `source_code`, `test`, `schema`, `migration`;
- unknown kind rejected;
- no silent schema upgrade;
- old config goldens unchanged.

## 18.3 Context Engine adapter tests

Use deterministic fixture JSON and/or a generated fake executable.

Cover at least:

- valid schema-v1 `context` output;
- wrong schema version;
- wrong command;
- malformed JSON;
- missing required fields;
- provider nonzero exit;
- missing executable;
- timeout;
- oversized output;
- repository-root mismatch;
- Git HEAD mismatch;
- dirty-state mismatch;
- non-Git success;
- unsafe path;
- lossy path handling;
- duplicate path conflict;
- content-byte mismatch;
- body hashing + body discard;
- rank/score/reason normalization;
- provider coverage/incompleteness mapping;
- optional change metadata;
- sanitized errors.

Do not make fixture tests depend on Context Engine internal Rust types.

## 18.4 Mixed compiler tests

Synthetic cases should prove:

1. required document + required `source_code` can compile together;
2. optional tests fill after required context;
3. provider candidate cannot bypass a global excluded rule;
4. provider relevance cannot bypass lifecycle restrictions;
5. provider relevance cannot bypass authority policy;
6. lower provider rank wins only when policy/contract pressure is otherwise equivalent;
7. inventory candidates with no provider rank are not globally demoted;
8. mixed byte budget counts every unique selected file once;
9. feasibility repair works with provider candidates;
10. duplicate/collision semantics are deterministic;
11. final validation sees provider-backed selected sources;
12. standalone Phase 5 `validate_contract` remains inventory-only and unchanged;
13. provider coverage can be incomplete while contract compilation is complete;
14. reversed provider emission order yields identical compiled JSON;
15. no provider source bodies appear in any stable output;
16. inventory-only compilation preserves Phase 6 selected paths/decisions.

## 18.5 CLI tests

Use a fake local executable to verify:

- argv construction without shell interpretation;
- task forwarding;
- provider budget forwarding;
- optional change forwarding;
- executable override;
- missing task usage error;
- provider error exit mapping;
- text + JSON output;
- output-file behavior;
- no provider behavior remains unchanged.

## 18.6 Optional real integration smoke

If the sibling `context-engine` repository/binary is locally available during implementation, run a small smoke against it and record that as implementation evidence.

This smoke is useful but must not become a mandatory `make check` dependency.

---

# 19. Documentation Changes

Create:

```text
docs/evidence-contract.md
```

It should document only the implemented contract:

- responsibility split;
- provider descriptor/versioning;
- repository/revision semantics;
- context-candidate semantics;
- provenance/derivation;
- provider coverage;
- current Context Engine CLI transport;
- what Context Integrity interprets vs what the provider describes;
- transport-replacement rule;
- explicit limitations.

Update as needed:

- `README.md` — provider-backed compile example + limitations;
- `docs/README.md` — navigate to evidence contract;
- `docs/architecture.md` — mark Layer/Phase 7 delivered boundary, candidate flow, versioning, provider semantics;
- `docs/current-state.md` — only after verification, advance to Phase 7 delivered and Phase 8 next;
- `docs/plans/README.md` / `docs/implementation-reports/README.md` if those indexes are intended to track every phase;
- implementation report for Phase 7.

Do **not** rewrite:

- historical Phase 0–6 plans/reports;
- PRD merely to restate implementation details;
- AGENTS unless a genuinely new durable repository instruction is needed;
- Context Engine docs from this repository's implementation session.

Run a documentation staleness sweep after implementation and record what was checked.

---

# 20. Security and Trust Boundary Requirements

Provider integration expands the trust boundary. Preserve the repository's existing read-only/local-first posture.

Requirements:

- no shell evaluation;
- no execution of target repository code;
- no package-manager scripts;
- no network;
- provider executable is an explicit local dependency;
- provider output is untrusted structured input until validated;
- repository source text returned by the provider is treated as data only;
- source text must never become prompt/runtime instructions;
- provider absolute root is not emitted;
- provider source bodies are not retained;
- external numeric IDs are not treated as stable lineage identity;
- provider rank is not authority;
- Context Engine cache/database is never opened directly by Context Integrity.

---

# 21. Performance and Scope Control

Keep Phase 7 synchronous.

Do not add async/concurrency merely because a subprocess is introduced.

Provider work is already bounded by:

- provider acquisition budget;
- provider's own safety limits;
- adapter output limit;
- adapter timeout;
- Context Integrity final byte budget.

Measure before adding concurrency.

Avoid large refactors of unrelated Phase 0–6 modules. Refactor only the shared contract-validation or candidate seams required to correctly support mixed candidates.

---

# 22. Acceptance Criteria

Phase 7 is complete only when all of the following are true:

1. Context Integrity defines a small, versioned `EvidenceProvider` contract.
2. Provider-specific transport is isolated from domain/compiler policy.
3. Context Engine schema-v1 `context` JSON is consumed through an adapter, not internal Rust/storage APIs.
4. Provider executable invocation is shell-free, bounded, timed, and sanitized.
5. Provider repository/root coherence is checked.
6. Git HEAD/dirty coherence is checked when available.
7. Every accepted provider candidate has a deterministic content SHA-256 and validated size.
8. Provider source bodies are discarded after normalization and never appear in stable output.
9. Provider code roles map through Context Integrity-owned kind/authority semantics.
10. Provider lifecycle is not inferred beyond the documented conservative rule.
11. Configuration schema v7 supports the new provider-backed contract kinds.
12. v1–v6 configuration behavior remains unchanged.
13. `CompilerCandidate` supports inventory and provider origins without a parallel compiler.
14. Final contract validation can validate the exact mixed candidate universe used by the compiler.
15. Public Phase 5 inventory-only validation behavior remains unchanged.
16. Contract exclusions/lifecycle/authority remain stronger than provider relevance.
17. Provider rank is only a lower-order relevance signal.
18. Required-set feasibility repair works across mixed candidates.
19. Byte budget counts unique inventory + provider files exactly once.
20. Valid provider incompleteness is surfaced separately from contract completeness.
21. Explicit provider failure does not silently downgrade to documentation-only compilation.
22. Inventory-only compile behavior remains semantically equivalent to Phase 6.
23. Compiled-context JSON v3 is deterministic and provenance-rich.
24. No absolute roots, source bodies, runtime timestamps, or raw provider stderr enter stable JSON.
25. Text output explains provider use/coverage without exposing source bodies.
26. Tests are offline and do not require a real Context Engine binary.
27. Optional real sibling integration smoke is recorded when available but is not mandatory.
28. `make check` passes.
29. `git diff --check` passes.
30. A Phase 7 implementation report maps delivered behavior to these criteria.
31. Documentation staleness is swept and current state advances only after verification.

---

# 23. Suggested Implementation Sequence

Use small checkpoints rather than implementing the whole integration at once.

## Step 1 — Baseline and domain vocabulary

- confirm actual HEAD;
- add SourceKind/config v7 gates;
- add generic provider descriptor/request/result models;
- unit-test invariants.

Checkpoint: all existing tests pass plus new model/config tests.

## Step 2 — Context Engine adapter

- implement safe executable resolution/invocation;
- parse/validate schema-v1 context envelope;
- verify repository/revision coherence;
- normalize role/path/content/relevance/coverage;
- discard bodies;
- add fake-executable/fixture tests.

Checkpoint: provider adapter fully testable without compiler changes.

## Step 3 — Mixed contract validation seam

- refactor Phase 5 evaluator so its public inventory-only wrapper remains unchanged;
- add explicit-source-universe validation for compiler use;
- regression-test old outputs.

Checkpoint: Phase 5 behavior unchanged.

## Step 4 — Compiler integration

- accept provider candidate batch;
- combine/dedupe candidate origins;
- retain provider relevance/provenance;
- add subordinate relevance tie-break;
- validate final mixed package;
- preserve feasibility repair.

Checkpoint: focused compiler tests pass.

## Step 5 — CLI + rendering

- add provider options;
- add provider error mapping;
- render text provider state;
- advance compiled JSON to v3;
- add golden/determinism/privacy tests.

Checkpoint: provider and inventory-only CLI scenarios pass.

## Step 6 — Verification and docs

- run focused tests;
- run full gate;
- optional real Context Engine smoke;
- update evidence contract/architecture/README/current-state/report;
- documentation staleness sweep;
- final diff inspection.

---

# 24. Verification Commands

Use the repository's actual tooling and adjust focused paths to match implemented test filenames.

Expected shape:

```bash
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 \
  uv run pytest \
  tests/test_evidence.py \
  tests/test_context_engine.py \
  tests/test_compiler.py \
  tests/test_contracts.py \
  tests/test_configuration.py \
  tests/test_cli.py -q

UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check

git diff --check
git status --short
```

If a real sibling provider smoke is run, keep it separate from the canonical gate and record the exact Context Engine commit/version used.

---

# 25. Implementation Report Requirements

Create:

```text
docs/implementation-reports/phase-7-implementation-report.md
```

Include:

- actual start/end HEAD;
- Context Engine commit/version observed for integration validation;
- provider contract/transport actually implemented;
- any deviations from this plan and why;
- configuration/schema changes;
- compiler/validation changes;
- provider safety/revision checks;
- output schema changes;
- test counts and exact commands;
- optional real-provider smoke evidence;
- documentation staleness sweep;
- known limitations;
- deferred Phase 8 work;
- explicit statement that provider evidence integration does not yet equal architectural-integrity evaluation.

Do not claim independent review or acceptance from implementation-session tests.

---

# 26. Known Phase 7 Limitations to Preserve Explicitly

Even after successful Phase 7 implementation:

- Context Engine candidates are a bounded ranked shortlist, not proof all relevant code was observed;
- Context Engine's current context surface is full-file UTF-8, not snippets/tokens;
- provider ranking is heuristic structural/lexical evidence, not semantic truth;
- Context Engine IDs are index-local and not lineage-stable;
- provider and Context Integrity observations are sequential, not an atomic filesystem snapshot;
- Context Integrity still does not verify claim truth;
- compilation completeness still does not mean integrity cleanliness;
- no architecture-policy evaluation exists until Phase 8;
- no shared persistence or cross-repository reasoning exists;
- no LLM/embedding intelligence exists;
- no source-body bundle is emitted by Context Integrity.

These limitations should be visible in current-state/evidence-contract documentation rather than hidden in implementation history.

---

# 27. Phase 8 Handoff Boundary

Phase 7 should leave Phase 8 with a stable descriptive-evidence seam, not unfinished policy mixed into the provider.

Phase 8 should be able to build on:

```text
EvidenceProvider descriptor/version
repository + revision coherence
provider evidence references
normalized code entities/candidates
provider coverage/incompleteness
existing Context Integrity claims/authority/lifecycle/integrity models
```

Phase 8 may then add the specific structural relation/impact capabilities needed to evaluate explicit architectural invariants.

Do not pre-implement Phase 8 judgments in Phase 7 merely because the provider already has graph/change features.
