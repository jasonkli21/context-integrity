# Context Integrity — Phase 3 Detailed Implementation Plan

**Phase:** 3 — Claims and Provenance
**Status:** Ready for implementation
**Date:** 2026-10-15
**Repository baseline:** `14ce25d6fcc3ecf65a8aaf79c177323ac3cb5772` (`fix phases 0-2 independent review findings`)
**Parent documents:** `docs/prd.md`, `docs/architecture.md`
**Predecessor:** Phase 2 — Lifecycle and Supersession
**Related project:** Codebase / Context Intelligence Engine, still intentionally unintegrated in this phase

---

# 1. Phase Objective

Phase 3 introduces the first claim-level domain model on top of the reviewed source inventory, authority, lifecycle, and supersession layers.

The phase should let Context Integrity answer:

> **What structured claims are explicitly declared, exactly where did each declaration come from, and which observed source revisions does the claim depend on?**

Phase 2 operates primarily at source/file granularity:

```text
source
  -> identity
  -> revision
  -> kind
  -> authority class
  -> lifecycle
  -> supersession
```

Phase 3 adds a new semantic unit:

```text
claim
  -> stable claim ID
  -> type
  -> subject / predicate / value
  -> declaration provenance
  -> source-revision dependencies
  -> independent claim validity state
```

The important architectural shift is:

```text
a file is no longer treated as one indivisible truth object
```

while preserving an equally important boundary:

```text
declared claim != verified truth
```

Phase 3 therefore builds the representation and provenance layer required by later contradiction, drift, revalidation, and context-compilation phases without implementing those later judgments yet.

---

# 2. Current Delivered Baseline

Phase 3 must build on the post-review-fix Phase 0–2 stack, not the original Phase 2 delivery.

Reference baseline:

```text
14ce25d6fcc3ecf65a8aaf79c177323ac3cb5772
fix phases 0-2 independent review findings
```

At that baseline, the repository has delivered:

- deterministic local repository discovery;
- repository identity protected from inherited Git boundary/config corruption;
- safe bounded source reads;
- stable `SourceId`;
- raw-byte `SourceRevision` with content SHA-256, Git HEAD, and working-tree status;
- source classification;
- five question-specific authority policies;
- equal-precedence authority tiers;
- explicit global authority eligibility;
- seven lifecycle states;
- schema-v2 lifecycle metadata;
- directional source supersession;
- lifecycle-aware authority gating;
- `scan`, `explain`, `authority ...`, and `lifecycle ...`;
- stable inventory JSON v1;
- stable authority JSON v1;
- stable lifecycle JSON v1;
- cumulative independent-review fixes for Phases 0–2;
- an offline quality gate reported as Ruff + 353 tests passing at the baseline.

`docs/current-state.md` explicitly identifies the next expected product step as:

```text
Phase 3 — Claims and Provenance
```

and states that Phase 3 should:

- use `SourceId`;
- use raw-byte `SourceRevision` dependencies;
- keep claim validity separate from source lifecycle;
- avoid broad claim extraction at this stage.

## 2.1 Baseline Verification Requirement

Before implementation, rerun:

```bash
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check
```

The historical reference count is 353 tests.

If HEAD has moved beyond `14ce25d6...`, do not force the repository back to that commit. Instead:

1. inspect the newer commits;
2. verify whether they are accepted Phase 0–2 fixes or documentation changes;
3. treat actual HEAD as the implementation baseline;
4. record the actual baseline SHA and test count in the Phase 3 implementation report.

If a new unresolved Phase 0–2 correctness finding exists, do not hide it inside Phase 3 work.

---

# 3. Product Boundary

## 3.1 In Scope

Phase 3 includes:

- a stable claim identifier;
- an explicit structured claim representation;
- deterministic explicit claim declarations;
- claim declaration provenance;
- source-revision dependencies;
- resolution of dependency paths to observed `SourceId` + `SourceRevision`;
- explicit distinction between:
  - claim validity;
  - source lifecycle;
  - provenance completeness;
- a configuration schema revision that can declare claims;
- a dedicated `claims` domain module;
- `claims list`;
- `claims show`;
- deterministic claims JSON v1;
- explainable warnings for unresolved claim dependencies;
- compatibility with all Phase 0–2 public contracts;
- focused tests and implementation evidence.

## 3.2 Explicitly Out of Scope

Do **not** implement:

- semantic contradiction detection;
- claim agreement scoring;
- automatic claim validation;
- automatic claim invalidation;
- automatic claim supersession;
- automatic claim extraction from arbitrary Markdown prose;
- parsing prose to discover assertions;
- ADR-specific body parsing;
- LLM/model claim extraction;
- embeddings/vector search;
- claim authority resolution;
- choosing a winning claim;
- drift detection;
- stale-document detection;
- plan-vs-delivery evaluation;
- architecture invariant evaluation;
- context contracts;
- task-context compilation;
- persistence/database storage;
- Codebase Intelligence integration;
- code symbol parsing;
- cross-repository claims;
- mutation commands;
- automatic rewriting of claim declarations;
- CI enforcement.

Phase 3 is the **structured claim and provenance substrate**, not the integrity evaluator built on top of it.

---

# 4. Central Design Decision: Explicit Claims in Configuration Schema v3

The first claim authoring surface should be explicit and deterministic.

Extend `.context-integrity.toml` with:

```text
schema_version = 3
```

Schema v3 retains all schema-v2 behavior and adds explicit claim declarations.

Example:

```toml
schema_version = 3

[[claims]]
id = "context_integrity_owns_normative_interpretation"
claim_type = "architectural_intent"
subject = "context_integrity"
predicate = "owns"
value = "normative interpretation of context"
scope = "repository"
depends_on = [
  "docs/architecture.md",
  "docs/prd.md",
]
```

This is intentionally a **bootstrap declarative surface**, not a claim-extraction strategy for the mature product.

Why start here:

- the repository already has a strict, bounded, fail-closed TOML parser;
- configuration bytes already have a verified content hash;
- configuration revision consistency is already enforced;
- no new parser dependency is needed;
- no source prose needs to be trusted as executable instructions;
- claim authoring is explicit;
- claim IDs can remain stable across formatting changes;
- later deterministic or model extractors can emit the same domain model without changing claim consumers.

Important:

> A claim declared in `.context-integrity.toml` is an explicit assertion, not proof that the assertion is true.

The configuration file is the declaration source. Other referenced files are dependencies/evidence inputs, not falsely attributed declaration sources.

---

# 5. Configuration Schema Evolution

## 5.1 Supported Versions

After Phase 3:

```text
schema_version = 1
schema_version = 2
schema_version = 3
```

Semantics:

```text
v1
- authority policies
- authority source metadata

v2
- all v1 behavior
- lifecycle metadata
- source supersession

v3
- all v2 behavior
- explicit claims
```

## 5.2 Strict Backward Compatibility

Schema v1 must reject:

- lifecycle;
- supersession;
- claims.

Schema v2 must reject:

- claims.

Schema v3 may use:

- authority;
- source metadata;
- lifecycle;
- supersession;
- claims.

Do not silently treat a v1/v2 file containing claim keys as v3.

## 5.3 Recommended Root Shape

Conceptually:

```toml
schema_version = 3

[authority]
# existing policies

[[source_metadata]]
# existing metadata

[[supersession]]
# existing edges

[[claims]]
# Phase 3 claim declarations
```

No additional claim file is required in Phase 3.

---

# 6. Claim Declaration Schema

Each `[[claims]]` table must contain:

```text
id
claim_type
subject
predicate
value
```

Optional:

```text
scope
depends_on[]
```

Conceptually:

```text
ClaimSpec
- id
- claim_type
- subject
- predicate
- value
- scope?
- depends_on[]
```

## 6.1 `id`

Requirements:

- explicit;
- repository-wide unique;
- stable across scans;
- nonblank;
- machine-safe identifier;
- does not depend on array position or claim text hash.

Recommended validation:

```regex
[a-z][a-z0-9_-]*
```

Do not generate the public claim ID from the claim text.

Reason:

Text changes should not silently replace identity when the repository owner intended to revise the same logical claim.

## 6.2 `claim_type`

`claim_type` is a stable semantic category identifier.

Use the same conservative identifier validation as claim IDs.

Examples:

```text
architectural_intent
delivered_behavior
implementation_status
operating_instruction
future_work
security_constraint
```

Phase 3 must **not** require `claim_type` to match an authority-policy ID.

That mapping may become useful later, but enforcing it now would prematurely couple claim representation to authority resolution.

## 6.3 `subject`

Required nonblank string.

Examples:

```text
context_integrity
ModelRouter
storage_backend
Phase 3
```

No ontology is imposed yet.

## 6.4 `predicate`

Required nonblank string.

Examples:

```text
owns
must_not_depend_on
uses
is_implemented
supersedes
```

Do not infer inverse predicates or normalize semantics beyond validation.

## 6.5 `value`

Required nonblank string.

Phase 3 uses a string value deliberately.

