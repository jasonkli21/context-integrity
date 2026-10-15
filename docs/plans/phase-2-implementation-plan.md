# Context Integrity — Phase 2 Detailed Implementation Plan

**Phase:** 2 — Lifecycle and Supersession  
**Status:** Ready for implementation  
**Date:** 2026-10-14  
**Repository baseline:** `36d150af6cf67b8bab41c528b4304fa83da51309` (`fix phase 1 review findings`)  
**Parent documents:** `docs/prd.md`, `docs/architecture.md`  
**Predecessor:** Phase 1 — Authority and Source-of-Truth Model  
**Related project:** Codebase / Context Intelligence Engine, still intentionally unintegrated in this phase

---

# 1. Phase Objective

Phase 2 introduces explicit lifecycle state and explicit directional supersession on top of the reviewed Phase 1 authority layer.

The phase should let Context Integrity answer:

> **What is the lifecycle state of this context source, what explicit evidence produced that state, and does another source explicitly supersede it?**

Phase 1 already answers:

> **For this kind of question, which source roles are preferred and which eligible observed sources occupy the highest observed authority tier?**

Phase 2 extends that answer by making lifecycle eligibility explicit.

Example:

```text
docs/adr/0008-storage.md
  kind: decision_record
  authority class: decision
  lifecycle: superseded
  superseded_by: docs/adr/0019-storage-v2.md
  reason: "ADR-0019 replaced ADR-0008"

docs/adr/0019-storage-v2.md
  kind: decision_record
  authority class: decision
  lifecycle: active
```

Authority resolution should then naturally exclude ADR-0008 from active authority candidates without changing the `architectural_intent` tier ordering.

The core Phase 2 relationship is:

```text
authority role
    +
lifecycle eligibility
    +
explicit supersession
```

but still **not**:

```text
claim correctness
claim extraction
semantic contradiction
architecture drift
```

---

# 2. Current Delivered Baseline

Phase 2 must build on the reviewed Phase 1 state, not on older plans.

Current `main` baseline:

```text
36d150af6cf67b8bab41c528b4304fa83da51309
fix phase 1 review findings
```

The current repository has already delivered:

- Phase 0 local context inventory;
- safe bounded POSIX source reads;
- deterministic source and repository IDs;
- raw-byte SHA-256 source revisions;
- Git-aware status/revision handling;
- deterministic kind / authority / lifecycle classification;
- lifecycle values `unknown` and heuristic `historical`;
- stable classification rule IDs;
- explicit projections for inventory JSON v1;
- Phase 1 authority policies with ordered equal-precedence tiers;
- repository-local `.context-integrity.toml`;
- strict fail-closed authority configuration;
- explicit authority-class overrides;
- explicit authority eligibility;
- pure authority resolution;
- separate authority JSON v1;
- `authority list/show/resolve`;
- review fixes preventing document metadata from synthesizing:
  - `executable_truth`;
  - `historical` authority class;
- 226-test offline quality gate after Phase 1 review fixes.

Phase 2 must preserve the Phase 0/1 public contracts unless this plan explicitly extends them.

---

# 3. Product Boundary

## 3.1 In Scope

Phase 2 includes:

- full lifecycle vocabulary:
  - `unknown`;
  - `draft`;
  - `active`;
  - `superseded`;
  - `historical`;
  - `expired`;
  - `invalid`;
- explicit lifecycle metadata in repository configuration;
- explicit directional supersession relationships;
- supersession validation;
- lifecycle provenance/explainability;
- lifecycle-aware authority eligibility;
- lifecycle inspection CLI;
- deterministic lifecycle JSON v1;
- explicit treatment of missing supersession endpoints;
- preservation of source identity and content revision provenance;
- configuration schema evolution with backward compatibility;
- Phase 0/1 regression preservation.

## 3.2 Explicitly Out of Scope

Do **not** implement:

- automatic supersession from:
  - Git timestamps;
  - file mtimes;
  - filename numbering;
  - "latest"/"v2"/"new";
  - directory order;
- semantic detection that one document replaces another;
- body parsing to discover phrases such as "supersedes ADR-3";
- claim extraction;
- claim-level lifecycle;
- contradiction detection;
- stale-document detection;
- architecture drift;
- derived-context invalidation;
- context contracts;
- context compilation;
- automatic expiration by clock/date;
- LLM lifecycle inference;
- embeddings/vector search;
- database persistence;
- Codebase Intelligence integration;
- cross-repository supersession;
- mutation commands that rewrite repository files;
- auto-fixing config;
- MCP/API/daemon work.

Phase 2 is about **explicit source lifecycle**, not semantic context reasoning.

---

# 4. Core Lifecycle Semantics

## 4.1 Lifecycle States

Expand `LifecycleState` to:

```text
UNKNOWN
DRAFT
ACTIVE
SUPERSEDED
HISTORICAL
EXPIRED
INVALID
```

Serialized values:

```text
unknown
draft
active
superseded
historical
expired
invalid
```

## 4.2 State Meanings

### `unknown`

No stronger lifecycle fact is available.

Important:

- remains authority-eligible by default to preserve Phase 1 behavior;
- does not mean "active";
- means the tool cannot establish a stronger lifecycle state.

### `draft`

The source exists but is not yet active authority.

Examples:

- proposed ADR;
- draft architecture doc;
- plan under review.

Authority behavior:

```text
excluded from active authority resolution
```

### `active`

