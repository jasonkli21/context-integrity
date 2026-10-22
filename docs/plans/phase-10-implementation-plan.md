# Context Integrity — Phase 10 Detailed Implementation Plan

**Phase:** 10 — Cross-Repository Integrity\
**Document role:** Proposed normative implementation plan; **not** implementation or acceptance evidence\
**Repository:** https://github.com/jasonkli21/context-integrity\
**Inspected baseline:** `main` at [`61ca15782dadff319c6d4ed2422d1d6e82fffd2a`](https://github.com/jasonkli21/context-integrity/commit/61ca15782dadff319c6d4ed2422d1d6e82fffd2a), October 21, 2026 (Pacific)\
**Predecessor:** Phase 9 — Derived Context Revalidation; fixes implemented, fresh independent re-review **pending**\
**Successor:** Phase 11 — CI / Governance / Observability

> **Start-state gate.** Before implementing, re-read `AGENTS.md`, `docs/current-state.md`, the active branch/commit, the relevant source and tests, and any newly accepted ADRs. Reconcile a changed HEAD in the implementation report. Do not treat Phase 9's fix report or passing tests as independent acceptance. If later review work changes Phase 9 interfaces, adjust this plan transparently and keep the review status visible.

## 1. Product objective and deliberately bounded promise

Phase 10 makes Context Integrity useful when a *product* spans independently versioned repositories. Given a user-declared local workspace, it should identify which repository and exact source revision a cross-repository assertion depends on; check **explicit** contract/claim alignments; produce explainable findings when observed inputs diverge or cannot be observed; and assemble one **namespaced, provenance-bearing** task-context index from multiple repositories.

The release should support these concrete journeys:

1. **Producer/consumer contract pin.** An API repository exports `spec/openapi.json`; a consuming repository stores a small, explicit lock recording the accepted producer repository ID, relative path, and SHA256. `workspace check` reports an observed mismatch after producer bytes change, even if HEAD has not advanced, and identifies *both* sides. It does not conclude the client is incompatible.
2. **Exact shared-file mirror.** Two repositories intentionally mirror an identical contract file. A declared byte-equality rule detects a mismatch with two distinct repository-qualified paths, without making a general claim about schema semantics.
3. **Product-wide declared claim alignment.** Two repositories each declare an explicit claim in existing configuration. A workspace rule pairs the claim IDs and reports exact agreement, declared disagreement, or insufficient comparability/coverage. Claim validity remains `unverified`; a disagreement is not an independently proven contradiction.
4. **Cross-repository task context.** A workspace command independently applies existing context contracts to two or more repositories and emits one deterministic index of selected references, reasons, source revisions, coverage, per-repo compilation state, and workspace findings. It neither concatenates source bodies nor globally ranks authority.
5. **Uncertain evidence.** Missing repos, stale/incorrect repository identity, unsafe paths, unreadable files, unsupported schema, incomplete inventory, ambiguous claims, and changed inputs while observing never produce a reassuring clean/compliant result.

Success means deterministic **observation and explicit alignment checking**, not automated API compatibility validation, semantic claim verification, a universal policy hierarchy, multi-repo structural graph traversal, or CI enforcement.

### Why this boundary

- `docs/prd.md` §21 and Phase 10 roadmap call for product-level claims, contract drift, integration alignment and cross-repo task context; §30 Stage E calls for shared repository/workspace identities without a shared database.
- `docs/architecture.md` §29 assigns cross-repo *policy/integrity* to Context Integrity and possible cross-repo *structural observation* to Codebase Intelligence. Its Phase 10 workspace syntax was intentionally deferred.
- The separate `context-engine` project currently exposes **repository-scoped** CLI/HTTP/MCP evidence, not a proven multi-repo graph contract. Its Phase 9 `docs/current-state.md` describes a server pinned to one root and ongoing independent review. Do not infer cross-repo structural facts by merging numeric/provider-local graph identities.
- Phase 9 receipt/result v1 is expressly one-repository and locally declared. Preserve that contract while adding workspace-specific evidence; avoid silently interpreting a relative path in some other repository.
- The Phase 9 plan's successor note anticipates cross-repository receipts/source identity and contract-change impact. Phase 10's **consumer-owned contract lock v1 is the first narrow, cross-repo revision-acceptance receipt**: it pins a producer repository ID, source path and content digest from another root, and can be checked without modifying Phase 9 receipts. It is **not** a generic derivative-provenance DAG; preserve that distinction in CLI and documentation.

## 2. Source-of-truth map and verified baseline

| Source | What it establishes | Phase 10 consequence |
| --- | --- | --- |
| `AGENTS.md` | Instructions, authority/source roles, local/read-only defaults, phase discipline and review workflow | Keep instructions singular; report claims as unverified; no hidden network, database or auto-fix |
| `docs/current-state.md` | Phase 9 review fixes offline-verified; 1,071 tests in its recorded environment; earlier independent review gaps remain | No unearned acceptance or phase status promotion |
| `docs/prd.md` §§4, 17–21, 29–30 | Intended CI vs Codebase Intelligence responsibilities and Phase 10 outcomes | Cover explicit cross-repo checks and context; defer semantics/governance |
| `docs/architecture.md` §§2, 6, 14–22, 29–34 | Repository IDs, relative source paths, normative/structural separation, canonical vs derived data | Namespace every reference; preserve local source authority and revision provenance |
| `docs/derived-context-contract.md` | Receipt/result v1, content hashing, graph limits, no-follow reads, non-atomic multi-file publication | No cross-repo receipt v1 reinterpretation; reuse security vocabulary and honest uncertainty |
| `docs/evidence-contract.md` / `docs/architecture-integrity-contract.md` | Optional descriptive provider v1, conservative coverage, integrity v2 | No provider authority promotion or fake cross-repo graph completion |
| `src/context_integrity/repository.py` | `discover_repository()`, origin-normalized `repo_...` IDs, location-dependent fallback for no origin | Bind manifest aliases to verified IDs; reject collision and ambiguous checkouts |
| `models.py`, `configuration.py`, `claims.py` | `SourceRecord`, `RepositoryRef`, explicit `ClaimRecord` with `unverified` validity; config v1–v8 | Reuse existing per-repo claim extraction; do not add cross-repo claims to config v9 without a justified migration |
| `acquisition.py`, `derived.py`, `derived_models.py` | Bounded raw-byte observation, content hashes, strict receipts and recheck statuses | Reuse safe observation primitives; do not equate HEAD with file identity |
| `contracts.py`, `compiler.py`, `rendering.py` | Deterministic per-repo contracts/selection; compiled JSON v3 | Compose typed results; do not change v3 or rank sources across repos |
| `integrity.py`, `relations.py`, `context_engine.py` | Phase 8 single-repository policy over provider relations | Keep workspace policy independent of provider graph internals |
| `cli.py` | `scan`, `check`, `contracts`, `compile`, `derived`; exit conventions 2/3/4/6/7 | Add a separate `workspace` command family; old commands remain unchanged |

Baseline implementation has Python 3.12+, Typer, pytest and Ruff. `make check` is the local verification gate. The active repository tree has no Phase 10 workspace module, workspace manifest, or cross-repository output contract at this baseline. The Phase 9 independent review at `docs/reviews/phase-9-independent-review.md` raised F9-001–004; `61ca157` contains reported fixes, **not a re-review verdict**. No active Phase 10 ADR is present in `docs/adr/` at the inspected baseline.

## 3. Scope and non-goals

### Required for Phase 10

1. A versioned, strict, bounded **local workspace declaration v1** describing 2–8 repositories with stable aliases, explicit local roots and expected observed repository identities.
2. Repository-qualified source and claim references, independent per-repo snapshots/coverage and typed cross-repo findings. There must be no collision between identical relative paths or claim IDs in different repositories.
3. Explicit **`contract_pin`** check, **`mirror_bytes`** check and **`claim_match`** check (defined below), each with evidence, uncertainty and deterministic output.
4. Deterministic `workspace check` and `workspace compile` CLI surfaces, with offline operation, bounded reads, strict validation, JSON/text rendering, and explicit output behavior.
5. Composite context selection using existing local `resolve_contract`/`compile_context`, a per-target budget, no global authority scalar, and results that truthfully expose compilation gaps and cross-repo check findings.
6. Unit/integration/golden tests, negative/adversarial tests, durable workspace contract documentation, implementation evidence and focused documentation staleness sweep.

### Explicitly deferred

- Automatically discovering repository topology or consumer relationships from imports/build manifests; semantic API/SQL/schema compatibility; transitive product dependency inference; automatic cross-repo claim extraction, truth adjudication or natural-language contradiction detection.
- Cross-repository structural graphs and symbol/link resolution; modifying Context Engine's protocol, database or service; cross-repo evidence provider contracts. Existing per-repo provider use may remain independent but is **not required** for the Phase 10 workspace commands.
- General cross-repository **derived-artifact** receipt DAGs, new Phase 9 receipt v2, automatic derivative regeneration, remote repository access and revision fetching. The consumer-owned cross-repo contract lock in this phase is a typed dependency/acceptance receipt for one producer source, but **not** a derived artifact receipt or a cross-root Phase 9 revalidation graph. A follow-up design is needed for durable cross-repo generated-artifact receipts.
- Global optimization/ranking of task context, global hierarchy of repository authority, hosted workspace registry, persistence, security attestations, signing, ACLs, auto-remediation, API/MCP service or UI, CI blocking, waivers and dashboards (Phase 11+).
- Any unconditional breaking change to single-repo config v1–v8, inventory v1, claims, compiled JSON v3, integrity JSON v2, derived receipt/result v1, or existing exit/status contracts.

## 4. Stable identity and manifest contract

### 4.1 Workspace declaration v1

Use a separate explicitly supplied TOML manifest (e.g. `workspace.context-integrity.toml`) loaded via `tomllib`. Do **not** silently scan parent directories or add a global registry. New schema marker `workspace_schema_version = 1` must not be confused with `.context-integrity.toml`'s `schema_version` 1–8. Unknown fields, duplicate TOML keys, wrong primitive types (including bool-as-int), duplicate IDs, invalid names, inconsistent references and unsupported versions are hard input errors with sanitized messages.

Illustrative shape (exact stable contract to be finalized with a fixture and documented before writing projectors):

```toml
workspace_schema_version = 1

[[repositories]]
alias = "api"
root = "../api"
repository_id = "repo_<32 lowercase hex characters>" # actual ID from `scan`, never inferred

[[repositories]]
alias = "web"
root = "../web"
repository_id = "repo_<32 lowercase hex characters>"

[[checks]]
id = "public-api-lock"
kind = "contract_pin"
producer_repo = "api"
producer_path = "spec/openapi.json"
consumer_repo = "web"
consumer_path = "contracts/public-api.lock.json"

[[checks]]
id = "schema-mirror"
kind = "mirror_bytes"
left_repo = "api"
left_path = "schemas/message.json"
right_repo = "web"
right_path = "schemas/message.json"

[[checks]]
id = "data-region-claim"
kind = "claim_match"
left_repo = "api"
left_claim_id = "data_region"
right_repo = "web"
right_claim_id = "data_region"

[[context_targets]]
repo = "api"
contract_id = "service-work"
budget_bytes = 12000

[[context_targets]]
repo = "web"
contract_id = "service-work"
budget_bytes = 12000
```

`repository_id` values are examples/placeholders above; the implementation must require real, validated IDs, not literal template values. Alias and rule IDs are stable explicit tokens; aliases have no implied trust precedence. Each context target is one `(repo alias, contract ID)` pair; duplicates should be rejected rather than silently rerun. `context_targets` may be absent for `workspace check` but are required for `workspace compile`.

Manifest roots are relative to the manifest's parent, may use `..` to locate explicit sibling repositories, and are **local machine configuration only**. They are never serialized in machine-readable reports. Reject absolute/URL/UNC root values unless a separate explicit, reviewed design is adopted; limit path length and component count. Resolve and validate the path without following manifest/root symlinks unexpectedly; record the actual discovered root. A root must be an actual repository boundary (not an accidental parent superproject or its subdirectory), distinct from every other declared root, and neither nested inside nor identical to another root. The workspace descriptor itself must be bounded and safely opened. A workspace can reside outside all participating repositories; avoid requiring writable shared parents.

Every alias must match the observed `RepositoryRef.id`. For a no-origin `local_fallback` identity, disclose the location-dependent portability limitation; do not substitute the human alias for identity or pretend that two clones with the same origin are two different logical repos. Reject duplicate observed repository IDs, including duplicate checkouts of the same remote, until a separate checkout-instance identity is designed. Preserve observed HEAD and dirty state as metadata, never as the sole content-change test. Repository discovery failures or identity mismatch cannot be downgraded to empty inventories.

### 4.2 Qualified references

Introduce narrow typed domain values such as `WorkspaceRepository`, `QualifiedSourceRef(repo_alias, repository_id, path)`, `QualifiedClaimRef(repo_alias, repository_id, claim_id)`, `WorkspaceCheckSpec` variants and `WorkspaceFinding`. Keep file I/O out of frozen models and interfaces out of policy.

- `path` is always normalized **relative to its own repository**, never the workspace directory or another repo; use existing safe-path validators and descriptor-relative, no-follow raw-byte reading. Do not accept `../`, absolute paths, `.git`, drive escapes, unsafe control characters, ambiguous separators, invalid encodings or symlink traversal. Reject refs to directories and non-regular files.
- Qualified identities must include the **actual repository ID**, not just alias, in internal comparisons and JSON. Aliases make output readable; IDs prevent accidental rebinding.
- Claim IDs are scoped to repo identity. Compare the typed declaration and its provenance; a simple matching string ID is insufficient to infer the same subject.
- Keep source metadata and origin separate from policy. Avoid inferring source authority from repository order, workspace alias, git recency or provider ranking.

## 5. Three explicit cross-repository checks

All checks are **opt-in and finite**. Every check's result needs a stable check ID and rule kind; evaluation status (`evaluated` or `inconclusive`); signal (`aligned`, `review_required`, `declared_disagreement`, or `not_established` as appropriate); deterministic reason code(s); and two or more repository-qualified observed evidence records. A positive result means only what that rule has tested. Never emit “compliant”, “compatible” or “verified true” from equal hashes or matching declarations.

### 5.1 `contract_pin`: producer-to-consumer change impact

The consuming repo maintains an ordinary **explicit lock file**, e.g. `contracts/public-api.lock.json`, with this strict JSON v1 shape:

```json
{
  "contract_lock_schema_version": 1,
  "producer_repository_id": "repo_0123456789abcdef0123456789abcdef",
  "producer_path": "spec/openapi.json",
  "accepted_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
}
```

The lock is a **consumer's declared accepted contract revision**, not generated truth or an authenticated signature. It is owned and changed explicitly by the consumer; the workspace command never updates it. Strictly validate unknown/duplicate keys and types, normalize path and match lock identity/path to the producer declaration. Hash raw producer bytes, not HEAD or git blob OIDs. Compare the observed producer SHA256 against `accepted_sha256` and report `producer_contract_revision_changed` when they differ. Include the lock's own observed content hash and both qualified paths as evidence. If the consumer lock is unreadable/invalid/missing or the producer unavailable, return an explicit uncertainty/input-failure distinction—not agreement. A matching pin is **revision alignment only**; it does not establish that consumer code uses the lock or that a schema change is breaking. Output a caveat such as `consumer_implementation_not_verified` without treating that general limitation as a fatal uncertainty when all expressly required pins are observable.

### 5.2 `mirror_bytes`: intentionally identical files

Read and SHA256 both explicit source files. A digest mismatch is definite **byte divergence**, not necessarily semantic incompatibility; equality is observed byte equality, not proof that either file is correct. A missing input is a review signal when it is deterministically missing; unsafe/unreadable/too-large/unstable input is inconclusive. Enforce no-follow restrictions independently in both roots. Test same relative path in different repos and ensure no path-key collision.

### 5.3 `claim_match`: paired declarations

Obtain **existing explicit** `ClaimRecord`s through each repository's configured claim pipeline; do not parse arbitrary prose. Compare `claim_type`, `subject`, `predicate`, `scope` and `value` only after deciding comparability:

- IDs locate declarations only. A declared pair is comparable for value disagreement only if its type/subject/predicate/scope match exactly under a documented deterministic normalization (prefer exact strings to arbitrary case-folding/semantic expansion).
- Comparable differing values yield `declared_claim_disagreement`; identical values yield `declarations_agree`. Both keep `ClaimValidity.UNVERIFIED`, provenance source/revision, original scopes and any dependency/coverage caveat. No automatic policy winner.
- Different types/subjects/predicates/scopes, non-active/superseded declaration provenance, unresolved claim dependencies, unknown current inventory/config, missing or ambiguous IDs yield `not_comparable` or `claim_evidence_incomplete` as **inconclusive**, rather than simply “no contradiction.” If pre-existing claim pipeline already constrains some cases, reuse that actual rule rather than inventing another.
- Treat a claim whose upstream dependency changed or became unobservable as uncertain even when its asserted text is identical; use existing claim dependency/provenance records where sufficient, and document any remaining revalidation gaps. Do not promote a plan, historical review or derivative to authoritative product truth.

Optional contextual explanation can show both distinct declarations; no snippets/source bodies, model calls or semantic matching. Do not generalize to an all-pairs contradiction engine.

### 5.4 Overall status and coverage

Separate **observation completeness** from **findings**. A check with a known mismatch remains a finding even if an independent evidence read is uncertain; retain both reasons. Workspace overall status must not flatten uncertainty into success. Suggested projection distinguishes `review_required` (definite divergence/missing required input), `inconclusive` (no definite mismatch, necessary evidence unavailable), and `aligned_observed` (all explicit checks observed aligned), with clear precedence and per-rule caveats. An empty check set must *not* imply product-wide compliance; report `no_checks_declared` or equivalent scope caveat. Mirror/lock/claim rule semantics should remain individually inspectable and may use more precise signals than the aggregate.

## 6. Composite task-context compilation

`workspace compile MANIFEST --task TEXT --format text|json [--output PATH]` processes each explicit `context_targets` entry using existing per-repo inventory/config, `resolve_contract`, `compile_context` and typed projections. The task is an opaque selection input: no automatic classification and no model. For Phase 10, disable provider mode at this surface unless the team can prove per-repo provider identity, errors and coverage are correctly represented; **do not silently invoke** Context Engine or conflate its per-repo graph snapshots.

Key behavior:

1. Reuse each repository's configured context contract; no implicit synthetic workspace-wide contract and no bypass of per-repo excluded/required semantics.
2. Enforce explicit positive per-target byte budgets and a bounded total sum. Use existing compilation semantics **independently per target**. No greedy cross-repo allocator, no global authority ranking, and no extra full-file reads. Preserve individual `complete/incomplete` and warnings.
3. Emit a new `workspace_context_schema_version = 1` body-free index: workspace manifest hash, sorted repository descriptors (alias, `repo_id`, observed HEAD/dirty, identity basis), target `(alias, contract_id, budget)`, per-repo typed selected sources with qualified `repo_id/path`, source revisions/derivation, selection decisions/dependencies, per-target completeness, check findings/coverage, and aggregate incomplete/review flags. Include a SHA256 of the task, not raw task text, in this new projection. If an existing per-repo JSON v3 projection includes task text, **do not embed that raw projection** in the workspace output.
4. Source IDs remain repo-scoped; two `src_...`/paths in different repos never deduplicate. Sort by declared/stable alias + qualified path + decision ID; explicitly document determinism and snapshot limitations.
5. If any per-repo compilation is incomplete, the workspace output is not “complete.” A check mismatch does not automatically delete or override selected sources, and an inconclusive check is prominently retained. Preserve separate `selection_complete`, `checks_status` and overall status to avoid confusing relevance selection with cross-repo policy approval.
6. Context output is an index for an agent/human to inspect, **not** source-body bundling, a durable Phase 9 receipt, or a promise that inputs will remain unchanged. If a saved output needs freshness guarantees, record that as a documented Phase 10 boundary and a follow-up to extend receipts across repository IDs.

## 7. CLI and stable machine contracts

Proposed additive commands:

```bash
uv run context-integrity workspace check ./workspace.context-integrity.toml --format json
uv run context-integrity workspace compile ./workspace.context-integrity.toml \
  --task "Update API consumer" --format json --output ./workspace-context.json
```

The manifest is explicit; no root or workspace discovery from an ambient cwd. Use a Typer sub-app near existing `derived`, not a parallel CLI package. Existing commands/options keep their old meanings. Outputs default to stdout; explicit `--output` should be a new file only, no implicit write/overwrite, with clear safety rules for a directory outside repository roots. Avoid placing outputs under any participating inventory root where they would change candidate sets or accidentally become dependency inputs. Fail closed on unsafe parents/symlinks; no silent partial result file or multi-file write assumption. A read-only check must not mutate a repository, Git index, consumer lock, receipt or context output.

New JSON contract names are **separate** from existing ones: `workspace_check_schema_version = 1`, `workspace_context_schema_version = 1`, and `contract_lock_schema_version = 1`. Strict allowlist projectors and parsers; no dataclass `asdict()` dumping unknown/internal fields. Record deterministic identifiers, rule/check ID, exact qualified input paths, content hashes, derivation/snapshot/coverage and structured codes. Exclude machine-specific absolute roots, raw source text, raw task text, credential-bearing remotes, provider raw JSON, stderr or timestamps. Text output must be escaped/sanitized and correlate unambiguously with JSON.

Follow established exit conventions: `0` for successful evaluation **even when findings are present** (no CI gate); `2` CLI usage; `3` repository/discovery errors; `4` explicit output publication failures; `6` malformed manifest/config/lock/input contract errors; `7` only actual provider/evaluation failures that existing interfaces classify there. Define and test the difference between a malformed declaration (input error) and an unobservable required source (reported uncertainty). Do not make a novel exit code mean “integrity violation” in this phase.

## 8. Architecture and implementation seams

Prefer small, phase-local modules rather than mutating single-repo models everywhere:

| Proposed module | Ownership |
| --- | --- |
| `workspace_models.py` | Frozen alias-qualified refs, check variants, typed observation/result and construction invariants |
| `workspace_config.py` | Strict TOML + consumer lock v1 parsing; safe root/relative path declaration; cardinality bounds |
| `workspace.py` | Workspace resolution, per-repo observation orchestration, pure policy comparisons, per-repo compilation composition |
| `workspace_output.py` or focused `rendering.py` additions | Stable allowlist JSON/text projectors, escaping and output shape |
| `cli.py` | Add `workspace check` and `workspace compile` entrypoints, error mapping and explicit output |
| Existing `repository.py`, `acquisition.py`, `claims.py`, `contracts.py`, `compiler.py` | Reuse single-repo discovery, safe bytes, claims, contract resolution and selection, with only necessary narrow hooks |

The module names are suggestions; reuse an existing abstraction when materially simpler. Keep I/O separate from policy; do not import the CLI into domain modules. Add focused types rather than modifying `SourceId`, `RepositoryRef`, `ClaimRecord` or Phase 9 receipt schemas in a breaking manner. A proposed convenience API that would require touching every renderer is probably a sign the abstraction is too broad.

### Observation and trust budget

- Manifest <= 256 KiB; consumer lock <= 16 KiB; at most 8 repos, 128 checks, 16 context targets, and 256 total distinct qualified source references. Use strictly bounded, no-follow file reads with an explicit per-file max (prefer Phase 9's 5 MiB) and an aggregate observation/read-attempt budget (e.g. 64 MiB / 4,096 operations). Treat budget exhaustion as uncertainty; don't continue after silently dropping checks.
- Cache observations by `(observed repo ID, relative path, observation limits)` **within one invocation**; never share cached bytes across repos just because paths match. Cache hashes/typed metadata, not entire document bodies. If two checks need the same path, take one coherent observation when safe.
- Check repository identities before trusting lock/claim/compiled evidence. Cross-repo checking is sequential, not an atomic two-repo snapshot. For a high-value check, optionally re-read selected identity/hash pins at end and downgrade changed-in-flight observations; at minimum disclose the non-atomic limitation and do not assert snapshot coherence not implemented.
- Staged/unstaged/untracked changes with same HEAD are observable by content hash. A missing producer is different from an unreadable producer; both differ from a malformed manifest/lock. Pre-existing Git warnings and inventory truncation must not be discarded when used by claim/compile checks.
- No network, untrusted code execution, hidden database, automatic Git checkout/fetch, symlink traversal or model/provider call. All untrusted string output sanitized; do not leak absolute user workspace paths through exception messages.

## 9. Work packages and ordering

1. **Reconcile:** Record actual HEAD, pending Phase 9 review disposition, source/test seams and any changed upstream contracts. Read only required history; verify previous config/output versions.
2. **Contract design first:** Finalize concrete strict manifest/lock examples, typed qualified identities, status/reason matrix and JSON v1 golden fixtures. Write a short `docs/workspace-integrity-contract.md` as the durable reference; resolve any architectural conflict with an ADR before coding.
3. **Safe workspace resolver:** Bound manifest read, parse/validate, discover declared roots, bind IDs, reject collisions/nesting/unsafe paths and memoize bounded repo contexts. Unit-test adversarial alias/identity/root cases.
4. **Explicit check evaluator:** Implement safe paired reads, lock validation, claim pipeline reuse, condition/coverage handling and deterministic evidence/reasons. Add small synthetic 2–3 repo fixtures that are genuinely independent Git repositories with separate configs.
5. **Context composition:** Reuse per-repo `compile_context`, emit namespaced source references and per-target completeness. Prove no raw bodies/tasks or accidental source deduplication, and no changes to compiled v3.
6. **CLI and output:** Add additive commands, strict projectors and explicit new-file publication with no overwrite. Exercise JSON/text, stdout/new-file flows and error exits.
7. **Regression/security/staleness:** Run full gate and targeted adversarial matrix. Update durable contract and architecture with the actual seam, `README.md`, `docs/README.md`, and implementation report. Update `docs/current-state.md` only after verified delivery and without closing pending independent reviews.

Prefer a coherent vertical slice with all three explicit check types and one composite context flow. If a requirement is infeasible safely, stop, document the defect/alternative and request scope resolution; do not quietly emit a happy-path-only implementation and mark the phase complete.

## 10. Acceptance matrix

| Scenario | Expected observable behavior |
| --- | --- |
| Two valid independent roots, matching identity and contract lock | `contract_pin` aligned **revision observation**, no semantic compatibility claim |
| Producer bytes edited unstaged or staged, HEAD unchanged | `review_required` with producer/consumer qualified provenance; reversion to same bytes can restore alignment |
| Producer missing versus unreadable/symlink/oversize | Missing is not aligned; unobservable is inconclusive with distinct reason; no outside-root reads |
| Lock producer ID/path forged, malformed JSON, duplicate key, unsupported version | Sanitized input rejection or explicit untrusted/inconclusive policy; never accepted as matching |
| Mirror exact bytes versus one-byte difference | Observed equality versus deterministic byte divergence; same relative filename across repos stays distinct |
| Paired claims with matching type/subject/predicate/scope and value | `declarations_agree`, **unverified**; provenance from both repository revisions |
| Comparable claims with different value | `declared_claim_disagreement`, no invented authority winner |
| Claims with incomparable scope, missing ID, superseded source, unknown dependency or inventory gap | Explicit inconclusive/not comparable; no fake agreement |
| Duplicate alias, duplicate observed repo ID, nested roots, wrong expected ID | Rejected, no accidental cross-binding |
| Missing/invalid per-repo config or required context contract | Input error/typed incomplete as defined; no fabricated empty-complete selection |
| Two targets select `docs/architecture.md` | Both records included with different repository identities, correct raw revision/selection context |
| One incomplete compilation or one uncertain check | Composite status distinguishes incompleteness/uncertainty; never “all complete” |
| Manifest has no checks, or context targets not declared | No false product-wide compliance; check can report empty-scope caveat; compile refuses absent targets |
| Provider missing or engine not installed | Default workflow remains fully offline and functional without optional provider |
| Unsafe output target, existing target or write failure | No replacement, sanitized exit 4, explicit partial-write behavior if unavoidable |
| Deterministic repeated run with unchanged files | Byte-identical canonical JSON; no timestamps, absolute paths, secrets, raw task/source bodies |
| Baseline single-repo scans, checks, compile, derived receipts | All remain compatible; no config v9/receipt v2/integrity v3 forced |

Additional tests: zero/very large values, non-ASCII and slash ambiguity, duplicate TOML/JSON keys, malicious control strings, symlinked manifest/locks/repos/outputs and swapped-parent race best-effort checks; many-to-one rule references, stable sorting under permutation, missing Git, no-origin fallback, same-origin clone ambiguity, dirty repo and byte budget exhaustion. Use repository fixtures rather than primarily mocking the evaluator. Consider test-time fuzz/property tests for decoding/normalization if dependency-free; do not add a fuzzing framework without justification.

### Verification gate

```bash
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 uv run pytest -q tests/test_workspace.py tests/test_workspace_cli.py
git diff --check
```

Adjust target filenames if test layout differs; record exact commands, platform, counts, failures/skips and whether the environment could run them. Do not cite the baseline's 1,071 passing tests as proof of the new changes. Require independent review after implementation, followed by a separate fix pass and re-review where warranted.

## 11. Deliverables and documentation sweep

- Code/tests/goldens for manifest, lock, evaluator, compiler composition, CLI and adversarial boundaries.
- `docs/workspace-integrity-contract.md` documenting exact grammar, version fields, command examples, status semantics, reason codes, ID/path rules, limits, source/claim provenance, output/privacy and limitations. Include a complete **valid** fixture in tests rather than only placeholders.
- Minimal durable architecture update describing workspace composition and ownership. Add an ADR only if a material design decision merits it (e.g. repository checkout identity conflict or changing trust rules). No duplicate source-of-truth documents.
- `docs/implementation-reports/phase-10-implementation-report.md` with actual changed paths, acceptance mapping, test evidence, deviations/known gaps and review handoff. This report is not acceptance.
- `docs/current-state.md`, `README.md`, `docs/README.md` and documentation index adjustments justified by delivered state, with explicit continued status of Phase 4/7/8/9 pending independent work.

Sweep for current-vs-historical staleness: phase number; single-repo-only claims in active docs; cross-repo previously deferred behavior; config v8/compiled v3/integrity v2/derived v1 compatibility; `Context Engine` actually per-repo; local/no-network guarantee; ambiguous “clean/verified/compatible” wording; absolute-path leakage; Phase 9 and Phase 8 review acceptance claims; workspace docs added to navigation. Preserve historical plans/reviews as historical evidence and list actual changed/deferred items in report.

## 12. Stop conditions, risks, and Phase 11 boundary

Stop and obtain a concrete architecture decision if Phase 10 requires: redefining existing repository IDs; treating two same-origin checkouts as independently authoritative without an instance identity; letting one repository escape its own path root; trusting a provider's cross-repo graph with no documented protocol; silently upgrading old schemas; or claiming semantic compatibility from hashes/strings. Make uncertainty visible if race-free multi-repo snapshots or full consumer implementation coverage cannot be established.

Phase 10 acceptance is **not** the end of the original cross-repository vision. Future increments may add external contract parsers with their own versioned semantics, code graph relationships, product policy/waivers, cross-repo receipt DAGs and provider-backed impact tracing. Phase 11 owns CI/governance/observability. Phase 12+ may own semantic inference and repair. Their eventual possibility is not a reason to build frameworks, persistence or automatic agents now.

## 13. Independent review mandate

The independent reviewer must compare the actual diff and runtime behavior with **this plan and independently with the PRD/architecture**, discover flaws in the plan itself, test false-alignment and missing-evidence pathways, inspect representative code outside newly added modules, and deliver prioritized reproducible findings under `docs/reviews/`. A plan checkbox is neither a proof of correctness nor permission to ignore an unanticipated material failure. The companion Phase 10 review prompt spells out this protocol.
