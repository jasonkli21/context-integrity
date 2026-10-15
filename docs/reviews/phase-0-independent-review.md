# Context Integrity — Phase 0 Independent Post-Implementation Review

**Reviewed commit:** `240dc93458ed11db901ede9cc264eb3e98a09594`
**Review date:** 2026-10-14
**Review mode:** Independent post-implementation review; no code changes made
**Fix handoff target:** Luna XHigh

---

## 15.1 Executive assessment

# PASS WITH REQUIRED FIXES

Phase 0 is substantially well-implemented and is close to being a sound foundation for Phase 1. The core architecture is appropriately simple, deterministic, and phase-bounded. The implementation keeps acquisition, classification, orchestration, rendering, and CLI concerns separate; it does not introduce authority resolution, supersession reasoning, claims, persistence, LLM calls, or Codebase Intelligence coupling. The existing test suite is broad for a Phase 0 repository and the exact reviewed commit passed its GitHub Actions lint, format, and 123-test job.

However, three findings should be fixed before Phase 1:

1. **F-001 (P1): Git repository discovery can be redirected to a different repository through target Git configuration.** `discover_repository()` trusts `git rev-parse --show-toplevel` and then starts subsequent Git operations from that returned path without proving it is still the same Git repository initially discovered. A crafted/local `core.worktree` can therefore cause a scan requested for repository A to inventory repository B if B is itself a Git repository.
2. **F-002 (P2): tracked context files deleted from the working tree are still emitted as inventory sources.** The recommended `git ls-files --cached --others --exclude-standard` enumeration includes unstaged deletions; the implementation retains those paths as `SourceRecord`s with unavailable content, contradicting the Phase 0 question "what context sources are present?" and the phase plan's own expectation that deleted files are normally not discovered.
3. **F-003 (P2): schema-version-1 JSON is coupled directly to internal dataclass layout through `dataclasses.asdict`.** A later internal model field can silently become public JSON while `schema_version` remains 1. The current bytes are deterministic, but the version boundary is not protected from future model evolution.

A **Luna XHigh fix pass is required**. The required fix set is narrow and does not require reopening the Phase 0 architecture.

---

## 15.2 Review scope and evidence

### Commit / revision reviewed

- Repository: `jasonkli21/context-integrity`
- Commit: `240dc93458ed11db901ede9cc264eb3e98a09594`
- Commit message: `initial commit`
- Review is of the complete repository state at that SHA because this is the initial commit.

### Canonical repository context consulted

In the intended review order:

1. `AGENTS.md`
2. `docs/current-state.md`
3. `docs/plans/phase-0-implementation-plan.md`
4. `docs/architecture.md`
5. repository implementation under `src/context_integrity/`
6. tests under `tests/`
7. `docs/implementation-reports/phase-0-implementation-report.md`
8. `README.md` where public Phase 0 behavior needed confirmation

No accepted ADR modifies the relevant Phase 0 requirements.

### Supplied review materials consulted

- Phase 0 Sol Medium implementation prompt
- Phase 0 implementation report
- Phase 0 independent Sol High review prompt / Luna XHigh handoff requirements

The implementation report was treated as claimed implementation evidence, not as proof of correctness.

### Exact implementation areas inspected

- `src/context_integrity/models.py`
- `src/context_integrity/repository.py`
- `src/context_integrity/acquisition.py`
- `src/context_integrity/classification.py`
- `src/context_integrity/inventory.py`
- `src/context_integrity/rendering.py`
- `src/context_integrity/cli.py`
- `src/context_integrity/evidence.py`
- `pyproject.toml`
- representative README/current-state documentation

### Tests inspected

- `tests/conftest.py`
- `tests/test_repository.py`
- `tests/test_acquisition.py`
- `tests/test_classification.py`
- `tests/test_cli.py`
- `tests/test_models.py`
- `tests/test_rendering.py`
- package-boundary test
- checked-in golden inventory JSON

### Independent executable evidence

The reviewed commit has a GitHub Actions run for the exact SHA:

- workflow: `CI`
- run id: `38597286633`
- conclusion: `success`
- Python: 3.12.3 on Ubuntu
- `uv run ruff check .`: passed
- `uv run ruff format --check .`: passed
- `uv run pytest`: **123 passed in 0.96s**

The GitHub CI ran the underlying quality-gate commands separately rather than `make check`, but they are the same lint/format/test commands represented by the repository Makefile.

### Targeted independent Git reproductions

The execution environment could not clone GitHub directly into the local container, so I did not rerun the project test suite locally. I did independently reproduce the two Git behaviors underlying F-001 and F-002 with the installed Git executable.

#### F-001 reproduction

Given two valid repositories A and B:

```bash
git init /tmp/ci-root-a
git init /tmp/ci-root-b
git -C /tmp/ci-root-a config core.worktree /tmp/ci-root-b
git -C /tmp/ci-root-a rev-parse --show-toplevel
```

Git reports:

```text
/tmp/ci-root-b
```