Do not introduce:

- arbitrary nested TOML values;
- JSON-like objects;
- expression languages;
- executable predicates.

A richer typed value model can be introduced later if actual use requires it.

## 6.6 `scope`

Optional nonblank string.

Examples:

```text
repository
storage
agent_runtime
phase_3
```

No scope hierarchy or matching engine is required.

## 6.7 `depends_on`

Optional array of repository-relative paths.

Example:

```toml
depends_on = [
  "docs/architecture.md",
  "docs/prd.md",
]
```

Rules:

- each path uses existing repository-path normalization;
- absolute paths are rejected;
- `..` traversal is rejected;
- Windows drive/UNC ambiguity is rejected;
- trailing directory syntax is rejected;
- duplicate normalized paths within one claim are rejected;
- `.context-integrity.toml` should be rejected as an explicit dependency because declaration provenance already captures it;
- paths are resolved only against observed inventory sources;
- missing dependency paths are not configuration syntax errors.

The final point is important:

> A syntactically valid claim can outlive or temporarily lose one of its referenced sources.

That should be inspectable rather than causing the whole configuration to become unparsable.

---

# 7. Claim Domain Model

Add claim-specific domain types in `models.py` only where they are genuinely shared.

Recommended models:

```text
ClaimId
ClaimValidity
ClaimSpec
ClaimProvenance
ClaimDependency
ClaimRecord
ClaimsOverview
```

Avoid a generic semantic graph framework in this phase.

## 7.1 `ClaimId`

Conceptually:

```python
ClaimId = NewType("ClaimId", str)
```

The configured ID is the stable public logical identity.

Do not combine it with source hash to produce the public ID.

## 7.2 `ClaimValidity`

Phase 3 must make claim validity a distinct dimension.

Initial Phase 3 contract:

```text
unverified
```

That is deliberately the only produced validity state.

Do **not** derive:

```text
active claim
historical claim
superseded claim
invalid claim
```

from the lifecycle of a source dependency.

Later phases may expand claim validity to values such as stale, contradicted, superseded, or verified, but Phase 3 should not fabricate those judgments.

## 7.3 `ClaimProvenance`

Conceptually:

```text
ClaimProvenance
- source_id
- source_path
- source_revision
- locator
- extraction_method
- extractor_version
```

For Phase 3 explicit configuration claims:

```text
source_path = ".context-integrity.toml"
locator = "claim:<claim_id>"
extraction_method = "repository_config_explicit"
extractor_version = "claims-v1"
```

The provenance revision must use the observed raw-byte `SourceRevision` for the actual configuration source.

Do not create a weaker duplicate revision model.

## 7.4 `ClaimDependency`

Conceptually:

```text
ClaimDependency
- path
- source_id?
- source_revision?
- resolved
```

A resolved dependency must carry:

- normalized repository-relative path;
- observed `SourceId`;
- observed raw-byte `SourceRevision`.

Do not store only Git HEAD.

Dirty working-tree bytes are part of the dependency identity.

If a source record exists but no trustworthy raw-byte content revision is available, the dependency is not provenance-complete.

## 7.5 `ClaimRecord`

Conceptually:

```text
ClaimRecord
- id
- claim_type
- subject
- predicate
- value
- scope?
- validity
- provenance
- dependencies[]
- provenance_complete
```

`provenance_complete` is **not** claim validity.

A claim can be:

```text
validity = unverified
provenance_complete = true
```

or:

```text
validity = unverified
provenance_complete = false
```

## 7.6 `ClaimsOverview`

Conceptually:

```text
ClaimsOverview
- repository
- config_sha256
- claims[]
- warnings[]
- schema_version = 1
```

This is derived inspection output.

It is rebuildable and non-authoritative.

---

# 8. Claim Provenance Semantics

## 8.1 Declaration Provenance

Every Phase 3 claim is explicitly declared in `.context-integrity.toml`.

Therefore the declaration provenance is:

```text
config SourceId
+
config raw-byte SourceRevision
+
stable claim locator
+
explicit extraction method/version
```

This avoids the false statement:

> “architecture.md asserted this claim”

when Phase 3 did not actually parse the architecture document.

## 8.2 Dependency Provenance

`depends_on` means:

> This explicit claim depends on the observed content of this source.

It does **not** mean:

- the source literally contains the same sentence;
- the source proves the claim;
- the source is authoritative for the claim;
- the claim is valid.

Those are later integrity/authority questions.

## 8.3 No Source-Lifecycle-to-Claim-Validity Mapping

These examples must all remain possible:

```text
source lifecycle = active
claim validity = unverified
```

```text
source lifecycle = historical
claim validity = unverified
```

```text
source lifecycle = superseded
claim validity = unverified
```

Phase 3 may expose source lifecycle elsewhere, but it must not convert it into claim validity.

This is a durable architectural invariant.

---

# 9. Claim Resolution Pipeline

Add a pure claims-resolution layer after inventory is complete.

Conceptually:

```text
Repository discovery
  ↓
Configuration load/validation
  ↓
Inventory + lifecycle/supersession resolution
  ↓
Verified config revision
  ↓
ClaimSpec declarations from RepositoryConfig
  ↓
Claim resolver
  ├── locate config SourceRecord
  ├── attach declaration SourceId/SourceRevision
  ├── resolve depends_on paths
  ├── attach dependency SourceId/SourceRevision
  ├── emit unresolved dependency warnings
  └── produce deterministic ClaimsOverview
```

Recommended module:

```text
src/context_integrity/claims.py
```

Responsibilities:

- claim ID/type validation helpers if not purely parser-local;
- explicit claim resolution;
- provenance attachment;
- dependency resolution;
- provenance completeness;
- claim warnings;
- `ClaimsOverview`.

Does not own:

- TOML parsing;
- authority resolution;
- lifecycle changes;
- contradiction evaluation;
- drift;
- rendering;
- CLI I/O.

---

# 10. Missing Dependency Semantics

A configured dependency may no longer be present in the inventory.

Example:

```toml
[[claims]]
id = "storage_backend_is_postgres"
claim_type = "architectural_intent"
subject = "storage_backend"
predicate = "is"
value = "postgres"
depends_on = ["docs/storage-architecture.md"]
```

If `docs/storage-architecture.md` is missing:

- keep the claim;
- set that dependency to unresolved;
- set `provenance_complete = false`;
- emit:

```text
claim_dependency_missing
```

Do not:

- silently drop the claim;
- mark the claim invalid;
- mark the claim stale;
- fail the entire config;
- infer a replacement source.

If a matching source exists but its trustworthy content revision is unavailable:

- keep the dependency visibly unresolved/incomplete;
- emit a distinct warning such as:

```text
claim_dependency_revision_unavailable
```

Again, do not change claim validity.

---

# 11. Claim Identity and Revision Semantics

Claim identity and claim observation must remain distinct.

## 11.1 Stable Logical ID

```text
claim ID = configured stable ID
```

## 11.2 Observed Declaration Revision

The claim declaration is observed at:

```text
.context-integrity.toml raw-byte SourceRevision
```

This means:

- editing claim text changes declaration provenance revision;
- retaining the same ID preserves logical identity;
- dirty config bytes are distinguished from HEAD.

## 11.3 Dependency Revisions

Each resolved dependency is pinned to its own observed raw-byte `SourceRevision`.

A claim therefore depends on exact observed content, not merely paths.

This is foundational for later revalidation.

---

# 12. Configuration Parsing and Validation

Extend `configuration.py` conservatively.

## 12.1 Schema Branching

Keep strict schema behavior obvious.

Conceptually:

```text
v1 allowed root keys
v2 allowed root keys
v3 allowed root keys
```

A compact implementation is fine, but do not make the parser permissive enough that older versions accidentally accept claim keys.

## 12.2 Claim Validation

Reject:

- missing required fields;
- blank required strings;
- invalid claim IDs;
- duplicate claim IDs;
- invalid claim-type identifiers;
- unsafe dependency paths;
- duplicate normalized dependencies;
- dependency on `.context-integrity.toml`;
- unknown claim keys.

Preserve the current security property:

> parser exceptions containing repository-controlled text must not leak arbitrary configuration content through fatal error messages.

## 12.3 No Claim Body Execution

Claim strings are data.

Do not:

- evaluate them;
- import them;
- interpret them as Python;
- interpret predicate/value as expressions;
- turn them into prompts automatically.

---

# 13. Source Candidate Boundary

Phase 3 dependency resolution is intentionally limited to currently inventoried sources.

This means:

- ordinary code files that Phase 0–2 do not inventory are not suddenly pulled into the inventory just because a claim references them;
- no second code scanner is added;
- no Codebase Intelligence substitute is created.

If a claim dependency points at a non-inventoried ordinary code file:

- it remains unresolved;
- emit the same clear dependency warning;
- do not expand repository candidate discovery in Phase 3 merely to satisfy that reference.

This preserves the project boundary with Codebase Intelligence and keeps Phase 3 focused.

---

# 14. Claims CLI

