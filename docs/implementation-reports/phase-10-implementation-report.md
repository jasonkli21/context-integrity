# Phase 10 implementation evidence

Date: 2026-10-21 Pacific. Implementation evidence, **not independent acceptance**.
Baseline: `main` at `61ca15782dadff319c6d4ed2422d1d6e82fffd2a`, exactly matching the
supplied prompt. Delivery remains on `main`, in one commit containing this report. The final
commit ID is reported by the implementation session; a commit cannot embed its own hash.
No subagents were used. No dependencies or lockfile changes were needed.

The only initial worktree entry was the supplied untracked Phase 10 plan. It is included;
Markdown double-space hard breaks were normalized to equivalent backslashes for whitespace
validation. Its requirements and historical/proposed role were preserved. The external
implementation prompt was read as task input, not added as a duplicate instruction source.

## Reconciliation and requirement map

Current-state identified Phase 9 fixes verified but fresh independent re-review pending.
The explicit Phase 10 request supplies the new phase scope. The plan, existing acquisition,
repository identity, inventory/config, claims/lifecycle, contracts/compiler, derived receipt,
rendering/CLI and tests were inspected against architecture, PRD and the durable evidence,
architecture-integrity and derived contracts. No accepted ADR conflicts or required migrations
were found. No separate Context Engine interface is necessary for this offline workspace
surface; existing repository-scoped evidence is not represented as cross-repo graph coverage.

| Requirement | Implemented seam |
| --- | --- |
| Strict workspace v1, roots and observed identity binding | `workspace_models.py`, `workspace_config.py`, `workspace.py::resolve_workspace` |
| Strict consumer acceptance receipt, exact producer binding | `ContractLock`, `parse_lock`, `Workspace.check` |
| Explicit contract pin / file mirror / claim alignment | bounded `Workspace.observe` / `claim`, pure `compare_sources` / `compare_claims` |
| Independent per-target contracts, budgets, policy and decisions | `Workspace.compile`, existing `resolve_contract` / `compile_context` |
| Root-free namespaced check/context v1 and digest-only task | allowlist projectors in `workspace_output.py` |
| Additive CLI, ordinary findings exit zero, safe exclusive output | `workspace` Typer sub-app; `publish_workspace`, existing `write_outputs` |
| No false equality from unsafe/unstable/budget-limited inputs | descriptor traversal, opt-in stable reads, shared inventory accounting and qualified invocation-local caches |
| Exact lifecycle, limitations, examples and navigation | workspace contract, four small golden declarations/results, README/architecture/current-state |

## Delivered journeys and contracts

1. Declare 2–8 local independent roots with observed repository IDs. Reject identity mismatch,
   aliases/ID duplication, unexpected discovery boundaries, nested/duplicate roots, same-origin
   checkout collisions and unsafe paths. No-origin identity is visibly location dependent.
2. Observe producer bytes against a consumer-owned strict lock, retaining producer/lock/accepted
   hashes. Staged and unstaged edits under unchanged HEAD produce change-impact review signals.
   Locks are never updated. Missing and unobservable inputs retain different outcomes.
3. Compare explicit mirrors without conflating equal relative paths in different repositories.
   Byte divergence indicates review, without assigning a semantic winner.
4. Pair existing explicit claims with scoped IDs, exact type/subject/predicate/scope/value,
   full provenance/dependency revisions and original declaration metadata. Ineligible lifecycle,
   changed/unknown dependencies and inventory gaps prevent positive agreement. Validity remains
   `unverified`; no claim extraction, truth determination or generic contradiction engine exists.
5. Compile independent configured context targets, including an incomplete target beside a
   complete one, with separate budgets, policy, selected identities/revisions, full decisions,
   dependencies and warnings. Review signals and selection completeness remain independent.

```bash
uv run context-integrity workspace check workspace.context-integrity.toml --format json
uv run context-integrity workspace compile workspace.context-integrity.toml \
  --task "Update API consumer" --format json --output workspace-context.json
```

Workspace TOML uses `workspace_schema_version=1`; consumer JSON uses
`contract_lock_schema_version=1`; reports use `workspace_check_schema_version=1` and
`workspace_context_schema_version=1`. Separate schemas preserve config v1–v8, compiled JSON v3,
integrity JSON v2 and Phase 9 receipt/result v1. Workspace context contains task SHA256, never
an embedded compiled-v3 task/source body. Text prepends a summary to the same escaped complete
structured evidence. Strict grammar, status matrices, bounds and valid examples are in
[`../workspace-integrity-contract.md`](../workspace-integrity-contract.md).

## Choices, deviations and limitations

- The plan allowed final grammar design; actual grammar follows its illustrative keys. Frozen
  typed declarations/references/results isolate workspace state from single-repo models. No
  repository config version or existing projection was advanced.
