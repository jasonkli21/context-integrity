# Context Integrity — Phase 1 Detailed Implementation Plan

**Phase:** 1 — Authority and Source-of-Truth Model  
**Status:** Ready for implementation  
**Date:** 2026-10-14  
**Parent documents:** `docs/prd.md`, `docs/architecture.md`  
**Predecessor:** Phase 0 — Context Inventory and Source Classification  
**Related project:** Codebase / Context Intelligence Engine, still intentionally unintegrated in this phase

---

## 1. Phase Objective

Phase 1 adds the first **normative** layer on top of the Phase 0 source inventory:

> **Given a type of question, identify which observed source roles are preferred, which observed sources are eligible candidates, which stronger authority tiers are missing, and why—without pretending that source precedence proves a claim is correct.**

Phase 0 answered:

> What context sources are present, what role does each appear to play, and what exact source revision did we observe?

Phase 1 should additionally answer questions such as:

```text
For architectural intent:
- accepted decisions are preferred to general architecture/product documents;
- architecture/product documents are preferred to implementation plans;
- historical sources are not active authority candidates.

For operating instructions:
- operating-instruction sources are preferred;
- architecture/product sources are fallback context;
- plans are weaker fallback context.

For delivered behavior:
- executable truth is the strongest source role;
- if it is not represented in the current Context Integrity inventory,
  the tool must say that a stronger tier is unobserved rather than silently
  treating the strongest observed document as equivalent to code.
```

The central Phase 1 distinction is:

```text
source precedence
      ≠
claim correctness
      ≠
claim agreement
      ≠
lifecycle/supersession
```

Phase 1 resolves **source-role precedence for a question**.

It does **not** yet resolve semantic claims.

---

# 2. Delivered Baseline

Phase 1 must build on the **actual delivered Phase 0 state**, not on the original Phase 0 plan as if it were unimplemented.

At the current reviewed baseline, Phase 0 already provides:

- local, read-only repository inventory;
- Git-aware and non-Git discovery;
- deterministic `SourceId` and repository identity;
- raw-byte SHA-256 source revisions;
- Git HEAD and working-tree status kept separate;
- provisional `SourceKind`, `AuthorityClass`, and `LifecycleState`;
- deterministic source classification with stable rule IDs;
- independent historical overlay;
- schema-version-1 inventory JSON with explicit projections;
- human-readable inventory;
- `scan`, `explain`, and `version` commands;
- structured warnings;
- safe POSIX source reads;
- no database, LLM, network service, or Codebase Intelligence dependency;
- reviewed fixes for Git-root redirects, deleted/disappearing candidates, and explicit JSON-v1 projections;
- offline quality verification.

The implementation must preserve these Phase 0 contracts unless this Phase 1 plan explicitly changes them.

---

# 3. Product Boundary

## 3.1 In Scope

Phase 1 includes:

- question-specific authority policies;
- ordered authority **tiers**, not a universal scalar rank;
- built-in policy profiles;
- repository-local authority configuration;
- deterministic config parsing and validation;
- basic explicit per-source authority metadata;
- source-level authority eligibility;
- source-level authority-class override where explicitly configured;
- authority-policy inspection;
- source-precedence resolution against the Phase 0 inventory;
- explanation of:
  - preferred tiers;
  - missing stronger tiers;
  - highest-precedence observed candidates;
  - lower-precedence candidates;
  - excluded candidates and reasons;
- stable machine-readable authority-resolution output;
- human-readable authority output;
- deterministic/offline tests;
- preservation of Phase 0 inventory behavior when no Phase 1 configuration exists.

## 3.2 Explicitly Out of Scope

Do **not** implement:

- claim extraction;
- claim parsing from document text;
- semantic contradiction detection;
- choosing between two claims inside same-tier sources;
- deciding that one same-tier document is "the winner" based on recency;
- active/superseded lifecycle inference;
- supersession graphs;
- automatic ADR acceptance detection;
- modification-time authority;
- Git-date authority;
- semantic staleness detection;
- architecture-drift checks;
- context contracts;
- context compilation;
- LLM calls;
- embeddings/vector search;
- database persistence;
- Codebase / Context Intelligence Engine integration;
- ordinary source-code indexing;
- MCP;
- HTTP/API server;
- background daemon;
- cross-repository authority resolution;
- policy inheritance;
- policy expressions/conditions;
- per-claim authority rules.

If one of these appears necessary, document the gap instead of silently expanding Phase 1.

---

# 4. Core Semantic Model

## 4.1 Authority Is a Function of the Question

There must be no global ordering such as:

```text
code > ADR > architecture > plan
```

Instead:

```text
AuthorityPolicy(question)
    -> ordered tiers of authority classes
```

Example:

```text
architectural_intent:
  tier 0: decision
  tier 1: architecture_product
  tier 2: plan
```

Another question can have a different order.

## 4.2 A Tier Is a Set of Equal-Precedence Source Roles

The model must support multiple authority classes in the same tier even if the built-in v1 policies mostly use one class per tier.

Example conceptually:

```text
tier 0:
  - class_a
  - class_b
```

