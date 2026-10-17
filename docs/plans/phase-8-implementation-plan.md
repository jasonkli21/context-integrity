# Context Integrity — Phase 8 Detailed Implementation Plan

**Phase:** 8 — Architectural Integrity
**Status:** Ready for implementation
**Date:** 2026-10-16
**Repository:** `jasonkli21/context-integrity`
**Inspected default branch:** `main`
**Inspected Context Integrity HEAD:** `cdee5befa78ccac3bbc4825ad7e0a943e406596a` (`Fix Phase 7 independent review findings`)
**Related repository:** `jasonkli21/context-engine`
**Inspected Context Engine HEAD:** `ef44712858f02b34f1fd4b43201ad6f26bbc3cf2` (`fix: address phase 7 review findings`)
**Parent documents:** `docs/prd.md`, `docs/architecture.md`, `docs/current-state.md`, `AGENTS.md`, `docs/evidence-contract.md`
**Predecessor:** Phase 7 — Codebase Intelligence `EvidenceProvider` Integration
**Successor:** Phase 9 — Derived Context Revalidation

---

# 1. Phase Objective

Phase 8 turns the structural evidence seam established in Phase 7 into the first explicit **architectural-integrity** capability.

The goal is to let a repository declare narrow, deterministic architectural invariants owned by Context Integrity, obtain structural observations from a replaceable evidence provider, and produce explainable findings when observed code violates those invariants.

The core Phase 8 question is:

> **Can Context Integrity take an explicit architecture policy, bind it to repository-owned claim/provenance, compare it with revision-scoped structural evidence, and report deterministic, inspectable violations without pretending the evidence provider owns policy or that incomplete static evidence proves architecture compliance?**

The intended progression is:

```text
Phase 0–6
inventory + authority + lifecycle + claims + drift + contracts + compiler

Phase 7
Codebase Intelligence context candidates
  + revision/provenance boundary
  -> mixed task context

Phase 8
explicit architecture invariant
  + structural relation evidence
  + claim/policy provenance
  -> explainable architecture-integrity result

Phase 9
derived artifact dependencies
  + upstream revisions
  -> revalidation / invalidation
```

The key responsibility boundary remains:

```text
Context Engine
  observes syntax / entities / relations / analysis coverage

Context Integrity
  owns architectural intent, selectors, rule semantics,
  authority context, findings, and governance meaning
```

Phase 8 must **not** move architectural policy into Context Engine, import Rust internals, read its SQLite schema directly, or build a second code parser.

---

# 2. Alignment with Product Requirements and Architecture

The original PRD defines Phase 8 as:

> connect architecture claims/invariants to structural evidence; detect dependency/boundary violations; generate explainable findings.

The architecture already reserves:

- architecture policy and invariant representation for Context Integrity;
- structural code observation for `EvidenceProvider`;
- deterministic evaluation in the integrity layer;
- `IntegrityFinding` as the user-visible judgment;
- richer relation/impact evidence as a future consumer of the Phase 7 evidence boundary.

Phase 7 deliberately integrated only `context_candidates()` because no relation consumer existed yet. Phase 8 is the point where a real relation consumer exists, so the provider boundary may grow **only as far as this use case needs**.

The current Context Engine external graph surface is sufficient for a first version:

```bash
ctx graph PATH --format json
```

Its schema-v1 output exposes:

- repository root and Git metadata;
- entities for repository, files, and symbols;
- structural relations;
- relation kinds: `contains`, `imports`, `references`;
- resolved or unresolved targets;
- resolution metadata;
- evidence path/range/language/derivation;
- per-file symbol and relation-analysis status;
- unresolved and unsupported-candidate counts;
- diagnostics and scan warnings.

The same surface explicitly says IDs are index-local and not lineage identifiers. Context Integrity therefore must normalize relation evidence into stable descriptors and must never persist or expose provider numeric IDs as durable identity.

## 2.1 Important limitation from the current Context Engine

Current structural evidence is intentionally best effort:

- imports remain unresolved in important cases;
- reference target resolution is conservative and largely same-file;
- no compiler/type/dispatch semantics are claimed;
- graph edges are syntactic evidence, not proof of semantic dependency;
- incomplete relation analysis is explicit.

Therefore Phase 8 must **not** interpret “no matching edge found” as proof that an architecture invariant holds in general.

The first Phase 8 invariant should be **violation-positive**:

> An observed relation that matches a prohibited dependency is enough to produce a finding.

No observed relation means:

- no violation was observed in the acquired evidence;
- not “the architecture is proven compliant.”

This distinction must be visible in model names, rendering, documentation, and tests.

---

# 3. Current Delivered Baseline

Implementation starts from the repository as it exists at the inspected HEAD, not from an older plan.

## 3.1 Context Integrity baseline

At `cdee5befa78ccac3bbc4825ad7e0a943e406596a`:

- Phases 0–7 are implemented.
- Phase 7 review findings have been addressed.
- Canonical offline verification records **850 tests**.
- Repository configuration is strict and versioned through schema v7.
- Explicit claims exist and retain `unverified` validity.
- Phase 4 integrity checks are deterministic and produce `IntegrityOverview`.
- Phase 5 contracts and Phase 6/7 compilation remain separate from integrity evaluation.
- `check` currently runs:
  - canonical instruction checks;
  - current-state navigation/delivery checks;
  - explicit document dependency change-review checks.
- `IntegrityEvidence` currently represents path/source-revision evidence only.
- Integrity JSON is a dedicated schema-v1 surface.
- Generic Phase 7 evidence contract v1 supports:
  - context-candidate requests;
  - provider descriptors;
  - snapshot metadata;
  - typed coverage;
  - provider state;
  - normalized body-free compiler candidates.
- `ContextEngineProvider` already owns bounded, sanitized subprocess/JSON handling.
- Provider failures use a distinct typed failure category and CLI exit 7.
- Stable provider output excludes:
  - source bodies;
  - absolute roots;
  - raw stderr;
  - index-local IDs.

`docs/current-state.md` explicitly says:

```text
Phase 8 architectural integrity follows a separately authorized plan;
structural evidence remains descriptive and Context Integrity owns its policy.
```

## 3.2 Context Engine baseline

At `ef44712858f02b34f1fd4b43201ad6f26bbc3cf2`:

- graph/query behavior is externally versioned with schema-v1 JSON;
- `graph`, `deps`, `callers`, and `related` exist;
- entity IDs and relation IDs are index-local;
- entities expose stable descriptive fields such as path and symbol qualified name;
- relation evidence exposes:
  - kind;
  - source;
  - resolved/unresolved target;
  - resolution;
  - syntax metadata;
  - source path/range;
  - language;
  - derivation;
- relation kinds are currently:
  - `contains`;
  - `imports`;
  - `references`;
- derivations identify parser/source of the relation;
- analysis incompleteness is reported per file;
- current-state analysis can use the validated external cache;
- no architecture-policy behavior exists.

Context Integrity should consume the stable JSON adapter surface, not internal Rust types.

---

# 4. Starting-State Workflow

Before editing:

```bash
git status --short
git rev-parse HEAD
git log -10 --oneline
```

Read in this order:

1. `AGENTS.md`
2. `docs/current-state.md`
3. this Phase 8 plan
4. `docs/architecture.md`
5. `docs/evidence-contract.md`
6. current:
   - `models.py`
   - `configuration.py`
   - `claims.py`
   - `evidence.py`
   - `context_engine.py`
   - `integrity.py`
   - `rendering.py`
   - `cli.py`
7. relevant Phase 7 implementation and review-fix reports only where needed
8. focused tests
9. `docs/prd.md` for roadmap/product-scope confirmation

For the sibling Context Engine, inspect only the external behavior required by the adapter:

1. `docs/current-state.md`
2. `docs/integrations/context-integrity.md`
3. `src/cli.rs`
4. graph JSON adapter DTOs
5. relation kind/resolution/derivation vocabulary

If either repository has advanced beyond the inspected commits:

- inspect the newer state;
- preserve accepted newer work;
- reconcile this plan against current interfaces;
- do not reset to the reference commits;
- do not modify Context Engine unless explicitly required and authorized.

---

# 5. Core User Journey

A repository declares an explicit architectural claim and a deterministic rule.

Illustrative schema-v8 configuration:

```toml
schema_version = 8

[[claims]]
id = "application-storage-boundary"
claim_type = "architecture_invariant"
subject = "application"
predicate = "must_not_depend_on"
value = "storage_adapter"
depends_on = ["docs/architecture.md"]

[[architecture_invariants]]
id = "application-storage-boundary"
claim_id = "application-storage-boundary"
rule = "forbid_relation"
relation_kinds = ["imports", "references"]

source_path_prefixes = ["src/application/"]

target_path_prefixes = ["src/storage/adapters/"]
target_names = ["DynamoTripStore"]
```

The user runs:

```bash
uv run context-integrity check . \
  --evidence-provider context-engine \
  --format text
```

Conceptual flow:

```text
inventory repository + load exact config revision
  -> run existing deterministic Phase 4 checks
  -> resolve configured architecture invariants
  -> resolve linked explicit claims
  -> request structural graph evidence
  -> validate provider root/revision/coherence
  -> normalize index-local graph DTOs into stable entity/relation descriptors
  -> evaluate Context Integrity-owned selectors/rules
  -> create deterministic findings for observed prohibited edges
  -> preserve claim validity as unverified
  -> report structural coverage/incompleteness separately
  -> render integrity JSON/text with explainable policy + evidence
```

Example text finding:

```text
HIGH — architecture_forbidden_relation
Invariant: application-storage-boundary
Claim: application-storage-boundary

Observed:
  src/application/travel_service.py
    --imports-->
  DynamoTripStore [unresolved provider target name]

Policy:
  source prefix: src/application/
  target name: DynamoTripStore
  relation kinds: imports, references

Evidence:
  provider: context-engine 0.1.0
  revision: <HEAD or current observation metadata>
  path: src/application/travel_service.py
  range: ...
  derivation: python_import_syntax

Note:
  This is an observed structural violation.
  Absence of other findings does not prove architecture compliance.
```

