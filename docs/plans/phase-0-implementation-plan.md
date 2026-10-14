# Context Integrity — Phase 0 Detailed Implementation Plan

**Phase:** 0 — Context Inventory and Source Classification  
**Status:** Ready for implementation  
**Date:** 2026-10-13  
**Parent documents:** `docs/prd.md`, `docs/architecture.md`  
**Integration constraint:** No dependency on the Codebase / Context Intelligence Engine in this phase.

---

## 1. Phase Objective

Build the smallest useful Context Integrity system:

> **A local, read-only CLI that inventories repository context sources, assigns transparent provisional classifications, records revision/provenance metadata, and explains why each source was classified that way.**

Phase 0 establishes the durable primitives required by all later work:

```text
RepositoryRef
SourceId
SourceRecord
SourceKind
AuthorityClass
LifecycleState
SourceRevision
ClassificationResult
```

It does **not** attempt to determine whether the repository is internally consistent yet.

The phase should answer:

- What context artifacts exist?
- What kind of artifact is each one?
- What broad authority role does it appear to play?
- Is it obviously historical?
- What exact revision/content did we observe?
- Which classification rule produced the result?
- Which artifacts remain unclassified?

---

# 2. Why Phase 0 Comes First

Later Context Integrity capabilities require stable source identity.

Without this phase, later features risk building on vague concepts such as:

```text
"some architecture docs"
"the current plan"
"old files"
"the source of truth"
```

Phase 0 turns these into inspectable records.

Example:

```json
{
  "path": "docs/plans/phase-4.md",
  "kind": "implementation_plan",
  "authority_class": "plan",
  "lifecycle": "unknown",
  "content_sha256": "...",
  "classification_basis": [
    "path_segment:plans"
  ]
}
```

That record does not claim Phase 4 is active, complete, or authoritative for delivered behavior.

Those judgments belong later.

---

# 3. Scope

## 3.1 In Scope

- initialize and verify the Python project;
- CLI;
- repository discovery;
- Git-aware file enumeration;
- context-source candidate selection;
- repository-relative path normalization;
- content hashing;
- source IDs;
- provisional source-kind classification;
- provisional authority-class classification;
- conservative lifecycle classification;
- human-readable inventory;
- JSON inventory;
- classification explanation;
- warnings;
- deterministic output;
- tests;
- documentation.

## 3.2 Explicitly Out of Scope

Do not implement:

- code AST parsing;
- symbol extraction;
- dependency graphs;
- Codebase Intelligence integration;
- authority precedence resolution;
- claim extraction;
- contradiction detection;
- stale-document detection;
- semantic drift;
- architectural invariants;
- supersession edges;
- context contracts;
- context compilation;
- embeddings;
- vector search;
- LLM calls;
- database persistence;
- daemon/server;
- MCP;
- web UI;
- multi-repository workspace execution;
- cloud storage;
- automatic file modification.

If implementation begins requiring one of these, stop and reassess scope.

---

# 4. Recommended Stack

Use:

```text
Python: 3.12+
Packaging/environment: uv + pyproject.toml
CLI: Typer
Testing: pytest
Lint/format: Ruff
Typing: standard type hints; add strict checker only if it does not slow Phase 0
```

Use the standard library for:

- `pathlib`;
- `hashlib`;
- `subprocess`;
- `json`;
- `enum`;
- `dataclasses` if Pydantic is not chosen.

A reasonable implementation choice is:

- dataclasses + enums for Phase 0;
- introduce Pydantic later if external schema validation/configuration makes it valuable.

Do not add:

- ORM;
- SQLite;
- async framework;
- web framework.

All dependencies should be locked reproducibly.

---

# 5. Initial Repository Layout

The scaffold already establishes the target shape:

```text
context-integrity/
├── AGENTS.md
├── README.md
├── pyproject.toml
├── Makefile
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
│   │   └── repositories/
│   ├── test_repository.py          # add during implementation
│   ├── test_acquisition.py         # add during implementation
│   ├── test_classification.py      # add during implementation
│   ├── test_rendering.py           # add during implementation
│   └── test_cli.py
└── docs/
    ├── prd.md
    ├── architecture.md
    ├── current-state.md
    ├── ai/
    ├── adr/
    ├── reviews/
    ├── implementation-reports/
    └── plans/
        └── phase-0-implementation-plan.md
```

