# Phase 2 implementation report

**Date:** 2026-10-14  
**Baseline:** `main`, `36d150af6cf67b8bab41c528b4304fa83da51309` (`fix phase 1 review findings`)  
**Original delivery:** `3ae38a6dc1fec72b24a64e3a0ccd8f6c2f7195d5` (`phase 2 implementation`).
Changes were developed in a working tree and subsequently committed at that revision.
**Status:** Implemented; independent review returned five findings, addressed by the
cumulative review-fix change recorded below.

At implementation-session start, `docs/plans/phase-2-implementation-plan.md` was an untracked
normative input; the original delivery commit includes it. The completed plan remains unchanged. Completed Phase 0/1 plans and historical reports were
not rewritten. This report records implementation evidence, not an independent review.

## Implemented behavior

`LifecycleState` contains exactly unknown, draft, active, superseded, historical, expired,
and invalid. Unknown is fallback, not active. Only unknown/active pass the lifecycle gate
for authority; the resolver checks lifecycle before explicit eligibility and policy membership.
State-specific exclusions are `draft_lifecycle`, `superseded_lifecycle`, `historical_lifecycle`,
`expired_lifecycle`, and `invalid_lifecycle`, followed by existing `explicitly_ineligible`
and `not_in_policy`. The five built-in policies and their ordering are unchanged.

The generic internal models are `SourceMetadata` and `RepositoryConfig`; internal source
and manifest fields are `source_metadata` and `repository_config`. No compatibility aliases
remain. Public inventory/authority JSON uses its existing explicit projections unchanged.
New frozen types represent configured edges, resolved edges with final endpoint records and
revisions, lifecycle origins, entries, and overviews.

Config v1 preserves authority-only semantics and rejects lifecycle/supersession keys.
Config v2 permits those fields and all existing authority behavior. Repository policies
identify their defining schema as `config-v1` or `config-v2`. Explicit unknown lifecycle is
rejected. Reasons are required. Lifecycle can combine with authority class/eligibility in
one entry. Executable-truth/historical authority overrides remain reserved. Config is never
rewritten. Lifecycle metadata and supersession cannot target the control-plane config.

Pass 1 retains bounded POSIX reads, raw-byte hashing, source identity/Git status, built-in
classification, authority overrides, and explicit lifecycle overrides. Pass 2 resolves only
observed endpoints, applies valid outgoing-edge lifecycle, rebuilds final records/edges,
checks the config hash again, and counts effective state. Missing endpoints emit warnings;
unresolved edges do not deactivate sources. Explicit superseded metadata remains effective
independently. Missing lifecycle and authority metadata get dimension-specific warnings.

Supersession supports one direct successor, chains, and convergence. Self edges, duplicate
outgoing edges (including exact duplicates), cycles, and conflicting lifecycle declarations
fail config validation before endpoint observation. Validation is iterative, including chains
longer than Python's recursion limit. A valid edge supersedes its source, never activates its
target, and never creates transitive edges. Resolved edges attach final effective endpoint
records, avoiding provisional lifecycle values in chain provenance.

Explicit non-historical lifecycle removes the historical path authority overlay and restores
the kind-derived role unless explicit authority metadata supplies the role. Kind/confidence
and all original rule evidence remain. New rules are `lifecycle.metadata.repository_override`,
`lifecycle.supersession.explicit`, and `authority.lifecycle.restore_kind_role`. Supersession
rule basis includes direct replacement path and reason; lifecycle overview reason retains
the declared reason. Built-in origin/reason comes from classification evidence.

## CLI and JSON

```bash
uv run context-integrity lifecycle list .
uv run context-integrity lifecycle list . --format json --output /tmp/lifecycle.json
uv run context-integrity lifecycle show docs/adr/0008-storage.md .
uv run context-integrity lifecycle show docs/adr/0008-storage.md . --format json --output /tmp/source-lifecycle.json
```

List/show support text/JSON/output files. Show returns one source and direct incoming/outgoing
relations, revision, origin/reason, lifecycle-only eligibility, explicit global eligibility,
and combined active-authority eligibility/exclusion without invoking an authority policy. It retains all scan warnings. Source-not-found exits 2, output failure 4,
configuration failure 6. Scan renders effective lifecycle/counts through existing fields;
explain displays built-in lifecycle, explicit metadata, reason, direct successor, effective
state, and lifecycle eligibility while retaining its policy-resolution limitation.

Lifecycle JSON is separate schema v1 with explicit projection. The full examples are:

- `tests/fixtures/lifecycle-v1-states.json` — six explicit states plus fallback/path origins;
- `tests/fixtures/lifecycle-v1-chain.json` — direct three-ADR chain and final endpoint revisions;
- `tests/fixtures/lifecycle-v1-override-warning.json` — historical override and unresolved edge;
- `tests/fixtures/authority-v1-lifecycle.json` — additional lifecycle-aware authority contract.

An abbreviated source record (not the complete schema):

```json
{
  "path": "docs/adr/a.md",
  "lifecycle": "superseded",
  "lifecycle_origin": "supersession",
  "lifecycle_reason": "Explicit replacement",
  "lifecycle_authority_eligible": false
}
```

Complete records also carry source ID, kind, authority class, raw-byte revision, direct
`superseded_by` edge or null, and direct `supersedes` edges. Each edge carries both endpoint
projections, reason, and config hash. Top-level fields are schema version, repository/Git
identity, config hash, sources, supersession, and warnings. Paths/sources/edges/predecessors
are deterministic; no absolute root, timestamp, or source body is added; JSON ends in newline.

## Verified quality gate and compatibility

Exact command before edits and after implementation:

```bash
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check
```

Baseline: Ruff lint/format and **226 tests passed**. Final: Ruff lint/format and **343 tests
passed**, Python **3.12.13**, pytest **9.1.1**, macOS. Tests require no network, model/API
credentials, or database. No dependencies or lockfile changes.

All three original inventory goldens and all three original authority goldens pass
byte-for-byte and are unmodified. Existing tests changed only for internal model/field
renaming, the expanded lifecycle enum, and schema 2 becoming supported (unsupported-version
regression now uses 3). The config revision race matrix was expanded to both schemas.
There are 117 additional test cases, including the new lifecycle suite and v2 race cases.

Real-checkout smoke checks, with the same offline/cache environment, passed:

```bash
uv run context-integrity lifecycle show docs/architecture.md .
uv run context-integrity lifecycle list . --format json --output /tmp/context-integrity-phase-2-lifecycle.json
```

Architecture remains unknown/fallback with no config, with identity and raw-byte revision
shown. Synthetic CLI tests verify v2 graph/state behavior and exit codes. `git diff --check`
passed. No old golden fixtures were regenerated.

Intermediate test failures were corrected: the exhaustive enum test needed the seven-state
contract, new graph fixtures initially placed generic documents outside candidate directories,
and new goldens needed generation. Candidate selection was preserved; fixtures now use docs/.

## Acceptance mapping

Every checkbox in plan §34–35 is mapped below. Test names without a prefix are in
`tests/test_lifecycle.py` (L). A means `tests/test_authority.py`; C means
`tests/test_configuration.py`; R means `tests/test_rendering.py`; M means
`tests/test_models.py`. Verification is implementation testing/source evidence, not a claim
of independent architectural approval.


### Security (§34)

| Criterion | Evidence |
| --- | --- |
| no `shell=True`; | L: test_no_inference_execution_network_or_shell guards argument-array Git calls and shell flags. |
| no config code execution; | L: test_no_inference_execution_network_or_shell; strict tomllib, no eval or directive execution. |
| no network; | L: test_no_inference_execution_network_or_shell rejects socket creation/connections. |
| lifecycle paths remain normalized repository-relative; | L: test_unsafe_paths; test_normalized_paths_and_deep_graph. |
| supersession paths remain normalized repository-relative; | L: test_unsafe_paths; test_normalized_paths_and_deep_graph. |
| config file cannot lifecycle/supersede itself; | L: test_invalid_v2_config metadata and both endpoint directions. |
| symlink/unsafe config handling remains fail-closed; | C: existing symlink/directory/oversize/unreadable/open-race tests; safe reader unchanged. |
| config revision used for lifecycle matches observed config hash; | C: test_config_revision_consistency v1/v2; L: test_explicit_state_matrix hash assertion. |
| missing endpoint cannot silently deactivate a source; | L: test_missing_endpoints_never_activate_edge; test_unobserved_symlink_endpoint_cannot_deactivate_source. |
| cycle cannot enter runtime graph; | L: test_invalid_v2_config; test_normalized_paths_and_deep_graph long cycle. |
| terminal-controlled reasons/paths are escaped; | L: test_terminal_safety text/JSON/explain. |
| lifecycle JSON includes no source bodies; | L: test_explicit_projection_and_compatibility; new goldens. |
| lifecycle JSON includes no absolute root; | L: test_explicit_projection_and_compatibility; new goldens. |
| no content body parsing is added. | L: test_no_inference_execution_network_or_shell; lifecycle.py uses structured records/config only. |

### Lifecycle Domain

