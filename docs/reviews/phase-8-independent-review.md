# Context Integrity — Phase 8 Independent Technical Review

**Reviewed commit:** [`9f782781d10707cb35a0059a88d1683250c1fc16`](https://github.com/jasonkli21/context-integrity/commit/9f782781d10707cb35a0059a88d1683250c1fc16) — *Implement Phase 8 architectural integrity*
**Repository:** `jasonkli21/context-integrity`
**Review date:** 2026-10-21
**Review basis:** supplied `context-integrity-phase-8-sol-high-review-prompt(1).md`, Phase 8 plan, architecture/PRD, delivered implementation/report, relevant tests, and the external Context Engine schema-v1 graph surface.
**Scope:** immutable implementation commit, not a claim about later `main` state. This is a **read-only review**; neither repository was modified.

## 1. Executive verdict

**Disposition: changes recommended before treating Phase 8 as a broadly reliable architectural-integrity check.** The foundational separation is good: Context Integrity owns explicit policy and violation judgment, Context Engine remains descriptive, and the normalizer strips index-local numeric IDs. The shipped statuses avoid the worst error of calling an absent edge “compliant,” and positive observed violations are not suppressed merely because evidence is incomplete.

However, an **empty/nonmatching source selector can receive `no_violation_observed` with no indication that the intended scope was never observed** (F8-001). This is a meaningful policy-coverage failure, particularly for misspelled paths, renamed packages, symbol-only rules, or incomplete selector migration. The plan itself did not specify a source-matchability requirement. Two additional improvements are warranted before wider reliance: enforce endpoint/coverage coherence at the generic relation-provider boundary (F8-002), and bound or index policy matching rather than scanning the entire graph for every invariant and performing linear symbol-selector membership (F8-003). A stale architecture-doc version statement and missing navigation should also be corrected (F8-004).

**Important verification qualification:** This review inspected the exact GitHub commit, files, tests, and an external Context Engine contract, but **did not execute this repository's pytest, Ruff, `make check`, `git diff --check`, or real `ctx` smoke**. Repository cloning failed due DNS/network restrictions in the local execution container. The author-reported **108 focused / 958 total tests** and real-binary smoke are recorded in the Phase 8 implementation report, **not independently verified here**. Accordingly, the verdict is a static-review assessment, not a runtime acceptance certificate.

### Finding summary

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| F8-001 | **HIGH** | No matched source entity can be reported as `no_violation_observed` | Fix before relying on absence/status interpretation |
| F8-002 | **MEDIUM** | Generic relation-batch validation does not establish resolved-target coverage coherence | Tighten contract or explicitly model non-covered endpoints |
| F8-003 | **MEDIUM** | Invariant evaluation can do unbounded `invariants × relations × selector-values` work | Index once and/or impose sane budgets |
| F8-004 | **LOW** | Architecture doc still states integrity JSON v1; document map omits new contract | Documentation cleanup |

No other **confirmed** blocking defect was found from static inspection. Absence of further findings is not proof that all behavior is correct.

## 2. Exactly what was inspected or executed

### Independently inspected via connected GitHub

- Fetched commit metadata and unified diff for `9f782781…` and enumerated its **23 changed paths**, covering configuration/domain models, separate relation protocol, Context Engine graph adapter, CLI, evaluation, rendering, new tests/fixtures, and docs.
- Fetched the **full file tree at the reviewed commit**, and read `AGENTS.md`, `docs/current-state.md`, the Phase 8 plan/report, `docs/architecture.md`, `docs/prd.md`, `docs/evidence-contract.md`, `docs/architecture-integrity-contract.md`, and relevant Phase 7 fix evidence.
- Inspected implementations: `configuration.py`, `models.py`, `relations.py`, `graph_adapter.py`, `context_engine.py`, `evidence.py`, `integrity.py`, `rendering.py`, `cli.py`, `claims.py`, `inventory.py`, relevant safe acquisition, and relevant tests in `test_architecture.py`, `test_graph_adapter.py`, `test_configuration.py`, `test_integrity.py`.
- Inspected Context Engine `src/output_graph.rs`, `src/relations.rs`, `src/graph.rs`, and `src/language/relations.rs` at the Phase 8 plan's referenced Context Engine commit `ef44712858f02b34f1fd4b43201ad6f26bbc3cf2`. Confirmed the current default-branch `src/output_graph.rs` blob is **identical** to the referenced blob (`9e267145cc900e34b84fa3335744b8c0861768d1`). The published schema-v1 DTO has `schema_version=1`, `command="graph"`, `data.root/git/entities/relations/files/relation_files/summary`, resolved/unresolved targets, nullable evidence spans, per-file statuses, and index-local IDs.
- Traced source→relation generation in Context Engine: graph construction uses lexical containment for source ownership, emits `imports` as unresolved targets, and permits exact same-file qualified resolution for references. These are appropriately treated as best-effort rather than compiler truth.
- Reasoned through the 20 adversarial cases in the supplied review prompt against the checked code and test assertions. The matrix in §8 distinguishes covered logic from missing proof.

### Attempted but not executed

- Attempted to clone `https://github.com/jasonkli21/context-integrity.git` and check out `9f782781…` for local verification. `git clone` failed: **`Could not resolve host: github.com`**.
- Consequently **no local checkout existed** in which to run `git status`, `git rev-parse HEAD`, `git show`, actual Python tests, `make check`, Ruff, or `git diff --check`. The commit SHA was verified through the connected GitHub API, not local Git.
- No installed `ctx` executable or Rust test invocation was exercised in this review.

### Reported by the implementer, not independently verified

`docs/implementation-reports/phase-8-implementation-report.md:107–149` reports `108 passed` focused, `958 passed` full `make check`, Ruff success, diff whitespace checks, and two-real-finding clean/dirty Context Engine binary smoke tests. These claims are useful provenance, **not substitutes for executing the tests**.

## 3. Findings (ordered by severity)

### F8-001 — HIGH — A rule whose source scope never appears can look successfully observed

**Evidence**

- `src/context_integrity/integrity.py:390–421`: `evaluate_architecture` walks only `batch.relations` to create match groups. It never checks whether **any observed file/symbol entity** matches the invariant's source selector independent of a prohibited relation.
- `src/context_integrity/integrity.py:466–487`: when no group exists and `coverage.summary.incomplete` is false, the status is unconditionally `ArchitectureStatus.NO_VIOLATION_OBSERVED`.
- `src/context_integrity/graph_adapter.py:68–108, 239–276`: the full graph entity table is used for decoding but not retained in `EvidenceRelationBatch`; only relations and coverage-file states cross the domain boundary.
- `src/context_integrity/relations.py:325–347`: the batch exposes `relations`, coverage, and state, but not a symbol/file entity inventory adequate to assess all source selectors.
- `tests/test_architecture.py:246–258` checks no matching **prohibited target** while the source is present in the fixture; it does not check the source selector matching **zero observed entities**. The supplied review prompt explicitly requests this case (#11).

**Concrete adversarial scenario**

Configure a `forbid_relation` rule selecting `source_path_prefixes = ["src/application/"]`, then run it against a fully reported, clean graph containing only `src/app/`, `src/storage/`, and no matching source path. If the graph has no unresolved/unsupported/file failures, the implementation produces `no_violation_observed` even if the selector became empty due to a typo/rename. Likewise, a `source_symbols` selector naming no observed symbol is not distinguishable from an intentionally empty policy scope.

**Why it matters**

`no_violation_observed` is carefully weaker than “compliant,” but it is still the most reassuring available evaluated state. A consumer/agent cannot tell whether a policy truly covered an intended module or checked nothing. This is a **policy applicability gap**, not a request for the provider to prove the absence of arbitrary dependencies. It is particularly dangerous in a product intended to protect architectural boundaries over code revisions.

**Concrete fix direction**

1. Preserve deterministic, body-free normalized **file and symbol entity identities** (or equivalent source-selector applicability evidence) from the graph, separate from observed relations; validate/sort/deduplicate them in the generic relation boundary. Make sure entity presence is not inferred from relations alone.
2. For each invariant, compute a source-selection count/applicability result. Where no source entity matches, produce an explicitly **`inconclusive`** result plus `source_selector_unmatched` caveat (or a separate well-documented status); do not return an unqualified `no_violation_observed`.
3. If vacuous policies are intentionally supported, add an **explicit** opt-in and document the semantic distinction. Do not silently impose a rule requiring a prohibited edge merely for scope to count as matched.
4. Do not use an observed source *relation* as proof that all intended source symbols/files were indexed. Verify against the provider entity/file inventory and coverage, including unavailable symbol analysis.
5. Keep positive `violated` outcomes authoritative as observations even when some sources or file statuses are incomplete.

**Verification needed**

- Fully clean synthetic graph with zero source matches → `inconclusive`/unmatched caveat.
- Source file present but no relations → `no_violation_observed` **only if source applicability and relevant coverage are established**.
- `source_symbols` not found while files exist → unmatched caveat.
- Prefix renamed, misspelled, or boundary-sibling case → expected applicability behavior.
- Positive violating relation plus unrelated incomplete file still → `violated`.
- Stable JSON/text/golden state and precise caveats, including a replacement-provider fixture.

**Plan-gap classification:** **Yes.** The Phase 8 plan `§13.1` specifies result states based on matched violations and material incompleteness but does not require evidence that the rule's source scope exists. The suggested provider batch design omits the entity inventory needed to answer the question. A review limited to plan conformance would miss this issue.

### F8-002 — MEDIUM — Generic relation evidence admits resolved targets absent from coverage

**Evidence**

- `src/context_integrity/relations.py:131–159`: `EvidenceRelationTarget(entity=EvidenceEntity(...))` can describe any otherwise valid repository-relative entity.
- `src/context_integrity/relations.py:325–347`: batch validation ensures **source** paths are in `coverage.files` and checks unresolved-source counts, but does not check that a **resolved target** entity's path belongs to the provider's file inventory/coverage.
- `src/context_integrity/graph_adapter.py:98–109, 145–195` provides a stronger **Context Engine-specific** guarantee: all decoded entities belong to declared file entities, and the declared graph files match those entities. That protection is not carried into the replaceable normalized batch contract.

**Concrete adversarial scenario**

A replacement relation provider returns a batch with `coverage.files=("src/app.py", analyzed)`, a resolved relation `src/app.py -> src/nonexistent_storage.py`, and `coverage.summary.incomplete=False`. The generic `EvidenceRelationBatch` validation accepts this (assuming valid IDs/types/order), allowing an unaccounted-for target to appear as an observed resolved endpoint. The current Context Engine adapter would reject a comparable malformed raw graph, but the advertised provider-agnostic boundary is less strict.

**Why it matters**

Phase 8 deliberately permits replacement providers; model-level coherence should not depend on Context Engine's private validation choices. For future providers, a resolved endpoint without an accompanying file observation might be real external graph evidence, or it might be a malformed/phantom target. The public model currently does not distinguish those interpretations.

**Concrete fix direction**

- Decide and document whether `coverage.files` means **all indexed file entities** or only **files analyzed for relations**. Under an exhaustive indexed-file contract, reject resolved targets whose path is absent. If external/unindexed endpoints are legitimate, model them explicitly with a dedicated state and mark coverage/derivation as incomplete rather than treating them as ordinary resolved in-repository entities.
- Apply coherence at the generic batch/model boundary, not only inside `graph_adapter.py`. Preserve the Phase 7 context-provider protocol independently.

**Verification needed**

- Construct direct `EvidenceRelationBatch` with a resolved target outside the declared file set and assert the chosen explicit behavior.
- Retain valid Context Engine graph fixtures with cross-file targets and symbol targets.
- Ensure replacement-provider tests are independently constructed rather than copying Context Engine normalizer output.

**Plan-gap classification:** **Yes/partial.** The plan emphasizes generic typed evidence and no index-local IDs but does not fully define whether relation coverage includes a resolved target's file identity. This is an underspecified extensibility contract, not a demonstrated raw Context Engine decoder failure.

### F8-003 — MEDIUM — Policy evaluation lacks a bounded scalable matching strategy

**Evidence**

- `src/context_integrity/integrity.py:405–423`: each configured invariant loops over **every normalized relation**.
- `src/context_integrity/integrity.py:377–387`: membership is direct tuple membership for exact paths/symbols/names; prefix matching loops over each configured prefix.
- `src/context_integrity/models.py:497–533`: selector families permit up to **1,024 values each**, but no repository-level maximum number of invariants or total compiled matcher budget is apparent.
- Graph acquisition is capped at 64 MiB stdout (`context_engine.py:29–30`), and Context Engine's graph may contain a substantial number of relations; that cap is not an evaluation CPU budget.

**Why it matters**

The resulting worst-case work is proportional to `number_of_invariants × relations × selector_values`, with many Python-level comparisons and repeated scans. Even within the finite configuration/file and graph-output limits, an adversarial or accidental large policy can force substantial CPU use after the bounded subprocess returns. This is an avoidable scalability and robustness problem for a repository scanning tool.

**Concrete fix direction**

- Precompile selector exact families into `frozenset`s and normalized boundary-safe directory prefix matchers once.
- Index or partition relations at least by kind and (where useful) source path/symbol, or otherwise bound the number of invariant-relation comparisons. Keep observed-edge grouping and result order deterministic.
- Introduce a measured, documented maximum invariant count or total matching budget if indexing alone does not make worst-case work practical. Preserve a clear configuration/provider error rather than silently dropping checks.

**Verification needed**

- A synthetic performance test with many nonmatching invariants and many relations; compare against a fixed wall-clock/resource envelope on supported CI hardware (avoid brittle microsecond thresholds).
- Deterministic output parity with shuffled relations and selectors.
- Tests that a limit failure is explicit, never partially reported as success.

**Plan-gap classification:** **Partial.** The plan calls for deterministic normalization and bounded acquisition, but does not budget the full invariant × graph matching workload. This finding is about code scalability, not an unmeasured assertion that ordinary small repositories are already slow.

### F8-004 — LOW — Documentation contains a current-version contradiction and navigation omission

**Evidence**

- `docs/architecture.md:1139` still says **“Integrity JSON v1 is separate from existing public projections.”** The section describes Phase 4, but its present-tense sentence is unqualified, while the delivered architecture boundary at `docs/architecture.md:1840–1845`, README, and code clearly state integrity JSON **v2**.
- `docs/README.md:43–48` describes the EvidenceProvider document but does not add the new `architecture-integrity-contract.md` under its document map, despite its role as the durable Phase 8 specification.

**Why it matters**

Agents using selective context loading may encounter the older version claim or miss the new authoritative contract. This is a small but concrete context-integrity failure within a project designed to prevent documentation drift.

**Concrete fix direction**

- Reword the Phase 4 section as **historical** (“Phase 4 originally introduced integrity JSON v1; Phase 8 advances this surface to v2”) and link to the Phase 8 architecture boundary.
- Add `architecture-integrity-contract.md` with a one-paragraph description in `docs/README.md`.
- Add this review to `docs/reviews/README.md` when merged, then update `docs/current-state.md` only **after** fixes and verification.

**Verification needed**

- Search current/nonhistorical docs for contradictory integrity schema or config-version statements. Leave historical plans and reports untouched unless their historical roles are unclear.

## 4. Architecture and plan assessment

### Boundaries that appear correctly preserved

- **Normative/descriptive split:** configuration and `integrity.py` choose selectors, match edges, and issue HIGH findings; `graph_adapter.py` normalizes syntax facts and does not decide architecture policy. No direct imports of Rust internals or shared Context Engine database are visible.
- **Config strictness:** `parse_config` permits `architecture_invariants` only for v8; unknown TOML keys fail; direct `RepositoryConfig` construction enforces v8 requirements, typed policies, invariant uniqueness, claim existence, and required claim type/predicate. Selectors reject unsafe repository paths, prefix ambiguity, duplicates, and unsupported relation kinds.
- **Phase 7 compatibility:** `RelationEvidenceProvider` is a separate protocol; `EvidenceProvider.context_candidates` is not expanded into a mega-interface. Context-engine `relations()` and `context_candidates()` use their own request/state contracts and the shared bounded subprocess helper.
- **External DTO mapping:** the referenced and current Context Engine output code supports the decoded envelope, entity IDs, relation kinds, target state, resolution, derivations, and file/summary counters. The adapter rejects duplicate/dangling IDs, root and known HEAD/dirty mismatches, invalid paths/ranges, inconsistent counts, and unknown status vocabulary. Provider numeric IDs disappear before stable domain output.
- **Selectors:** paths are exact, prefixes are literal slash-terminated starts-with, source/relation-kind/target are ANDed; families within one side are ORed. Unresolved target names are matched only against `target_names`, never invented paths.
- **Positive findings and identity:** one observed prohibited edge yields a HIGH finding; syntax occurrences of an equivalent edge group with their ranges; entity descriptors (not provider IDs) distinguish source/target locations. IDs use a stable hash of invariant/claim/rule and semantic relation identity, independent of prose, absolute roots, and provider iteration order. Definition-range movement is an acknowledged limitation.
- **Claim separation:** explicit claim linkage is validated, `ClaimValidity.UNVERIFIED` is not modified, and missing claim source dependencies warn without suppressing the configured invariant. Phase 4 findings compose with architecture findings rather than being replaced.
- **Outputs:** integrity JSON v2 has explicit projectors; observed coverage/provider/snapshot/claim/policy/relations are structured; no raw stderr, source body, absolute root, timestamp, or numeric graph ID is intentionally projected. The status labels explicitly avoid certification language.
- **CLI/error strategy:** v8 without a provider yields `not_evaluated` with a warning, legacy checks still run, findings exit 0, and recognized provider failures exit 7. Executable override is runtime-only.

### Plan gaps, separate from bugs in implementing the plan

1. **Source-selector applicability** (F8-001): the plan assumes a provider graph can support a meaningful no-observed-violation status without asking whether the selected sources were observed.
2. **Generic resolved-endpoint coherence** (F8-002): a replacement-provider batch contract needs an explicit distinction between known indexed endpoints and legitimate out-of-coverage endpoints.
3. **Evaluation-cost budget** (F8-003): process output/deadline limits do not by themselves protect the subsequent Python evaluation.
4. **Coverage precision is intentionally conservative:** global incompleteness can make unrelated rules inconclusive. This errs on the safe side and is not treated as a Phase 8 blocker. For future useful no-violation statuses, add **selector-relevant coverage** with careful tests so an unrelated failed file need not poison all invariants **without** hiding relevant unsupported/unresolved evidence or assuming missing symbols/files are irrelevant.
5. **Policy provenance is not policy truth:** the claim linkage proves a declaration and its dependencies are traceable where present; it does not certify `claim.value`, expected architectural design, or physical resolution. Keep that explicit when adding source-applicability semantics.

## 5. Documentation staleness sweep

| Document | Finding | Action |
| --- | --- | --- |
| `README.md` | Phase 8 section and v2 description present; no major Phase 8 drift found | Keep, update only if fix changes contract |
| `docs/current-state.md` | Accurate delivery-status qualification and known limitations at reviewed commit | Update following independent fixes, not prematurely |
| `docs/architecture.md` | **Unqualified v1 integrity statement** around line 1139 contradicts new v2 contract | F8-004 |
| `docs/evidence-contract.md` | Phase 7 protocol/history and Phase 8 extension generally distinguish roles; historical v7 language is appropriate | No obligatory rewrite |
| `docs/architecture-integrity-contract.md` | Correctly states status limitations and global coverage; update to specify applicability and resolved-endpoint semantics if fixed | F8-001/F8-002 follow-up |
| `docs/README.md` | Missing navigation for new architecture-integrity contract | F8-004 |
| `docs/plans/phase-8-implementation-plan.md` | Historical plan accurately records original intent but omits applicability/endpoint contracts | Preserve as plan evidence; document accepted fix elsewhere |
| `docs/implementation-reports/phase-8-implementation-report.md` | Reports author verification, labels limitations; historical evidence not independent proof | Preserve; make a **new fixes report** after remediation |
| `docs/reviews/README.md` | Does not yet index a Phase 8 review (none existed in the inspected tree) | Link this handoff upon adoption |

No support was found for claiming full dependency/call-graph completeness, compiler certainty, or an architecture-compliance certificate; the present docs appropriately disclaim those abilities.

## 6. Adversarial-case evidence matrix

**Legend:** *Code/test inspected* means assertions/source logic were read through GitHub; **not executed** in this session. *Gap* means an important end-to-end assertion or boundary condition is missing or unclear in the examined tests.

| Review-prompt case | Static assessment / test evidence |
| --- | --- |
| 1. Numeric provider IDs changed | Covered in `test_graph_adapter.py:test_reordering_numeric_id_changes_do_not_change_normalized_state`; identity excludes IDs |
| 2. Relation order reversed | Covered in graph adapter and `test_architecture.py:test_grouping_distinct_edges_and_stability` |
| 3. Two syntax occurrences | Covered by `test_grouping_distinct_edges_and_stability`; both ranges retained under one finding |
| 4. Distinct targets, same short name | Descriptor includes owning path and range; **gap:** explicit two-target fixture warranted |
| 5. Unresolved target name matches | Covered by `test_unresolved_only_explicit_names` |
| 6. Unresolved name cannot match target path | Covered by selector/unit and unresolved tests |
| 7. Source prefix sibling collision | Covered by `test_selectors_exact_prefix_symbol_or_and_names` |
| 8. Target prefix sibling collision | Same matcher enforces slash boundary; **gap:** direct target-side integration assertion warranted |
| 9. Relevant file incomplete | Global incomplete => `inconclusive`; tests exercise incomplete flag; **gap:** realistic relevant-file status fixture |
| 10. Unrelated file incomplete | Globally conservative by documented design; **gap:** explicit unrelated-file scenario |
| 11. No matching source entity | **F8-001; gap in status semantics and tests** |
| 12. Missing claim dependency | Covered in `test_violation_and_no_domain_mutation`; warns but evaluates |
| 13. HEAD mismatch | Covered by `test_snapshot_mismatch` and snapshot guard |
| 14. Dirty mismatch | Covered by `test_snapshot_mismatch` and snapshot guard |
| 15. Root mismatch | Covered by `test_snapshot_mismatch` |
| 16. Dangling entity | Covered by `test_invalid_graph_fails_sanitized` |
| 17. Giant/unsafe target name | Bounded domain text and malformed-graph tests; **gap:** explicit oversized name and terminal-control cases |
| 18. Old v7 without provider | v1–v7 config-gating and Phase 4 regressions inspected; **gap:** exact full v7 CLI golden recommended |
| 19. v8 invariant without provider | Covered by `test_no_provider_visible_and_existing_checks` |
| 20. Violation alongside Phase 4 finding | Phase 4 domain composition and architecture/no-provider test inspected; **gap:** explicit same-run architecture-violation-plus-legacy-finding assertion |

The matrix is **not** a claim these tests passed during this review.

## 7. Areas still unverified

- Actual Python/CLI runtime, `pytest`, Ruff, `make check`, package installation, `git diff --check`, and GitHub Actions status for the commit.
- A fresh binary `ctx graph` smoke at the reviewed commit and its correspondence to a specific Context Engine build; the implementation report's smoke used an existing release binary.
- Repository-state races and multi-process/subprocess cleanup under active filesystem mutation.
- Runtime memory/latency at the maximum realistic config and 64 MiB graph output sizes.
- Windows portability (the transport and descriptor-safe source reads are intentionally POSIX-oriented).
- More complete malicious-provider fixtures, especially inconsistent target coverage, huge names, and all entity ordering/collision cases.
- Reproducing the old v1-v2 integrity goldens in a local test runner; static schema migration inspection did not indicate other surfaces were changed.

## 8. Recommended fix order and implementation handoff

**Fix pass 1 — F8-001 (priority).** Design a generic source-entity applicability representation; extend normalization and stable state/result projectors without numeric IDs or bodies. Define status semantics for zero matched sources, add code + tests + golden text/JSON, and revise the architecture-integrity contract. Ensure positive findings are unaffected.

**Fix pass 2 — F8-002.** Specify generic file-coverage/endpoint semantics before coding. Reject structurally inconsistent in-repository resolved targets, or represent intentionally external/noncovered targets explicitly; avoid provider-specific policy branches.

**Fix pass 3 — F8-003.** Precompile reusable matchers and index relations, then apply a documented budget/limit if needed. Add deterministic stress tests. Do not trade safety for a shortcut that silently omits edges.

**Fix pass 4 — F8-004 and acceptance polish.** Correct the historical v1 wording, link the new contract from doc navigation, add this review to the review index, and record a separate Phase 8 review-fixes implementation report. Update current-state only after verification.

### Post-fix verification checklist (run in a clean checkout at the reviewed baseline plus fixes)

```bash
# Document actual status/head (not assumed from the GitHub-connected review).
git status --short
git rev-parse HEAD

# Run focused suites with the existing offline environment.
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 \
  uv run pytest \
  tests/test_architecture.py \
  tests/test_graph_adapter.py \
  tests/test_configuration.py \
  tests/test_evidence.py \
  tests/test_context_engine.py \
  tests/test_integrity.py \
  tests/test_rendering.py \
  tests/test_cli.py \
  -q --tb=short

UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check
git diff --check
```

Also independently run/adapt focused tests for the 20-case matrix; add at minimum the missing source-scope, cross-file target coverage, two same-name targets, target prefix sibling, realistic incomplete-file, oversized-name, mixed Phase 4+8, and large-policy regression cases. If an existing `ctx` binary is readily available, smoke clean and dirty Git fixtures, and record its exact `ctx --version` and provenance; do **not** install it solely for this review.

**Acceptance criteria after fixes:** no ambiguous false-clean unmatched-source result; no silent malformed resolved-target state; budgeted deterministic evaluation; existing Phase 4/7 behavior and strict v1–v8 config compatibility preserved; stable root-free/body-free/ID-free JSON; truthful incompleteness and claim-unverified state; current docs consistent with code. **Fresh verification should make the final accept/reject decision** rather than relying on this static assessment alone.