Do not create separate `domain/`, `application/`, `ports/`, and `adapters/` trees yet.

The logical boundaries from `architecture.md` matter; the filesystem can stay simple until complexity justifies a refactor.

---

# 6. CLI Contract

Executable:

```bash
context-integrity
```

The scaffold includes placeholder `scan` and `explain` commands that intentionally fail until Phase 0 behavior is implemented.

## 6.1 `scan`

```bash
context-integrity scan [PATH]
```

`PATH` defaults to `.`.

Examples:

```bash
context-integrity scan .
context-integrity scan ~/code/my-project
context-integrity scan . --format json
context-integrity scan . --format json --output inventory.json
context-integrity scan . --summary-only
```

Options:

```text
--format text|json       default: text
--output PATH            write rendered output to file instead of stdout
--summary-only           omit per-source table from text output
--include-runtime-meta   include machine-local runtime metadata in JSON
--fail-on-warning        non-zero exit if warnings exist; default false
```

`--include-runtime-meta` exists so stable manifests can avoid embedding machine-specific absolute paths by default.

## 6.2 `explain`

```bash
context-integrity explain SOURCE_PATH [--root PATH]
```

Examples:

```bash
context-integrity explain docs/adr/0012-storage.md
context-integrity explain AGENTS.md
```

Output:

```text
Source: docs/adr/0012-storage.md

kind: decision_record
authority_class: decision
lifecycle: unknown

Matched rules:
1. directory "adr" -> decision_record
2. decision_record -> authority class "decision"

Lifecycle:
- no explicit historical rule matched
- Phase 0 does not infer active/superseded status

Revision:
- sha256: ...
- git status: tracked_modified
```

## 6.3 `version`

```bash
context-integrity version
```

The scaffold already provides this command.

---

# 7. Exit Codes

Use a small stable scheme.

```text
0  success
2  CLI usage / invalid argument
3  repository could not be opened/scanned
4  output could not be written
5  completed with warnings when --fail-on-warning is set
```

Per-source warnings do not normally fail a scan.

---

# 8. Repository Discovery

Implement:

```python
discover_repository(path) -> RepositoryContext
```

## 8.1 Behavior

1. Resolve the requested path.
2. If inside a Git worktree:
   - discover Git repository root;
   - use that as scan root.
3. Otherwise:
   - use the supplied directory as scan root.
4. Gather:
   - repository name;
   - Git availability;
   - HEAD commit if available;
   - dirty status if available.
5. Do not require a remote.

## 8.2 Repository Identity

Phase 0 should construct:

```text
RepositoryRef
- id
- name
- identity_basis
```

Preferred basis:

1. normalized canonical Git remote if safely available;
2. otherwise repository name + deterministic local fallback.

The exact ID algorithm should be documented and deterministic.

Do not emit the canonical absolute path in stable JSON by default.

Record an `identity_basis` such as:

```text
git_remote
local_fallback
```

## 8.3 Git Invocation

Use subprocess argument arrays.

Never construct shell commands from repository content.

Example conceptually:

```python
subprocess.run(["git", "-C", root, "rev-parse", "HEAD"], ...)
```

Do not use `shell=True`.

---

# 9. Candidate File Discovery

Phase 0 inventories **context sources**, not every source-code file.

## 9.1 Git Repository

Prefer:

```text
git ls-files --cached --others --exclude-standard
```

This provides:

- tracked files;
- non-ignored untracked files;
- `.gitignore` behavior without reimplementing it.

Then apply context-source candidate filtering.

## 9.2 Non-Git Repository

Walk the filesystem while skipping known generated/vendor directories.

Default skipped directories:

```text
.git
.hg
.svn
node_modules
.venv
venv
__pycache__
.pytest_cache
.mypy_cache
.ruff_cache
target
dist
build
coverage
.coverage
vendor
.next
.cache
```