- Existing config **cannot set its own lifecycle**. Existing `unknown | active` lifecycle
  eligibility is reused; explicit noneligible provenance/dependencies make claims inconclusive.
  Requiring explicit active config would have made all valid claims permanently incomparable.
- Existing claim dependencies record current revisions, not accepted historical pins. Dirty,
  untracked, staged, unknown-status or generated dependencies are uncertain; clean dependencies
  retain `dependency_history_not_pinned`. No prior committed freshness, transitive receipt
  revalidation or semantic validity is inferred. All inventory warnings conservatively prevent
  positive claim agreement, even when a gap may be unrelated.
- Observable malformed locks and producer-binding mismatch are input errors (6); unavailable
  locks are findings. Missing producer/consumer/mirror inputs indicate review. Missing claims
  are uncertainty. Definite missing input/mismatch dominates independent uncertainty while
  retaining both observations. Empty check sets are inconclusive.
- Outputs are restricted to new paths **outside all participating roots**, a conservative
  implementation of the plan's inventory-safety requirement. Root/manifest/source/output
  symlink traversal is rejected. Canonical host paths are required; symlink aliases such as
  macOS `/tmp` are intentionally refused. Output parent directories are never created.
- Explicit hashing and inventories each have an independent shared 64 MiB / 4,096 work budget;
  failed/skipped reads reserve allowance. Inventory accounting was made reusable so refused
  sources cannot disappear from the next repository's budget. Configuration consistency and
  Git enumeration retain existing separate bounds; compiler feasibility has existing semantics.
- Optional stable reads compare post-read inode/device/size/mtime/ctime and named identity;
  no extra full-file compile reads are needed. Root-ancestor no-follow hardening also applies to
  existing acquisition callers. Observations remain sequential, without end-of-command identity
  revalidation or an atomic cross-root snapshot. Publication reuses exclusive mode-0600
  prepare/fsync/link/rollback; process loss can leave orphaned temporary/output files.
- Provider support is deliberately disabled. Required code-provider context remains visibly
  incomplete; no provider executable, installation, network, SQLite, model or shared graph ID
  namespace is needed. No global authority/budget allocation or Phase 11 CI gate was added.
- Consumer locks are editable unauthenticated acceptance declarations. They do not establish
  implementation use or API compatibility. Context indexes are rebuildable observations, not
  durable cross-repo Phase 9 receipts. Semantic compatibility, structural cross-repo graphs,
  checkout-instance IDs and generated-artifact receipt DAGs remain deferred.

## Requirements-to-tests matrix

Tests use small real independent Git repositories, explicit configs and actual bytes; mocks
are limited to deterministic budget/race/publication failure injection.

| Acceptance scenario | Evidence in `tests/test_workspace.py` / `tests/test_workspace_cli.py` |
| --- | --- |
| Matching pin; dirty staged/unstaged edits, HEAD unchanged, reversion | `three_checks_qualified_provenance_and_determinism`, `dirty_contract_content_unchanged_head` |
| Same path/claim ID in different repos, scoped cache | `three_checks_qualified_provenance_and_determinism`, `observation_budget_and_repo_qualified_cache` |
| Wrong/missing ID, duplicate origin/root, nested/subdirectory/root symlink | `strict_manifest`, `repository_binding_and_boundaries` |
| Equal/different declarations, subject/scope and inactive/missing/changed provenance | `claim_comparability_and_coverage`, `mismatch_and_independent_uncertainty_retained` |
| Missing, directory, symlink leaf/parent, unreadable and oversized file | `file_acquisition_failures`, `unreadable_source_is_not_alignment` |
| Malformed/duplicate/unknown lock; forged producer binding; missing producer cannot hide bad lock | `invalid_lock_bytes`, `strict_lock_shape`, `wrong_lock_binding_is_input_failure`, `invalid_lock_never_masked_by_missing_producer` |
| TOML types, unknown fields, version/cardinality/budget/path/alias errors | `strict_manifest`, `manifest_model_bounds_and_bad_primitives`, `typed_qualified_refs_validate` |
| Unstable read and replaced root ancestor | `unstable_file_read_is_not_alignment`, `inventory_ancestor_symlink_is_refused` |
| Byte/attempt/inventory exhaustion and skipped-read accounting | `observation_budget_and_repo_qualified_cache`, `observation_attempt_budget`, `inventory_budget_incomplete_target`, `shared_inventory_accounts_skipped_reads` |
| Independent budgets, incomplete target, separate authority policy | `composite_independent_budgets_body_free`, `independent_configured_authority_policies` |
| No provider binary/service, provider-required contract incomplete | `default_offline_with_no_provider_binary`, `provider_requirements_remain_incomplete_offline` |
| No checks, sibling `..` roots, local identity, reversed declaration order | `zero_checks_no_global_compliance`, `sibling_roots_and_local_identity`, `declaration_order_only_changes_manifest_digest` |
| Definite review with independent uncertainty retained | `missing_plus_unobservable_preserves_both_reasons`, `mismatch_and_independent_uncertainty_retained` |
| Strict body-free/digest-only JSON, golden schemas and text parity | `workspace_schema_goldens`, `composite_independent_budgets_body_free`, `cli_text_json_parity_and_no_writes` |
| Usage/repository/input/output exits; no overwrite or implicit writes | `usage_errors`, `sanitized_errors`, `exclusive_output_and_no_inventory_side_effect`, `unsafe_output_paths`, `output_failure_is_sanitized` |
| Legacy config v1–v8 and output versions | `config_versions_remain_local_and_supported`, `existing_compile_v3_keeps_task_and_other_versions`, full pre-existing suite |