Subsequent Git commands started from `/tmp/ci-root-b` operate on B's own repository. That matches the current `discover_repository()` control flow: it replaces `root` with the returned top level, then later executes HEAD/status/origin/listing calls from the replacement root.

#### F-002 reproduction

For a committed `docs/architecture.md` removed only from the working tree:

```bash
git ls-files --cached --others --exclude-standard
git status --porcelain=v1
```

Git still lists:

```text
docs/architecture.md
```

while status reports:

```text
 D docs/architecture.md
```

The implementation parses that status as `deleted`, but `inventory_repository()` does not exclude it before constructing a `SourceRecord`.

### Environment limitations

- The local container had no direct network path to GitHub, so the repository could not be cloned and `make check` could not be rerun locally.
- Exact-commit CI provides independent executable evidence for the existing suite and quality gates.
- The two new defects were validated through source inspection plus targeted Git behavior reproduction, not through patched project tests.

---

## 15.3 Findings summary

| ID | Severity | Category | Title | Fix required before Phase 1? |
| --- | --- | --- | --- | --- |
| F-001 | P1 — High | Security / repository discovery | Git discovery can switch the scan to a different repository | **Yes** |
| F-002 | P2 — Medium | Functional correctness / plan defect | Deleted tracked context files are emitted as present inventory sources | **Yes** |
| F-003 | P2 — Medium | Architecture / machine contract | JSON schema v1 is coupled to internal dataclass layout | **Yes** |

No P0 findings were identified.

---

## 15.4 Detailed actionable findings

### F-001

**ID:** F-001
**Severity:** P1 — High
**Category:** Security / repository discovery
**Fix required before Phase 1:** yes

#### Affected files/symbols

- `src/context_integrity/repository.py`
  - `discover_repository()`
  - `git_command()` only if helper changes are useful
- `tests/test_repository.py`
- potentially `docs/implementation-reports/phase-0-implementation-report.md`
- `docs/current-state.md` after the fix pass is verified

#### Requirement / invariant

- A scan requested for one repository/directory must not silently inventory a different repository because of target-controlled Git metadata.
- Repository discovery may expand a nested requested path to its enclosing Git worktree, but the discovered top level must remain bound to the **same Git repository identity** that was discovered from the requested path.
- The scanner is local-first and read-only, and untrusted repository state must not cause path/repository-scope escape.
- Linked worktrees and ordinary nested-directory invocation must continue to work.

#### Observed behavior

`discover_repository()`:

1. resolves the user-supplied path;
2. calls:

   ```python
   git rev-parse --show-toplevel
   ```

   from that path;
3. unconditionally replaces `root` with the returned path;
4. sets `is_git = True`;
5. performs later HEAD/status/origin calls from the replacement path;
6. `enumerate_candidates()` later performs `git ls-files` from the replacement path.

There is no check that:

- the returned top level is still the same Git repository discovered from the requested path; or
- Git invoked from the returned top level resolves to the same Git directory.

Git honors `core.worktree`. A repository A can therefore report repository B's worktree as its top level. If B is also a valid repository, the scanner's later calls run against B and inventory B.

#### Why this is incorrect or risky

This violates the expected scan boundary. It is stronger than an ordinary Git metadata warning because the scanner can change which repository it is observing.

The current symlink protections are strong once a repository root is selected, but they do not protect the **root-selection step itself**.

A scanner whose product purpose is context integrity should not let repository-local Git configuration silently substitute a different repository.

#### Required outcome

After the fix:

- Git discovery from the requested path may return the containing worktree as normal.
- The implementation must verify that subsequent Git operations at the discovered top level refer to the **same Git repository/worktree identity** initially discovered.
- A mismatch must **not** result in scanning the substituted repository.
- The safest Phase 0 behavior is to fail the scan with `RepositoryError` / CLI exit code 3 and a generic message rather than silently falling back to filesystem discovery.
- The error/warning must not expose sensitive absolute paths by default.
- Normal repository-root invocation, nested invocation, unborn branches, detached HEAD, and linked worktrees must remain supported.

#### Recommended implementation direction

Keep the fix in `repository.py`; do not push trust logic into acquisition or CLI.

A good direction is:

1. preserve `requested_root` before replacing it;
2. during initial Git discovery, also obtain an absolute Git-directory identity, e.g. through `git rev-parse --absolute-git-dir` (or an equivalent robust form supported by the minimum Git expectations);
3. obtain the reported top-level path;
4. validate the top level is a plausible enclosing worktree for the requested path;
5. invoke Git at the reported top level and resolve its Git-directory identity;
6. require the initial and top-level Git-directory identities to match;
7. if they do not match, raise `RepositoryError` rather than switching repositories.

The exact command grouping may differ. The key invariant is **same Git repository before and after root normalization**.

Do not solve this by accepting `GIT_DIR` / `GIT_WORK_TREE` from the environment. The current stripping of repository-location environment overrides should remain.

#### Plan requirement that should be corrected