The list belongs in one constant with tests.

## 9.3 Candidate Context Sources

Phase 0 should consider these candidates.

### Root / well-known instruction files

```text
AGENTS.md
CLAUDE.md
GEMINI.md
CONTRIBUTING.md
README.md
README.rst
```

Also consider known agent-instruction locations such as:

```text
.github/copilot-instructions.md
```

Do not attempt exhaustive vendor-specific support yet.

### Documentation trees

Text/document files under:

```text
docs/
doc/
documentation/
adr/
adrs/
decisions/
architecture/
plans/
planning/
reviews/
releases/
history/
archive/
```

Supported Phase 0 extensions:

```text
.md
.mdx
.rst
.txt
.adoc
```

### Context-specific files

Any file whose name strongly suggests context metadata, for example:

```text
current-state.md
current_state.md
architecture.md
prd.md
product-requirements.md
```

## 9.4 Not Context Candidates by Default

Do not enumerate all:

```text
.py
.rs
.ts
.tsx
.go
.java
.cpp
```

That would move Phase 0 toward the Codebase Intelligence project.

Code may become evidence later through `EvidenceProvider`.

## 9.5 Symlinks

- do not follow symlinks outside root;
- safest Phase 0 behavior: skip symlink files and record a warning;
- add richer symlink handling only if a real repository requires it.

## 9.6 File Size

Set a defensive maximum size for hashing/inspection, e.g. 5 MiB.

If a candidate exceeds the limit:

- preserve an inventory record;
- set content hash to null;
- add warning `source_too_large`;
- do not read its body.

The exact default should be one named constant.

---

# 10. Path Normalization

Every stored source path must be:

- relative to repository root;
- `/` separated;
- free of `..`;
- case preserved;
- deterministic.

Example:

```text
docs/adr/0012-storage.md
```

Never persist:

```text
/Users/name/code/project/docs/adr/0012-storage.md
```

unless the user explicitly requested runtime metadata.

---

# 11. Source Identity

Implement:

```python
make_source_id(repository_id, normalized_path) -> SourceId
```

Recommended Phase 0 format:

```text
src_<truncated sha256>
```

Input:

```text
repository_id + "\0" + normalized_path
```

Properties:

- deterministic;
- opaque;
- no absolute path;
- collision-resistant enough for local use.

A rename may create a new ID in Phase 0.

That is acceptable.

---

# 12. Revision Metadata

For each source, record:

```text
SourceRevision
- content_sha256?
- git_head?
- git_status?
- observed_revision_basis
```

## 12.1 Content Hash

SHA-256 over raw file bytes.

## 12.2 Git Status

If Git is available, classify source status:

```text
tracked_clean
tracked_modified
untracked
deleted          # normally not discovered in current scan
unknown
```

A working tree may be dirty.

Never represent `git_head` alone as the observed content revision.

---

# 13. Source Classification

Classification should produce three separate values:

```text
kind
authority_class
lifecycle
```

plus explanation.

---

# 14. Source Kind Rules

Rule order matters.

Use the first high-confidence rule for `SourceKind`.

## 14.1 Agent Instructions

Exact/well-known:

```text
AGENTS.md
CLAUDE.md
GEMINI.md
.github/copilot-instructions.md
```

Result:

```text
kind = agent_instruction
authority_class = operating_instruction
```

## 14.2 Decision Records

Strong signals:

```text
path segment: adr
path segment: adrs
path segment: decisions
filename begins ADR-
filename matches numeric ADR convention inside ADR directory
```

Result:

```text
kind = decision_record
authority_class = decision
```

Lifecycle remains `unknown`.

Do not infer `active` merely because it is under `adr/`.

## 14.3 Implementation Plans

Strong path/name signals:

```text
plans/
planning/
implementation-plan
phase-*-plan
```

Result:

```text
kind = implementation_plan
authority_class = plan
```

## 14.4 Reviews

Signals:

```text
reviews/
*-review.md
post-implementation-review
independent-review
```

Result:

```text
kind = review
authority_class = verification_evidence
```