The resolver must not invent ordering inside one tier.

## 4.3 "Highest Observed" Is Not "Highest Possible"

This is critical.

Suppose the `delivered_behavior` policy is:

```text
tier 0: executable_truth
tier 1: verification_evidence
tier 2: generated_derivative
```

The Phase 0 inventory does not currently index ordinary source code.

If the repository contains an implementation report but no executable-truth source record, Phase 1 may report:

```text
highest observed tier: 1
highest observed candidates:
- docs/implementation-reports/phase-0-implementation-report.md

missing stronger tiers:
- tier 0: executable_truth
```

It must **not** report:

```text
"implementation report is the authoritative truth for delivered behavior"
```

The stronger tier is known to exist conceptually even if this phase cannot observe it.

## 4.4 Multiple Highest-Tier Candidates Are Not Automatically a Conflict

If two active-looking architecture documents are in the same highest observed tier:

```text
docs/architecture.md
docs/subsystem-architecture.md
```

the Phase 1 result is:

```text
multiple highest-precedence observed candidates
```

not:

```text
contradiction
ambiguous truth
error
```

Claim-level agreement/conflict belongs to later phases.

## 4.5 Historical Is Not Active Authority

A source whose Phase 0 lifecycle is `historical` must be excluded from active authority resolution.

It should remain visible in the resolution output as an excluded candidate with reason:

```text
historical_lifecycle
```

Do not delete or hide it.

## 4.6 Unknown Remains Valid

A source classified with unknown authority should not be forced into an authority tier.

It can appear as:

```text
excluded / not applicable to policy
```

Unknown is not an error.

---

# 5. Domain Model Additions

The exact file placement can adapt to the current implementation, but the domain concepts should be explicit.

## 5.1 Extend `AuthorityClass`

Add:

```text
executable_truth
```

The Phase 1 document inventory does not need to produce this class from ordinary code.

It exists because:

- the architecture already defines it;
- built-in authority policy needs to represent a stronger tier that may be unobserved;
- a later EvidenceProvider may supply executable-truth evidence.

Preserve all existing Phase 0 enum values.

## 5.2 Extend `SourceKind`

Add:

```text
configuration
```

Use it for the repository authority configuration file described below.

Its default authority class should be:

```text
unknown
```

Rationale:

The config is authoritative **for Context Integrity policy behavior**, but it is not automatically a source of product, architectural, implementation, or agent-operating claims.

Do not classify it as `operating_instruction`, because that would incorrectly make it a candidate for the `operating_instructions` authority policy.

## 5.3 `AuthorityPolicyId`

Represent policy IDs as stable strings, optionally via a `NewType`.

Policy ID requirements:

- lowercase ASCII;
- starts with a letter;
- remaining characters: letters, numbers, `_`, `-`;
- stable across output;
- no whitespace.

## 5.4 `AuthorityTier`

Conceptual model:

```text
AuthorityTier
- classes: tuple[AuthorityClass, ...]
```

Requirements:

- at least one class;
- no duplicates within tier;
- one class may not appear in more than one tier in the same policy.

## 5.5 `AuthorityPolicy`

```text
AuthorityPolicy
- id
- description
- tiers[]
- origin
- policy_version
- config_revision?      # when repository-defined
```

Suggested `origin` values:

```text
builtin
repository_config
```

`policy_version` should identify built-in policy semantics separately from application version.

## 5.6 `SourceAuthorityMetadata`

Repository config may attach explicit metadata to one inventory source:

```text
SourceAuthorityMetadata
- path
- authority_class_override?
- authority_eligible?
- reason
```

Rules:

- `reason` is required for an override;
- path is repository-relative and normalized;
- no lifecycle override in Phase 1;
- no source-kind override in Phase 1;
- `authority_eligible = false` removes the source from active authority candidate selection for all policies;
- omitted `authority_eligible` means eligible;
- authority-class override changes the source's **effective** authority class for inventory/authority purposes.

## 5.7 `RepositoryAuthorityConfig`

```text
RepositoryAuthorityConfig
- schema_version
- policies[]
- source_metadata[]
- content_sha256
```

No persistence.

## 5.8 `AuthorityCandidate`

A compact authority-facing projection of an observed source:

```text
AuthorityCandidate
- source_id
- path
- kind
- authority_class
- lifecycle
- tier_index
```

It may also include source revision metadata in machine-readable output where useful.

## 5.9 `AuthorityExclusion`

```text
AuthorityExclusion
- source_id
- path
- authority_class
- reason
```

Initial reasons:

```text
historical_lifecycle
explicitly_ineligible
not_in_policy
```

`not_in_policy` may be omitted from human output by default if it is too noisy, but the JSON contract should be explicit about whether it includes or omits these sources.

Choose one behavior and test it.

Recommended behavior:

- JSON includes all inventoried sources relevant to authority evaluation, including `not_in_policy`;
- text output summarizes `not_in_policy` count unless verbose output is later added.

## 5.10 `AuthorityResolution`