| Criterion | Evidence |
| --- | --- |
| full seven-state lifecycle enum exists. | M: test_enum_contract. |
| unknown remains fallback. | L: test_invalid_v2_config rejects explicit unknown; existing no-config R goldens. |
| unknown and active are authority-eligible. | L: test_authority_lifecycle_matrix, all states with explicit eligibility. |
| draft is authority-ineligible. | L: test_authority_lifecycle_matrix draft cases. |
| superseded is authority-ineligible. | L: test_authority_lifecycle_matrix superseded cases. |
| historical is authority-ineligible. | L: test_authority_lifecycle_matrix historical cases. |
| expired is authority-ineligible. | L: test_authority_lifecycle_matrix expired cases. |
| invalid is authority-ineligible. | L: test_authority_lifecycle_matrix invalid cases. |
| explicit unknown lifecycle metadata is rejected. | L: test_invalid_v2_config unknown case. |

### Configuration

| Criterion | Evidence |
| --- | --- |
| config schema 1 still supported. | L: test_authority_only_schema_compatibility; existing C/A v1 cases. |
| config schema 2 supported. | L: test_authority_only_schema_compatibility; lifecycle/graph matrices. |
| v1 cannot use lifecycle fields. | L: test_v1_rejects_phase_two_keys. |
| v1 cannot define supersession. | L: test_v1_rejects_phase_two_keys. |
| v2 supports lifecycle metadata. | L: test_explicit_state_matrix. |
| v2 supports supersession. | L: test_direction_chains_and_convergence. |
| reason required for lifecycle metadata. | L: test_invalid_v2_config missing/blank metadata reasons. |
| reason required for supersession. | L: test_invalid_v2_config missing/blank edge reasons. |
| lifecycle metadata cannot target config file. | L: test_invalid_v2_config normalized config-path metadata case. |
| supersession cannot involve config file. | L: test_invalid_v2_config both endpoint directions. |
| unsafe paths fail. | L: test_unsafe_paths metadata/source/target; C: existing parser matrix. |
| config revision consistency remains fail-closed. | C: test_config_revision_consistency, five mutations for each schema. |

### Supersession

| Criterion | Evidence |
| --- | --- |
| relation is directional. | L: test_direction_chains_and_convergence. |
| source != target. | L: test_invalid_v2_config self edge. |
| one direct successor per source. | L: test_invalid_v2_config repeated source/exact duplicate. |
| multiple predecessors may share successor. | L: test_direction_chains_and_convergence convergence case. |
| chains allowed. | L: test_direction_chains_and_convergence chain; test_normalized_paths_and_deep_graph. |
| cycles rejected. | L: test_invalid_v2_config; test_normalized_paths_and_deep_graph. |
| valid relation sets source to superseded. | L: test_direction_chains_and_convergence. |
| relation does not mark target active. | L: test_direction_chains_and_convergence asserts targets without outgoing edges unknown. |
| conflicting explicit lifecycle + outgoing relation rejected. | L: test_conflicting_lifecycle all five contradictory states. |
| missing source endpoint warned. | L: test_missing_endpoints_never_activate_edge including both missing. |
| missing target endpoint warned. | L: test_missing_endpoints_never_activate_edge including both missing. |
| unresolved edge alone does not set source superseded. | L: test_missing_endpoints_never_activate_edge with/without independent metadata. |

### Precedence / Heuristics

| Criterion | Evidence |
| --- | --- |
| explicit lifecycle overrides path heuristic. | L: test_historical_override five states, with/without authority override. |
| supersession outranks explicit non-conflicting lifecycle metadata. | L: test_supersession_historical_override_and_metadata_precedence. |
| heuristic historical output unchanged with no config. | L: test_historical_override initial scan; R: original historical golden unchanged. |
| explicit non-historical override restores underlying authority role. | L: test_historical_override; test_edge_alone_restores_historical_authority. |
| explicit authority override remains strongest authority-dimension input. | L: test_historical_override; test_edge_alone_restores_historical_authority. |
| recency never implies lifecycle. | L: test_no_inference_execution_network_or_shell; A: test_equal_tier_and_no_recency. |
| Git dates never imply lifecycle. | L: test_git_dates_and_filename_order_do_not_set_lifecycle; lifecycle resolver has no date input. |
| filenames never imply supersession. | L: test_git_dates_and_filename_order_do_not_set_lifecycle; test_no_inference_execution_network_or_shell. |

### Authority Integration