The Phase 0 plan says to discover the Git repository root using Git but does not require validating that the returned root remains the same Git repository.

For this issue:

> **Luna XHigh should follow the review's corrected requirement rather than the original phase-plan wording for this issue.**

The plan is incomplete on hostile/misconfigured Git worktree metadata.

#### Likely files to change

- `src/context_integrity/repository.py`
- `tests/test_repository.py`
- possibly `tests/test_cli.py` for exit-code coverage
- `docs/implementation-reports/phase-0-implementation-report.md`
- `docs/current-state.md` only after fixes are verified

#### Tests to add or update

Add a regression test with two real tiny Git repositories:

1. create repository A;
2. create repository B with a context document such as `docs/architecture.md`;
3. configure A with `core.worktree` pointing at B;
4. scan A;
5. assert the scan fails safely rather than returning B's context source;
6. assert no B path/content metadata is rendered.

Also preserve/regress:

- root discovery from repository root;
- nested directory discovery;
- linked worktree test already present;
- no-remote behavior;
- unborn branch behavior;
- environment `GIT_DIR` / `GIT_WORK_TREE` sanitization.

A CLI-level regression should verify this maps to exit 3 rather than 0 or 5.

#### Non-goals / do not change

- Do not add a sandbox, chroot, or OS isolation framework.
- Do not add persistence.
- Do not add repository allowlists.
- Do not remove nested-path-to-repository-root behavior.
- Do not break legitimate linked worktrees.
- Do not make Git configuration a Phase 1 policy concern.
- Do not broaden this into generic Git hardening unrelated to a demonstrated scope-switch risk.

#### Documentation updates required

After fixing and verifying:

- update the Phase 0 implementation report security audit to include the repository-root binding regression;
- amend the prior claim that the security audit is complete;
- update `docs/current-state.md` to indicate the independent review fixes are verified and Phase 0 can proceed to closure;
- architecture changes are not required if the fix is treated as enforcement of the existing read-only/safe acquisition boundary.

#### Verification

Run:

```bash
make check
```

Then run the new targeted test, for example:

```bash
uv run pytest tests/test_repository.py -k "worktree or root or redirect"
```

and a CLI regression if added.

Expected result:

- malicious/misconfigured A → B root substitution fails with repository scan failure;
- no B context source appears;
- legitimate nested and linked-worktree tests still pass;
- all existing tests pass.

#### Downstream relevance

Phase 1 authority policy must operate on the repository the caller actually asked to inspect. If Phase 0 can silently substitute repositories during acquisition, every later authority/lifecycle/claim conclusion can be correct about the wrong repository. This must be fixed at the acquisition boundary before higher semantic layers are added.

---

### F-002

**ID:** F-002
**Severity:** P2 — Medium
**Category:** Functional correctness / plan defect
**Fix required before Phase 1:** yes

#### Affected files/symbols

- `src/context_integrity/repository.py`
  - `parse_status()`
- `src/context_integrity/acquisition.py`
  - `enumerate_candidates()`
  - potentially `read_source()` for concurrent disappearance semantics
- `src/context_integrity/inventory.py`
  - `inventory_repository()`
- `tests/test_acquisition.py`
- possibly `tests/test_repository.py`
- golden fixtures only if the intended representative scenario is added there

#### Requirement / invariant

Phase 0 answers:

> What context sources are present?

The phase plan explicitly describes `GitFileStatus.DELETED` as:

```text
deleted  # normally not discovered in current scan
```

Current inventory records should represent observed context artifacts, not index entries that no longer exist in the working tree.

Oversized and unreadable **existing** files are intentionally retained as records with null hashes. A known deleted path is different: there is no current source body to inventory.

#### Observed behavior

Git enumeration uses:

```text
git ls-files --cached --others --exclude-standard
```

That command includes tracked files deleted only from the working tree.

`parse_status()` correctly maps such a path to:

```text
GitFileStatus.DELETED
```

but `inventory_repository()` does not check that status before calling `read_source()` and constructing `SourceRecord`.

For the missing path:

- `read_source()` reports `candidate_metadata_failed`;
- returns no size/hash but does **not** mark the candidate as skipped;
- `inventory_repository()` then emits a `SourceRecord` with:
  - the deleted path;
  - `git_status = deleted`;
  - `content_sha256 = null`;
  - `observed_revision_basis = unavailable`.

So a path that is not present in the working tree is counted as a present context source.

#### Why this is incorrect or risky

The source registry established in Phase 0 becomes the base for authority, lifecycle, and claims.

If deleted paths are represented as current sources:

- source counts are wrong;
- classifications include artifacts that are not present;
- later phases can attach policy/claims to a phantom current source;
- the semantic distinction between "present but unreadable/too large" and "not present" is lost.

This is also a flaw in the written plan's enumeration assumption: `git ls-files --cached` does include unstaged deletions.

#### Required outcome

After the fix:

- a path known by bulk Git status to be `DELETED` must not become a Phase 0 `SourceRecord`;
- repository dirty state still reports the deletion;
- ordinary deletion should not be treated as an unsafe read failure;
- if a file disappears between enumeration and opening, the scan should emit an appropriate structured warning and omit the vanished source rather than produce a phantom record;
- existing oversized and permission-unreadable files should continue to retain inventory records as required by the plan.

#### Recommended implementation direction

Prefer a minimal correction in the inventory/acquisition seam:

- use the already-built bulk status map;
- before reading/constructing a source, skip candidates whose status is `GitFileStatus.DELETED`.

For race-time disappearance after enumeration, refine the `read_source()` outcome so `ENOENT` / an ancestor disappearing can mean "candidate vanished; warning + omit record" rather than "retain null-hash record".

Do **not** re-run Git once per file.

Do not change the existing policy for:

- oversized regular files;
- permission-unreadable existing regular files;
- symlinks;
- non-regular special files unless needed to cleanly distinguish disappearance.

#### Plan requirement that should be corrected

The recommended enumeration command is fine, but the plan's statement that deleted files are "normally not discovered" is technically incomplete.

For this issue:

> **Luna XHigh should follow the review's corrected requirement rather than the original phase-plan wording for this issue.**

The corrected requirement is: **enumeration may produce tracked-deleted paths, and Phase 0 must filter them from the current source inventory.**

#### Likely files to change

- `src/context_integrity/inventory.py`
- possibly `src/context_integrity/acquisition.py`
- `tests/test_acquisition.py`
- possibly `tests/test_cli.py` if warning/output behavior changes
- implementation report/current-state after verification

#### Tests to add or update

At minimum:

1. Initialize a tiny Git repo.
2. Commit `docs/architecture.md`.
3. Delete it from the working tree without staging the deletion.
4. Scan.
5. Assert:
   - repository is dirty;
   - `docs/architecture.md` is absent from `manifest.sources`;
   - it is not counted by kind/authority/lifecycle summary;
   - no per-source Git subprocess was introduced.

Also add a concurrent-disappearance test at the acquisition/inventory level:

- enumerate a valid candidate;
- cause it to disappear before/open during `read_source`;
- assert warning + omission, not a null-hash `SourceRecord`.

Preserve existing tests proving:

- permission-unreadable source remains a record with a warning;
- oversized source remains a record with a warning;
- symlink source is skipped;
- tracked clean / modified / untracked statuses remain correct.

#### Non-goals / do not change

- Do not add historical deletion tracking.
- Do not infer lifecycle `invalid` or `superseded`.
- Do not add Git history lookup.
- Do not add tombstone records in Phase 0.
- Do not turn deletion into a claim or integrity finding.
- Do not perform one Git status call per source.

#### Documentation updates required

After fixing and verifying:

- update the implementation report acceptance/security/limitation sections where deleted-path behavior is relevant;
- current-state should be updated only as part of review-fix closure;
- no PRD or architecture change is needed.

#### Verification

Run:

```bash
make check
uv run pytest tests/test_acquisition.py -k "deleted or disappear"
```

Expected result:

- known deleted tracked document is absent from inventory;
- repository dirty status remains true;
- existing dirty/untracked tests still pass;
- no new Phase 1 behavior appears.

#### Downstream relevance

Authority and lifecycle policy need a trustworthy current source set. Fixing phantom deleted records now prevents every later semantic layer from needing to special-case a Phase 0 acquisition error.

---

### F-003

**ID:** F-003
**Severity:** P2 — Medium
**Category:** Architecture / machine-readable contract
**Fix required before Phase 1:** yes

#### Affected files/symbols

- `src/context_integrity/rendering.py`
  - `manifest_dict()`
  - `render_json()`
- `tests/test_rendering.py`
- checked-in JSON goldens
- possibly `models.py` only if helper placement requires a minor change; avoid model redesign

#### Requirement / invariant

Phase 0 establishes:

> JSON schema version 1 — the first machine-readable contract.

The architecture/review requirements also ask whether the JSON/schema can evolve without accidentally breaking consumers.

A schema version must be controlled by an explicit serialization boundary. Internal dataclass evolution must not silently change public schema version 1.

#### Observed behavior

`manifest_dict()` serializes sources, summaries, and warnings using:

```python
asdict(...)
```

For example:

```python
"sources": [asdict(s) for s in ...]
"summary": asdict(manifest.summary)
"warnings": [asdict(w) for w in ...]
```

This makes public JSON shape depend directly on every dataclass field.

If a future phase adds an internal field to:

- `SourceRecord`;
- `ClassificationResult`;
- `SourceRevision`;
- `InventorySummary`;
- `ScanWarning`;

that field will automatically appear in JSON even if `schema_version` remains 1 and no public schema change was intended.

The current golden tests freeze today's bytes, but a developer could update the golden alongside a model change and unintentionally redefine v1 without a deliberate schema decision.

#### Why this is incorrect or risky

Phase 0's JSON is explicitly a versioned machine contract. Direct `asdict` serialization makes the version boundary incidental rather than intentional.