The source is explicitly active.

Authority behavior:

```text
eligible subject to authority policy and explicit authority eligibility
```

### `superseded`

The source has been explicitly replaced, either:

- by lifecycle metadata; or
- by a valid explicit supersession edge.

Authority behavior:

```text
excluded
```

### `historical`

The source is retained for historical/reference purposes.

May still come from:

- existing path heuristic;
- new explicit lifecycle metadata.

Authority behavior:

```text
excluded
```

### `expired`

The source is explicitly no longer valid because its applicability ended.

Phase 2 does not implement clock-based automatic expiry.

Authority behavior:

```text
excluded
```

### `invalid`

The source is explicitly invalid/unusable as active context.

Authority behavior:

```text
excluded
```

---

# 5. Lifecycle Eligibility for Authority

Phase 1 currently excludes only `historical`.

Phase 2 changes the active-authority lifecycle gate.

Eligible lifecycle states:

```text
ACTIVE
UNKNOWN
```

Excluded lifecycle states:

```text
DRAFT
SUPERSEDED
HISTORICAL
EXPIRED
INVALID
```

This rule is deterministic and global at the source-lifecycle layer.

It does not change authority tier ordering.

Authority exclusion reasons should be stable:

```text
draft_lifecycle
superseded_lifecycle
historical_lifecycle
expired_lifecycle
invalid_lifecycle
explicitly_ineligible
not_in_policy
```

Ordering of checks:

```text
1. inactive lifecycle
2. explicit authority_eligible = false
3. not in selected authority policy
4. candidate
```

Thus:

```text
superseded + explicitly_ineligible
```

is reported as:

```text
superseded_lifecycle
```

Lifecycle is the more fundamental exclusion.

---

# 6. Explicit Lifecycle vs Heuristic Lifecycle

Current Phase 0 classification uses path heuristics such as:

```text
docs/history/...
```

to classify:

```text
lifecycle = historical
authority_class = historical
```

Phase 2 introduces explicit lifecycle metadata with stronger precedence.

Precedence:

```text
explicit supersession relation
        >
explicit lifecycle metadata
        >
built-in lifecycle heuristic
        >
unknown fallback
```

However, explicit supersession and explicit lifecycle metadata must not contradict one another.

## 6.1 Explicit Metadata Can Override a Heuristic

Example:

```text
docs/archive/current-exception.md
```

would currently be heuristically historical.

Config may explicitly say:

```toml
lifecycle = "active"
```

The effective lifecycle becomes:

```text
active
```

This is intentional:

> explicit repository metadata outranks path convention.

## 6.2 Historical Authority Overlay Compatibility

Phase 0 historically couples a heuristic `historical` lifecycle to:

```text
authority_class = historical
```

For backward compatibility:

- no-config behavior must remain byte-identical;
- heuristic historical sources remain exactly as Phase 0/1 currently render.

If explicit lifecycle metadata or supersession changes a heuristically historical source to a non-historical lifecycle:

1. remove the effect of the heuristic historical authority overlay;
2. restore the effective authority role to:
   - explicit Phase 1 authority-class override, if present;
   - otherwise the normal authority class derived from source kind.

Example:

```text
docs/history/current-policy.md

built-in:
  kind = architecture
  lifecycle = historical
  authority = historical

explicit config:
  lifecycle = active

effective:
  kind = architecture
  lifecycle = active
  authority = architecture_product
```

If an explicit authority override also exists:

```text
authority_class = decision
lifecycle = active
```

effective authority is:

```text
decision
```

Do not require users to duplicate the authority class merely to override a lifecycle heuristic.

---

# 7. Supersession Semantics

Supersession is explicit and directional.

```text
Source A --superseded_by--> Source B
```

Means:

```text
A lifecycle = superseded
```

It does **not** imply:

```text
B lifecycle = active
```

B may itself be:

- unknown;
- draft;
- active;
- superseded by C;
- historical;
- expired;
- invalid.

This supports chains:

```text
A -> B -> C
```

where:

```text
A = superseded
B = superseded
C = active or unknown
```

---

# 8. Supersession Graph Rules

## 8.1 Directed Acyclic Graph

The configured supersession relation must be acyclic.

Reject:

```text
A -> A
A -> B -> A
A -> B -> C -> A
```

as configuration errors.

## 8.2 One Direct Successor per Source

A source may have at most one outgoing `superseded_by` relation.

Reject:

```text
A -> B
A -> C
```

Reason:

A single source lifecycle should not claim two competing direct replacements in Phase 2.

Multiple sources may converge on one successor:

```text
A -> C
B -> C
```

This is allowed.

## 8.3 Chains Are Allowed

```text
A -> B
B -> C
```

is valid.

## 8.4 No Automatic Transitive Edge Creation

Do not materialize:

```text
A -> C
```

as a second configured edge.

Traversal may show the chain, but provenance must preserve declared direct edges.

## 8.5 Supersession Edge Implies Source State

A valid observed edge:

```text
A -> B
```

forces:

```text
A.lifecycle = superseded
```

unless config validation already failed because A has a contradictory explicit lifecycle.

## 8.6 Target State Is Not Inferred

Do not infer B as active.

---

# 9. Configuration Schema Evolution

The current `.context-integrity.toml` schema version is 1.

Phase 2 introduces:

```text
schema_version = 2
```

## 9.1 Backward Compatibility

The parser must accept both:

```text
schema_version = 1
schema_version = 2
```