| Criterion | Evidence |
| --- | --- |
| authority resolver uses lifecycle eligibility helper. | authority.resolve_authority shares active_authority_exclusion_reason with inspection; L: test_authority_lifecycle_matrix. |
| new state-specific exclusion reasons stable. | L: test_authority_lifecycle_matrix pins every state exclusion. |
| equal-tier semantics unchanged. | A: test_equal_tier_and_no_recency; original goldens unchanged. |
| missing-stronger-tier semantics unchanged. | A: test_resolution_policies; test_no_candidates; original goldens unchanged. |
| built-in authority policies unchanged. | A: test_exact_builtin_set unchanged. |
| executable-truth boundary unchanged. | A: existing reserved-class tests; L: test_invalid_v2_config rejects reserved overrides. |
| explicit authority eligibility still works. | L: test_authority_lifecycle_matrix; existing A metadata/eligibility tests. |

### CLI / Output

| Criterion | Evidence |
| --- | --- |
| `lifecycle list` works. | L: test_lifecycle_cli text/JSON list. |
| `lifecycle show` works. | L: test_lifecycle_cli text/JSON show; test_show_unknown_and_scan_explain. |
| text output exposes origin/reason. | L: test_lifecycle_cli; test_terminal_safety; render_lifecycle_text. |
| JSON lifecycle schema version 1 exists. | L: test_lifecycle_goldens; test_explicit_projection_and_compatibility. |
| JSON projection is explicit. | L: test_explicit_projection_and_compatibility adds private overview field and pins public key sets. |
| JSON deterministic. | L: test_lifecycle_goldens reverses source order; repeated scan test. |
| no source body/absolute root. | L: test_explicit_projection_and_compatibility. |
| inventory JSON adds no new keys. | L: test_explicit_projection_and_compatibility; original R goldens unchanged. |
| authority JSON adds no new keys. | L: test_explicit_projection_and_compatibility; original A goldens unchanged. |
| source-not-found exits 2. | L: test_show_unknown_and_scan_explain missing/unsafe paths. |
| config errors exit 6. | L: test_lifecycle_cli_outputs_and_errors; existing A config-exit matrix. |

### Compatibility

| Criterion | Evidence |
| --- | --- |
| Phase 0 no-config inventory goldens byte-identical. | R: original three inventory golden comparisons pass; fixture bytes unchanged. |
| Phase 1 no-config/v1 authority goldens byte-identical. | A: test_authority_golden original three scenarios pass; fixture bytes unchanged. |
| existing rule IDs unchanged. | L: test_historical_override preserves original evidence prefix; existing classification table/goldens pass. |
| existing safe-read protections unchanged. | All existing acquisition/repository/config safety tests pass; acquisition.py/repository.py unchanged. |
| 226-test reviewed baseline passes before edits or discrepancy is explained. | Baseline offline make check: 226 passed at 36d150a before edits. |
| no database added. | Unchanged pyproject.toml/uv.lock; no persistence module/import added. |
| no LLM/model integration. | Unchanged dependencies; deterministic local lifecycle/config/authority operations only. |
| no Codebase Intelligence dependency. | Unchanged evidence.py/dependencies; no engine calls/imports added. |
| no claims. | New models contain sources/config/lifecycle only; no extraction/body parsing added. |
| no contradiction engine. | No semantic evaluator added; output describes explicit source state only. |
| no context compiler. | No compiler/budget/ranking functionality added. |

### Testing / Docs

| Criterion | Evidence |
| --- | --- |
| lifecycle state matrix tested. | L: test_explicit_state_matrix; test_authority_lifecycle_matrix. |
| supersession graph validation tested. | L: test_direction_chains_and_convergence; test_invalid_v2_config; test_conflicting_lifecycle. |
| config v1/v2 compatibility tested. | L: test_authority_only_schema_compatibility; test_v1_rejects_phase_two_keys; C: v1/v2 race matrix. |
| lifecycle goldens pass. | L: test_lifecycle_goldens, three lifecycle plus new authority fixture. |
| full offline `make check` passes. | Exact offline make check: Ruff lint/format, 343 tests passed. |
| README updated. | README status/lifecycle commands/states/config/relations/JSON/limits updated. |
| Phase 2 implementation report maps acceptance criteria. | This report maps each plan §34 and §35 checkbox. |
| current-state updated only after verification. | docs/current-state.md edited after verified 343-test offline gate. |

## Decisions, deviations, and remaining limitations

No phase-scope deviations or unresolved implementation acceptance criteria. The recommended
internal renames were applied to both types and attached fields. JSON projections were not
renamed. `show --output` is included. List and show share lifecycle schema v1; show filters
to the requested source and direct edges while retaining repository scan warnings.