Add a Typer sub-app:

```text
context-integrity claims ...
```

No mutation commands.

## 14.1 `claims list`

```bash
context-integrity claims list [PATH]
```

Options:

```text
--format text|json
--output PATH
```

Human-readable example:

```text
Claims

ID                                              TYPE                    VALIDITY    PROVENANCE
context_integrity_owns_normative_interpretation architectural_intent    unverified  complete
phase_2_is_delivered                            implementation_status   unverified  complete
legacy_storage_rule                             architectural_intent    unverified  incomplete

Warnings: 1
```

The list should be concise.

Do not print full claim values in a way that makes large lists unreadable.

## 14.2 `claims show`

```bash
context-integrity claims show CLAIM_ID [PATH]
```

Options:

```text
--format text|json
--output PATH
```

Human-readable example:

```text
Claim: context_integrity_owns_normative_interpretation

Type: architectural_intent
Subject: context_integrity
Predicate: owns
Value: normative interpretation of context
Scope: repository

Validity: unverified
Provenance complete: true

Declared by:
  path: .context-integrity.toml
  source id: src_...
  sha256: ...
  git status: tracked_modified
  locator: claim:context_integrity_owns_normative_interpretation
  extraction: repository_config_explicit
  extractor version: claims-v1

Depends on:
  docs/architecture.md
    source id: src_...
    sha256: ...
  docs/prd.md
    source id: src_...
    sha256: ...

Note:
  claim validity is not derived from source lifecycle or authority resolution
```

Do not run authority resolution.

Do not perform contradiction analysis.

Unknown claim ID:

```text
exit 2
```

Output write failure:

```text
exit 4
```

Configuration failure:

```text
exit 6
```

No new exit code is required.

---

# 15. Claims JSON v1

Claims must use a separate machine-readable projection.

Do not add claim fields to:

- inventory JSON v1;
- authority JSON v1;
- lifecycle JSON v1.

Illustrative contract:

```json
{
  "schema_version": 1,
  "repository": {
    "id": "repo_...",
    "name": "context-integrity",
    "git": {
      "available": true,
      "head": "...",
      "dirty": true
    }
  },
  "config_sha256": "...",
  "claims": [
    {
      "id": "context_integrity_owns_normative_interpretation",
      "claim_type": "architectural_intent",
      "subject": "context_integrity",
      "predicate": "owns",
      "value": "normative interpretation of context",
      "scope": "repository",
      "validity": "unverified",
      "provenance_complete": true,
      "provenance": {
        "source_id": "src_...",
        "path": ".context-integrity.toml",
        "revision": {
          "content_sha256": "...",
          "git_head": "...",
          "git_status": "tracked_modified",
          "observed_revision_basis": "content_sha256+git"
        },
        "locator": "claim:context_integrity_owns_normative_interpretation",
        "extraction_method": "repository_config_explicit",
        "extractor_version": "claims-v1"
      },
      "dependencies": [
        {
          "path": "docs/architecture.md",
          "resolved": true,
          "source_id": "src_...",
          "revision": {
            "content_sha256": "...",
            "git_head": "...",
            "git_status": "tracked_clean",
            "observed_revision_basis": "content_sha256+git"
          }
        }
      ]
    }
  ],
  "warnings": []
}
```

Exact field names may be refined during implementation if a cleaner explicit projection emerges, but the semantics above are normative.

---

# 16. Determinism Requirements

Claims JSON must:

- sort claims by claim ID;
- sort dependencies by normalized path;
- use repository-relative paths;
- use stable explicit projection;
- omit timestamps by default;
- omit absolute local roots;
- omit source bodies;
- preserve raw-byte content hashes;
- serialize unresolved dependencies explicitly;
- end with a newline.

Two runs against unchanged repository/config bytes must be byte-identical.

Do not sort by declaration order if claim IDs provide a stable canonical order.

---

# 17. Text Rendering Safety

Claim fields are repository-controlled text.

Text rendering must prevent terminal-control injection from at least:

- subject;
- predicate;
- value;
- scope;
- claim ID/type if validation somehow permits control characters;
- dependency paths;
- warning text derived from repository values.

JSON may represent the strings normally through JSON escaping.

Human terminal output should reuse the existing safe text rendering approach rather than introducing a second inconsistent escaping mechanism.

---

# 18. Compatibility Requirements

Phase 3 must preserve Phase 0–2 public behavior unless explicitly extended here.

## 18.1 Inventory

Inventory JSON remains schema v1.

No new keys.

Existing golden files remain byte-identical.

## 18.2 Authority

