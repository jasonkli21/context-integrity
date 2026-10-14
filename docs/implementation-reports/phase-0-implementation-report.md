# Phase 0 implementation report

**Implementation date:** 2026-10-14  
**Status:** Implemented and verified; independent review fixes applied and verified.
**Initial implementation checkout:** The original implementation report was prepared from a
source copy without `.git` metadata. The subsequent review-fix pass is recorded in one commit
on the repository branch.
**Normative scope:** `docs/plans/phase-0-implementation-plan.md`; architecture unchanged.

## Implemented

A local, offline context-source inventory with deterministic provisional kind, authority
class, and lifecycle; stable source/repository identity; raw-byte hashes; independent Git
HEAD/status; structured nonfatal warnings; text/JSON rendering; scan options; explanation;
and the specified exit codes. Ordinary code is not indexed or executed.

Changed components:

- `models.py`: enums, frozen dataclasses, IDs, revisions, rules, summary/manifest.
- `repository.py`: discovery, identity, safe bounded Git calls, bulk status and rename parsing.
- `acquisition.py`: candidate filtering, Git listing/non-Git walk, descriptor-based safe reads,
  incremental bounded hashing, warnings.
- `classification.py`: ordered built-in rules, authority-role mapping, independent historical overlay.
- New `inventory.py`: application orchestration and deterministic summary assembly.
- `rendering.py`, `cli.py`: pure renderers and interface adapter, all Phase 0 options/exits.
- Tests: models, repository, acquisition, classification, rendering, CLI; generated synthetic
  repositories and three small JSON golden fixtures.
- README, current-state, fixture documentation, this report; new `uv.lock` for reproducibility.

`evidence.py`, architecture, ADRs, phase plan, and runtime dependencies were not changed.

## Key implementation decisions

- Standard-library dataclasses/enums; one small application module, no framework.
- Kind precedence follows architecture §10.1: exact known filenames, strong directories,
  filename patterns, fallback. Historical lifecycle runs independently and overrides only
  authority/lifecycle. Classification confidence at the top level is kind confidence;
  `basis` carries confidence and explanation for each dimension/rule.
- Repository ID: `repo_` plus the first 32 hex digits of SHA-256. Prefer normalized `origin`
  network remote (host/repository path, `.git` stripped, credentials/query/fragment discarded).
  Otherwise hash repository name + NUL + resolved root. Local moves can change IDs; absolute
  roots are never serialized by default. Source ID hashes repository ID + NUL + relative path.
- All successful hashes identify `working_tree_content`, including clean files. HEAD is
  separate metadata, never an assertion that working bytes equal the commit.
- One NUL-delimited Git file listing and one bulk porcelain status per scan; no per-file Git
  subprocesses. Unborn branches have null HEAD without warnings. Optional origin is not required.
- Git commands use argument arrays, disable optional locks and `core.fsmonitor`, disable lazy
  fetch, and discard inherited repository-location overrides. This prevents an fsmonitor
  program configured by the target from executing and keeps the index read-only.
- If Git enumeration fails after Git discovery, fail with exit 3 rather than silently include
  ignored files via a filesystem walk. Metadata failures otherwise degrade to warnings.
- POSIX directory-relative opens with `O_NOFOLLOW` reject symlink components even across
  replacement races. Symlink candidates are skipped; oversized/unreadable candidates retain
  records with null hashes. Reads use 64 KiB chunks and stop after the 5 MiB limit plus one
  defensive byte if a file grows. Oversized files identified by stat are never read.
- JSON escapes unusual filenames/control bytes and ends with a newline; terminal output
  escapes controls. No source body is rendered.

## Verified: acceptance audit

Every checkbox in phase-plan §29 is mapped below. “Verified” denotes implementation
verification, not independent architectural review or closure of Phase 0.