A lifecycle entry holds effective state through its attached SourceRecord rather than
storing a duplicate state field. Supersession provenance uses the direct path and reason in
classification evidence; overview/edge output also retains the separate declared reason.
The existing safe config reader and final hash check serve every config dimension.

Only observed inventory endpoints activate edges. Existing inventory candidate selection
is unchanged: config cannot pull arbitrary code/noncandidate files into the inventory.
Symlink endpoints skipped by acquisition are unresolved; oversized/unreadable sources that
retain inventory records retain their existing null-revision warnings. Config itself must
be safely readable and consistent. Scans remain sequential observations, not atomic snapshots;
transient changes that leave identical bytes between reads cannot all be detected. POSIX
safe-open support remains the platform boundary.

The independent Phase 0–2/Phase 2 review is retained under `docs/reviews/`.
This implementation report records fixes and testing, not independent approval of those fixes.
Final independent verification of the corrections remains the next review step.

## Deferred / key Phase 3 inputs

Phase 3 claims/provenance remains unimplemented. Use stable SourceId plus raw-byte
SourceRevision, config hash, and per-dimension lifecycle evidence as dependencies. Keep
claim validity distinct from source lifecycle: an active source can contain stale claims.
Authority policies still express observed source-role preference, never semantic correctness
or agreement. Preserve explicit edge provenance; do not infer transitive or recency edges.

Claim extraction, semantic contradiction/drift, clock-based expiry, mutation/auto-fix,
persistence, LLMs/embeddings, context contracts/compiler, cross-repository lifecycle,
Codebase Intelligence integration, and API/MCP/daemon work remain deferred.


## Cumulative independent review fixes (2026-10-14)

Review: [Phase 2 independent review and collective Phase 0–2 audit](../reviews/phase-2-independent-review.md),
reviewed original delivery `3ae38a6dc1fec72b24a64e3a0ccd8f6c2f7195d5`, outcome
**PASS WITH FINDINGS** (one P1 and four P2). Finding IDs here belong to that review.

- **F-001:** Shared pure `active_authority_exclusion_reason` applies lifecycle first, then
  explicit global ineligibility. Lifecycle text/JSON exposes the lifecycle gate, nullable
  explicit eligibility, combined eligibility, and nullable exclusion reason. Policy membership
  is not consulted. Five CLI scenarios verify JSON/text and agreement with authority resolve.
  Only the three new lifecycle JSON v1 goldens gain the three eligibility fields; original
  inventory/authority schema keys and golden files are unchanged.
- **F-002:** Original delivery provenance now names the committed Phase 2 tree and preserves
  the original implementation-session chronology.
- **F-003:** Repository discovery neutralizes inherited ceiling/cross-filesystem controls;
  remote identity uses repository-local config. Synthetic tests cover external global/system/
  command origin scopes, same-path source-ID separation, Git ignores, and real local origins.
- **F-004:** Phase 0/1 reports name the actual delivery and review-fix commits from Git history.
- **F-005:** Retained the supplied independent review and recovered the original Phase 0/1
  independent review artifacts from Downloads, verifying their reviewed commits against Git
  history. All three original review records are preserved; no historical prose was invented.

All five findings have implementation/evidence corrections; final independent verification
of these corrections remains separate from this implementation session.

**Review-fix commit:** the single commit titled `fix phases 0-2 independent review findings`
containing this section, based directly on original Phase 2 delivery `3ae38a6d`.
Resolve its exact SHA with:

```bash
git log -1 --format=%H --fixed-strings --grep='fix phases 0-2 independent review findings'
```

The commit is identified by its containing change rather than embedding its own hash
(which would change that hash). The final delivery message records the created SHA.


### Post-fix verification

```bash
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check
```

Passed Ruff lint, Ruff format (50 files), and **353 tests** on Python **3.12.13**,
pytest **9.1.1**, macOS. The reviewed Phase 2 delivery recorded 343 tests; this correction
adds ten regression cases. Targeted repository/acquisition tests passed (57), followed by
lifecycle/authority/configuration tests (218). The full gate includes the strengthened
local-origin checks under all three external config scopes. The five new CLI scenarios
exercise text/JSON inspection and authority resolve end to end.

`git diff --check` and the staged equivalent passed. All original Phase 0 inventory and
Phase 1 authority goldens remain unmodified and pass byte-for-byte. Only lifecycle v1
source entries gain `explicit_authority_eligible`, `active_authority_eligible`, and
`active_authority_exclusion_reason`. This satisfies Phase 2 §21.2 and the first two global
authority gates; discovery/identity regressions restore the Phase 0 identity/ignore contract.
No dependencies, architecture decisions, completed plans, or Phase 3 scope were changed.