Note: a review is evidence that a review occurred, not proof that every reviewed claim is correct.

## 14.5 Verification Records

Signals:

```text
verification/
*-verification.md
verification-record
```

Result:

```text
kind = verification_record
authority_class = verification_evidence
```

## 14.6 Release Records

Signals:

```text
releases/
release-*.md
```

Result:

```text
kind = release_record
authority_class = verification_evidence
```

## 14.7 Current State

Signals:

```text
current-state.md
current_state.md
status/current*.md
```

Result:

```text
kind = current_state
authority_class = generated_derivative
```

Rationale:

A current-state document is a curated snapshot. It should not outrank executable truth or direct verification evidence.

## 14.8 Architecture

Signals:

```text
architecture.md
architecture/
*-architecture.md
system-design.md
```

Result:

```text
kind = architecture
authority_class = architecture_product
```

## 14.9 Product Requirements

Signals:

```text
prd.md
*-prd.md
product-requirements*
requirements/product*
```

Result:

```text
kind = product_requirement
authority_class = architecture_product
```

## 14.10 Handoffs

Signals:

```text
handoff
HANDOFF
CODEX_HANDOFF.md
```

Result:

```text
kind = handoff
authority_class = generated_derivative
```

## 14.11 Generated Summaries

Strong generated naming only:

```text
summary/
generated/
*-summary.md
```

Do not classify a generic document as generated merely because prose looks model-written.

Result:

```text
kind = generated_summary
authority_class = generated_derivative
```

## 14.12 README

Result:

```text
kind = readme
authority_class = architecture_product
```

The authority is provisional.

Phase 1 policy decides what a README can outrank for a specific claim type.

## 14.13 Other Documents

Other discovered document candidates:

```text
kind = other_document
authority_class = unknown
```

Never drop them silently.

---

# 15. Lifecycle Rules

Phase 0 is deliberately conservative.

## 15.1 Historical

Strong path signals:

```text
history/
historical/
archive/
archived/
deprecated/
```

Result:

```text
lifecycle = historical
```

Also set:

```text
authority_class = historical
```

while preserving the original `SourceKind`.

Example:

```text
docs/history/old-architecture.md

kind: architecture
authority_class: historical
lifecycle: historical
```

## 15.2 Unknown

Everything else defaults to:

```text
lifecycle = unknown
```

## 15.3 Do Not Infer

Do not infer these from filename age or Git timestamps:

```text
active
superseded
expired
invalid
```

Those require explicit semantics in later phases.

---

# 16. Classification Result

Implement:

```text
ClassificationResult
- kind
- authority_class
- lifecycle
- matched_rules[]
- basis
- confidence
```

Suggested confidence enum:

```text
explicit
strong
heuristic
unknown
```

Phase 0 uses:

- `strong` for exact/path conventions;
- `heuristic` for weaker filename patterns;
- `unknown` for fallback.

Do not invent numeric precision such as `0.873`.

---

# 17. Rule Explainability

Every rule gets a stable ID.

Examples:

```text
kind.agent_instruction.exact_agents
kind.decision.directory_adr
kind.plan.directory_plans
kind.architecture.filename
lifecycle.historical.directory_history
```

A `ClassificationResult` stores matched rule IDs.

This is important for:

- `explain`;
- debugging;
- future migration;
- test stability.

---

# 18. Human-Readable Scan Output

Default `scan` output should resemble:

```text
Context Integrity — Source Inventory

Repository: context-integrity
Revision: 8d4c1f2 (dirty)
Git: yes

Sources: 18

By kind
  architecture             2
  decision_record          4
  implementation_plan      3
  agent_instruction        1
  current_state            1
  review                   2
  readme                   1
  other_document           4

By authority class
  decision                 4
  architecture_product     3
  plan                     3
  verification_evidence    2
  operating_instruction    1
  generated_derivative     1
  unknown                  4

Lifecycle
  historical               3
  unknown                 15

Sources
PATH                                      KIND                  AUTHORITY              LIFECYCLE
AGENTS.md                                 agent_instruction     operating_instruction  unknown
docs/architecture.md                      architecture          architecture_product   unknown
docs/adr/0012-storage.md                  decision_record       decision               unknown
docs/plans/phase-0.md                     implementation_plan   plan                   unknown
docs/history/old-plan.md                  implementation_plan   historical             historical

Warnings: 0
Unclassified authority: 4
```