### v1

Must retain exactly the Phase 1 semantics:

- authority policies;
- authority-class metadata;
- authority eligibility;
- no lifecycle metadata;
- no supersession.

### v2

Supports all v1 authority behavior plus:

- lifecycle metadata;
- supersession relationships.

Do not auto-upgrade or rewrite a v1 file.

---

# 10. Proposed Configuration Schema v2

Example:

```toml
schema_version = 2

[[authority.policies]]
id = "architectural_intent"
description = "Repository-specific architectural authority"
tiers = [
  ["decision"],
  ["architecture_product"],
  ["plan"],
]

[[source_metadata]]
path = "docs/adr/0008-storage.md"
lifecycle = "superseded"
reason = "Replaced by ADR-0019"

[[source_metadata]]
path = "docs/adr/0019-storage-v2.md"
lifecycle = "active"
reason = "Current storage decision"

[[source_metadata]]
path = "docs/drafts/new-routing.md"
lifecycle = "draft"
reason = "Proposal has not been accepted"

[[supersession]]
source = "docs/adr/0008-storage.md"
superseded_by = "docs/adr/0019-storage-v2.md"
reason = "ADR-0019 replaces ADR-0008"
```

Existing Phase 1 fields remain valid:

```toml
[[source_metadata]]
path = "docs/custom-verification.md"
authority_class = "verification_evidence"
authority_eligible = true
reason = "Curated verification evidence"
```

A single metadata entry may contain both authority and lifecycle fields:

```toml
[[source_metadata]]
path = "docs/policy.md"
authority_class = "decision"
lifecycle = "active"
reason = "Accepted repository policy"
```

---

# 11. Lifecycle Metadata Validation

In schema v2, allow:

```text
lifecycle = draft
lifecycle = active
lifecycle = superseded
lifecycle = historical
lifecycle = expired
lifecycle = invalid
```

Do not allow explicit:

```text
unknown
```

Rationale:

`unknown` is the fallback for insufficient evidence, not a useful explicit declaration.

To override a heuristic historical source, choose the intended explicit state, such as:

```text
active
draft
```

## 11.1 Metadata Reason

Existing `reason` remains required.

If one metadata entry sets:

- authority class;
- eligibility;
- lifecycle;

one reason may explain the combined metadata.

## 11.2 Lifecycle Metadata for Missing Source

If a lifecycle metadata path is absent from the observed inventory:

emit:

```text
lifecycle_metadata_source_missing
```

If the same metadata entry also includes Phase 1 authority metadata, preserve the existing:

```text
authority_metadata_source_missing
```

behavior.

It is acceptable to emit both dimension-specific warnings for one missing source.

Do not fail the scan merely because metadata references a missing path.

---

# 12. Supersession Configuration

Add root array:

```toml
[[supersession]]
source = "docs/old.md"
superseded_by = "docs/new.md"
reason = "New document replaces old document"
```

Allowed keys only:

```text
source
superseded_by
reason
```

Unknown keys fail closed.

Paths use the same normalized repository-relative path rules as `source_metadata`.

Reject:

- absolute paths;
- `..`;
- Windows drive/UNC ambiguity;
- trailing-directory paths;
- empty strings;
- source == target.

---

# 13. Cross-Validation Between Metadata and Supersession

After parsing the whole config, validate relationships across entries.

If a source appears as an outgoing supersession source:

```text
A -> B
```

and `source_metadata[A].lifecycle` exists:

allowed:

```text
superseded
```

not allowed:

```text
draft
active
historical
expired
invalid
```

Those are contradictory declarations.

Reject the config.

If no explicit lifecycle is declared for A:

```text
A -> B
```

is sufficient to make A superseded once the edge is successfully resolved against inventory.

---

# 14. Missing Supersession Endpoints

Configuration syntax may be valid even when repository contents changed.

After inventory:

## 14.1 Missing Source Endpoint

If configured:

```text
A -> B
```

but A is absent from inventory:

emit:

```text
supersession_source_missing
```

No relation is activated.

## 14.2 Missing Target Endpoint

If A is present but B is absent:

emit:

```text
supersession_target_missing
```

Do **not** apply the edge-implied `superseded` state solely from that unresolved edge.

If A also has explicit:

```text
lifecycle = superseded
```

that explicit lifecycle remains effective independently.

## 14.3 Both Missing

Emit both warnings.

## 14.4 Why Missing Endpoints Are Warnings, Not Config Errors

This follows the Phase 1 stale-metadata pattern:

- syntax and graph shape can be valid;
- repository contents may have changed;
- stale lifecycle configuration should be inspectable;
- a stale edge should not silently change active authority.

---

# 15. Control-Plane Config Constraint

`.context-integrity.toml` is the active file controlling interpretation.

Phase 2 lifecycle metadata and supersession must not target:

```text
.context-integrity.toml
```

Reject config that attempts to set lifecycle state for the config file or includes the config file in a supersession relation.

Reason:

A file actively controlling interpretation cannot coherently declare itself superseded/invalid/historical while still being used to interpret the same scan.

Phase 1 authority metadata behavior for the config file may remain unchanged for compatibility, though it is not an authority candidate under built-in policy.

---

# 16. Recommended Internal Model Refactor

The configuration is no longer authority-only.

Phase 2 is the right time to make the internal naming generic.

Recommended:

```text
SourceAuthorityMetadata
        ↓
SourceMetadata

RepositoryAuthorityConfig
        ↓
RepositoryConfig
```

Add:

```text
SupersessionSpec
ResolvedSupersession
LifecycleOrigin
LifecycleEntry
LifecycleOverview
```

A compatibility alias is acceptable temporarily if it significantly reduces churn, but do not keep semantically misleading names indefinitely.

This is an **internal refactor**.

Public JSON schemas must not change merely because Python class names change.

---

# 17. Proposed Domain Models

## 17.1 `SourceMetadata`

Conceptually:

```text
SourceMetadata
- path
- reason
- authority_class_override?
- authority_eligible?
- lifecycle_override?
```

## 17.2 `SupersessionSpec`

```text
SupersessionSpec
- source_path
- superseded_by_path
- reason
```

## 17.3 `RepositoryConfig`

```text
RepositoryConfig
- authority policies
- source metadata
- supersession specs
- content_sha256
- schema_version
```

## 17.4 `ResolvedSupersession`

```text
ResolvedSupersession
- source: SourceRecord
- superseded_by: SourceRecord
- reason
- config_sha256
```

The resolved relation therefore carries both endpoint identities and revisions through the attached source records.

## 17.5 `LifecycleOrigin`

Suggested values:

```text
fallback_unknown
path_heuristic
repository_metadata
supersession
```

## 17.6 `LifecycleEntry`

```text
LifecycleEntry
- source
- state
- origin
- reason?
- superseded_by?
- supersedes[]
```

`supersedes[]` contains direct incoming predecessors only.

## 17.7 `LifecycleOverview`

```text
LifecycleOverview
- repository
- config_sha256
- entries[]
- supersessions[]
- warnings[]
- schema_version = 1
```

This is a derived inspection result, not canonical state.

---

# 18. Lifecycle Application Pipeline

The inventory flow becomes two-pass.

## Pass 1 — Source Observation

1. discover repository;
2. load/validate config;
3. enumerate context candidates;
4. read/hash sources;
5. classify built-in kind/authority/lifecycle;
6. apply Phase 1 authority metadata;
7. apply explicit lifecycle metadata;
8. construct provisional `SourceRecord`s.

## Pass 2 — Supersession Resolution

1. build `path -> SourceRecord`;
2. evaluate every configured supersession relation;
3. emit endpoint warnings where needed;
4. create valid `ResolvedSupersession` edges;
5. set valid outgoing-edge source lifecycle to `superseded`;
6. add explicit lifecycle provenance/rule match;
7. restore non-historical authority role if an explicit lifecycle/supersession overrides a heuristic historical state;
8. rebuild source tuple deterministically;
9. verify config revision;
10. produce summary.

No source body parsing.

---

# 19. Classification / Provenance Rules

Keep all existing Phase 0/1 rule IDs unchanged.

Add stable Phase 2 rule IDs.

Suggested:

```text
lifecycle.metadata.repository_override
lifecycle.supersession.explicit
authority.lifecycle.restore_kind_role
```

The last rule applies only when explicit lifecycle/supersession moves a source out of heuristic historical status and no explicit authority-class override already supplies the role.

## 19.1 Kind Confidence

As in Phase 1:

> explicit lifecycle metadata must not change top-level kind confidence.

Lifecycle provenance belongs in per-dimension `RuleMatch` entries.

## 19.2 Supersession Provenance

A source superseded by relation should have a lifecycle rule match whose basis includes:

- direct replacement path or stable relation reference;
- explicit reason.

Do not copy arbitrary source body text into the rule.

---

# 20. Lifecycle and Authority Integration

Update the existing pure authority resolver.

Replace:

```text
if lifecycle == historical
```

with:

```text
if lifecycle not in {active, unknown}
```

Use state-specific exclusion reasons.

Everything else in Phase 1 remains:

- equal-precedence tiers;
- all top-tier candidates retained;
- missing stronger tiers;
- no recency;
- no semantic truth;
- explicit authority eligibility after lifecycle gate.

No new authority policies are needed in Phase 2.

---

# 21. Lifecycle CLI

Add a Typer sub-app:

```text
context-integrity lifecycle ...
```

Do not add mutation commands.

---

## 21.1 `lifecycle list`

```bash
context-integrity lifecycle list [PATH]
```

Options:

```text
--format text|json
--output PATH
```

Human output example:

```text
Lifecycle

SOURCE                                   STATE        ORIGIN
docs/adr/0008-storage.md                 superseded   supersession
docs/adr/0019-storage-v2.md              active       repository_metadata
docs/drafts/new-routing.md               draft        repository_metadata
docs/history/legacy.md                   historical   path_heuristic
README.md                                unknown      fallback_unknown

Supersession
docs/adr/0008-storage.md
  -> docs/adr/0019-storage-v2.md
  reason: ADR-0019 replaces ADR-0008

Warnings: 0
```

---

## 21.2 `lifecycle show`

```bash
context-integrity lifecycle show SOURCE_PATH [PATH]
```

Options:

```text
--format text|json
```

Human output:

```text
Source: docs/adr/0008-storage.md

Lifecycle: superseded
Origin: supersession
Reason: ADR-0019 replaces ADR-0008

Superseded by:
  docs/adr/0019-storage-v2.md

Supersedes:
  none

Revision:
  sha256: ...
  git status: tracked_clean

Authority:
  class: decision
  active authority eligible: no
  exclusion reason: superseded_lifecycle
```