```text
AuthorityResolution
- policy
- status
- highest_observed_tier?
- highest_candidates[]
- lower_candidates[]
- missing_stronger_tiers[]
- excluded[]
```

Suggested status enum:

```text
candidates_found
no_eligible_candidates
```

Do not use:

```text
resolved_truth
winner
correct_source
```

Those names imply semantics Phase 1 cannot prove.

---

# 6. Built-In Authority Policy Set v1

Implement the following built-in policies.

They are a deterministic default policy set, not universal truth for every repository.

Repository config can replace a built-in policy by ID or add a custom policy.

---

## 6.1 `delivered_behavior`

Question:

> What source roles are preferred when reasoning about behavior that is actually delivered?

Tiers:

```text
tier 0: executable_truth
tier 1: verification_evidence
tier 2: generated_derivative
```

Important:

The current Context Integrity document scanner may not observe tier 0.

The resolver must surface that gap.

---

## 6.2 `architectural_intent`

Question:

> What source roles are preferred when reasoning about intended architecture?

Tiers:

```text
tier 0: decision
tier 1: architecture_product
tier 2: plan
```

This follows the repository's canonical development instructions:

- accepted durable decisions are strongest for specific architecture decisions;
- architecture docs carry system-wide intent;
- plans are future implementation guidance, not durable architecture by themselves.

---

## 6.3 `operating_instructions`

Question:

> What source roles are preferred when determining how agents/developers should operate in this repository?

Tiers:

```text
tier 0: operating_instruction
tier 1: architecture_product
tier 2: plan
```

This should make `AGENTS.md` a natural top candidate without hard-coding its path into the authority resolver.

---

## 6.4 `implementation_status`

Question:

> What source roles are preferred when determining what has been implemented or verified?

Tiers:

```text
tier 0: verification_evidence
tier 1: generated_derivative
tier 2: plan
```

Rationale:

- verified implementation evidence is stronger than a current-state summary;
- current-state is useful navigation/status, but remains a generated derivative;
- a plan is weaker evidence of implementation status.

This policy still does not inspect claims inside those sources.

---

## 6.5 `future_work`

Question:

> What source roles are preferred when determining authorized future implementation work?

Tiers:

```text
tier 0: plan
tier 1: architecture_product
tier 2: generated_derivative
```

A future plan can be the normative source for implementation requirements without proving delivery.

---

# 7. Repository Configuration

Introduce one optional repository-root file:

```text
.context-integrity.toml
```

Use Python 3.12 standard-library `tomllib`.

Do not add a TOML dependency.

## 7.1 Configuration File Is Optional

If absent:

- use built-in policy set v1;
- apply no source metadata;
- Phase 0 scan behavior must remain unchanged.

If present:

- read safely;
- hash raw config bytes;
- parse strictly;
- validate before using any config-derived policy or metadata.

## 7.2 Initial Schema

Example:

```toml
schema_version = 1

[[authority.policies]]
id = "architectural_intent"
description = "Repository-specific architectural authority order"
tiers = [
  ["decision"],
  ["architecture_product"],
  ["plan"],
]

[[authority.policies]]
id = "security_posture"
description = "Repository-specific security guidance"
tiers = [
  ["operating_instruction", "decision"],
  ["architecture_product"],
]

[[source_metadata]]
path = "docs/adr/0000-template.md"
authority_eligible = false
reason = "ADR template, not an accepted decision"

[[source_metadata]]
path = "docs/implementation-reports/release-verification.md"
authority_class = "verification_evidence"
reason = "Curated verification record with a non-standard filename"
```

## 7.3 Policy Override Semantics

If repository config defines a policy whose ID matches a built-in policy:

> the repository definition replaces that built-in policy completely.

Do not implement:

- inheritance;
- prepend/append;
- patch syntax;
- conditional tiers.

This keeps the behavior obvious.

If repository config defines a new policy ID, add it alongside built-ins.

## 7.4 Tier Validation

Reject configuration when:

- a policy has no tiers;
- a tier is empty;
- an authority class name is unknown;
- the same class appears more than once in one policy;
- `historical` is used as an active tier;
- `unknown` is used as an active tier;
- policy IDs are duplicated;
- policy ID format is invalid.

`generated_derivative` is allowed.

`executable_truth` is allowed even if no current document source produces it.

## 7.5 Source Metadata Validation

Reject configuration when:

- `path` is absolute;
- `path` contains traversal;
- path normalization changes semantic location outside root;
- source-metadata entries duplicate the same normalized path;
- neither `authority_class` nor `authority_eligible` is present;
- `reason` is missing/blank;
- `authority_class` value is invalid.

Do not support lifecycle metadata in this phase.

## 7.6 Stale Source Metadata

If a valid source-metadata entry references a path that is not in the observed inventory:

- do not fail the scan;
- emit a structured warning:

```text
authority_metadata_source_missing
```

This keeps config robust to file deletion/rename while making stale policy visible.

---

# 8. Configuration Security and Consistency

The authority config controls tool behavior and must be read more strictly than an ordinary optional document.

## 8.1 Reuse the Existing Safe-Read Boundary

Do not introduce a casual:

```python
Path(".context-integrity.toml").read_text()
```

path that bypasses Phase 0's symlink/race protections.

Reuse or refactor the existing safe repository-relative read mechanism.

## 8.2 Fail Closed on Unsafe Config

If `.context-integrity.toml` exists but is:

- a symlink;
- unreadable;
- malformed TOML;
- oversized;
- invalid against schema;
- replaced/changed between the policy read and the inventory observation in a way that makes the applied config revision inconsistent;

return a configuration error.

Do not silently ignore the config and fall back to built-ins.

## 8.3 Config Revision Consistency

The config's parsed bytes and the source revision represented in the inventory should correspond to the same content hash.

If the config changes during the scan:

- fail with a configuration-consistency error rather than applying policy from one byte sequence while reporting another.

This is one of the few Phase 1 places where a concurrent modification should fail closed because the file directly controls interpretation.

## 8.4 No Network

Config cannot:

- include URLs;
- import another config;
- fetch remote policy;
- execute commands;
- include Python.

Phase 1 config is pure local TOML data.

---

# 9. Config as an Inventory Source

Add `.context-integrity.toml` as an exact known context candidate.

Classify:

```text
kind: configuration
authority_class: unknown
lifecycle: unknown
```

Use a stable classification rule ID, e.g.:

```text
kind.configuration.exact_context_integrity
```

The config should:

- receive a normal `SourceId`;
- receive normal source revision metadata;
- appear in `scan`;
- never become an active policy candidate merely because it configures the tool.

---

# 10. Applying Explicit Authority Metadata

## 10.1 Authority-Class Override

If config contains:

```toml
[[source_metadata]]
path = "docs/reports/custom.md"
authority_class = "verification_evidence"
reason = "Curated verification record"
```

the effective `SourceRecord.authority_class` should be:

```text
verification_evidence
```

even if the built-in path classifier would have returned `unknown`.

Preserve:

- the original source kind;
- the original kind classification rule;
- the explicit override as an authority-dimension rule/evidence.

Suggested stable rule ID:

```text
authority.metadata.repository_override
```

Rule confidence:

```text
explicit
```

## 10.2 Do Not Change Overall Kind Confidence Semantics

Phase 0 currently treats top-level `ClassificationResult.confidence` as kind confidence, with per-dimension confidence in `basis`.

Preserve that behavior unless a separate architecture change is justified.

The authority override should appear in `basis` with `explicit` confidence; it should not falsely imply the kind classification itself became explicit.

## 10.3 Eligibility Metadata

If:

```toml
authority_eligible = false
```

the source remains visible in the inventory exactly as a source.

Authority resolution excludes it with reason:

```text
explicitly_ineligible
```

`scan` schema v1 does not need a new field for eligibility.

`explain` should show the explicit eligibility metadata and reason.

---

# 11. Authority Resolution Algorithm

Implement the resolver as a pure domain/application operation over:

- `InventoryManifest`;
- effective policy set;
- source metadata.

Do not perform filesystem I/O inside the resolver.

Conceptual algorithm:

```text
1. load selected policy
2. enumerate inventory sources
3. for each source:
   a. if lifecycle == historical:
        exclude: historical_lifecycle
   b. elif authority_eligible == false:
        exclude: explicitly_ineligible
   c. elif authority_class appears in selected policy:
        assign tier
   d. else:
        exclude/ignore: not_in_policy
4. find first tier with at least one candidate
5. candidates in that tier are highest_candidates
6. candidates in later tiers are lower_candidates
7. tiers before the selected tier become missing_stronger_tiers
8. sort all candidate lists deterministically by normalized path
9. do not choose one source inside highest_candidates
```

If no tier has candidates:

```text
status = no_eligible_candidates
highest_observed_tier = null
highest_candidates = []
missing_stronger_tiers = all policy tiers
```

No error.

---

# 12. Authority CLI

Add a Typer sub-app:

```text
context-integrity authority ...
```

Keep business logic outside `cli.py`.

---

## 12.1 `authority list`

```bash
context-integrity authority list [PATH]
```

Shows:

- policy ID;
- origin;
- short description.

Example:

```text
POLICY                  ORIGIN              DESCRIPTION
architectural_intent    builtin             Preferred sources for intended architecture
delivered_behavior      builtin             Preferred sources for delivered behavior
security_posture        repository_config   Repository-specific security authority
```

JSON is optional for this command.

Recommended: support `--format text|json` for consistency.

---

## 12.2 `authority show`

```bash
context-integrity authority show POLICY_ID [PATH]
```

Example:

```text
Policy: architectural_intent
Origin: builtin
Policy version: builtin-v1

Tier 0
  decision

Tier 1
  architecture_product

Tier 2
  plan
```

If repository config overrides the built-in, show:

```text
Origin: repository_config
Config revision: <sha256>
```

---

## 12.3 `authority resolve`

```bash
context-integrity authority resolve POLICY_ID [PATH]
```

Options:

```text
--format text|json
--output PATH
```

It performs a fresh inventory using the same repository/config semantics as `scan`.

Example text:

```text
Authority — architectural_intent

Policy origin: builtin
Highest observed tier: 1

Missing stronger tiers
  0  decision

Highest-precedence observed candidates
  docs/architecture.md
  docs/prd.md

Lower-precedence observed candidates
  docs/plans/phase-1-implementation-plan.md

Excluded
  docs/history/old-architecture.md  historical_lifecycle

Important:
This resolves observed source-role precedence only.
It does not prove that candidate claims are correct or mutually consistent.
```

That final warning should be prominent in human-readable output.

---

# 13. Existing Command Integration

## 13.1 `scan`

`scan` should load `.context-integrity.toml` when present so explicit authority-class metadata is reflected in the inventory.

If no config exists:

> existing Phase 0 golden JSON must remain byte-identical.

This is a hard regression gate.

## 13.2 `explain`

Extend:

```bash
context-integrity explain SOURCE_PATH
```

to show, when applicable:

- repository authority-class override;
- override reason;
- explicit authority eligibility;
- policy-independent note that eligibility affects Phase 1 authority resolution.

Do not turn `explain` into semantic policy resolution.

## 13.3 `version`

No semantic change.

---

# 14. Machine-Readable Authority Resolution Contract

Authority resolution gets its own schema-version-1 JSON projection.

Do not serialize dataclasses generically.

Use explicit projections, following the Phase 0 review lesson.

Illustrative shape:

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
  "policy": {
    "id": "architectural_intent",
    "description": "Preferred sources for intended architecture",
    "origin": "builtin",
    "policy_version": "builtin-v1",
    "config_revision": null,
    "tiers": [
      ["decision"],
      ["architecture_product"],
      ["plan"]
    ]
  },
  "resolution": {
    "status": "candidates_found",
    "highest_observed_tier": 1,
    "missing_stronger_tiers": [
      {
        "tier": 0,
        "classes": ["decision"]
      }
    ],
    "highest_candidates": [
      {
        "source_id": "src_...",
        "path": "docs/architecture.md",
        "kind": "architecture",
        "authority_class": "architecture_product",
        "lifecycle": "unknown",
        "tier": 1,
        "content_sha256": "..."
      }
    ],
    "lower_candidates": [],
    "excluded": [
      {
        "source_id": "src_...",
        "path": "docs/history/old-architecture.md",
        "authority_class": "historical",
        "reason": "historical_lifecycle"
      }
    ]
  },
  "warnings": []
}
```

Exact key names may be refined during implementation, but preserve these semantics.

## 14.1 Determinism

Stable authority JSON must:

- use repository-relative paths;
- sort candidates by path;
- sort excluded items deterministically;
- use stable tier order from policy;
- omit timestamps by default;
- omit absolute local paths;
- contain no source bodies;
- end with newline.

Two runs on unchanged repository/config state should be byte-identical.

---

# 15. Error Model

Add:

```text
ConfigurationError
```

Recommended exit code:

```text
6  invalid/unsafe/inconsistent Context Integrity configuration
```

Preserve:

```text
0  success
2  CLI usage / unknown requested policy
3  repository scan failure
4  output write failure
5  warnings with --fail-on-warning
6  configuration error
```

`authority resolve` returning no eligible candidates is a valid result and exits `0`.

Malformed repository config exits `6`.

Unknown requested policy ID exits `2`.

---

# 16. Architecture / Module Changes

Recommended small additions:

```text
src/context_integrity/
  authority.py
  configuration.py