## Verification

Final verification results are recorded below after the final gate. Earlier development gate:
1,163 tests passed, then shared inventory accounting and final projection provenance were
hardened and additional tests added. A formatting gate caught the fixture regeneration Python
fence; Ruff formatting fixed it before the final rerun. These intermediate results are not
substituted for final verification.

- `UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check`: **passed**;
  Ruff lint, formatting (102 files at the gate), **1,167 tests passed in 187.99s**.
- `UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 uv run pytest -q tests/test_workspace.py tests/test_workspace_cli.py`:
  **96 passed in 68.37s** after the final provenance projection changes.
- `UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 uv run ruff format --check .`:
  passed after the documentation/report additions (103 files at that check).
- `git diff --check` and `git diff --cached --check`: passed. Staged inventory contains
  exactly the 21 files listed below, including the supplied plan; no unrelated changes.
- Workspace CLI help smoke check passed. Platform: macOS/Darwin, Python 3.12.13,
  pytest 9.1.1. No tests skipped, network/model/provider/database dependency, or verification blocker.

Final current-state updates contain only the verified delivery/navigation and pending-review
status. Source/tests/golden payloads were not changed after the final passing gates.

## Complete changed-file inventory

- `src/context_integrity/workspace_models.py`: typed workspace declarations, identities, observations and findings.
- `src/context_integrity/workspace_config.py`: strict TOML/JSON parsing and safe manifest/root validation.
- `src/context_integrity/workspace.py`: binding, bounded observations, explicit checks and local composition.
- `src/context_integrity/workspace_output.py`: allowlist schemas, digest-only context, text and safe publication.
- `src/context_integrity/acquisition.py`: all-ancestor no-follow traversal; optional stable reads.
- `src/context_integrity/inventory.py`: optional stable reads and reusable shared observation budget.
- `src/context_integrity/cli.py`: additive `workspace check` / `workspace compile`, safe diagnostics/exits.
- `tests/test_workspace.py`, `tests/test_workspace_cli.py`: domain, adversarial and CLI integration evidence.
- `tests/fixtures/workspace-v1.toml`, `tests/fixtures/contract-lock-v1.json`: complete strict declarations.
- `tests/fixtures/workspace-check-v1.json`, `tests/fixtures/workspace-context-v1.json`: deterministic schema goldens.
- `tests/fixtures/workspace-fixtures.md`: fixture purpose and reproducible generation.
- `docs/workspace-integrity-contract.md`: exact implemented grammar, semantics, examples, bounds and trust limitations.
- `docs/implementation-reports/phase-10-implementation-report.md`: this evidence and reviewer handoff.
- `docs/plans/phase-10-implementation-plan.md`: supplied normative planning input, retained without requirement changes.
- `README.md`, `docs/README.md`: delivered feature/command navigation.
- `docs/architecture.md`: durable workspace ownership, schema/receipt boundaries and resolved format deferral.
- `docs/current-state.md`: verified current phase/navigation and preserved review gaps.

## Documentation staleness and independent review handoff

README's phase-plan navigation still named Phase 9: updated to Phase 10. Architecture's exact
workspace-format deferral and next-step text were stale: updated narrowly with a durable Phase 10
boundary and contract link. Docs navigation gained the workspace contract. PRD remains long-term
intent and was not rewritten. Historical Phase 9 plans/reviews/reports were not rewritten.

Independent Phase 10 review should compare this commit's code/tests and all four fixtures against
the supplied Phase 10 plan, architecture and three predecessor contracts, concentrating on false
alignment, qualified identity, skipped/read budgets, source/output races, claim freshness limits,
compiler policy/privacy and exit compatibility. This session implements and tests; it does not
self-certify independent architectural acceptance. No independent reviewer was spawned, as
requested. Phase 9 fresh independent re-review, Phase 8 fresh independent re-review, Phase 7 fresh
independent review and Phase 4 final independent verification remain pending.