A provider warning or incomplete graph must remain visible and must not be transformed into a false “pass.”

---

# 6. Product Boundary

## 6.1 In scope

Phase 8 includes:

- strict repository configuration schema v8;
- explicit architecture invariant specs;
- required linkage from each invariant to an explicit configured claim;
- deterministic selector semantics for source and target structural entities;
- first invariant rule: `forbid_relation`;
- deterministic relation-kind filtering;
- stable structural entity and relation evidence models;
- a relation-evidence provider protocol/seam that coexists with Phase 7 context-candidate providers;
- Context Engine `ctx graph --format json` adapter support;
- reuse/refactoring of the existing safe bounded subprocess runner where appropriate;
- provider graph-envelope validation;
- repository and Git observation coherence checks;
- removal of provider index-local IDs at the adapter boundary;
- structural coverage/incompleteness normalization;
- architecture-invariant evaluation in the integrity layer;
- deterministic, explainable architecture findings;
- integrity JSON evolution to v2 when architecture data is present;
- backwards-compatible existing Phase 4 checking;
- CLI provider options for `check`;
- focused tests for:
  - schema v8;
  - relation normalization;
  - selector semantics;
  - false-positive resistance;
  - deterministic finding IDs;
  - incomplete provider evidence;
  - provider failure handling;
  - legacy regression;
- a durable architecture-integrity contract document;
- current-state/README/architecture/navigation updates where actual source-of-truth behavior changes;
- a Phase 8 implementation report.

## 6.2 Explicitly out of scope

Do **not** implement:

- general semantic contradiction detection;
- LLM-assisted architecture reasoning;
- claim truth verification or mutation of claim validity;
- “architecture clean/compliant” certification from absent edges;
- compiler/type-checker/dispatch semantics;
- new code parsing inside Context Integrity;
- direct Context Engine SQLite access;
- importing Context Engine Rust modules;
- shared storage;
- HTTP/MCP/FFI transport;
- a provider daemon;
- network calls;
- cross-repository architecture integrity;
- derived-context invalidation/revalidation (Phase 9);
- CI failure thresholds, waivers, ownership, or governance (Phase 11);
- automatic architecture repair;
- inferred architecture policy from prose;
- task-context compiler gating on architecture findings unless separately authorized;
- persistence of graph evidence;
- arbitrary glob/regex selector DSL;
- generalized positive “must have dependency” rules whose correctness depends on proving absence;
- broad impact/change-policy integration merely because Context Engine exposes it.

---

# 7. Configuration Schema v8

Introduce:

```text
schema_version = 8
```

Schemas v1–v7 must preserve their accepted behavior.

Add one new top-level key:

```toml
[[architecture_invariants]]
...
```

Earlier schema versions must reject it.

## 7.1 Architecture invariant shape

Recommended conceptual model:

```text
ArchitectureInvariantSpec
- id
- claim_id
- rule
- relation_kinds[]
- source_selector
- target_selector
```

First supported `rule`:

```text
forbid_relation
```

The invariant means:

> If an observed structural relation matches the source selector, relation kind, and target selector, emit an architecture violation finding.

## 7.2 Required claim linkage

Every invariant must reference exactly one configured explicit claim.

Requirements:

- `claim_id` must exist in `RepositoryConfig.claims`;
- referenced claim must use:
  - `claim_type = "architecture_invariant"`;
- referenced claim predicate must be compatible with the rule:
  - `forbid_relation` requires `predicate = "must_not_depend_on"`;
- one claim may back one or more technical selectors only if the mapping is deliberate and documented;
- duplicate invariant IDs are rejected;
- invariant ID and claim ID may be identical and should normally be identical.

The selector is executable policy. The claim supplies human/domain intent and provenance. Do not parse selectors out of free-form claim text.

Claim validity remains `unverified`. Architecture evaluation does not rewrite it.

## 7.3 Selector vocabulary

Keep the first selector language intentionally small.

Recommended fields:

```text
source_paths[]
source_path_prefixes[]
source_symbols[]

target_paths[]
target_path_prefixes[]
target_symbols[]
target_names[]
```

At least one source selector and one target selector must be present.

Semantics:

- `*_paths`: exact normalized repository-relative path match;
- `*_path_prefixes`: literal normalized directory prefix match;
- `*_symbols`: exact provider-normalized qualified symbol name match;
- `target_names`: exact provider target name match for unresolved targets.

No regexes or arbitrary globs in Phase 8.

### Prefix validation

A path prefix:

- is repository-relative;
- uses `/`;
- has no `..`, backslash, drive/colon, NUL, or empty segment;
- ends in `/`;
- never matches a sibling lexical prefix accidentally.

Example:

```text
src/application/
```

matches:

```text
src/application/service.py
```

but not:

```text
src/application_old/service.py
```

## 7.4 Relation kinds

Initial allowed policy kinds:

```text
imports
references
```