Formatting may adapt to terminal width, but the information should remain stable.

---

# 19. JSON Manifest Contract

Phase 0 JSON is the first machine-readable contract.

Top level:

```json
{
  "schema_version": 1,
  "repository": {},
  "sources": [],
  "summary": {},
  "warnings": []
}
```

## 19.1 Repository

```json
{
  "id": "repo_...",
  "name": "context-integrity",
  "identity_basis": "git_remote",
  "git": {
    "available": true,
    "head": "8d4c1f2...",
    "dirty": true
  }
}
```

No absolute path by default.

## 19.2 Source

```json
{
  "id": "src_...",
  "path": "docs/plans/phase-0.md",
  "kind": "implementation_plan",
  "authority_class": "plan",
  "lifecycle": "unknown",
  "revision": {
    "content_sha256": "...",
    "git_head": "8d4c1f2...",
    "git_status": "tracked_modified",
    "observed_revision_basis": "working_tree_content"
  },
  "classification": {
    "confidence": "strong",
    "matched_rules": [
      "kind.plan.directory_plans"
    ]
  },
  "size_bytes": 12345
}
```

## 19.3 Stable Output Rules

- sources sorted by path;
- count maps sorted consistently;
- no generation timestamp by default;
- no absolute local root by default;
- no raw document contents;
- no nondeterministic object ordering.

`--include-runtime-meta` may add:

```json
"runtime": {
  "resolved_root": "...",
  "observed_at": "..."
}
```

Runtime metadata is outside deterministic snapshot expectations.

---

# 20. Warnings

Warnings are structured.

Conceptual type:

```text
ScanWarning
- code
- path?
- message
```

Initial codes:

```text
source_unreadable
source_too_large
symlink_skipped
git_command_failed
hash_failed
candidate_metadata_failed
```

Warnings should appear in:

- human output;
- JSON.

A warning should not normally remove every other valid result.

---

# 21. Determinism Requirements

Given the same:

- repository contents;
- Git status;
- application version;

two JSON scans without runtime metadata should be byte-equivalent after canonical serialization.

Implementation requirements:

- sort input paths;
- sort output sources;
- sort summary keys;
- stable enum serialization;
- stable rule IDs;
- UTF-8 JSON;
- newline at EOF.

---

# 22. Application Flow

`scan` should execute approximately:

```text
1. discover_repository(path)
2. enumerate_files(repository)
3. select_context_candidates(files)
4. for each candidate:
     a. normalize path
     b. obtain file metadata
     c. safely hash
     d. obtain git status
     e. classify kind
     f. classify authority class
     g. classify lifecycle
     h. create SourceRecord
5. sort SourceRecords
6. aggregate summary
7. render text or JSON
8. write stdout/output file
```

Do not mix rendering into discovery/classification.

---

# 23. Detailed Implementation Work Breakdown

## Step 0 — Scaffold Verification

The repo scaffold should already provide:

- `pyproject.toml`;
- package structure;
- test structure;
- console entry point;
- Ruff config;
- pytest config;
- README quick start;
- canonical `AGENTS.md`.

Acceptance:

```bash
context-integrity --help
pytest
ruff check .
```

all run successfully after setup.

## Step 1 — Domain Models

Implement enums:

```text
SourceKind
AuthorityClass
LifecycleState
ClassificationConfidence
GitFileStatus
```

Implement dataclasses/models:

```text
RepositoryRef
SourceRevision
ClassificationResult
SourceRecord
ScanWarning
InventorySummary
InventoryManifest
```

Requirements:

- JSON-safe serialization;
- type annotations;
- no filesystem behavior inside models.

Tests:

- enum serialization;
- model roundtrip to dict/JSON;
- invariant validation if used.

## Step 2 — Repository Discovery