Do not run an authority policy resolution here.

"active authority eligible" refers only to lifecycle eligibility + explicit global authority eligibility, not policy membership.

---

# 22. `scan` Integration

When schema v2 lifecycle metadata is present:

`scan` should report the effective lifecycle in its existing `lifecycle` field.

Do not add new inventory JSON v1 keys.

Examples:

```json
"lifecycle": "active"
```

or:

```json
"lifecycle": "superseded"
```

The existing lifecycle summary counts should naturally reflect new states.

## Hard Compatibility Requirement

When:

- no config exists; or
- an existing schema-v1 config is used;

existing Phase 0/1 golden outputs must remain unchanged unless the config content itself changes.

---

# 23. `explain` Integration

Extend existing `explain` output with lifecycle metadata and supersession.

Show:

- built-in lifecycle rule;
- explicit lifecycle override, if present;
- override reason;
- supersession relationship, if present;
- effective lifecycle;
- whether lifecycle makes source active-authority-eligible.

Example:

```text
Lifecycle:
- built-in: historical via path rule
- explicit override: active
- reason: archive directory is organizational only
- effective: active
```

or:

```text
Lifecycle:
- explicit supersession:
  docs/adr/0008-storage.md
    -> docs/adr/0019-storage-v2.md
- reason: ADR-0019 replaces ADR-0008
- effective: superseded
```

Preserve Phase 1 note:

```text
authority policy resolution is not performed by explain
```

---

# 24. Lifecycle JSON v1 Contract

Add a separate machine-readable lifecycle projection.

Do not add lifecycle graph fields to:

- inventory JSON v1;
- authority JSON v1.

Illustrative:

```json
{
  "schema_version": 1,
  "repository": {
    "id": "repo_...",
    "name": "context-integrity",
    "git": {
      "available": true,
      "head": "...",
      "dirty": false
    }
  },
  "config_sha256": "...",
  "sources": [
    {
      "source_id": "src_...",
      "path": "docs/adr/0008-storage.md",
      "kind": "decision_record",
      "authority_class": "decision",
      "lifecycle": "superseded",
      "origin": "supersession",
      "reason": "ADR-0019 replaces ADR-0008",
      "content_sha256": "...",
      "superseded_by": {
        "source_id": "src_...",
        "path": "docs/adr/0019-storage-v2.md"
      },
      "supersedes": []
    }
  ],
  "supersessions": [
    {
      "source": {
        "source_id": "src_...",
        "path": "docs/adr/0008-storage.md"
      },
      "superseded_by": {
        "source_id": "src_...",
        "path": "docs/adr/0019-storage-v2.md"
      },
      "reason": "ADR-0019 replaces ADR-0008"
    }
  ],
  "warnings": []
}
```

The exact projection may be refined, but these semantics must remain.

---

# 25. Determinism Requirements

Lifecycle JSON must:

- sort sources by path;
- sort supersession edges by:
  - source path;
  - target path;
- sort incoming predecessor lists by path;
- use repository-relative paths;
- omit timestamps by default;
- omit absolute roots;
- omit source bodies;
- use explicit projection;
- end with newline.

Two runs on unchanged repository/config state must be byte-identical.

---

# 26. Configuration Revision Consistency

Preserve Phase 1's fail-closed configuration consistency.

The same raw config bytes govern:

- authority policy;
- authority metadata;
- lifecycle metadata;
- supersession relations.

The config hash reported in lifecycle output must match the bytes used to interpret the lifecycle graph.

If the config changes during the observation:

```text
ConfigurationError
exit 6
```

Do not partially apply lifecycle data from one config revision and authority data from another.

---

# 27. Error Model

Preserve Phase 1 codes:

```text
0 success
2 usage / source not found / unknown requested identifier
3 repository error
4 output write failure
5 warnings with --fail-on-warning where supported
6 configuration error
```

Phase 2 does not require a new exit code.

Examples that produce exit 6:

- invalid lifecycle value;
- v1 config using v2 lifecycle fields;
- supersession cycle;
- duplicate outgoing successor;
- self-supersession;
- lifecycle/supersession contradiction;
- lifecycle metadata targeting control-plane config;
- unsafe path.

Missing observed endpoints are warnings, not configuration errors.

---

# 28. Authority JSON Compatibility

Authority JSON remains schema version 1.

It may now encounter new exclusion reasons:

```text
draft_lifecycle
superseded_lifecycle
expired_lifecycle
invalid_lifecycle
```

Existing fields remain unchanged.

No-config and schema-v1-config authority goldens must remain byte-identical.

Add new Phase 2 goldens for lifecycle-aware authority resolution rather than rewriting Phase 1 goldens.

---

# 29. Inventory JSON Compatibility

Inventory JSON remains schema version 1.

No new keys.

The `lifecycle` enum domain expands for schema-v2 configured repositories.

No-config Phase 0 goldens must remain byte-identical.

---

# 30. Recommended Module Changes

Add:

```text
src/context_integrity/lifecycle.py
```

Recommended responsibilities:

- lifecycle state helpers;
- active-authority lifecycle eligibility;
- explicit lifecycle application;
- supersession graph validation/resolution;
- lifecycle overview construction.

Refactor:

```text
configuration.py
```

to support schema 1 and 2.

Potential internal rename:

```text
RepositoryAuthorityConfig -> RepositoryConfig
SourceAuthorityMetadata -> SourceMetadata
```