```

Extend existing modules only where responsibilities already belong.

Suggested ownership:

## `models.py`

May add:

- `AuthorityClass.EXECUTABLE_TRUTH`;
- `SourceKind.CONFIGURATION`;
- compact authority/config dataclasses if the code remains readable.

Do not add filesystem I/O.

## `configuration.py`

Owns:

- config path;
- safe config loading;
- TOML parsing;
- validation;
- normalized source metadata;
- config content hash.

It should call/refactor existing safe repository read primitives rather than invent unsafe I/O.

## `authority.py`

Owns:

- built-in policy set;
- policy merge/override;
- authority resolution;
- source eligibility application;
- pure authority-domain behavior.

No filesystem traversal.

## `classification.py`

Owns:

- config-file kind classification;
- application of explicit authority-class override to authority dimension.

Do not move policy ordering into classification.

## `inventory.py`

Orchestrates:

- repository discovery;
- config load;
- source inventory;
- source metadata application;
- stale metadata warning aggregation.

Do not put policy resolution here.

## `rendering.py`

Owns explicit projections/rendering for:

- authority list/show;
- authority resolution JSON/text;
- extended explain output.

## `cli.py`

Wires new `authority` commands.

No policy logic.

---

# 17. Backward Compatibility Requirements

These are mandatory.

## 17.1 Existing No-Config Repository

When `.context-integrity.toml` is absent:

- existing Phase 0 source classification remains unchanged;
- existing Phase 0 scan JSON goldens remain byte-identical;
- existing `scan` exit behavior remains unchanged;
- existing `explain` behavior remains compatible;
- existing security protections remain intact.

## 17.2 Existing Schema Version 1

Do not add Phase 1-specific fields to Phase 0 inventory JSON merely for convenience.

The existing explicit inventory-v1 projection should remain a stable contract.

Authority resolution has a separate schema-v1 projection.

## 17.3 Existing Rule IDs

Do not rename Phase 0 rule IDs.

Add new IDs only.

---

# 18. Detailed Implementation Work Breakdown

## Step 0 — Close Phase 0 State Cleanly

Before Phase 1 code:

- confirm current Phase 0 review-fix state passes `make check`;
- confirm current-state/report accurately describe the delivered baseline;
- do not edit the completed Phase 0 plan to retroactively describe Phase 1.

If the repository has already recorded Phase 0 closure, do not duplicate closure work.

---

## Step 1 — Extend Domain Vocabulary

Add:

```text
AuthorityClass.EXECUTABLE_TRUTH
SourceKind.CONFIGURATION
```

Add Phase 1 authority/config domain models.

Tests:

- enum contract;
- serialization;
- duplicate-tier validation;
- policy IDs.

---

## Step 2 — Built-In Policy Set

Implement immutable built-in v1 definitions.

Tests must assert exact policy IDs and tier ordering.

The built-in policy set should be easy to inspect without repository I/O.

---

## Step 3 — Config Schema Parser

Implement strict TOML parse from bytes.

Tests:

- absent config;
- valid config;
- malformed TOML;
- unsupported schema version;
- unknown key policy decision;
- invalid policy ID;
- duplicate policy ID;
- empty tiers;
- duplicate class across tiers;
- invalid authority class;
- historical/unknown active tier rejection;
- duplicate source metadata path;
- invalid path;
- missing reason;
- empty override.

Prefer rejecting unknown top-level/table keys so typos do not silently alter authority behavior.

---

## Step 4 — Safe Config Loading

Integrate with existing repository-safe read boundary.

Tests:

- regular config;
- symlink config rejected;
- unreadable config rejected;
- oversized config rejected;
- config replacement/change detected;
- no absolute path leak in error text where existing repository error policy avoids it.

---

## Step 5 — Config Source Discovery and Classification

Add `.context-integrity.toml` to exact context candidates.

Classify:

```text
configuration / unknown / unknown
```

Test:

- candidate discovery;
- rule ID;
- source ID/hash;
- config appears in scan when present.

---

## Step 6 — Authority-Class Overrides

Apply `source_metadata.authority_class`.

Requirements:

- kind unchanged;
- lifecycle unchanged;
- effective authority class changed;
- explicit authority rule appended to classification basis;
- top-level kind confidence unchanged.

Tests:

- unknown -> verification override;
- decision -> unknown override if allowed by chosen validator;
- historical lifecycle still remains historical and cannot become active authority merely via class override.

Recommended rule:

> Even if authority class is explicitly overridden, historical lifecycle always excludes active authority resolution.

---

## Step 7 — Authority Eligibility

Apply `authority_eligible`.

Tests:

- false excludes candidate;
- source still appears in inventory;
- explain shows reason;
- stale metadata produces warning;
- eligible omission defaults true.

---

## Step 8 — Policy Merge

Merge built-ins + repository policy definitions.

Rules:

- no config: built-ins only;
- new ID: append custom policy;
- same ID: replace built-in completely;
- output sorted by policy ID for listing;
- tier ordering remains declared ordering.

Tests:

- custom addition;
- built-in replacement;
- deterministic policy list.

---

## Step 9 — Pure Authority Resolver

Implement as a pure function over manifest/config/policy.

Tests:

- tier 0 observed;
- tier 0 missing/tier 1 observed;
- all tiers missing;
- multiple same-tier candidates;
- historical exclusion;
- explicit ineligible exclusion;
- lower-precedence candidate retention;
- no recency sorting;
- path-deterministic sorting;
- executable-truth gap.

---

## Step 10 — Authority JSON Projection

Add explicit schema-v1 renderer.

Golden fixtures:

1. built-in `architectural_intent`;
2. missing-stronger-tier `delivered_behavior`;
3. repository config override/custom metadata.

Do not use generic dataclass recursion for the public contract.

---

## Step 11 — Human Authority Rendering

Implement text output for:

- `list`;
- `show`;
- `resolve`.

Must visibly say:

> This resolves source-role precedence only; it does not establish claim correctness or agreement.

---

## Step 12 — CLI Wiring

Add Typer authority subcommands.

Tests:

- help;
- list;
- show;
- resolve text;
- resolve JSON;
- output file;
- unknown policy;
- config error exit 6;
- no candidates still exit 0.

---

## Step 13 — Integrate Config with `scan`

When config absent:

- assert existing JSON goldens remain byte-identical.

When config present:

- config source appears;
- explicit authority override affects inventory classification;
- stale metadata warning appears.

---

## Step 14 — Extend `explain`

Show:

- explicit authority class override;
- override reason;
- eligibility override;
- eligibility reason.

Do not show policy winner unless the user calls `authority resolve`.

---

## Step 15 — Documentation

Update README with:

- what authority policy means;
- built-in policy table;
- `.context-integrity.toml` example;
- explicit warning that source precedence is not claim truth;
- authority CLI examples;
- current limitations.

Create Phase 1 implementation report at completion.

Update `docs/current-state.md` only after verification.

Do not rewrite the PRD or architecture unless implementation discovers a true durable architecture change.

---

# 19. Test Fixture Plan

Reuse Phase 0 synthetic repositories and add small targeted fixtures.

## Fixture A — `authority-basic`

Contains:

```text
AGENTS.md
docs/architecture.md
docs/prd.md
docs/adr/0001-storage.md
docs/plans/phase-1.md
docs/implementation-reports/phase-0.md
docs/current-state.md
docs/history/old-architecture.md
```

Expected examples:

```text
architectural_intent:
  highest tier = decision
  highest candidate = ADR
  architecture/prd lower
  plan lower
  historical excluded