Implement repository root and Git metadata discovery.

Tests:

- called at Git root;
- called in nested directory;
- non-Git directory;
- Git unavailable/failure path.

Do not require a remote.

## Step 3 — File Enumeration

Implement:

```python
enumerate_repository_files(...)
```

Behavior:

- Git-aware enumeration when possible;
- filesystem fallback;
- deterministic sort;
- ignored/generated directory filtering.

Tests:

- tracked file;
- untracked nonignored file;
- gitignored file absent;
- generated directory absent;
- nested docs present.

## Step 4 — Candidate Selection

Implement:

```python
is_context_candidate(path) -> CandidateDecision
```

Keep candidate selection separate from semantic classification.

Tests should cover:

- root known files;
- docs tree;
- ADR tree;
- plan tree;
- generic source file rejected;
- generic Markdown under docs accepted;
- Markdown under node_modules rejected before this stage.

## Step 5 — Safe Metadata + Hashing

Implement:

- size;
- SHA-256;
- large-file handling;
- read-error warning.

Tests:

- normal file;
- zero-byte file;
- oversized file;
- unreadable fixture where platform permits;
- binary-like bytes do not crash hashing.

Do not parse document contents.

## Step 6 — Git Per-File Status

Implement enough status information to distinguish:

- tracked clean;
- tracked modified;
- untracked;
- unknown.

Avoid running one Git subprocess per file if a single porcelain-status invocation can build a lookup map.

This is the first modest performance requirement.

Tests:

- clean tracked;
- modified;
- untracked.

## Step 7 — Classification Engine

Implement rule functions that return:

```text
rule_id
dimension
result
confidence
```

Then compose:

```python
classify_source(path) -> ClassificationResult
```

Order rules explicitly.

Tests should be table-driven.

A useful test shape:

```python
@pytest.mark.parametrize(
    "path, kind, authority, lifecycle, expected_rule",
    [...]
)
```

Do not hide rule priority in a long chain of untested `if` statements.

## Step 8 — Historical Lifecycle Overlay

Kind classification and lifecycle classification run independently.

Test:

```text
docs/history/old-architecture.md
```

must yield:

```text
kind = architecture
authority_class = historical
lifecycle = historical
```

not:

```text
kind = unknown/historical
```

This test protects an important architectural distinction.

## Step 9 — Manifest Assembly

Implement application use case:

```python
build_inventory(root) -> InventoryManifest
```

This function orchestrates lower-level components.

It should not print.

Tests:

- deterministic source ordering;
- counts;
- warning aggregation;
- dirty repo metadata.

## Step 10 — JSON Renderer

Implement stable JSON.

Requirements:

- `schema_version = 1`;
- stable order;
- no absolute root by default;
- no runtime timestamp by default;
- newline at EOF.

Golden tests:

- simple repository;
- dirty repository;
- historical source.

## Step 11 — Text Renderer

Implement readable summary + optional table.

Requirements:

- counts;
- warnings;
- unknown count;
- Git status;
- all per-source classifications unless `--summary-only`.

Do not over-optimize terminal styling.

Plain output must remain readable when redirected to a file.

## Step 12 — `scan` CLI

Wire:

```bash
context-integrity scan
```

to the application layer.

Tests:

- default path;
- explicit path;
- JSON stdout;
- JSON output file;
- summary only;
- missing directory;
- fail-on-warning.

## Step 13 — `explain` CLI

Implement:

```bash
context-integrity explain <source>
```

Output must show:

- source path;
- kind;
- authority class;
- lifecycle;
- rule IDs;
- confidence;
- what Phase 0 intentionally did not infer.

Tests:

- ADR;
- plan;
- historical architecture;
- other document.

## Step 14 — Documentation

Update README with real CLI examples only after the behavior exists.

Add a Phase 0 implementation report under `docs/implementation-reports/`.

Keep `docs/current-state.md` concise and update it only after verification.

Developer note must remain explicit:

> Plans do not prove delivery, and Phase 0 classifications do not resolve authority conflicts.

---

# 24. Test Fixture Design