Keep aliases temporarily only if they materially simplify migration.

Update:

```text
models.py
inventory.py
authority.py
classification.py
rendering.py
cli.py
```

Do not add:

- persistence module;
- graph database;
- generic plugin system.

---

# 31. Detailed Implementation Work Breakdown

## Step 0 — Verify Baseline

Before edits:

run:

```bash
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check
```

Expected reviewed baseline:

```text
226 tests
```

If the exact count has changed due to a subsequent commit, inspect why before implementing.

Record actual baseline in Phase 2 implementation report.

---

## Step 1 — Expand Lifecycle Vocabulary

Extend `LifecycleState`.

Add tests that pin the exact lifecycle enum contract.

Do not modify authority policies.

---

## Step 2 — Generalize Config Models

Refactor internal authority-only config naming if needed.

Add:

```text
lifecycle_override
supersession specs
schema_version = 1|2
```

Preserve existing v1 behavior.

---

## Step 3 — Versioned Config Parser

Implement explicit parser branches:

```text
parse_config_v1
parse_config_v2
```

or equivalent clear structure.

Avoid a single permissive parser where v1 accidentally accepts v2 keys.

Tests must prove:

```text
schema 1 + lifecycle -> error
schema 1 + supersession -> error
schema 2 + authority-only -> valid
schema 2 + lifecycle -> valid
```

---

## Step 4 — Lifecycle Metadata Validation

Test every state.

Reject:

```text
unknown
```

as explicit lifecycle metadata.

Test:

- missing reason;
- invalid source path;
- config path target;
- combined authority+lifecycle metadata.

---

## Step 5 — Supersession Parse / Structural Validation

Validate:

- normalized source/target paths;
- no self edge;
- no duplicate exact relation;
- max one outgoing edge;
- DAG/cycle-free;
- reason required;
- no config-path endpoint;
- explicit lifecycle conflict.

Do this before repository endpoint resolution.

---

## Step 6 — Apply Explicit Lifecycle Metadata

Add per-dimension rule provenance.

Test:

- unknown -> active;
- unknown -> draft;
- heuristic historical -> active;
- heuristic historical -> expired;
- ordinary source -> historical;
- top-level kind confidence unchanged.

---

## Step 7 — Resolve Supersession Against Inventory

After sources are observed:

- build path map;
- detect missing endpoints;
- emit warnings;
- resolve valid edges;
- apply `superseded` lifecycle to valid source endpoints.

Test:

- valid A -> B;
- A -> B -> C;
- A/B -> C;
- missing A;
- missing B;
- both missing;
- explicit superseded state with missing B remains superseded via metadata;
- relation-only A with missing B does not become superseded.

---

## Step 8 — Historical Authority Restoration

Implement the specific backward-compatible rule for sources whose heuristic historical lifecycle is explicitly overridden.

Tests:

```text
docs/history/architecture.md
```

without config:

```text
lifecycle = historical
authority = historical
```

with:

```text
lifecycle = active
```

becomes:

```text
lifecycle = active
authority = architecture_product
```

with authority override:

```text
authority_class = decision
lifecycle = active
```

becomes:

```text
authority = decision
```

No-config golden remains unchanged.

---

## Step 9 — Update Authority Resolver

Use lifecycle eligibility helper.

Tests for every state:

```text
unknown -> eligible
active -> eligible
draft -> excluded
superseded -> excluded
historical -> excluded
expired -> excluded
invalid -> excluded
```

Pin exclusion reason strings.

Confirm:

- equal-tier behavior unchanged;
- missing stronger tier behavior unchanged;
- explicit authority ineligibility unchanged;
- lifecycle check runs before explicit ineligibility.

---

## Step 10 — Lifecycle Overview

Build pure lifecycle overview from inventory/config.

No filesystem I/O.

Include:

- source states;
- lifecycle origin;
- direct supersession incoming/outgoing;
- warnings.

---

## Step 11 — Lifecycle JSON Projection

Create explicit schema-v1 projection.

Add goldens:

1. explicit states;
2. supersession chain;
3. heuristic override + warning case.

Do not generically serialize dataclasses.

---

## Step 12 — Lifecycle Text Rendering

Implement:

```text
lifecycle list
lifecycle show
```

Escape repository-controlled text using the same terminal-safety pattern as Phase 1.

---

## Step 13 — CLI Wiring

Add:

```text
lifecycle list
lifecycle show
```

Support output file on `list`.

Recommended to support `--output` on `show` too if consistent and low-cost.

Source not found:

```text
exit 2
```

Config failure:

```text
exit 6
```

---

## Step 14 — Extend `scan`

No new keys.

Verify:

- effective lifecycle rendered;
- summary counts expanded states;
- no-config goldens unchanged;
- schema-v1 config outputs unchanged.

---

## Step 15 — Extend `explain`

Expose:

- explicit lifecycle metadata;
- supersession;
- effective lifecycle;
- lifecycle authority eligibility.

Do not run semantic claim checks.

---

## Step 16 — Regression + Security Tests

Run all Phase 0/1 suites.

Add:

- v1 config compatibility tests;
- control-plane config restriction;
- supersession cycles;
- terminal escaping;
- safe config revision consistency;
- missing endpoint warnings;
- no-body/no-absolute-path lifecycle JSON checks.

---

## Step 17 — Documentation

Update:

- README;
- `docs/current-state.md` after verification;
- create Phase 2 implementation report.