`contains` is provider structural bookkeeping and should not be accepted as a dependency-boundary rule in Phase 8.

Unknown relation kinds fail configuration or provider normalization closed, depending on origin.

## 7.5 Strict version behavior

Requirements:

- central supported-version vocabulary advances through v8;
- direct `RepositoryConfig(...)` construction enforces the same gate as TOML parsing;
- schemas v1–v7 reject architecture-invariant config;
- v8 retains all v7 semantics;
- no implicit schema upgrade;
- unknown invariant keys fail closed;
- host-specific executable paths remain runtime options, not repository config;
- no provider-specific IDs are embedded in architecture policy.

---

# 8. Architecture Policy Domain Model

Add narrow domain types rather than raw dicts.

Recommended:

```text
ArchitectureRuleKind
- FORBID_RELATION

ArchitectureEntitySelector
- paths
- path_prefixes
- symbols
- unresolved_names  # target-only in Phase 8

ArchitectureInvariantSpec
- id
- claim_id
- rule
- relation_kinds
- source
- target

ArchitectureEvaluationStatus
- NO_VIOLATION_OBSERVED
- VIOLATED
- INCONCLUSIVE

ArchitectureInvariantResult
- invariant
- claim_id
- status
- matched_relation_count
- finding_ids
- evidence_complete
- notes/warnings
```

Exact naming may vary.

Important semantics:

- `NO_VIOLATION_OBSERVED` is **not** named `COMPLIANT`, `PASS`, or `SATISFIED`;
- incomplete provider evidence can make a result `INCONCLUSIVE`;
- a directly observed forbidden relation remains a violation even if unrelated graph coverage is incomplete, provided the matching relation itself is valid and its snapshot is coherent;
- an invariant with no matching source entities may be `INCONCLUSIVE` rather than silently clean;
- result ordering is deterministic by invariant ID.

Do not build a generic policy-engine framework around one rule type.

---

# 9. Evidence Contract Evolution

Phase 7 evidence contract v1 must remain valid.

Do not break replacement context-candidate providers merely because Phase 8 needs relations.

## 9.1 Protocol split

Prefer two small protocols over one mandatory mega-interface:

```text
EvidenceProvider
- context_candidates(...)

RelationEvidenceProvider
- relations(...)
```

The Context Engine adapter may implement both.

A provider used for `check --evidence-provider ...` must advertise relation capability.

## 9.2 Descriptor compatibility

Evolve descriptor semantics carefully.

Recommended capability vocabulary:

```text
context_candidates
change_context
relations
```

Requirements:

- existing v1 context-candidate descriptors remain accepted for Phase 7 compiler use;
- Phase 8 relation batches require the relation-capable contract/version;
- capability order is canonical/deterministic;
- unsupported capability combinations fail closed;
- compiler code checks for context-candidate capability, not for the absence of newer capabilities.

A simple evidence contract v2 is reasonable if relation batch semantics are meaningfully new.

If the implementation can preserve `contract_version = 1` and add relation-specific versioning without ambiguity, that is acceptable, but the version boundary must be explicit and documented. Do not silently widen a stable v1 contract with incompatible requirements.

## 9.3 Relation request

Conceptually:

```text
EvidenceRelationRequest
- repository_root       # runtime-only
- repository_ref
```

No task is required.

Do not reuse `EvidenceContextRequest` just to avoid a new type; it has task/budget/change semantics that do not belong to graph acquisition.

## 9.4 Stable entity descriptor

Normalize provider entities to a body-free, index-ID-free representation.

Conceptually:

```text
EvidenceEntity
- kind: file | symbol
- path
- symbol_name?
- qualified_name?
- symbol_kind?
- language?
- range?
```

Requirements:

- repository-relative normalized path;
- no provider numeric ID;
- bounded strings;
- validated source ranges;
- exact symbol identity is descriptive, not lineage identity.

## 9.5 Relation target

Conceptually:

```text
EvidenceRelationTarget
- resolved_entity?
- unresolved_name?
```

Exactly one target form is present.

Unresolved target names are valid evidence, but selectors must opt into them through `target_names`.

Do not fabricate a target path from an unresolved import name.

## 9.6 Stable relation evidence

Conceptually:

```text
EvidenceRelation
- kind
- source
- target
- resolution
- evidence_path
- evidence_range?
- language?
- derivation
```

Provider numeric relation IDs are decode-local only and disappear after normalization.

## 9.7 Coverage

Normalize enough provider state to explain uncertainty.

Recommended:

```text
EvidenceRelationFileState
- path
- symbol_status
- relation_status
- unresolved_count
- unsupported_candidate_count

EvidenceRelationCoverage
- files[]
- summary counts
- incomplete
- warnings[]
```

Do not expose raw provider diagnostic prose if it can contain arbitrary repository content. Normalize counts/statuses and sanitized warning categories.

---

# 10. Context Engine Graph Adapter

Extend `ContextEngineProvider` behind the relation protocol.

Expected invocation:

```text
ctx graph ROOT --format json
```

Use the same safety principles as Phase 7:

- argv sequence only;
- `shell=False`;
- closed stdin;
- finite timeout;
- bounded stdout/stderr;
- process cleanup;
- sanitized errors;
- no network;
- no auto-install;
- no raw stderr in stable output.

Prefer refactoring the existing bounded process execution into a shared private helper in `context_engine.py` rather than duplicating process management.

Do not create a generic subprocess framework outside the adapter unless the current code clearly warrants it.

## 10.1 Envelope validation

Require:

```text
schema_version == 1
command == "graph"
```

Validate:

- root;
- Git metadata;
- entity array;
- relation array;
- file status arrays;
- relation-file status arrays;
- supported relation vocabulary;
- supported resolution vocabulary;
- source ranges;
- path safety;
- ID uniqueness inside the response;
- every referenced entity ID exists;
- relation source/target types are structurally valid.

Provider-local IDs may be used while decoding only.

## 10.2 Repository/snapshot coherence

Reuse Phase 7 principles:

- provider root must resolve to the requested repository root;
- known Git HEAD must match the Context Integrity observation;
- known dirty state must match;
- mismatch is provider failure, not a warning;
- unknown snapshot metadata remains explicit;
- no absolute root enters stable output.

Unlike Phase 7 context candidates, graph relations do not currently carry per-file content hashes.

Therefore documentation and model names must not claim atomic or content-hash-bound graph snapshots.

A dirty or sequential observation may still produce an observed violation, but the provider state must preserve that it is a current structural observation rather than immutable proof.

## 10.3 Relation normalization

Only normalize evidence useful to Phase 8.

Required:

- file and symbol entities;
- `imports`;
- `references`;
- resolved targets;
- unresolved target names;
- evidence path/range;
- resolution;
- language;
- derivation;
- per-file analysis coverage.

Ignore repository containment relations for architecture rule evaluation.

Preserve unknown/unsupported upstream states as coverage, not invented facts.

## 10.4 Index-local IDs

A hard invariant:

> No Context Engine entity or relation numeric ID may appear in a stable Context Integrity model, JSON surface, finding ID, config, golden, report, or policy.

Tests must prove this.

---

# 11. Selector Matching Semantics

Keep matching deterministic and inspectable.

For each normalized relation:

```text
source selector
AND relation kind
AND target selector
```

must all match.

Within a selector dimension, configured values use OR semantics.

Across dimensions that are present, use OR across selector families for the same side, not accidental AND.

Example:

```text
target_path_prefixes = ["src/storage/adapters/"]
target_names = ["DynamoTripStore"]
```

means:

```text
target path has prefix src/storage/adapters/
OR
unresolved target name == DynamoTripStore
```

This is intentional because unresolved targets do not have stable target paths.

Document this clearly.

## 11.1 Source matching

A relation source can match by:

- exact source path;
- source path prefix;
- exact source qualified symbol name.

If the provider relation source is a symbol, its owning path is also available for path selectors.

## 11.2 Target matching

Resolved targets can match:

- target path;
- target path prefix;
- target qualified symbol.

Unresolved targets can match only:

- `target_names`.

Never map unresolved names to paths or symbols heuristically.

## 11.3 Duplicate evidence

The provider may expose multiple occurrences of the same architectural dependency.

Do not produce noisy duplicate findings solely because a relation appears at multiple syntax occurrences if the user-level violation is the same architectural edge.

Recommended finding grouping key:

```text
invariant id
+ relation kind
+ stable source descriptor
+ stable target descriptor
```

Evidence occurrences/ranges can be retained in sorted form under one finding, with a bounded count if necessary.

Do not erase genuinely distinct source entities or target entities.

---

# 12. Claim and Policy Integration

Phase 8 connects policy to claims without pretending to verify claim truth.

For every invariant:

1. resolve its configured `claim_id`;
2. confirm claim type/predicate compatibility;
3. include claim identity in the result/finding;
4. retain claim provenance/dependencies for explanation;
5. do not mutate:
   - `ClaimValidity`;
   - source lifecycle;
   - source authority;
   - supersession.

If claim provenance is incomplete:

- continue evaluating the explicit repository policy;
- surface a deterministic architecture-policy warning/result note;
- do not silently treat the claim as independently verified.

Rationale:

- repository configuration is the executable declaration used by the tool;
- the linked claim provides human intent/provenance;
- missing claim dependencies are an integrity concern, but should not automatically disable an explicit safety boundary.

This distinction should be tested.

---

# 13. Architectural Integrity Evaluation

Add architecture evaluation to the integrity layer, not to the adapter.

Conceptually:

```text
architecture_findings(
    manifest,
    claims_overview,
    relation_batch,
) -> architecture results + findings + warnings
```

The provider supplies facts. `integrity.py` supplies judgment.

## 13.1 Rule: `forbid_relation`

For each invariant:

1. gather normalized relations matching the source selector;
2. keep only configured relation kinds;
3. match target selector;
4. group equivalent stable edges;
5. emit one HIGH finding per distinct prohibited edge;
6. produce invariant status:
   - `VIOLATED` if one or more findings;
   - `INCONCLUSIVE` if provider evidence is materially incomplete for the selector and no violation is observed;
   - `NO_VIOLATION_OBSERVED` otherwise.

This is **not** a generic architecture-compliance proof.

## 13.2 Severity

Architecture boundary violations are HIGH in Phase 8.

Do not add repository-configurable severity yet; severity/governance policy is a later concern.

Evidence incompleteness should be a warning/result status, not a fabricated HIGH violation.

## 13.3 Finding identity

Finding IDs must be deterministic and independent of prose, provider numeric IDs, ordering, or runtime paths.

Include stable semantic identity such as:

```text
rule family/version
invariant id
claim id
relation kind
source stable descriptor
target stable descriptor
```

Do not include:

- message text;
- absolute root;
- index-local IDs;
- timestamps;
- raw provider score;
- provider emission order.

## 13.4 Finding evidence

A Phase 8 finding should be able to answer:

- Which invariant was violated?
- Which claim grounds it?
- Which source entity produced the edge?
- Which target entity/name did it point to?
- What relation kind was observed?
- Where was the syntax evidence?
- What provider/version/derivation produced the fact?
- What repository/Git observation did it describe?
- Was graph coverage incomplete?

Extend evidence models deliberately; do not overload the old `path + derivation` structure with opaque encoded strings.

---

# 14. Integrity Overview and JSON v2

Current integrity JSON is schema v1.

Phase 8 should evolve the integrity surface deliberately.

Recommended:

```text
integrity_schema_version = 2
```

when using the new model globally.

v2 should retain all v1 fields and add structured architecture state.

Conceptually:

```json
{
  "integrity_schema_version": 2,
  "repository": {},
  "config_sha256": "...",
  "change_set": {},
  "architecture": {
    "evaluation_status": "evaluated",
    "provider": {},
    "coverage": {},
    "invariants": []
  },
  "findings": [],
  "warnings": []
}
```

Requirements:

- explicit projectors, not `asdict()` over provider/domain dataclasses;
- no source bodies;
- no absolute roots;
- no index-local IDs;
- no raw stderr;
- no runtime timestamp in stable JSON;
- deterministic sorting;
- safe/bounded strings;
- existing Phase 4 finding information remains represented;
- architecture-specific finding evidence is typed rather than encoded in prose.

If no architecture invariants are configured and no provider is requested, it is acceptable for JSON v2 to be the new stable integrity schema as long as regression is intentional, documented, and golden-tested.

Alternatively, preserve v1 for legacy-only checks and emit v2 only when architecture state is present. Choose one approach deliberately and document it; do not produce ambiguous schema semantics.

---

# 15. CLI Surface

Extend existing `check` rather than creating a disconnected architecture checker.

Recommended options:

```text
--evidence-provider context-engine
--context-engine-bin PATH
```

No task or evidence budget is required for `ctx graph`.

Requirements:

- no provider option + schemas v1–v7 => existing Phase 4 behavior remains semantically unchanged;
- provider-specific executable override is runtime-only;
- only recognized relation-capable providers are accepted;
- provider errors use the existing provider error category/exit 7;
- integrity findings still do **not** fail the command;
- CI fail thresholds remain deferred;
- `--output`, text, and JSON continue to work;
- CLI only orchestrates;
- provider JSON parsing and policy logic stay outside CLI.

## 15.1 Schema-v8 config without provider

If architecture invariants are configured but no relation provider is selected:

- run existing Phase 4 checks;
- mark architecture evaluation `not_evaluated` or `inconclusive`;
- emit a clear deterministic warning;
- do not pretend the architecture invariant was checked;
- do not fail merely because the user omitted an optional runtime provider.

This keeps local legacy behavior usable while making the gap visible.

---

# 16. Error Model

Reuse `EvidenceProviderError`/provider exit 7 for unsafe or incompatible external evidence.

Add typed codes where useful:

- relation capability missing;
- graph process unavailable;
- graph timeout;
- graph output too large;
- malformed graph JSON;
- unsupported graph schema;
- wrong command;
- repository mismatch;
- Git revision mismatch;
- dirty-state mismatch;
- unsafe entity path;
- invalid source range;
- duplicate entity ID;
- dangling entity reference;
- duplicate/conflicting normalized relation;
- unsupported relation kind/resolution/derivation;
- malformed coverage.

Configuration errors remain exit 6.

Do not include arbitrary provider/source text in stable error messages.

---

# 17. Testing Strategy

Testing should be focused, deterministic, and offline.

The normal suite must not require the real Context Engine binary.

## 17.1 Configuration v8 tests

Cover:

- schemas v1–v7 unchanged;
- v7 rejects `architecture_invariants`;
- v8 accepts a valid invariant;
- direct `RepositoryConfig` enforces v8-only behavior;
- duplicate invariant ID rejected;
- missing claim rejected;
- wrong claim type rejected;
- incompatible predicate/rule rejected;
- no source selector rejected;
- no target selector rejected;
- unsafe prefix rejected;
- `contains` rejected as a Phase 8 dependency relation kind;
- unknown keys rejected;
- no silent upgrade.