This is particularly risky because future phases are expected to add:

- authority-resolution data;
- richer lifecycle metadata;
- provenance;
- claims/evidence references.

Those are exactly the kinds of domain fields that should not automatically leak into an existing schema version.

#### Required outcome

After the fix:

- JSON schema version 1 must be emitted through explicit projection/serialization functions;
- only deliberate v1 fields are serialized;
- adding a new internal dataclass field must not automatically change v1 output;
- the existing v1 JSON bytes should remain unchanged unless a separate intentional schema correction is justified;
- `schema_version` remains 1 for this hardening refactor;
- stable ordering/determinism remains unchanged.

#### Recommended implementation direction

Keep versioned projection in `rendering.py` or a comparably small serialization module; do not add a generic schema framework.

For example, use explicit helpers conceptually like:

```text
repository_v1(...)
source_v1(...)
revision_v1(...)
classification_v1(...)
summary_v1(...)
warning_v1(...)
manifest_v1(...)
```

Each helper should enumerate the public keys intentionally.

Do not introduce Pydantic only for this.

Do not make JSON serialization a method on domain models if doing so would couple interface concerns back into `models.py`.

#### Likely files to change

- `src/context_integrity/rendering.py`
- `tests/test_rendering.py`
- goldens should ideally remain byte-identical
- implementation report after verification

#### Tests to add or update

Keep all current golden tests.

Add explicit schema-shape assertions for the v1 contract, including exact key sets at important levels, for example:

- top-level keys;
- repository keys;
- repository.git keys;
- source keys;
- revision keys;
- classification keys;
- `basis` entry keys if `basis` remains part of v1;
- summary keys;
- warning keys.

The goal is not to duplicate the entire golden JSON in code; it is to make the public boundary explicit and reviewable.

If practical, structure the serializer so a new internal-only model field could be added later without requiring a v1 golden update. No synthetic field needs to be added solely for this test.

#### Non-goals / do not change

- Do not redesign domain models.
- Do not add schema v2.
- Do not remove useful existing v1 fields merely to match the shorter illustrative plan example.
- Do not add Pydantic/Marshmallow/JSON Schema tooling unless a concrete need emerges later.
- Do not move rendering logic into CLI.
- Do not add persistence.

#### Documentation updates required

If output bytes remain identical:

- no public README/schema wording change is required;
- update the implementation report to record the explicit v1 projection hardening and verification.

If the fix intentionally changes any public key, that would require a separate schema decision and documentation update; this review does **not** recommend doing so.

#### Verification

Run:

```bash
make check
uv run pytest tests/test_rendering.py
```

Expected result:

- all existing v1 goldens remain byte-identical;
- exact-key schema tests pass;
- runtime metadata remains opt-in;
- no absolute root/timestamp enters stable output;
- future domain model fields are no longer implicitly part of v1 serialization.

#### Downstream relevance

Phase 1 and later phases will grow domain state. An explicit serializer lets those domain models evolve without accidentally mutating the first public machine-readable contract.

---

## 15.5 Non-actionable observations

These are deliberately **not** part of the Luna XHigh required-fix queue.

### O-001 — Kind-level confidence is acceptable but must not be reused as authority confidence

`ClassificationResult.confidence` currently represents **kind confidence**; README/explain output explicitly labels it that way, while `basis` contains per-dimension rule confidence.

This is acceptable for Phase 0.

Phase 1 authority policy should not interpret `classification.confidence` as a generic confidence in authority resolution. If Phase 1 needs authority-specific confidence, it should use the appropriate rule evidence or introduce a clearer authority-domain representation rather than silently reusing the kind field.

### O-002 — Implementation reports currently classify as `other_document` / unknown

The repository's own `docs/implementation-reports/phase-0-implementation-report.md` is not recognized by a specific Phase 0 implementation-report rule and therefore remains an `other_document` unless another name/path rule matches.

That is a real heuristic limitation but not a Phase 0 correctness defect:

- the source is still inventoried;
- Phase 0 does not inspect content semantically;
- the written classification plan did not define an `implementation_report` kind or an `implementation-reports/` verification rule.

A later heuristic refinement can decide whether curated implementation reports should map to `verification_record` or another explicit kind.

### O-003 — POSIX-only safe reads are documented

The descriptor-relative `O_NOFOLLOW` implementation is strong for macOS/Linux and is explicitly documented as not implemented/verified on Windows.

There is no explicit Phase 0 Windows acceptance criterion. Do not expand the fix pass into a portability layer.

### O-004 — Local fallback repository IDs are move-sensitive

The local fallback hashes repository name plus resolved local root. This is opaque in stable output but changes if a local-only repository moves.

The behavior is documented and the plan explicitly allows a simple deterministic local fallback without solving move identity in Phase 0.

### O-005 — Scans are sequential rather than atomic snapshots

The source content hash identifies bytes read from each file; Git HEAD/status are collected separately. Concurrent mutation can therefore make status metadata stale relative to a later file read.