Create synthetic repositories rather than depending only on the project's own docs.

## Fixture A — `basic-context`

```text
AGENTS.md
README.md
src/app.py
docs/
  architecture.md
  current-state.md
  adr/
    0001-storage.md
  plans/
    phase-1.md
  reviews/
    phase-0-review.md
  misc.md
```

Expected:

- `src/app.py` not inventoried;
- all context docs inventoried;
- authority classes correct;
- lifecycle unknown.

## Fixture B — `history`

```text
docs/
  architecture.md
  history/
    old-architecture.md
    plans/
      old-plan.md
```

Expected:

- historical overlay;
- original kind retained.

## Fixture C — `git-ignore`

```text
docs/visible.md
generated/ignored.md
```

with ignore rules.

Expected:

- ignored file absent when Git enumeration is used.

## Fixture D — `dirty`

Tracked file modified + untracked context doc.

Expected correct Git statuses.

## Fixture E — `warnings`

- symlink;
- oversized context document.

Expected warnings without full scan failure.

---

# 25. Required Unit Tests

At minimum:

## Models

- serialization;
- enum stability;
- IDs deterministic.

## Repository

- Git root discovery;
- non-Git fallback;
- repository ID determinism.

## Acquisition

- candidate enumeration;
- ignore behavior;
- path normalization;
- symlink behavior;
- max-size behavior;
- hashing.

## Classification

Every built-in rule needs at least one positive test.

Priority conflicts need tests, e.g.:

```text
docs/history/adr/0001.md
```

should remain:

```text
kind: decision_record
authority: historical
lifecycle: historical
```

## Rendering

- stable JSON golden;
- summary counts;
- no absolute paths in stable JSON.

## CLI

- success;
- invalid path;
- output file;
- explain;
- warning exit behavior.

---

# 26. Quality Gates

Required before Phase 0 is considered complete:

```bash
pytest
ruff check .
ruff format --check .
```

The repo-level equivalent is:

```bash
make check
```

If static type checking is configured, it must also pass.

No network-backed tests are required.

No model/provider credentials are allowed in the Phase 0 test suite.

---

# 27. Performance Expectations

Phase 0 is not performance optimization work.

However:

- use a single Git listing command rather than `git status` per file;
- hash only context candidates;
- do not read full source-code trees;
- do not load candidate contents into memory unnecessarily.

Target behavior:

- common personal repositories should feel interactive;
- no obvious O(files × subprocesses) design.

No formal benchmark gate is required yet.

---

# 28. Security Acceptance Criteria

- no `shell=True`;
- no repository file execution;
- no network access;
- symlink escape not followed;
- output contains no raw document contents;
- stable JSON contains no absolute local root;
- malformed/unusual filename does not permit path traversal;
- unreadable source becomes warning, not unsafe fallback.

---

# 29. Phase 0 Acceptance Criteria

Phase 0 is complete only when all of the following are true.

## Functional

- [ ] `context-integrity scan .` works on a Git repository.
- [ ] Scan works on a non-Git directory.
- [ ] Git-ignored files are excluded in Git mode.
- [ ] Untracked nonignored context files are discoverable.
- [ ] Common context artifacts are classified.
- [ ] `SourceKind`, `AuthorityClass`, and `LifecycleState` are separate.
- [ ] Historical overlay preserves original source kind.
- [ ] Unknown classification is preserved rather than dropped.
- [ ] Every inventoried readable source receives a SHA-256 hash.
- [ ] Dirty repository content is not represented as equivalent to HEAD.
- [ ] `context-integrity explain` shows matched rules.
- [ ] JSON output uses repository-relative paths.
- [ ] JSON output has `schema_version: 1`.
- [ ] Stable JSON omits absolute root and current timestamp by default.
- [ ] Warnings are structured.
- [ ] `--fail-on-warning` behaves as documented.

## Architecture

- [ ] CLI does not own classification logic.
- [ ] Models do not perform filesystem I/O.
- [ ] Acquisition does not resolve authority precedence.
- [ ] No claim model is prematurely used to simulate Phase 3.
- [ ] No database is added.
- [ ] No LLM dependency is added.
- [ ] No Codebase Intelligence dependency is added.
- [ ] Evidence/provider concepts remain separate from classification.

