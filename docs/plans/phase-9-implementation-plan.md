# Context Integrity — Phase 9 Detailed Implementation Plan

**Phase:** 9 — Derived Context Revalidation\
**Document role:** Normative *proposed* implementation plan, not evidence of delivery\
**Repository:** https://github.com/jasonkli21/context-integrity\
**Repository baseline inspected:** `main` at [`917a9d318824d4fa67a7206dd3784068dabc7a21`](https://github.com/jasonkli21/context-integrity/commit/917a9d318824d4fa67a7206dd3784068dabc7a21), October 21, 2026\
**Predecessor:** Phase 8 — Architectural Integrity; review fixes applied, independent re-review still pending according to `docs/current-state.md`\
**Successor:** Phase 10 — Cross-Repository Integrity

> **Starting-state rule:** Re-read `docs/current-state.md`, the current branch/head, and affected code/tests before editing. If HEAD differs from the reference, reconcile rather than applying this plan literally. The Phase 8 independent acceptance state is an outstanding prerequisite risk, not permission to rewrite or hide that status.

---

## 1. Purpose and product boundary

Deliver a deterministic, local, explainable means to **record the known provenance of derived context** and **reassess that context after its upstream inputs change**. The first supported artifacts are generated summaries, agent handoffs, and saved outputs of the existing deterministic context compiler. Derived context must remain an explicitly labeled, non-authoritative cache; a matching hash is *not* a factual or semantic validation of a summary.

The minimum useful user journey:

1. An agent produces `docs/handoff.md` from repository documentation and records exactly which source revisions it used; or a user saves a JSON `context-integrity compile` output.
2. A small, schema-versioned **receipt** captures artifact identity, its own content digest, origin/derivation, observed repository identity, pinned dependency content digests, optional policy/config provenance, and known coverage gaps.
3. After edits to any declared input—including dirty worktree edits—a local revalidation command compares the receipt with the current observed repository. It reports **unchanged observed inputs**, **review required**, or **inconclusive** with precise reasons.
4. If a derived artifact depends on another registered derivative, upstream changes propagate **transitively** without needing the intermediate artifact's bytes to change.
5. A human/agent reviews and regenerates or deliberately re-acknowledges artifacts. The tool does **not** rewrite the artifact or silently advance its dependency snapshot.

### Success and non-success examples

- Change an unrelated source: recorded dependencies remain unchanged; no blanket HEAD-based invalidation.
- Change one upstream document: the corresponding artifact requires review even if the document is later Git-staged but HEAD stays the same.
- Remove a dependency or make it unreadable: the check never reports that artifact as verified/fresh.
- Change an accepted ADR's effective lifecycle or configured authority: an artifact pinned to that policy state is flagged even if the ADR body did not change.
- Parent derivative unchanged but its upstream source changed: a dependent handoff is marked for review through the parent receipt.
- A produced summary is factually false while all declared hashes match: **the checker cannot tell** and must say so.

## 2. Traceability to the actual repo

| Existing source | Observed implementation | Phase 9 reuse / constraint |
| --- | --- | --- |
| `docs/prd.md`, §20 and roadmap §29 | Generated summaries/handoffs are caches; dependencies, derivation, revalidation and expiration are required; Phase 9 specifically covers derived revalidation | Do not create new authority for generated text |
| `docs/architecture.md`, §§2.4–2.7, 6.12, 16, 18–22, 33 | Read-only/local-first; canonical vs derived distinction; suggested `SourceDependency`; determinism, versioned contracts and trust boundary | Prefer an independent receipt format and pure evaluator before persistence/automation |
| `AGENTS.md`, §§2–5, 7–11 | Current-state navigation, phase discipline, minimal dependencies, acceptance via tests, documentation lifecycle | No mass document rewrite, no automatic status promotion |
| `docs/current-state.md` (2026-10-21) | Phase 8 delivered and remediated; independent acceptance remains pending; Phase 9 not delivered | Preserve truthful status and known limitations |
| `docs/architecture-integrity-contract.md` | Phase 8 config v8, relation provider, integrity JSON v2; conservative coverage and explicit inconclusive state | Revalidation is **not** another architecture-check rule |
| `docs/evidence-contract.md` | Phase 7 provider v1, compiled-context v3, snapshot coherence, coverage | Provider-backed compiles cannot be called fully revalidated from file hashes alone |
| `src/context_integrity/models.py` | `SourceRecord`, `SourceRevision` (content SHA256, HEAD, git status), `CompiledDependency`, `CompiledContext.dependencies`, `ClaimDependency`, `RepositoryRef`; config versions through v8 | Reuse the vocabulary/normalization; do not overload claim validity or existing statuses |
| `src/context_integrity/acquisition.py` | Bounded descriptor-safe raw-byte hashing, symlink protection, candidate inventory distinct from file existence | Reuse/harden safe file reads for explicit artifact/code paths; do not assume code files appear in inventory |
| `src/context_integrity/compiler.py` / `rendering.py` | `compile_context` composes inventory and provider candidates; `compiled_context_dict` v3 serializes selected sources, config fingerprint, provider state and dependencies | Preserve JSON v3; build a separate receipt projector from typed compile state |
| `src/context_integrity/cli.py` | Typer commands `scan`, `check`, `contracts`, `compile`; error conventions (3 repo, 4 output, 6 config, 7 provider) | New `derived` subcommands, no change in old command behavior without explicit option |
| Phase 8 review fixes / report | HEAD `917a9d3` addresses F8-001..004; 965 tests claimed in report, not independently rerun here | Do not assume prior review has accepted fixes; regression suites remain mandatory |

### Existing data-model trap to avoid

`CompiledContext.dependencies` accounts for **selected inventory `SourceRecord`s**. Phase 7 can additionally select code/evidence-provider candidates; their provenance is in `decisions`/provider state, not necessarily in that `dependencies` tuple. A Phase 9 receipt generated only by serializing `compiled.dependencies` would silently omit real dependencies. Similarly, selected-source hashes alone do not cover a changed contract, configuration, relevant provider snapshot, or previously omitted newly eligible source. Explicitly model these limitations.

## 3. Phase scope

### In scope

- A dedicated typed, strictly validated **derived receipt v1**; deterministic JSON/text projection; no document bodies in receipts.
- Explicit local capture of a generated summary/handoff with named source dependencies and derivation metadata.
- First-class receipt emission for **saved** JSON `compile` output, with no change to the compiled-context JSON v3 schema.
- Pure revalidation against the observed repository: content drift, artifact mutation, missing/unreadable/symlinked inputs, lifecycle/authority/config drift, unsupported/unknown evidence, duplicate/corrupt receipts.
- Chained derivative dependencies, bounded graph traversal, cycle checks and deterministic propagation of review/inconclusive state.
- Provenance honesty: distinguish declared from exhaustively known dependencies and support conservative provider-aware treatment.
- Offline deterministic CLI/tests, safety/resource budgets, minimal docs and implementation report.

### Explicitly out of scope

- Claim verification, semantic truth checking, rewriting or regenerating summaries, auto-expiration/deletion, LLM calls, embeddings, model routing, automatic dependency extraction from prose, automatic source-to-summary mapping, shared persistence/database, global receipt registry/daemon, filesystem watchers, network fetching, periodic jobs, cross-repository dependencies, CI blocking/waivers/governance dashboards, change-lineage/rename inference, or Context Engine internals.
- Improving Phase 8 architectural graph analysis unless a focused regression directly affects Phase 9.
- Changing existing claim `unverified` semantics, Phase 4 finding severity, Phase 5 contracts, Phase 6/7 selection, config schema v8, inventory v1, compiled context v3, or integrity JSON v2.

Do **not** introduce config schema v9 merely for receipt storage. The new `derived_receipt_schema_version=1` is an independent machine-readable contract. If a narrowly justified new config key is indispensable, make it an explicit design decision with compatibility tests; do not silently advance v8.

## 4. Proposed core architecture

```text
Existing canonical repository files / Git / explicit config
                      |
            repository discovery + bounded safe reads
                      |
          snapshot + source revision observation
                      |
        +-------------+-------------+
        |                           |
  manual derivative capture    optional compile receipt
        |                           |
        +---------- typed receipt v1
                            |
                 sidecar JSON (derived metadata)
                            |
                    pure revalidator
                     /            \
            direct inputs      referenced receipts
                     \            /
                typed status + reasons
                            |
                explicit JSON/text projector
```

Recommended seams (adjust exact filenames to established layout):

- `src/context_integrity/derived.py`: receipt domain validation, deterministic identity and revalidation logic. If too large, split `derived_models.py` and `revalidation.py`; do not put file I/O in frozen models.
- `src/context_integrity/derived_io.py` (or existing acquisition/repository helpers): strictly bounded receipt decode, artifact/dependency file observation, secure write of **only explicitly requested** new receipt files.
- `src/context_integrity/rendering.py`: explicit `derived_receipt_dict` and `derived_check_dict` allowlist projectors; avoid dumping raw dataclasses.
- `src/context_integrity/cli.py`: `derived capture`, `derived check`; additive `compile --receipt-output` only if output is saved JSON and receipt can be generated from same in-memory result.
- `tests/test_derived.py`, `tests/test_derived_cli.py`, purpose-built golden fixtures; reuse `tests/conftest.py` temporary repositories.

Keep `repository.py` responsible for identity/Git; `acquisition.py` for safe raw-byte observation; `derived` for policy/status; CLI for user interaction; rendering for projection. Neither the Context Engine adapter nor the policy/authority engine should own derived cache validity.

## 5. Receipt schema v1: precise contract

A receipt is a **claim about a particular observed derivation**, not a trusted attestation. Example *illustrative* JSON (implement exact keys, types, ordering and defaults consistently in a durable contract doc):

```json
{
  "derived_receipt_schema_version": 1,
  "artifact": {
    "id": "handoff-a",
    "kind": "handoff",
    "path": "docs/handoff.md",
    "content_sha256": "<64 lowercase hex characters>",
    "derivation": {"kind": "model", "producer": "agent", "version": null}
  },
  "repository": {"id": "<stable repository id>", "git_head": "<HEAD or null>", "git_dirty": true},
  "provenance_scope": "declared",
  "config_sha256": "<config SHA256 or null>",
  "dependencies": [
    {
      "kind": "source",
      "path": "docs/prd.md",
      "source_id": "<stable source id>",
      "content_sha256": "<SHA256>",
      "observed_lifecycle": "active",
      "observed_authority": "architecture_product"
    }
  ],
  "upstream_receipts": [],
  "provider_context": [],
  "coverage": {"known_incomplete": false, "reasons": []}
}
```

Use a normal valid SHA in fixtures; the placeholders above are instructional, not fixtures. Be explicit about the following:

1. **Identity:** repository ID, artifact ID/path/kind, artifact bytes digest, derivation kind (`manual`, `tool`, `model`), bounded producer/version tokens where known; generated types never imply authority. A manual declaration of model origin is self-reported.
2. **Source dependencies:** normalized repository-relative exact paths, stable source IDs, pinned SHA256, optional observed effective lifecycle/authority; include source kind/observation basis only when useful to explain confidence. Allow explicit dependencies on code files not present in the documentation inventory via secure file hashing rather than inventing an inventory classification.
3. **Context/policy dependencies:** pin config fingerprint (including `null` vs present); for compiled receipts, record contract ID and a deterministic digest of the effective contract and relevant compilation inputs (selection/budget/task digest). Do not persist raw task text in the receipt. Capture provider id/version/schema/snapshot/coverage fingerprints only from already validated typed provider state.
4. **Upstream derived dependencies:** path to a referenced receipt (repo-relative), pinned upstream artifact identity/hash and receipt hash; the checker must validate the referenced receipt, require matching repository identity, and propagate its status. Do not silently infer relations from filenames.
5. **Coverage:** `declared` vs `compiler_selection` scope; explicit gaps, unresolved inputs, and provider-dependent limitations. The absence of a gap flag is not proof of exhaustive semantic provenance.
6. **Versioning:** reject unknown receipt version, unrecognized enum, unknown required/extra keys, conflicting duplicate ID/path, invalid digest, invalid token, inconsistent content/receipt pointers and noncanonical path; keep standalone version v1, independent of configuration and other JSON outputs.
7. **Determinism:** stable sorted dependencies, stable IDs/digests based on normalized typed data, no timestamp/absolute path/process PID/random value, portable JSON encoding, paths as POSIX strings. Reject rather than quietly reorder ambiguous duplicate declarations; canonical serializer controls key order.
8. **Safety:** never embed summary content, model prompts, credential-bearing env, raw stderr, provider raw output, private absolute paths or untrusted free-form source prose in stable receipt/result JSON. Bound string lengths, item counts, JSON depth, receipt bytes and total dependency traversal work.

### Provenance distinctions

- `declared`: user explicitly listed the sources they believe the artifact used. The checker **does not** certify list completeness.
- `compiler_selection`: capture from a successfully completed compilation object, preserving every selected inventory **and provider** candidate, effective policy/config/contract context, provider coverage/incompleteness, task digest and budget; still not a claim of semantic truth or a frozen closed-world repository.
- For an incomplete compiler package or any provider uncertainty, retain that fact. Do not call the artifact globally fresh just because its file hashes match.

### Artifact/receipt storage

- Receipt JSON is written only when an explicit `--receipt-output` is supplied. No hidden `.context-integrity` state directory, DB, or automatic modification of repo files.
- Artifact files and referenced source/receipt files must remain in one repository root in Phase 9. A user-selected receipt output outside that root is acceptable only as an output destination if it cannot introduce unsafe input references; all serialized paths must remain repo-relative. The simplest safe v1 contract can require receipts inside the root and should document that limitation.
- Never load a repository instruction file as instructions; treat its bytes as untrusted data only.
- Disallow an artifact depending on its own receipt or itself and reject cyclic receipt dependencies.

## 6. User-facing CLI, deliberately narrow

Illustrative interface (final spelling may fit Typer conventions; document actual flags in the durable contract and test them):

```bash
# Capture a manually/agent-produced summary/handoff. No modification of the artifact.
uv run context-integrity derived capture docs/handoff.md . \
  --id handoff-a --kind handoff --derivation model --producer agent \
  --depends-on AGENTS.md --depends-on docs/prd.md \
  --receipt-output docs/handoff.provenance.json

# Revalidate one receipt (reports; does not fix content or advance pins).
uv run context-integrity derived check docs/handoff.provenance.json . --format json

# First-class compiler receipt, without changing compiled JSON schema v3.
uv run context-integrity compile <existing-contract-id> . --format json \
  --output docs/saved-context.json \
  --receipt-output docs/saved-context.provenance.json
```

For a derived dependency, allow repeatable `--upstream-receipt <path>` at capture time. A `derived check` follows only explicitly referenced receipts, with a bounded DAG walk. If the chosen interface differs, preserve these **observable behaviors**, the explicit sidecar and the low-friction workflows. Do not require users to hand-edit receipt SHA fields.

Output and exit conventions:

- `derived check` defaults to read-only, deterministic report; `--format text|json`, optional `--output` consistent with current commands.
- Content drift/review-required/inconclusive are **results**, ordinarily exit 0 (not CI policy). Invalid receipt/config exits 6; unreadable/invalid repository 3; unable to write explicit output 4; keep provider failures at 7 where already applicable. Clearly distinguish malformed input from a valid-but-unverifiable dependency.
- No `--fix`, silent refresh, auto-promote, global scan of generated files, watcher, or fail-on-staleness CI gate.
- If requested output paths overlap artifact/dependency/receipt inputs or produce self-invalidating snapshots, refuse the command. Define atomic new-file write/cleanup and no-surprise overwrite behavior.

## 7. Revalidation algorithm

Use a **pure decision core** that accepts a validated receipt and typed current observations. Side-effecting reads happen in a small adapter.

### 7.1 Validate before comparing

- Decode strict version/shape with bounded JSON limits, including duplicate JSON keys and duplicate dependency identities.
- Verify expected repository ID, artifact path, artifact kind and available pinned context.
- Read actual artifact and each dependency through existing descriptor-safe helpers or equivalent no-follow relative-FD open logic. Validate normalized paths *before* filesystem use.
- Reject unexpected JSON fields and invalid trust-bearing metadata; do not ignore unknown schema versions.
- Check both raw content SHA256 and effective lifecycle/authority (when pinned and resolvable). Config absence/presence change is material; a config content change is not masked by its filename remaining the same.

### 7.2 Establish the current observation

- A change in the *declared* source's raw digest is a definite review trigger even when Git HEAD remains fixed, the file was staged, or the worktree is dirty.
- A changed Git HEAD alone is **not** automatically a trigger if relevant observed content/config/policy remains pinned and comparable; retain HEAD as explanatory snapshot metadata.
- A deleted or missing dependency, missing artifact, unreadable path, unsupported size, unknown revision/hash, symlink, or unavailable manifest field must not become a false “unchanged” assertion. Distinguish definite missing/changed from inability to observe safely.
- Lifecycle becoming superseded/historical/expired/invalid, policy/classification changes where pinned, or a changed config/contract fingerprint is material. Do not treat mere recency as supersession.
- A derivative whose own bytes changed without updated provenance needs review; its metadata cannot be accepted as matching the new artifact.
- For path renames, report missing old path/unmatched receipt instead of automatically applying Git similarity heuristics.

### 7.3 Provider and compiler caveats

- Preserve existing compiler selection semantics, including selected code candidates and provider origin. **Never** produce a `compiler_selection` receipt by simply copying `compiled.dependencies`: this omits provider candidates.
- If provider-backed evidence is present and the check does not re-query the *same validated provider contract* and compare an adequate snapshot/fingerprint, expose `provider_not_revalidated` and return **inconclusive** absent a stronger definite review trigger. Local code file hashes can detect some changes but cannot certify rank/coverage/structural context.
- Re-running Context Engine is optional in this phase, not required for the baseline. If attempted, use only Phase 7's bounded public adapter, never its internal cache/SQLite; treat changed capability/version/coverage/selection as review-required, failed runs as inconclusive. No network/install/daemon.
- Source-closure uncertainty for newly eligible/reclassified sources remains an explicit limitation: selected-source hashes do not prove that recompiling under present policy would choose the same complete package. A deterministic compile replay is an optional **validated** enhancement, never a silent claim.

### 7.4 Transitive dependencies

- Traverse referenced receipts by repository-relative path; validate each, hash the referenced receipt bytes, require matching pinned upstream artifact identity/path/digest and repository ID, and recursively evaluate.
- Memoize by normalized receipt identity for diamond DAGs; deterministically sort edges; reject cycles, missing links, excessive fan-out/depth and duplicate conflicting IDs.
- A stale upstream triggers review for a downstream artifact **even if every intermediate artifact body is byte-identical**. An upstream with unobservable state makes downstream inconclusive unless a definite changed input already establishes review-required.
- A modified parent receipt is not an automatically trusted new source of truth: surface changed metadata / untrusted chain instead of accepting newly replaced pins.

### 7.5 Status and reasons

Proposed aggregate enum:

| Status | Required meaning |
| --- | --- |
| `unchanged_observed_inputs` | Artifact bytes and every **declared/validated, observable** pinned dependency match. **Not** semantic validation, completeness proof or authority. Only emit if no material gaps affect this status. |
| `review_required` | One or more **definite** material changes: source/config/contract/artifact hash, effective lifecycle/authority (when compared), transitive upstream review, or a required input disappeared. All changed paths and uncertainty caveats remain visible. |
| `inconclusive` | No definite change established, but the check cannot evaluate all required evidence safely/fully (missing/unsafe/unreadable info, unsupported schema in a referenced receipt, provider not revalidated, known incomplete capture, etc.). Never render as fresh or valid. |

Precedence: definite change wins `review_required` while preserving other inconclusive reasons; otherwise any material uncertainty wins `inconclusive`; else `unchanged_observed_inputs`. If artifact/source absence is treated as definite review, distinguish from a transient read error in the reason code. Every result includes machine-typed reason codes and stable path/ID references (where safe), pinned and observed digests when present, declared-provenance caveat, and totals. Keep messages explanatory and never put untrusted source text in output. Use stable deterministic ordering and no timestamps.

## 8. Data integrity / security constraints

- Use existing `normalize_path` **and** a secure descriptor-relative file opening strategy to defeat symlink/TOCTOU escapes; POSIX paths only, no absolute paths, `..`, `\\`, empty components, NUL or URI-like path fields. Do not blindly use `Path.resolve()` then open.
- **Bounded reads:** define sensible hard caps (for example, receipt <= 1 MiB, individual artifact/dependency <= existing 5 MiB source cap, <= 256 direct deps, <= 128 total visited receipts, <= 16 nested depth and an aggregate byte/work budget). Make constants explicit, enforce during incremental reads, test boundary cases; adapt sizes if genuine usage requires it.
- A config file, code candidate or generated artifact omitted from `InventoryManifest.sources` still needs safe direct observation or an explicit inconclusive result; the mere existence of a file is not evidence of a pinned digest.
- Detect duplicate JSON object keys rather than allowing the second to overwrite critical hashes or paths. Validate Python model constructors too, not just parsed JSON.
- Do not execute artifact text, shell it, eval it, read arbitrary network locations or follow symlinks. Keep sensitive source bodies/task text/provider raw payload out of receipts/results.
- Output files should be written safely to user-chosen destinations only; avoid overwriting artifacts, cross-file inconsistent success or partially written receipts. No implicit durable state.
- A locally writable receipt is **not** tamperproof. File digests detect change relative to the receipt but do not authenticate the original agent/source; describe the trust limitation.

## 9. Tests: acceptance matrix

Write unit/fixture tests around the decision core **and** repository/CLI tests over real temporary Git worktrees, not mocks alone. At least:

| Suite | Minimum adversarial cases |
| --- | --- |
| Receipt model/parser | correct v1, old/future versions, duplicate keys/ids/paths, invalid digests/enums/paths, unknown fields, missing required fields, unsafe values, malformed/oversized JSON, deterministic roundtrip |
| Capture | summary/handoff captures actual bytes; multiple deps, unknown/non-inventory code path, config absent/present; unsafe path, missing file, symlink/escape, too-large file, same artifact/receipt path, duplicate deps, failure to write; no silent overwrite |
| Direct revalidation | unchanged, one dep edited in dirty worktree, staged edits with same HEAD, unrelated HEAD change, reverted identical bytes, artifact edited, dep deleted, unreadable/unknown hash, lifecycle/supersession changed, config/contract changed, no config->config, source renamed |
| Declared coverage | manual capture does not imply exhaustive provenance; no-source capture cannot falsely certify content; unknown/missing evidence never becomes unchanged |
| Compiler integration | inventory-only v3 produces receipt; provider-backed compiler selection not lost; config/contract fingerprint pinned; compilation status/integrity/warnings captured honestly; `--receipt-output` w/o saved JSON rejected; existing v3 golden unchanged |
| Provider | provider absent/incomplete -> inconclusive; wrong provider/version/snapshot/coverage (if replay supported) -> non-fresh; evidence-source content change catches review; no provider/network required for default offline suite |
| Chain / graph | A->B source drift propagates to B without A body change; diamond DAG memoization; missing parent, changed parent receipt, artifact/receipt hash mismatch, cycle/self-link, depth/fan-out/work cap, repository mismatch |
| Rendering / CLI | deterministic across insertion order and repeated runs; output JSON/text, expected exit convention, no absolute paths/body/task/raw stderr/timestamp, stable typed reasons, stdout unaffected by input order |
| Regressions | inventory, claims, authority/lifecycle, contracts, compiler v3, Phase 4 check, Phase 8 graph v2 untouched; schemas v1–v8 accepted as before; non-Git repository handling |

Additional important properties:

1. A stale derivative **never** becomes safe from a newer timestamp, a newer HEAD alone, or a newer receipt without explicit recapture.
2. A missing known upstream cannot silently be dropped from dependencies.
3. Independently repeat with permutation of dependency/receipt order and equivalent checkout roots; canonical JSON must be stable.
4. When both changed and unknown inputs exist, report definite change **and** uncertainty.
5. Receipt capture and check must not read files outside root or leak the content of untrusted files in errors.
6. No broad expensive scanning of codebases merely to establish a few explicit dependency hashes.

### Normal verification gate

```bash
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 uv run pytest -q tests/test_derived.py tests/test_derived_cli.py
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check
git diff --check
git status --short
```

If an offline environment is unavailable, record the exact constraint rather than claiming a pass. Do not download Context Engine to satisfy routine Phase 9 tests.

## 10. Work packages, in order

1. **Baseline/reconcile:** verify HEAD, review status and seams in `AGENTS.md`, `docs/current-state.md`, `models.py`, `acquisition.py`, `compiler.py`, `rendering.py`, `cli.py`, relevant tests and PRD/architecture.
2. **Define receipt contract:** choose exact schemas, status precedence, path/source identity, budgets and CLI flags. Write small fixtures for good and bad receipts *before* wide implementation. Confirm semantics for manual/compiled/provider contexts.
3. **Safe observations:** reuse bounded no-follow reads for arbitrary explicit paths, unify consistent SHA capture with status warnings, avoid source-body retention.
4. **Core evaluator:** pure typed comparisons of artifact/source/policy/contract snapshots with explainable stable reasons; no filesystem in core.
5. **Transitive provenance:** implement bounded receipt DAG traversal, hash linkage, cycle/conflict detection, memoization and deterministic propagation.
6. **Manual capture:** local explicit capture/receipt output; validate self/circular/unsafe references; no automatic source inference or authority escalation.
7. **Compiler receipt:** generate metadata from the in-memory typed compile result for **saved JSON** outputs, without changing v3 or losing provider-backed selections. Ensure two outputs are emitted without inconsistent half-success; choose/describe safe write ordering.
8. **Rendering/CLI:** explicit stable projectors and tests; meaningful text states, safe output/error behavior, unchanged existing defaults.
9. **Documentation:** add `docs/derived-context-contract.md` (durable v1 schema/semantics); update architecture/current-state/README/docs map *only after verified implementation*; keep original PRD and historical reports accurate.
10. **Verify and report:** focused and full offline checks, diff check, independently inspect status, log known limits/deviations and create `docs/implementation-reports/phase-9-implementation-report.md`.

## 11. Deliverables and documentation staleness sweep

Expected code/tests as above; durable `docs/derived-context-contract.md`; implementation report; adjusted `docs/architecture.md`, root `README.md`, `docs/README.md`, and `docs/current-state.md` only when warranted. Keep phase plans as plans, not retrospective proof. Do not add review findings to normative docs without acceptance and promotion.

Search specifically for stale claims about: phase number, unsupported revalidation, source dependencies, compiled-context schema version, provider-derived candidate coverage, v8 config cap, integrity output v2, canonical-vs-derived authority, model-free behavior, persistence/SQLite being future, optional Context Engine coupling, cross-repository support, and Phase 8 independent acceptance. Record file/path, statement, whether historical or current, and fix/defer decision in the report. Maintain navigation to the new contract and report. Do **not** mechanically rewrite correct historical prose.

## 12. Acceptance criteria / stop conditions

- [ ] A new schema-v1 receipt records an artifact's actual content SHA, repository identity, explicit source paths/revisions and derivation metadata, with version/key/type validation.
- [ ] Manual handoff/summary capture and revalidation work end to end in an offline temporary Git repository; dirty edits, deletes, symlinks and lifecycle changes have correct conservative results.
- [ ] Compiler-generated receipts are first-class without modifying compiled-context JSON v3; all selected inventory/provider origins and config/contract context are addressed, never silently omitted.
- [ ] A chain of derivatives propagates changed/unknown upstream state and rejects cycles or untrusted receipt substitution.
- [ ] Machine-readable statuses and reason codes distinguish definite review from incomplete observation and never equate hash equality with semantic validity.
- [ ] Defaults are read-only/local-first, versioned, deterministic, body-free, bounded and safe across symlinks/paths; no network/database/LLM/Context Engine installation requirement.
- [ ] Phase 0–8 behavior/schema regressions pass; old config versions remain valid; no premature Phase 10/11 features.
- [ ] Focused tests and full `make check` pass (or blockers are explicitly reported), docs reflect *verified* delivery, implementation report lists deviations/limits and outstanding Phase 8 independent re-review.

### Stop and explicitly reconsider design if

- The only way to call provider-backed compiled context fresh is to **ignore** provider dependencies or incomplete coverage.
- Capturing from compiled state changes existing compilation selection/output semantics.
- A seemingly convenient receipt format requires a shared DB, automatic code parsing, implicit content reads outside the root, or a new provider contract.
- Safe artifact observation cannot distinguish actual source bytes from stale HEAD assumptions.
- Tests reveal that a plan-specific checklist misses a more fundamental source/authority/trust or cache invalidation defect. Fix the design, not just the checklist.

## 13. Independent review hotspots

The reviewer should **independently reconstruct the required user journey** and challenge this plan. Focus especially on: completeness of compiled/provider provenance; false fresh results on partial evidence; omitted context/policy dependencies; transitive graph behavior; receipt tampering/version confusion; dirty worktree/TOCTOU; schema evolution; file-size/work-budget DoS; authority escalation of generated text; current-state/architecture documentation staleness. The review must look for unforeseen gaps outside the listed tests and treat plan errors as review findings, not exemptions.

## 14. Phase 10+ deferrals

Phase 10: cross-repository receipts/source identity, inter-repo contract change impact. Phase 11: automated CI/PR policy, waiver/approvals, observability, dashboards, persistence/lifecycle service if justified. Phase 12+: semantic revalidation and automatic repair suggestions, retrieval optimization, model-assisted generation/extraction. Phase 9 should create narrow, reusable typed provenance and status seams for those futures **without implementing them**.