The implementation report and README disclose this. The review prompt explicitly says not to require snapshot isolation in Phase 0.

Do not turn the fix pass into a snapshotting system.

### O-006 — Manifest-level repository association is sufficient for Phase 0

The architecture's conceptual `SourceRecord` includes repository association, while the implementation stores one `RepositoryRef` at manifest level and derives `SourceId` from repository ID + path.

That is adequate for the current single-repository Phase 0 contract. Multi-repository/cross-repository execution is explicitly out of scope.

Revisit only when a later phase introduces a concrete need to move/aggregate source records outside their manifest.

---

## 15.6 Acceptance-criteria audit

The implementation report's audit was not accepted at face value. The statuses below are based on code/test inspection plus exact-commit CI where applicable.

### Functional

| Acceptance criterion | Review status | Evidence / note |
| --- | --- | --- |
| `context-integrity scan .` works on a Git repository | verified | CLI integration test; exact-commit CI passes. F-001 is an uncovered hostile/misconfigured-root case, not a failure of the ordinary case. |
| Scan works on a non-Git directory | verified | acquisition/CLI tests. |
| Git-ignored files are excluded in Git mode | verified | `test_git_ignore_dirty_and_raw_bytes`. |
| Untracked nonignored context files are discoverable | verified | same Git fixture. |
| Common context artifacts are classified | verified | table-driven classification suite + aliases. |
| `SourceKind`, `AuthorityClass`, `LifecycleState` are separate | verified | distinct enums/fields and historical overlay. |
| Historical overlay preserves original source kind | verified | table-driven historical tests + repository inventory test. |
| Unknown classification is preserved rather than dropped | verified | fallback is retained as `other_document` with unknown authority; source remains inventoried. |
| Every inventoried readable source receives SHA-256 | verified | raw-byte and empty-file tests. |
| Dirty content is not represented as equivalent to HEAD | verified | independent content hash + Git status/HEAD model and tests. |
| `explain` shows matched rules | verified | CLI tests. |
| JSON uses repository-relative paths | verified | normalization + rendering/golden tests. |
| JSON has `schema_version: 1` | verified | golden contract. |
| Stable JSON omits absolute root/timestamp by default | verified | rendering tests. |
| Warnings are structured | verified | model + acquisition/CLI tests. |
| `--fail-on-warning` behaves as documented | verified | CLI test. |

### Architecture

| Acceptance criterion | Review status | Evidence / note |
| --- | --- | --- |
| CLI does not own classification logic | verified | CLI delegates to inventory/classification. |
| Models do not perform filesystem I/O | verified | models contain domain values/hash ID helper only. |
| Acquisition does not resolve authority precedence | verified | only candidate/file handling; no ranking. |
| No claim model simulates Phase 3 | verified | no claim implementation. |
| No database added | verified | runtime dependency/source inspection. |
| No LLM dependency added | verified | runtime dependency/source inspection. |
| No Codebase Intelligence dependency added | verified | evidence seam is only a docstring placeholder. |
| Evidence/provider concepts remain separate from classification | verified | separate reserved module; no coupling. |

### Testing

| Acceptance criterion | Review status | Evidence / note |
| --- | --- | --- |
| Every classification rule has tests | verified | `RULE_CASES` zipped against `KIND_RULES` plus aliases/overlays. |
| Golden JSON fixture passes | verified | exact-commit CI passes all rendering tests. |
| Git clean/dirty/untracked tests pass | verified | exact-commit CI. **Gap:** deleted tracked path not covered; F-002. |
| Historical path tests pass | verified | exact-commit CI. |
| Warning tests pass | verified | exact-commit CI. |
| CLI integration tests pass | verified | exact-commit CI. |
| Ruff passes | verified | exact-commit CI lint and formatting jobs pass. |
| Entire test suite passes offline | verified with environment note | exact commit has 123 passing tests; source/tests show no test-time network dependency. I did not independently rerun `UV_OFFLINE=1 make check` locally because the repository could not be cloned into the execution container. |

### Documentation

| Acceptance criterion | Review status | Evidence / note |
| --- | --- | --- |
| README says classifications are provisional | verified | README inventory section. |
| README says authority is later/question-dependent | verified | README inventory section. |
| README explains Codebase Intelligence relationship | verified | repository docs/README context and roadmap. |
| Implementation report maps acceptance criteria | verified as a documentation artifact | the report contains a per-criterion mapping, though F-001/F-002/F-003 show that the prior audit was not complete. |

### Additional review-level acceptance concerns

The written checklist itself does not explicitly include "Git root cannot switch to another repository" or "deleted tracked paths are excluded." Those are nevertheless required by the Phase 0 product/security semantics.

- F-001: **not verified / implementation defect + plan gap**
- F-002: **not verified / implementation defect + plan technical assumption**
- F-003: existing output is deterministic, but version-boundary maintainability is **partially verified** until explicit v1 projection is added.

---

## 15.7 Architecture audit