| Acceptance criterion | Status | Evidence |
| --- | --- | --- |
| `context-integrity scan .` works on a Git repository. | Verified | `tests/test_cli.py::test_scan_dot_git` (CLI scan `.` in a synthetic Git repository). |
| Scan works on a non-Git directory. | Verified | `test_default_scan_non_git`; `test_non_git_candidate_selection`; real-checkout smoke scan. |
| Git-ignored files are excluded in Git mode. | Verified | `test_git_ignore_dirty_and_raw_bytes`. |
| Untracked nonignored context files are discoverable. | Verified | `test_git_ignore_dirty_and_raw_bytes`; basic-context golden. |
| Common context artifacts are classified. | Verified | `tests/test_classification.py` table/aliases; `test_basic_context_repository`. |
| `SourceKind`, `AuthorityClass`, and `LifecycleState` are separate. | Verified | Distinct enums/fields in `models.py`; `test_enum_contract`; golden manifests. |
| Historical overlay preserves original source kind. | Verified | `test_history_overlay`; `test_history_repository_inventory`; history golden. |
| Unknown classification is preserved rather than dropped. | Verified | `test_precedence_and_conservative_fallback`; `test_history_repository_inventory`. |
| Every inventoried readable source receives a SHA-256 hash. | Verified | `test_git_ignore_dirty_and_raw_bytes`; `test_empty_file_hash`; golden digests. The planned 5 MiB exception retains a null hash and warning, verified by size-limit tests. |
| Dirty repository content is not represented as equivalent to HEAD. | Verified | `test_git_ignore_dirty_and_raw_bytes`; dirty golden preserves HEAD separately from byte hash/status. |
| `context-integrity explain` shows matched rules. | Verified | `test_summary_and_explain`; `test_explain_document_roles`; real-checkout explanations. |
| JSON output uses repository-relative paths. | Verified | `test_golden_json`; `test_unsafe_paths`; `test_unsafe_git_listing_paths`; real JSON assertions. |
| JSON output has `schema_version: 1`. | Verified | `test_golden_json`; CLI JSON/file tests. |
| Stable JSON omits absolute root and current timestamp by default. | Verified | `test_golden_json`; repeated real JSON byte comparison; runtime metadata opt-in test. |
| Warnings are structured. | Verified | `ScanWarning` model; warning tests; `test_fail_on_warning_and_runtime`. |
| `--fail-on-warning` behaves as documented. | Verified | `test_fail_on_warning_and_runtime` (default 0, strict 5 after rendering). |
| CLI does not own classification logic. | Verified | Code inspection: `cli.py` invokes inventory/renderers; rules live only in `classification.py`. |
| Models do not perform filesystem I/O. | Verified | Code inspection: `models.py` imports dataclasses/enums/hashlib/typing only. |
| Acquisition does not resolve authority precedence. | Verified | Code inspection: `acquisition.py` selects/reads/hashes files; no authority policy or ranking. |
| No claim model is prematurely used to simulate Phase 3. | Verified | Code/model inspection: no claim types or claim extraction. |
| No database is added. | Verified | Dependency and source inspection: unchanged `pyproject.toml`; no persistence implementation. |
| No LLM dependency is added. | Verified | Dependency and source inspection: Typer is the sole direct runtime dependency; no model calls. |
| No Codebase Intelligence dependency is added. | Verified | Dependency and source inspection: no companion engine imports or coupling. |
| Evidence/provider concepts remain separate from classification. | Verified | `evidence.py` remains the untouched reserved boundary; classification is independent. |
| Every classification rule has tests. | Verified | `test_each_kind_rule`; alias/overlay tests; `test_builtin_rule_ids_are_stable`; fallback test. Authority mappings are checked for each kind. |
| Golden JSON fixture passes. | Verified | `test_golden_json`, `test_dirty_golden_json`, `test_history_golden_json`; checked-in JSON fixtures. |
| Git clean/dirty/untracked tests pass. | Verified | `test_git_ignore_dirty_and_raw_bytes`; repository discovery; linked-worktree/rename test. |
| Historical path tests pass. | Verified | Every historical directory overlay table; historical repository/golden. |
| Warning tests pass. | Verified | All six warning categories covered across acquisition/repository/CLI tests. |
| CLI integration tests pass. | Verified | `tests/test_cli.py`: help, version, scan, options, exits, explanations. |
| Ruff passes. | Verified | `UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check`: Ruff lint and formatting passed. |
| Entire test suite passes offline. | Verified | Same offline `make check`: 123 passed on Python 3.12.13/macOS; fixtures use local Git only. |
| README explains that classifications are provisional. | Verified | README, “Using the inventory”: explicit provisional path/name conventions. |
| README explains authority is resolved in a later phase. | Verified | README, “Using the inventory”: question-dependent authority precedence deferred. |
| README explains relationship to Codebase Intelligence. | Verified | README, “Relationship to the Codebase / Context Intelligence Engine”. |
| Phase 0 implementation report can state exactly which acceptance criteria were met. | Verified | This per-criterion audit plus commands, limitations, and delivery evidence below. |