## Testing

- [ ] Every classification rule has tests.
- [ ] Golden JSON fixture passes.
- [ ] Git clean/dirty/untracked tests pass.
- [ ] Historical path tests pass.
- [ ] Warning tests pass.
- [ ] CLI integration tests pass.
- [ ] Ruff passes.
- [ ] Entire test suite passes offline.

## Documentation

- [ ] README explains that classifications are provisional.
- [ ] README explains authority is resolved in a later phase.
- [ ] README explains relationship to Codebase Intelligence.
- [ ] Phase 0 implementation report can state exactly which acceptance criteria were met.

---

# 30. Non-Acceptance Examples

The following do **not** count as Phase 0 success.

## "We scan every file and ask an LLM what it is."

Fails deterministic/local-first architecture.

## "We mark the newest architecture doc active."

Fails lifecycle semantics.

## "We rank code > ADR > plan globally."

Prematurely implements an incorrect universal authority model.

## "We parse Python imports so we can detect architecture drift."

Invades the Codebase Intelligence boundary and later phases.

## "We put everything into SQLite because we'll need it eventually."

Adds persistence before a demonstrated need.

## "We generate a summary of every document."

Creates derived context before provenance/lifecycle foundations are ready.

---

# 31. Implementation Notes for Future Compatibility

Phase 0 should make these later additions straightforward.

## Phase 1 — Authority

`SourceRecord.authority_class` already exists.

Add:

```text
AuthorityPolicy
AuthorityQuery
AuthorityResolution
```

without changing source discovery.

## Phase 2 — Lifecycle

`LifecycleState` already exists.

Add explicit metadata + supersession edges without changing source identity.

## Phase 3 — Claims

Add claims that reference `SourceId + SourceRevision`.

Do not replace source records.

## Phase 4 — Drift

Use existing revisions and claims.

## Phase 7 — Codebase Intelligence

Add an `EvidenceProvider` adapter.

Do not replace the source scanner with Rust.

The Rust engine and document/source scanner solve different acquisition problems.

---

# 32. AI-Development Requirements for the Phase

Phase 0 should also validate the repository's AI-development organization.

Implementation sessions should use:

1. `AGENTS.md`;
2. `docs/current-state.md`;
3. this phase plan;
4. relevant `docs/architecture.md` sections;
5. target code/tests.

The implementation report should contain only delivery evidence and deviations rather than restating the entire plan.

If an implementation or review uncovers a durable architectural rule, move that rule into architecture/ADR/tests rather than leaving it solely in a report or review.

Do not add model-specific duplicated instructions.

---

# 33. Suggested Implementation Commit Structure

A clean implementation could use commits like:

1. `phase0: add domain models`
2. `phase0: add repository and source discovery`
3. `phase0: add deterministic source classification`
4. `phase0: add inventory renderers and explain command`
5. `phase0: add fixtures, tests, and implementation report`

This is guidance, not a requirement.

Avoid a single enormous commit if implementation is being reviewed phase-by-phase.

---

# 34. Implementation Report Requirements

At completion, create a Phase 0 implementation report containing:

- commit(s);
- files added/changed;
- architecture decisions made;
- deviations from this plan;
- CLI examples;
- acceptance-criteria mapping;
- test results;
- known limitations;
- classification ambiguities observed on real repositories;
- recommendations for Phase 1;
- confirmation that no Phase 1+ semantics were accidentally introduced.

The report should distinguish:

```text
implemented
verified
deferred
```

It must not treat this plan as proof of delivery.

---

# 35. Final Definition of Done

Phase 0 is done when Context Integrity can inspect a real repository and produce a deterministic, explainable answer to:

> **What context sources are present, what role does each appear to play, and what exact source revision did we observe?**

It is **not** yet expected to answer:

> **Which source wins, which claim is correct, or whether the architecture has drifted?**

Those questions become safe to implement only after Phase 0 has established trustworthy source identity and provenance.