### Acquisition / classification separation

**PASS.**

`acquisition.py` selects/reads/hashes candidates and emits warnings. `classification.py` owns deterministic kind/authority/lifecycle rules. There is no authority resolution in acquisition.

F-001 and F-002 are acquisition/repository correctness issues, not a separation failure.

### Domain model boundaries

**PASS with minor future observations.**

`models.py` contains dataclasses/enums/ID generation and no filesystem access. The distinctions among kind, authority class, lifecycle, revision, and classification explanation are preserved.

No Phase 1 policy model was pulled forward.

### CLI / rendering separation

**PASS.**

CLI performs argument handling, discovery/orchestration invocation, output writing, and exit-code adaptation. Rendering is separate and pure.

### Authority semantics

**PASS.**

No global scalar ranking is implemented. Authority class is a role derived from provisional source kind, with historical overlay. Plans do not become proof of delivery.

### Lifecycle semantics

**PASS.**

Only `historical` and `unknown` are implemented. Recency does not imply supersession. Historical overlay preserves original kind.

### Deterministic output

**PASS for current bytes; architectural hardening required by F-003.**

The implementation sorts sources/warnings/maps and omits runtime metadata by default. JSON uses sorted keys and newline-at-EOF.

The weakness is not current nondeterminism; it is that future internal model changes can silently mutate schema v1 through `asdict`.

### Revision model

**PASS for current intended semantics, with F-002 correction required.**

Content hash and Git HEAD are independent, and status differentiates clean/modified/untracked.

Deleted paths should not be emitted as present source records.

Sequential observation race is acceptable for Phase 0 and is documented.

### Repository discovery / trust boundary

**NOT READY until F-001 is fixed.**

Normal nested and linked worktree behavior is handled, but Git top-level is not bound to the repository identity discovered from the requested path.

### EvidenceProvider future seam

**PASS.**

`evidence.py` is only a reserved seam. No companion-engine dependency or behavior exists.

### Future-phase leakage

**PASS.**

No material Phase 1+ implementation was found.

---

## 15.8 Test-quality assessment

### Overall

The suite is strong for Phase 0: **123 tests** at the exact reviewed commit, with heavy use of tiny real Git repositories, table-driven classification tests, path/symlink/error cases, CLI integration, and golden JSON.

The tests generally prove behavior rather than mocking every Git operation.

### Fixture realism

Good:

- real local Git repositories;
- root/nested/worktree behavior;
- dirty/untracked/ignored cases;
- newline/control filenames;
- symlink ancestors;
- size and unreadable cases;
- generated goldens.

Missing realistic cases:

- malicious/misconfigured Git `core.worktree` switching repository root — **F-001**;
- unstaged deletion of a tracked context source — **F-002**;
- concurrent candidate disappearance — should be added with F-002.

### Determinism coverage

Good for current output:

- byte-equal golden rendering;
- repeated JSON rendering;
- sorted paths/maps;
- no runtime metadata by default.

Missing contract-evolution protection:

- exact public v1 key boundary independent of internal dataclasses — **F-003**.

### Git coverage

Strong:

- root/nested;
- no remote/local fallback;
- Git unavailable;
- status failure;
- rename parsing;
- linked worktree;
- fsmonitor suppression/index read-only;
- environment location overrides.

Important missing cases:

- root/repository identity mismatch through `core.worktree` — **F-001**;
- tracked deleted path — **F-002**.

### Classification coverage

Strong and appropriately table-driven.

Each declared built-in kind rule has a direct example, authority mapping is checked, historical overlays are parameterized, fallback is covered, and stable rule IDs are asserted.

No required classification finding.

### Missing failure modes

Material gaps are captured as F-001 and F-002.

No recommendation to broadly increase mocking or test count beyond those concrete regressions.

---

## 15.9 Plan / architecture issues discovered

### P-A01 — repository-root trust validation missing from the plan

The plan instructs implementation to discover the repository root with Git, but it does not state that the returned root must be proven to belong to the same Git repository originally discovered from the requested path.

This omission enabled F-001.

**Corrected requirement for fix pass:**

> A Git-discovered top level may replace the requested nested path only after the implementation validates that both locations resolve to the same Git repository/worktree identity. Otherwise the scan must fail safely rather than inventory another repository.

**Luna XHigh should follow the review's corrected requirement rather than the original phase-plan wording for this issue.**

### P-A02 — `git ls-files --cached` includes worktree deletions

The plan recommends:

```text
git ls-files --cached --others --exclude-standard
```

and separately says `deleted` is normally not discovered.

Those statements are incomplete together: unstaged deleted tracked files are still returned by `--cached`.

This omission enabled F-002.

**Corrected requirement for fix pass:**

> Git enumeration may yield tracked-deleted paths; Phase 0 must remove known deleted paths from the current source inventory without adding per-file Git subprocesses.

**Luna XHigh should follow the review's corrected requirement rather than the original phase-plan wording for this issue.**

### Architecture ambiguity: public schema projection