## 17.2 Relation evidence model tests

Cover:

- stable file entity;
- stable symbol entity;
- resolved target;
- unresolved target;
- range invariants;
- provider/index IDs cannot survive normalization;
- deterministic ordering;
- malformed paths rejected;
- malformed/duplicate relations rejected;
- bounded identifiers/strings;
- coverage state validation.

## 17.3 Context Engine graph adapter tests

Use fixture JSON and/or a fake executable.

Cover at least:

- valid graph schema-v1 response;
- wrong schema version;
- wrong command;
- malformed JSON;
- missing required arrays/fields;
- duplicate entity ID;
- dangling relation source;
- dangling resolved target;
- unsafe path;
- malformed range;
- unsupported relation kind;
- repository root mismatch;
- HEAD mismatch;
- dirty-state mismatch;
- incomplete relation-file status normalization;
- unresolved target retained without fabricated path;
- raw IDs absent from normalized batch;
- sanitized process errors;
- timeout;
- output ceiling;
- executable override;
- no shell interpretation.

## 17.4 Selector tests

Prove:

- exact path matching;
- path-prefix segment safety;
- symbol matching;
- unresolved-name matching;
- unresolved names do not match path selectors;
- resolved paths do not accidentally match unrelated lexical siblings;
- relation-kind filtering;
- OR semantics across configured selector families;
- provider emission order does not affect results.

## 17.5 Architecture integrity tests

Synthetic cases should prove:

1. observed prohibited import produces HIGH finding;
2. observed prohibited reference produces HIGH finding;
3. unrelated relation does not produce finding;
4. multiple syntax occurrences of the same stable edge do not create noisy duplicate findings;
5. distinct prohibited edges remain distinct;
6. unresolved target can violate only through explicit `target_names`;
7. no target-path inference is performed for unresolved target names;
8. no observed violation + complete relevant evidence yields `no_violation_observed`, not `compliant`;
9. no observed violation + incomplete relevant evidence yields `inconclusive`;
10. an observed violation remains a violation even if unrelated coverage is incomplete;
11. claim validity remains `unverified`;
12. incomplete claim provenance is surfaced without silently disabling the explicit rule;
13. finding IDs are stable under provider order changes;
14. finding IDs contain no provider numeric IDs;
15. old Phase 4 findings remain unchanged semantically;
16. architecture findings do not mutate lifecycle/authority/supersession;
17. `check` without provider does not silently claim evaluation.

## 17.6 Rendering/golden tests

Add intentional integrity-v2 golden coverage.

Prove:

- stable JSON;
- no absolute root;
- no source bodies;
- no raw stderr;
- no index-local IDs;
- provider/version/derivation visible;
- claim/invariant identity visible;
- coverage visible;
- text clearly distinguishes:
  - violation;
  - no violation observed;
  - inconclusive/not evaluated.

## 17.7 CLI tests

Cover:

- `check --evidence-provider context-engine`;
- executable override;
- missing executable => exit 7;
- malformed provider output => exit 7;
- architecture findings still exit 0;
- output file behavior;
- JSON/text;
- no-provider legacy path;
- schema-v8 invariant without provider is visibly not evaluated.

## 17.8 Full verification

Canonical end-of-phase gate:

```bash
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check
git diff --check
git status --short
```

If a real sibling `ctx` binary is already available locally, one optional smoke may exercise:

```bash
context-integrity check <fixture> \
  --evidence-provider context-engine \
  --context-engine-bin <existing-local-ctx> \
  --format json
```

Do not install/build/download Context Engine merely to satisfy the normal test suite.

---

# 18. Documentation Deliverables

Update documentation only where source-of-truth behavior actually changes.

Required:

- `docs/plans/phase-8-implementation-plan.md`
- `docs/implementation-reports/phase-8-implementation-report.md`
- `docs/current-state.md` after verification
- `docs/architecture.md`
- `docs/evidence-contract.md` if the generic evidence contract evolves
- a focused durable document such as:
  - `docs/architecture-integrity-contract.md`
- README/docs navigation where needed

The durable architecture-integrity document should specify:

- config schema v8 invariant shape;
- claim linkage;
- selector semantics;
- relation evidence semantics;
- provider normalization;
- finding semantics;
- “no violation observed” vs compliance;
- coverage/inconclusive behavior;
- privacy/determinism/versioning guarantees.

Do not rewrite historical Phase 0–7 plans to match later reality.

---

# 19. Documentation Staleness Sweep

At the end of implementation, search current canonical docs/code for stale statements such as:

```text
Phase 7 is next
relation evidence deferred
architectural integrity not delivered
EvidenceProvider only supports context candidates
configuration supported through v7
integrity schema v1 only
no structural evidence consumer
```

Use targeted `rg` searches, not broad documentation rewriting.

Record material corrections in the implementation report.

---

# 20. Implementation Order

Recommended sequence:

## Step 1 — Reconfirm current state