Do not edit:

- completed Phase 0 plan;
- completed Phase 1 plan;

to pretend they anticipated Phase 2 implementation details.

Update architecture only if implementation produces a durable decision not already covered.

---

# 32. Fixture Plan

## Fixture A — `lifecycle-basic`

```text
docs/
  active.md
  draft.md
  expired.md
  invalid.md
  history/
    historical.md
```

Config sets explicit lifecycle for first four.

Expected state coverage.

---

## Fixture B — `supersession-chain`

```text
docs/adr/
  0001.md
  0002.md
  0003.md
```

Config:

```text
0001 -> 0002
0002 -> 0003
0003 active
```

Expected:

```text
0001 superseded
0002 superseded
0003 active
```

---

## Fixture C — `historical-override`

```text
docs/history/architecture.md
```

Config:

```text
lifecycle = active
```

Expected:

```text
kind = architecture
lifecycle = active
authority = architecture_product
```

---

## Fixture D — `missing-supersession`

Config references:

```text
present.md -> missing.md
missing-old.md -> present.md
```

Expected warnings.

No unresolved relation applies lifecycle.

---

## Fixture E — `v1-config`

Exact current Phase 1 config fixture.

Expected:

- no output change;
- no lifecycle behavior change;
- authority goldens byte-identical.

---

## Fixture F — `invalid-supersession`

Cases:

- self edge;
- duplicate outgoing;
- A -> B -> A;
- lifecycle active + outgoing supersession;
- config file endpoint;
- invalid path.

Expected exit 6.

---

# 33. Required Test Categories

## Models

- exact lifecycle enum;
- supersession model immutability;
- lifecycle-origin values.

## Config Compatibility

- all existing v1 config tests;
- v1 rejects Phase 2 keys;
- v2 preserves authority behavior;
- strict unknown keys.

## Lifecycle Metadata

- every explicit state;
- no explicit unknown;
- reason required;
- authority metadata combination.

## Supersession

- DAG;
- cycle rejection;
- unique outgoing;
- converging predecessors;
- chain;
- missing endpoints;
- relation provenance.

## Classification

- heuristic historical unchanged without config;
- explicit lifecycle overrides heuristic;
- rule IDs stable;
- kind confidence unchanged.

## Authority

- all states eligibility;
- exclusion reasons;
- no authority tier changes;
- Phase 1 goldens unchanged.

## Rendering

- lifecycle JSON goldens;
- explicit projection;
- path sorting;
- terminal escaping;
- no source bodies;
- no absolute root;
- newline.

## CLI

- lifecycle list text/json;
- lifecycle show text/json;
- source not found;
- config exit 6;
- output file.

## Regression

- all Phase 0/1 tests;
- Phase 0 inventory goldens unchanged;
- Phase 1 authority goldens unchanged for v1/no-config cases.

---

# 34. Security Acceptance Criteria

- [ ] no `shell=True`;
- [ ] no config code execution;
- [ ] no network;
- [ ] lifecycle paths remain normalized repository-relative;
- [ ] supersession paths remain normalized repository-relative;
- [ ] config file cannot lifecycle/supersede itself;
- [ ] symlink/unsafe config handling remains fail-closed;
- [ ] config revision used for lifecycle matches observed config hash;
- [ ] missing endpoint cannot silently deactivate a source;
- [ ] cycle cannot enter runtime graph;
- [ ] terminal-controlled reasons/paths are escaped;
- [ ] lifecycle JSON includes no source bodies;
- [ ] lifecycle JSON includes no absolute root;
- [ ] no content body parsing is added.

---

# 35. Phase 2 Acceptance Criteria

Phase 2 is complete only when all are true.

## Lifecycle Domain

- [ ] full seven-state lifecycle enum exists.
- [ ] unknown remains fallback.
- [ ] unknown and active are authority-eligible.
- [ ] draft is authority-ineligible.
- [ ] superseded is authority-ineligible.
- [ ] historical is authority-ineligible.
- [ ] expired is authority-ineligible.
- [ ] invalid is authority-ineligible.
- [ ] explicit unknown lifecycle metadata is rejected.

## Configuration

- [ ] config schema 1 still supported.
- [ ] config schema 2 supported.
- [ ] v1 cannot use lifecycle fields.
- [ ] v1 cannot define supersession.
- [ ] v2 supports lifecycle metadata.
- [ ] v2 supports supersession.
- [ ] reason required for lifecycle metadata.
- [ ] reason required for supersession.
- [ ] lifecycle metadata cannot target config file.
- [ ] supersession cannot involve config file.
- [ ] unsafe paths fail.
- [ ] config revision consistency remains fail-closed.

## Supersession

- [ ] relation is directional.
- [ ] source != target.
- [ ] one direct successor per source.
- [ ] multiple predecessors may share successor.
- [ ] chains allowed.
- [ ] cycles rejected.
- [ ] valid relation sets source to superseded.
- [ ] relation does not mark target active.
- [ ] conflicting explicit lifecycle + outgoing relation rejected.
- [ ] missing source endpoint warned.
- [ ] missing target endpoint warned.
- [ ] unresolved edge alone does not set source superseded.

## Precedence / Heuristics

- [ ] explicit lifecycle overrides path heuristic.
- [ ] supersession outranks explicit non-conflicting lifecycle metadata.
- [ ] heuristic historical output unchanged with no config.
- [ ] explicit non-historical override restores underlying authority role.
- [ ] explicit authority override remains strongest authority-dimension input.
- [ ] recency never implies lifecycle.
- [ ] Git dates never imply lifecycle.
- [ ] filenames never imply supersession.