operating_instructions:
  highest candidate = AGENTS.md
```

## Fixture B — `authority-missing-executable`

Contains verification/current-state evidence but no executable-truth source.

Expected:

```text
delivered_behavior:
  highest observed tier = verification_evidence
  missing stronger tier = executable_truth
```

## Fixture C — `authority-config`

Contains:

```text
.context-integrity.toml
docs/adr/0000-template.md
docs/custom-verification.md
```

Config:

- template ineligible;
- custom verification gets explicit authority class;
- custom policy defined.

Expected deterministic result.

## Fixture D — `authority-invalid-config`

Cases can be generated separately:

- malformed TOML;
- duplicate policy;
- empty tier;
- unknown class;
- traversal path;
- missing reason.

## Fixture E — `authority-config-race`

Use controlled test hooks/monkeypatching to show config content changing between policy load and observed inventory does not produce a silently inconsistent result.

---

# 20. Required Test Categories

## Domain

- built-in IDs;
- tier equality;
- no duplicate class in policy;
- stable enums.

## Configuration

- strict parsing;
- schema version;
- safe paths;
- deterministic merge;
- source metadata.

## Classification

- config file kind;
- explicit authority override;
- Phase 0 rules unchanged.

## Resolution

- every built-in policy;
- missing stronger tiers;
- historical exclusion;
- explicit exclusion;
- multiple top candidates;
- no candidates;
- deterministic ordering.

## Rendering

- authority JSON goldens;
- no dataclass-layout coupling;
- no absolute paths/timestamps;
- text disclaimer.

## CLI

- all authority commands;
- exit codes;
- output files;
- malformed config.

## Regression

- all 129+ existing tests continue to pass;
- Phase 0 JSON goldens byte-identical with no config.

---

# 21. Quality Gates

Before Phase 1 is complete:

```bash
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check
```

must pass.

No network.

No model/API credentials.

No external database.

If current repository conventions use a different writable cache path, keep the command logically equivalent.

---

# 22. Security Acceptance Criteria

- [ ] no `shell=True`;
- [ ] config parsing executes no code;
- [ ] no config includes/imports;
- [ ] no network;
- [ ] config symlink/path escape fails closed;
- [ ] config read reuses safe repository-relative read boundary;
- [ ] invalid config is not silently ignored;
- [ ] config revision used for policy matches observed config content;
- [ ] source-metadata paths cannot traverse outside repository;
- [ ] authority JSON contains no source bodies;
- [ ] authority JSON contains no absolute local root;
- [ ] repository content cannot inject terminal control sequences unescaped;
- [ ] policy IDs/descriptions are safely rendered.

---

# 23. Phase 1 Acceptance Criteria

Phase 1 is complete only when all of the following are true.

## Domain / Semantics

- [ ] `AuthorityClass.EXECUTABLE_TRUTH` exists.
- [ ] `.context-integrity.toml` is represented as `SourceKind.CONFIGURATION`.
- [ ] authority policy is question-specific, not global.
- [ ] policies contain ordered equal-precedence tiers.
- [ ] multiple top-tier candidates are not treated as contradictions.
- [ ] historical lifecycle excludes active authority candidacy.
- [ ] missing stronger tiers are explicit.
- [ ] "highest observed" is never represented as "correct truth".
- [ ] no recency/mtime/Git-time authority inference exists.

## Built-In Policies

- [ ] `delivered_behavior` implemented exactly as specified.
- [ ] `architectural_intent` implemented exactly as specified.
- [ ] `operating_instructions` implemented exactly as specified.
- [ ] `implementation_status` implemented exactly as specified.
- [ ] `future_work` implemented exactly as specified.
- [ ] built-in policy version is explicit/stable.

## Configuration

- [ ] optional `.context-integrity.toml` supported.
- [ ] no config preserves Phase 0 behavior.
- [ ] schema version validated.
- [ ] repository policy can replace built-in by ID.
- [ ] repository policy can add custom ID.
- [ ] invalid/duplicate tiers fail.
- [ ] `historical` and `unknown` cannot be active policy tiers.
- [ ] source authority-class override supported.
- [ ] source authority eligibility supported.
- [ ] override reason required.
- [ ] stale metadata path emits structured warning.
- [ ] lifecycle override is not supported.
- [ ] config is safely read and hashed.
- [ ] unsafe/invalid config fails with exit 6.

## CLI / Output

- [ ] `authority list` works.
- [ ] `authority show` works.
- [ ] `authority resolve` works.
- [ ] text resolution clearly states its semantic limitation.
- [ ] authority JSON has schema version 1.
- [ ] JSON uses explicit projection.
- [ ] JSON is deterministic.
- [ ] JSON contains no absolute root or source body.
- [ ] no-candidate resolution exits 0.
- [ ] unknown policy exits 2.
- [ ] config error exits 6.

## Integration / Regression

- [ ] `scan` applies explicit authority-class metadata.
- [ ] `explain` shows explicit authority metadata/eligibility.
- [ ] config source is inventoried.
- [ ] Phase 0 no-config JSON goldens remain byte-identical.
- [ ] existing security/repository protections remain intact.
- [ ] no database added.
- [ ] no LLM/model dependency added.
- [ ] no Codebase Intelligence dependency added.
- [ ] no claim model/extraction added.
- [ ] no supersession graph added.

## Testing / Docs

- [ ] all built-in policies tested.
- [ ] config validation thoroughly tested.
- [ ] authority golden JSON tests pass.
- [ ] Phase 0 regression suite passes.
- [ ] full offline `make check` passes.
- [ ] README documents Phase 1 behavior and limitations.
- [ ] Phase 1 implementation report maps every acceptance criterion.
- [ ] current-state updated only after verification.

---

# 24. Non-Acceptance Examples

The following are specifically wrong for Phase 1.

## Wrong: One Universal Authority Score

```python
AUTHORITY = {
    "code": 100,
    "adr": 90,
    "architecture": 80,
    "plan": 70,
}
```

Why wrong:

Authority depends on the question.

---

## Wrong: Newest Same-Tier Source Wins

```text
architecture-v3.md is newer than architecture.md,
therefore it is authoritative.
```

Why wrong:

Recency does not establish supersession.

---

## Wrong: Multiple ADRs Mean Contradiction

Two decision records in the top tier may cover different topics.

Claim extraction/semantic comparison does not exist yet.

---

## Wrong: Highest Observed Means Highest Possible

If executable truth is not indexed, verification evidence can be the highest **observed** tier without becoming equivalent to executable truth.

---

## Wrong: Config Silently Ignored

A malformed authority config must fail closed.

---

## Wrong: Use an LLM to Pick the Best Doc

Phase 1 is deterministic authority policy, not semantic arbitration.

---

## Wrong: Add Active/Superseded Metadata Now

Explicit lifecycle/supersession is Phase 2.

Phase 1 may exclude already-detected historical sources, but it must not introduce an active/superseded model.

---

# 25. Future Compatibility

## Phase 2 — Lifecycle / Supersession

Phase 2 should be able to replace:

```text
historical vs unknown
```

with explicit:

```text
draft
active
superseded
historical
expired
invalid
```

Authority resolution should then consume richer lifecycle decisions without changing policy tier semantics.

## Phase 3 — Claims

Claims should reference:

```text
SourceId + SourceRevision
```

and use the Phase 1 authority policy to determine which source roles can govern a claim type.

Phase 3 may finally answer:

> Which claim is authoritative?

Phase 1 only answers:

> Which observed source roles are preferred for this question?

## Phase 7 — Codebase Intelligence

The companion engine may supply:

```text
executable_truth
```

and other structured evidence.

The `delivered_behavior` policy should then naturally start observing its tier 0 without redesign.

This is an important reason to model unobserved stronger tiers now.

---

# 26. Suggested Implementation Commit Structure

A reasonable series:

1. `phase1: add authority domain model and built-in policies`
2. `phase1: add repository authority configuration`
3. `phase1: add source authority metadata and resolution`
4. `phase1: add authority CLI and stable rendering`
5. `phase1: add regression fixtures docs and implementation report`

This is guidance, not a requirement.

Do not combine unrelated cleanup.

---

# 27. Implementation Report Requirements

At completion create:

```text
docs/implementation-reports/phase-1-implementation-report.md
```

Include:

- implementation commit(s);
- exact current baseline;
- files/modules changed;
- authority model delivered;
- config schema delivered;
- built-in policy matrix;
- CLI examples;
- JSON schema example;
- Phase 0 compatibility result;
- test/quality results;
- security verification;
- deviations from plan;
- limitations;
- acceptance-criterion mapping;
- inputs/recommendations for Phase 2.

Distinguish:

```text
implemented
verified
deferred
```

Do not use the plan itself as evidence of implementation.

---

# 28. Definition of Done

Phase 1 is done when Context Integrity can deterministically answer:

> **For this kind of question, what source roles does the repository policy prefer, which eligible observed sources occupy the strongest observed tier, and which stronger tiers are currently unobserved?**

while being explicit that it still cannot answer:

> **Which semantic claim is correct, whether same-tier sources agree, or whether one source supersedes another?**

That distinction is the main correctness requirement of Phase 1.