Authority JSON remains schema v1.

No claim fields.

Existing authority goldens remain byte-identical.

No claim-level authority resolution is added.

## 18.3 Lifecycle

Lifecycle JSON remains schema v1.

No claim fields.

Existing lifecycle goldens remain byte-identical.

## 18.4 Existing CLI

No behavior changes should be required for:

```text
scan
explain
authority ...
lifecycle ...
```

except any minimal documentation/navigation update.

## 18.5 Existing Configuration

Existing v1/v2 configs must parse exactly as before.

Do not make schema v3 the implicit default for existing files.

---

# 19. Security and Trust Boundaries

Phase 3 must preserve all existing security constraints.

Required:

- no network;
- no model/API calls;
- no shell execution;
- no claim evaluation;
- no dynamic imports;
- no source body execution;
- no new unbounded file reads;
- dependency paths normalized and repository-relative;
- no following outside-repository symlinks;
- configuration consistency remains fail-closed;
- machine output contains metadata/claim values only, not arbitrary dependent source bodies;
- terminal output escapes control characters;
- claims do not acquire authority merely by being declared.

Important:

> Explicitness is provenance, not trust.

A repository can explicitly declare a false claim.

Phase 3 must represent that fact without blessing it as correct.

---

# 20. Recommended Module Changes

Add:

```text
src/context_integrity/claims.py
tests/test_claims.py
```

Update:

```text
src/context_integrity/models.py
src/context_integrity/configuration.py
src/context_integrity/rendering.py
src/context_integrity/cli.py
```

Potentially update:

```text
README.md
docs/current-state.md
docs/plans/README.md
docs/implementation-reports/README.md
```

Do not add:

```text
integrity.py
contradictions.py
compiler.py
storage.py
database schema
provider framework
model client
```

unless an existing module with that name already legitimately exists for a narrow reason.

The `evidence.py` seam may remain a small reserved boundary in Phase 3. Do not expand it into Codebase Intelligence integration merely because claim dependencies resemble evidence.

---

# 21. Detailed Implementation Work Breakdown

## Step 0 — Verify Actual Baseline

Before edits:

```bash
git status --short
git log -5 --oneline
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check
```

Record:

- baseline SHA;
- baseline test count;
- whether the worktree was clean;
- any discrepancy from the historical 353-test reference.

Do not rewrite completed Phase 0–2 plans.

---

## Step 1 — Add Claim Models

Implement the minimum domain types:

```text
ClaimId
ClaimValidity
ClaimSpec
ClaimProvenance
ClaimDependency
ClaimRecord
ClaimsOverview
```

Keep them immutable/frozen consistent with existing domain models.

Add focused unit tests for:

- claim validity enum contract;
- stable ID validation if validation is model-level;
- no accidental lifecycle coupling.

---

## Step 2 — Extend RepositoryConfig for Claim Specs

Add:

```text
claims: tuple[ClaimSpec, ...] = ()
```

Prefer keyword construction where touching `RepositoryConfig` creation to reduce positional-field mistakes.

Existing default construction must remain valid.

---

## Step 3 — Add Configuration Schema v3

Update strict config parsing.

Prove:

```text
v1 + claims -> error
v2 + claims -> error
v3 + authority-only -> valid
v3 + lifecycle -> valid
v3 + supersession -> valid
v3 + claims -> valid
```

Keep all existing Phase 1/2 restrictions.

---

## Step 4 — Validate Claim Declarations

Add targeted tests for:

- valid minimal claim;
- valid scope;
- valid dependencies;
- duplicate claim ID;
- blank ID;
- malformed ID;
- blank claim type;
- malformed claim type;
- blank subject;
- blank predicate;
- blank value;
- unknown claim key;
- unsafe dependency path;
- duplicate normalized dependency path;
- config self-dependency.

Do not create a combinatorial test explosion.

Use table-driven cases.

---

## Step 5 — Implement Claim Resolution

Create `claims.py`.

Given an `InventoryManifest`:

1. read `RepositoryConfig.claims`;
2. locate the observed config `SourceRecord`;
3. build declaration provenance from its `SourceId` and `SourceRevision`;
4. resolve each dependency path against `manifest.sources`;
5. attach exact observed identity/revision;
6. mark incomplete dependencies explicitly;
7. emit warnings;
8. produce sorted `ClaimsOverview`.

This should be pure over the already-observed manifest.

Do not reread dependency source bodies.

---

## Step 6 — Enforce Claim/Lifecycle Separation

Add focused regression tests proving:

1. a claim depending on an `active` source remains `unverified`;
2. a claim depending on a `historical` source remains `unverified`;
3. a claim depending on a `superseded` source remains `unverified`;
4. source lifecycle does not auto-change claim validity;
5. missing dependency changes provenance completeness, not validity.

This is one of the most important Phase 3 tests.

---

## Step 7 — Pin Raw-Byte Revision Semantics

Add tests proving that a resolved dependency carries the exact observed `SourceRevision`.

At least one test should distinguish dirty working-tree content from Git HEAD, if the existing repository fixture utilities make that focused and inexpensive.

Do not invent a separate claim hash that loses source revision semantics.

---

## Step 8 — Add Claims Rendering

Implement:

```text
render_claims_text
render_claims_json
```

or equivalent clearly separated functions.

Requirements:

- explicit JSON projection;
- deterministic sorting;
- no dataclass dumping;
- no absolute roots;
- no dependent source bodies;
- safe terminal text;
- newline-terminated JSON.

---

## Step 9 — Add `claims list/show`

Add CLI subcommands.

Test:

- list text;
- list JSON;
- show text;
- show JSON;
- output file;
- unknown claim ID -> exit 2;
- invalid config -> exit 6;
- output failure -> exit 4.

Keep CLI logic thin.

---

## Step 10 — Add Focused Golden Contracts

Recommended fixtures:

```text
tests/fixtures/claims-v1-basic.json
tests/fixtures/claims-v1-unresolved.json
```

The basic fixture should prove:

- more than one claim;
- deterministic claim-ID ordering;
- declaration provenance;
- resolved dependency revision;
- independent validity.

The unresolved fixture should prove:

- claim retained;
- unresolved dependency represented;
- provenance incomplete;
- warning emitted;
- validity remains unverified.

Avoid large generated fixtures.

---

## Step 11 — Run Compatibility Checks

Verify:

- all original inventory goldens unchanged;
- all original authority goldens unchanged;
- all original lifecycle goldens unchanged;
- schema-v1 configs unchanged;
- schema-v2 configs unchanged;
- no unrelated README/CLI output drift.

Use targeted tests during development, then full gate.

---

## Step 12 — Documentation and Implementation Report

Create:

```text
docs/implementation-reports/phase-3-implementation-report.md
```

Record:

- baseline SHA;
- implementation SHA if committed;
- exact design delivered;
- any deviations from this plan;
- focused test evidence;
- final `make check` evidence;
- compatibility evidence;
- new JSON fixtures;
- known limitations.

Update `README.md` only for actual user-facing claim configuration/commands.

Update `docs/current-state.md` only after implementation is verified.

Expected post-implementation state:

```text
Current phase: Phase 3 — Claims and Provenance
Status: implemented; independent review pending
Next expected step: independent Phase 3 review, then Phase 4 planning
```

Do not claim Phase 4 behavior exists.

---

# 22. Focused Test Strategy

Testing should be risk-driven rather than exhaustive for its own sake.

Primary risk groups:

## 22.1 Configuration Compatibility

Prove:

- v1/v2 remain strict;
- v3 is additive;
- malformed claim declarations fail closed.

## 22.2 Identity and Provenance

Prove:

- stable claim IDs;
- config declaration revision attached;
- dependency `SourceId` attached;
- dependency raw-byte `SourceRevision` attached;
- dirty content does not collapse to HEAD identity.

## 22.3 Semantic Separation

Prove:

- declaration != verification;
- claim validity != source lifecycle;
- provenance completeness != claim validity;
- missing dependency != config syntax failure.

## 22.4 Machine Contract

Prove:

- explicit schema;
- deterministic order;
- no absolute root/source body;
- unresolved dependency visible;
- old schemas unchanged.

## 22.5 Security

Prove:

- unsafe paths fail;
- terminal-controlled claim text is escaped;
- no source execution/network/model behavior is introduced.

Do not add dozens of near-duplicate cases where a compact table test proves the same invariant.

---

# 23. Acceptance Criteria

Phase 3 is complete only when all applicable items below are satisfied.

## Baseline and Scope

- [ ] implementation is based on the current accepted Phase 0–2 head;
- [ ] baseline quality gate is recorded;
- [ ] no unresolved pre-Phase-3 defect is silently absorbed;
- [ ] no contradiction/drift/compiler/LLM/persistence scope creep is introduced.

## Claim Domain

- [ ] stable explicit `ClaimId` exists;
- [ ] claim has type, subject, predicate, value, optional scope;
- [ ] claim validity is a separate dimension;
- [ ] Phase 3 claims are `unverified`;
- [ ] source lifecycle does not determine claim validity;
- [ ] provenance completeness does not determine claim validity.