## Authority Integration

- [ ] authority resolver uses lifecycle eligibility helper.
- [ ] new state-specific exclusion reasons stable.
- [ ] equal-tier semantics unchanged.
- [ ] missing-stronger-tier semantics unchanged.
- [ ] built-in authority policies unchanged.
- [ ] executable-truth boundary unchanged.
- [ ] explicit authority eligibility still works.

## CLI / Output

- [ ] `lifecycle list` works.
- [ ] `lifecycle show` works.
- [ ] text output exposes origin/reason.
- [ ] JSON lifecycle schema version 1 exists.
- [ ] JSON projection is explicit.
- [ ] JSON deterministic.
- [ ] no source body/absolute root.
- [ ] inventory JSON adds no new keys.
- [ ] authority JSON adds no new keys.
- [ ] source-not-found exits 2.
- [ ] config errors exit 6.

## Compatibility

- [ ] Phase 0 no-config inventory goldens byte-identical.
- [ ] Phase 1 no-config/v1 authority goldens byte-identical.
- [ ] existing rule IDs unchanged.
- [ ] existing safe-read protections unchanged.
- [ ] 226-test reviewed baseline passes before edits or discrepancy is explained.
- [ ] no database added.
- [ ] no LLM/model integration.
- [ ] no Codebase Intelligence dependency.
- [ ] no claims.
- [ ] no contradiction engine.
- [ ] no context compiler.

## Testing / Docs

- [ ] lifecycle state matrix tested.
- [ ] supersession graph validation tested.
- [ ] config v1/v2 compatibility tested.
- [ ] lifecycle goldens pass.
- [ ] full offline `make check` passes.
- [ ] README updated.
- [ ] Phase 2 implementation report maps acceptance criteria.
- [ ] current-state updated only after verification.

---

# 36. Non-Acceptance Examples

## Wrong: Newer File Automatically Supersedes Older

```text
ADR-0019 has a larger number than ADR-0008,
so mark 0008 superseded.
```

Not allowed.

---

## Wrong: Git Commit Date Determines Active Source

```text
whichever architecture document was edited most recently is active
```

Not allowed.

---

## Wrong: Parse "supersedes" From Markdown Body

Phase 2 is explicit metadata only.

Body/claim parsing belongs later.

---

## Wrong: Missing Target Still Deactivates Source

```text
A -> missing-B
```

must not silently make A superseded unless A independently has explicit lifecycle metadata saying so.

---

## Wrong: Supersession Makes Target Active

```text
A -> B
therefore B = active
```

Not valid.

---

## Wrong: Draft Can Win Authority Because It Has Stronger Class

A draft ADR remains authority-ineligible even though its authority class is `decision`.

---

## Wrong: New Lifecycle Database

No persistence layer is required.

---

## Wrong: Claim-Level Lifecycle

Phase 2 is source lifecycle only.

Claims begin in Phase 3.

---

# 37. Future Compatibility

## Phase 3 — Claims and Provenance

Claims should reference:

```text
SourceId
SourceRevision
```

and inherit/source lifecycle context without being permanently conflated with source lifecycle.

A future claim may become stale while its source remains active.

Do not design Phase 2 such that:

```text
source lifecycle == claim validity
```

They are distinct.

## Phase 4 — Drift

Drift rules can later ask:

```text
Does an active source contain claims inconsistent with stronger active evidence?
```

Phase 2 should only supply lifecycle.

## Phase 6 — Context Compiler

Compiler can later filter:

```text
superseded
historical
expired
invalid
draft
```

before budget/ranking.

## Phase 7 — Codebase Intelligence

No change to the Rust integration boundary.

Lifecycle applies to Context Integrity sources/evidence policy.

The Codebase Intelligence Engine remains descriptive.

---

# 38. Suggested Commit Structure

A reasonable implementation sequence:

1. `phase2: add lifecycle domain and config v2`
2. `phase2: add explicit lifecycle and supersession resolution`
3. `phase2: integrate lifecycle with authority and inventory`
4. `phase2: add lifecycle CLI and stable rendering`
5. `phase2: add compatibility tests docs and report`

Avoid broad unrelated cleanup.

---

# 39. Implementation Report Requirements

At completion create:

```text
docs/implementation-reports/phase-2-implementation-report.md
```

Include:

- baseline commit;
- implementation commits;
- delivered lifecycle states;
- config schema v1/v2 behavior;
- supersession semantics;
- lifecycle/authority interaction;
- CLI examples;
- JSON schema example;
- compatibility results;
- exact tests/check commands;
- security verification;
- deviations;
- known limitations;
- acceptance-criterion mapping;
- recommendations for Phase 3.

Distinguish:

```text
implemented
verified
deferred
```

Do not use the plan as evidence of delivery.

---

# 40. Definition of Done

Phase 2 is done when Context Integrity can deterministically answer:

> **What is the effective lifecycle of each observed context source, what explicit or heuristic evidence produced that lifecycle, and which source explicitly supersedes which?**

and Phase 1 can correctly use those states to answer:

> **Which observed sources remain eligible for active authority resolution?**

without claiming:

> **that one source's claims are semantically correct, that two sources contradict each other, or that supersession can be inferred from recency.**