The architecture correctly treats JSON as an interface concern but does not explicitly state that schema-versioned JSON must be projected independently from domain dataclass layout.

F-003 should be treated as a Phase 0 interface hardening rule, not as a broad architecture rewrite.

No ADR is necessary unless the project wants a durable general rule such as "public schema versions never serialize domain dataclasses implicitly."

---

## 15.10 Required fix set

### Required before Phase 1

Fix order:

1. **F-001 — bind Git root discovery to the same repository identity**
   - Highest priority because it is a scan-boundary/security defect.
   - No dependency on other findings.

2. **F-002 — exclude tracked-deleted / vanished candidates from current inventory**
   - Builds on the existing bulk status map.
   - Independent of F-003.

3. **F-003 — replace implicit `asdict` public serialization with explicit v1 projection**
   - Prefer to do after behavioral fixes so any intentional output decision is made once.
   - Preserve current schema bytes.

### Optional / defer

Do **not** add these to the Luna XHigh fix queue:

- implementation-report-specific classification rule;
- Windows safe-read backend;
- repository move-stable local fallback ID;
- atomic snapshot semantics;
- multi-repository `SourceRecord.repository` redesign;
- authority/lifecycle/claim features.

---

## 15.11 Fix-pass constraints

Luna XHigh must:

- remain strictly within Phase 0;
- fix only F-001, F-002, F-003 plus tests/docs required by those fixes;
- preserve the existing acquisition/classification/rendering/CLI ownership boundaries;
- not add authority precedence or resolution;
- not add active/superseded lifecycle inference;
- not add persistence, LLM/model calls, servers, MCP, embeddings, or Codebase Intelligence integration;
- not replace bulk Git operations with per-source subprocesses;
- preserve the current public CLI commands and exit codes except that F-001 must map unsafe repository substitution to scan failure (exit 3);
- preserve stable JSON version 1 and existing bytes unless a finding explicitly requires otherwise; F-003 is intended to be behavior-preserving;
- preserve existing symlink, size-limit, unreadable-source, and fsmonitor protections;
- preserve linked-worktree support;
- avoid unrelated cleanup/refactoring;
- update implementation evidence only after tests pass;
- keep `docs/current-state.md` concise and use it to record review-fix closure, not to restate this review.

---

## 15.12 Expected post-fix verification

After implementing all required fixes, run:

```bash
make check
```

Expected:

- Ruff lint passes;
- Ruff format check passes;
- full pytest suite passes.

Also run targeted tests equivalent to:

```bash
uv run pytest tests/test_repository.py -k "worktree or root or redirect"
uv run pytest tests/test_acquisition.py -k "deleted or disappear"
uv run pytest tests/test_rendering.py
uv run pytest tests/test_cli.py
```

Required observable post-fix outcomes:

- scanning repository A cannot be redirected into repository B through `core.worktree` or equivalent root substitution;
- legitimate nested invocation still resolves to its enclosing repository;
- legitimate linked worktree support still passes;
- a tracked context file deleted from the working tree is absent from `sources` and summary counts;
- a candidate that disappears during scanning does not become a phantom null-hash source;
- oversized/unreadable existing files retain records exactly as before;
- no per-file Git subprocess pattern is introduced;
- all existing dirty/untracked/rename/fsmonitor tests continue to pass;
- v1 JSON goldens remain byte-identical;
- v1 key-shape tests make the public projection explicit;
- stable JSON still omits absolute root/timestamp/source bodies;
- no future-phase dependency or behavior is introduced.

After verification, update:

- `docs/implementation-reports/phase-0-implementation-report.md` with the independent review fix evidence;
- `docs/current-state.md` so it no longer says independent review is merely pending and instead identifies the correct closure/next step.

A separate final verification pass should confirm the three finding IDs are actually resolved rather than relying only on the fix session's report.

---

## 15.13 Downstream readiness

### Is Phase 0 a trustworthy enough foundation to begin planning Phase 1 now?

**Not yet. It is trustworthy enough only after the required F-001/F-002/F-003 fix set is implemented and verified.**

The overall architecture does **not** need reconsideration. The seams are good:

- repository/acquisition;
- classification;
- domain models;
- application orchestration;
- rendering;
- CLI;
- future evidence boundary.

The blockers are localized correctness/contract issues at those seams.

F-001 is the only high-severity finding and must be resolved before higher-level semantic policy is built on top of repository discovery.

F-002 matters because Phase 1 should reason over sources that actually exist.

F-003 matters because Phase 1+ will evolve domain state and should not accidentally mutate schema version 1.

### Is this document sufficient as the sole Luna XHigh fix handoff?

**Yes.**

It identifies:

- the exact defects;
- affected modules;
- required outcomes;
- corrected plan requirements;
- recommended architectural seams;
- regression scenarios;
- non-goals;
- documentation changes;
- verification commands;
- fix order and dependencies.

Luna XHigh should be able to implement and verify the required fixes from this document and the repository without reopening the design from scratch.