## Configuration

- [ ] schemas 1, 2, and 3 are supported;
- [ ] v1 rejects claims;
- [ ] v2 rejects claims;
- [ ] v3 preserves all v2 behavior;
- [ ] v3 supports explicit claims;
- [ ] duplicate claim IDs fail;
- [ ] unknown claim keys fail;
- [ ] unsafe dependency paths fail;
- [ ] duplicate normalized dependencies fail;
- [ ] config self-dependency is rejected;
- [ ] existing config revision consistency remains fail-closed.

## Provenance

- [ ] every claim has declaration provenance;
- [ ] declaration provenance uses config `SourceId`;
- [ ] declaration provenance uses raw-byte `SourceRevision`;
- [ ] locator identifies the specific claim declaration;
- [ ] extraction method/version are explicit;
- [ ] resolved dependencies carry `SourceId`;
- [ ] resolved dependencies carry raw-byte `SourceRevision`;
- [ ] Git HEAD alone is never treated as sufficient dependency revision for dirty content.

## Missing Dependencies

- [ ] missing dependency does not invalidate the whole config;
- [ ] claim remains visible;
- [ ] unresolved dependency is explicit;
- [ ] provenance completeness becomes false;
- [ ] warning is emitted;
- [ ] validity remains unverified;
- [ ] no replacement source is inferred.

## CLI

- [ ] `claims list` works;
- [ ] `claims show` works;
- [ ] text and JSON are supported;
- [ ] output file is supported;
- [ ] unknown claim exits 2;
- [ ] output write failure exits 4;
- [ ] configuration error exits 6;
- [ ] commands do not resolve claim authority;
- [ ] commands do not perform contradiction/drift analysis.

## JSON

- [ ] separate claims JSON schema v1 exists;
- [ ] explicit projection is used;
- [ ] claims sorted deterministically by ID;
- [ ] dependencies sorted deterministically by path;
- [ ] repository-relative paths only;
- [ ] no timestamp by default;
- [ ] no absolute root;
- [ ] no dependency source bodies;
- [ ] unresolved dependencies are machine-readable;
- [ ] JSON ends with newline.

## Compatibility

- [ ] inventory JSON v1 unchanged;
- [ ] authority JSON v1 unchanged;
- [ ] lifecycle JSON v1 unchanged;
- [ ] existing golden fixtures remain byte-identical;
- [ ] existing CLI semantics remain intact;
- [ ] no new network/model/database dependency is added;
- [ ] no Codebase Intelligence dependency is added.

## Security

- [ ] no claim text execution;
- [ ] no dynamic import/eval;
- [ ] no network;
- [ ] no shell execution added;
- [ ] bounded config read remains;
- [ ] dependency paths use existing normalization;
- [ ] terminal text escapes control characters;
- [ ] explicit claim declaration does not make the claim authoritative or verified.

## Quality Gate and Evidence

- [ ] focused Phase 3 tests pass;
- [ ] full `make check` passes offline;
- [ ] exact final test count is recorded;
- [ ] `git diff --check` passes;
- [ ] implementation report exists;
- [ ] `docs/current-state.md` reflects only verified delivered behavior;
- [ ] implementation is ready for independent review.

---

# 24. Non-Goals Rechecked at Completion

Before declaring Phase 3 complete, explicitly verify that the implementation did **not** accidentally add:

```text
semantic contradiction detection
automatic validity decisions
claim authority winner selection
source-lifecycle-to-claim-lifecycle propagation
body/prose extraction
LLM extraction
drift checks
context contracts
context compiler
database persistence
Codebase Intelligence coupling
cross-repository claims
automatic mutation
```

A clean Phase 3 should make these later capabilities easier without pretending to implement them.

---

# 25. Expected Phase 3 End State

After Phase 3, the system should conceptually support:

```text
Repository
  ↓
Source inventory
  ↓
Source identity + raw-byte revisions
  ↓
Authority metadata
  ↓
Lifecycle + supersession
  ↓
Explicit structured claim declarations
  ↓
Claim provenance
  ├── declaration source/revision
  └── dependency source/revisions
```

It should **not yet** support:

```text
Claim A contradicts Claim B
Claim A is stale
Claim A wins
Claim A is verified
Architecture drift exists
```

Those judgments belong to later phases.

The Phase 3 foundation is successful when later integrity logic can consume claims without needing to rediscover:

- what a claim is;
- how it is identified;
- where it came from;
- what exact observed source bytes it depends on.