## Verified: security audit (phase-plan §28)

| Requirement | Evidence |
| --- | --- |
| No `shell=True` | Source inspection: the sole subprocess runner uses an argument array and no shell option. |
| No repository file execution | Candidate filtering/raw-byte reads; fsmonitor execution prevention test; ordinary-code fixture excluded. |
| No network access | No network client/imports; Git commands are local and lazy fetch is disabled; offline quality gate. |
| Symlink escape not followed | File/directory/ancestor symlink tests; `O_NOFOLLOW` directory-relative reads. |
| No raw document contents in output | Renderers serialize metadata; golden and real JSON content assertions. |
| No absolute local root in stable JSON | Golden contract, runtime opt-in tests, real JSON assertions. |
| No filename traversal | Normalization rejection tests, unsafe Git listing tests, newline/control filename tests. |
| Unreadable sources become warnings | Deterministic permission failure test retains a null-hash record; no unsafe read fallback. |

## Verification commands and results

Initial `uv sync --group dev` succeeded and produced `uv.lock`. A subsequent default-cache
invocation hit sandbox restrictions on the user's uv cache. Further commands used a writable
`UV_CACHE_DIR=/tmp/context-integrity-uv-cache`; no permission escalation was needed.

Final quality command:

```bash
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check
```

Result: Ruff lint passed, Ruff formatting passed, **123 tests passed**. The underlying commands
were `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pytest`.
Earlier test iterations exposed and fixed a test fault-injection scope issue, a missing golden
file before generation, and import formatting; none remain unresolved. A diagnostic coverage
run (`uv run pytest --cov=context_integrity --cov-report=term-missing -q`, same environment)
on the earlier 112-test suite passed with 94% combined coverage. Coverage is not a phase gate.

Real-checkout smoke commands (all with the same UV_CACHE_DIR and UV_OFFLINE environment):

```bash
uv run context-integrity scan .
uv run context-integrity scan . --format json
uv run context-integrity scan . --format json --output /tmp/context-integrity-phase-0-inventory.json
uv run context-integrity explain AGENTS.md
uv run context-integrity explain docs/architecture.md
uv run context-integrity explain docs/plans/phase-0-implementation-plan.md
```

All succeeded. After documentation updates, the original source copy had 18 context sources, no warnings,
no ordinary code sources, and unknown lifecycle for all sources. Instructions, architecture,
and active plan receive operating-instruction, architecture/product, and plan authority roles.
Each readable candidate has a SHA-256. Two stable real JSON scans were byte-identical, source
paths were relative, and no resolved root, timestamp, or source body appeared in stable output.
At initial implementation handoff, that source copy had no Git metadata, so Git metadata was
unavailable there. Synthetic Git fixtures verify clean, dirty, ignored, untracked, staged
rename, nested root, unborn branch, and linked-worktree behavior. Real-checkout Git smoke
verification was unavailable during that initial handoff.

## Deviations, limitations, and classification ambiguities