- inspect HEAD;
- inspect Phase 7 evidence boundary;
- inspect current Context Engine graph JSON;
- record any upstream drift.

## Step 2 — Add schema-v8 domain/config models

- selector type;
- invariant type;
- validation;
- claim linkage;
- strict version gating;
- focused config tests.

## Step 3 — Add structural evidence domain types

- stable entity descriptor;
- relation target;
- relation;
- relation coverage;
- request/batch/protocol;
- generic invariants.

## Step 4 — Extend Context Engine adapter

- reuse bounded subprocess helper;
- parse `ctx graph --format json`;
- validate envelope/root/revision;
- normalize IDs away;
- normalize relations/coverage;
- fixture tests.

## Step 5 — Add selector evaluator

- exact path;
- prefix;
- symbol;
- unresolved target name;
- deterministic grouping.

## Step 6 — Add architecture integrity rule

- resolve claim;
- evaluate `forbid_relation`;
- build results;
- build HIGH findings;
- stable IDs;
- coverage-aware status.

## Step 7 — Integrate with `IntegrityOverview`

- preserve Phase 4 checks;
- merge architecture findings;
- add provider/architecture state;
- no mutation of claims/authority/lifecycle.

## Step 8 — Evolve rendering

- integrity JSON v2;
- explicit projectors;
- text explanation;
- privacy/determinism golden tests.

## Step 9 — Extend CLI

- provider options on `check`;
- error exit mapping;
- no-provider behavior.

## Step 10 — Documentation + report

- architecture/evidence/contract docs;
- current-state after verification;
- implementation report;
- staleness sweep.

## Step 11 — Verification

- focused tests during implementation;
- full offline `make check`;
- `git diff --check`;
- optional real-provider smoke if locally available.

---

# 21. Acceptance Criteria

Phase 8 is implemented only if all of the following are true.

## 21.1 Policy/config

- schema v8 is strict and backward-compatible;
- explicit architectural invariants are repository-defined;
- every invariant is linked to an explicit architecture claim;
- selectors are deterministic and narrowly specified;
- no free-form prose is parsed into executable policy.

## 21.2 Evidence boundary

- structural evidence comes through a replaceable relation-provider seam;
- Context Engine adapter uses the external JSON/CLI contract only;
- provider numeric IDs are eliminated before domain use;
- relation evidence retains provider/version/revision/path/range/derivation;
- coverage/incompleteness is explicit;
- no source body is retained.

## 21.3 Integrity semantics

- observed prohibited relations produce deterministic HIGH findings;
- no observed edge is not called “compliant”;
- incomplete evidence produces visible uncertainty;
- claim validity is unchanged;
- Context Integrity owns policy judgment;
- provider ranking or graph implementation never becomes authority.

## 21.4 Compatibility

- Phase 4 check semantics remain intact;
- Phase 7 compilation remains intact;
- old config schemas remain valid;
- provider/compiler regressions pass;
- no new network/database/service dependency is introduced.

## 21.5 Output safety

- stable JSON is deterministic;
- no absolute roots;
- no raw stderr;
- no source bodies;
- no index-local IDs;
- no timestamps in canonical output;
- finding IDs are stable and prose-independent.

## 21.6 Verification

- focused Phase 8 tests pass;
- full offline `make check` passes;
- Ruff passes;
- `git diff --check` passes;
- implementation report records exact verification;
- current-state is updated only after verification.

---

# 22. Review Hotspots

The independent reviewer should pay particular attention to:

1. false “architecture clean” claims from incomplete graph evidence;
2. accidental policy leakage into Context Engine adapter code;
3. provider index-local IDs entering durable identity;
4. unsafe path-prefix matching;
5. unresolved target names being heuristically converted into paths;
6. duplicate-edge grouping hiding distinct violations;
7. claim linkage that appears authoritative but bypasses provenance;
8. schema-v8 behavior leaking into v1–v7;
9. relation-provider changes breaking Phase 7 replacement providers;
10. `asdict()` or broad serialization exposing internal provider fields;
11. graph root/HEAD/dirty mismatches being downgraded to warnings;
12. source-body/raw-stderr/privacy leaks;
13. unstable finding IDs;
14. tests that mock away the real selector/relation semantics;
15. documentation claiming more static-analysis strength than Context Engine actually provides.

---

# 23. Deliberate Deferrals to Phase 9+

Phase 8 should leave these explicit:

- derived-summary dependency invalidation;
- context revalidation after upstream revision changes;
- general contradiction engine;
- cross-repository rules;
- semantic architecture extraction;
- must-depend proofs that require exhaustive analysis;
- LLM judgment;
- learned/inferred policy;
- CI enforcement;
- waivers;
- organization policy ownership;
- persistence/history of findings;
- dashboards/trends;
- automatic fixes.

The phase should end with a strong, narrow primitive:

> **“This explicit architecture boundary says relation X must not exist. The current revision-scoped structural evidence shows relation X here, and this is why Context Integrity reports a violation.”**

That is enough to make architectural integrity real without overstating the capabilities of either project.