- Added `inventory.py` to keep orchestration out of the CLI and I/O/model modules.
- Candidate discovery additionally includes strong convention directories used by required
  classification rules (`verification`, `status`, `requirements`, `summary`, `generated`,
  and historical aliases). It still filters document extensions and skips vendor/build trees.
- Fixtures are generated at test time. Three small checked-in goldens cover basic, dirty, and
  historical manifests; the fixture README identifies generators and purpose.
- Exact known filenames precede directory conventions, as specified by architecture; this
  resolves the plan's less explicit ordering. `docs/adr/README.md` is a README, not a decision.
- Safe descriptor reads currently target POSIX (macOS/Linux); Windows is not implemented or
  verified. Verification ran on macOS only.
- Scans are sequential observations, not atomic snapshots across files and Git metadata.
- Git-unavailable fallback warns and cannot honor Git ignores. Non-Git walks do not interpret
  `.gitignore`. No remote is required; only `origin` is used for preferred remote identity.
- Symlink sources are intentionally omitted with warnings. Files above the size limit retain
  records but no body/hash, as required by the plan's defensive policy.
- ADR templates look like decision records by path. Their classification does not establish
  acceptance or activity. CONTRIBUTING and implementation reports without stronger names are
  retained as `other_document`/unknown authority. No content is interpreted to “fix” this.
- Local-fallback IDs change on moves; rename lineage is not tracked. Hashes distinguish dirty
  bytes, but status can change during a concurrent scan.

## Deferred and inputs for Phase 1

No authority ranking/resolution, active/superseded inference, claims, persistence, model calls,
semantic checks, servers, or companion-engine integration were added. `unknown` remains valid.
Plans do not prove delivery; Phase 0 classifications do not resolve authority conflicts.

The initial implementation handoff requested independent review against implementation, tests,
the active plan, architecture, and actual state. After Phase 0 closure, Phase 1 planning can
consider explicit repository/source metadata for ADR templates, curated reports, and
filename/directory collisions; question-specific authority policy must stay separate from
discovery and provisional kind classification.

## Independent review fix pass (2026-10-14)

The independent post-implementation review identified F-001, F-002, and F-003. All three
findings were addressed without changing the Phase 0 architecture or adding future-phase
behavior:

| Finding | Resolution | Verification |
| --- | --- | --- |
| F-001 — Git root can redirect to another repository | Discovery now records the Git directory from the requested path, checks that the reported top level encloses the request, and verifies the Git directory again from the normalized root. A mismatch or unverifiable identity raises `RepositoryError` with a path-free message and maps to CLI exit 3. | `test_discovery_rejects_git_worktree_redirect`; `test_discovery_fails_closed_when_git_identity_cannot_be_read`; `test_scan_rejects_git_worktree_redirect`; existing nested-root and linked-worktree tests. |
| F-002 — Deleted tracked files appear as sources | Candidates marked deleted by the bulk status map are omitted before reads. If a candidate or ancestor disappears after enumeration, it is omitted with `candidate_metadata_failed`; unreadable and oversized existing files retain their prior behavior. | `test_deleted_tracked_source_is_not_in_inventory`; `test_candidate_disappearing_after_enumeration_is_warned_and_omitted`; unreadable/oversized regression tests. |
| F-003 — JSON v1 follows dataclass layout | `rendering.py` now uses explicit v1 projections for each public object and rejects unsupported manifest schema versions. | `test_schema_v1_uses_explicit_key_sets`; all three existing JSON golden tests remain byte-identical. |

The review also identified that the plan's note that deleted files are “normally not discovered”
was technically incomplete. The completed Phase 0 plan remains unchanged as historical planning
evidence; the implementation and this report record the corrected behavior.

Final verification on the review-fix state:

```bash
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check
```

Ruff lint and format passed; **129 tests passed** on Python 3.12.13/macOS. A focused run of
`tests/test_repository.py`, `tests/test_acquisition.py`, `tests/test_rendering.py`, and
`tests/test_cli.py` also passed (71 tests). No public JSON bytes or architecture schema changed;
the README now documents deleted-source behavior.
