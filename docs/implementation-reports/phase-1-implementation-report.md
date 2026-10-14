# Phase 1 implementation report

**Date:** 2026-10-14
**Status:** Implemented and verified; independent review findings F-001–F-004 addressed.
**Baseline:** `d5b62ad` (`fix phase 0 independent review findings`), branch `main`.
**Phase 1 delivery:** `9efd5fb` (`implement phase 1`). The post-review corrections and this
updated report are included together in one follow-up commit.
**Review:** `context-integrity-phase-1-independent-post-implementation-review.md`, findings
F-001–F-004.
**Normative scope:** `docs/plans/phase-1-implementation-plan.md` and the supplied Phase 1
implementation prompt. Phase 0 baseline gate passed all 129 tests before edits.

## Implemented

Question-specific authority tiers resolve observed source roles, preserve every same-tier
highest candidate, retain lower candidates, and report missing stronger tiers. They do not
establish claim correctness, agreement, contradiction, or supersession.

Changed modules:

- `models.py`: executable/configuration vocabulary; frozen policy, tier, metadata, config,
  candidate, exclusion, status, and resolution values. Internal source/manifest fields carry
  metadata/config without expanding inventory JSON v1.
- `authority.py`: immutable built-ins, whole-policy merge, pure resolver; no filesystem I/O.
- `configuration.py`: strict `tomllib` parser, safe bounded loader, raw-byte SHA-256, and
  verification against inventory hash plus final config observation.
- `acquisition.py`: exact root config candidate and shared descriptor-safe byte capture.
- `classification.py`: new config rule and explicit authority override basis; kind confidence
  and lifecycle preserved. Existing Phase 0 rule IDs remain unchanged.
- `inventory.py`: config orchestration, metadata classification, stale metadata warnings,
  revision consistency. Ignored policy config is still inventoried.
- `rendering.py`: explicit separate authority v1 projection, text/list/show, mandatory semantic
  disclaimer, escaped metadata reasons, extended explain output.
- `cli.py`: `authority list/show/resolve`; config errors map to exit 6.
- Tests: new authority/config suites, three small JSON goldens; additive config case/rule ID
  assertions in the existing classification suite. README, fixture notes, current-state,
  and this report record the delivered behavior.

Architecture, ADRs, completed Phase 0 plan, evidence boundary, dependencies, and lockfile
are unchanged. No database, network service, model calls, claims, supersession, or ordinary
code indexing was added.

## Policy and configuration contracts

Built-ins use `builtin-v1`; repository policies use `repository_config` / `config-v1` and the
raw config hash. The resolution-level config hash also records config that only supplies
metadata or affects other policies, even when the selected policy remains built-in.

| Policy | Tier 0 | Tier 1 | Tier 2 |
| --- | --- | --- | --- |
| delivered_behavior | executable_truth | verification_evidence | generated_derivative |
| architectural_intent | decision | architecture_product | plan |
| operating_instructions | operating_instruction | architecture_product | plan |
| implementation_status | verification_evidence | generated_derivative | plan |
| future_work | plan | architecture_product | generated_derivative |

Config schema 1 allows only `schema_version`, `authority.policies`, and `source_metadata`.
Policies require ID, description, and nonempty tiers; classes cannot repeat within a policy,
and historical/unknown classes cannot be active tiers. Metadata supports only path, reason,
authority class, and eligibility; kind/lifecycle overrides fail validation. Phase 1 source
metadata may explicitly set `unknown` but rejects `executable_truth` and `historical` so a
document cannot manufacture executable evidence or emulate lifecycle. Use
`authority_eligible = false` for policy-independent exclusion. Unknown keys fail closed;
reasons are required for all metadata entries.

## Post-implementation review findings

- **F-001:** Source metadata now rejects `executable_truth` and `historical`; `unknown` and
  ordinary document-role overrides remain supported. Tests preserve the delivered-behavior
  tier-0 gap, actual historical exclusion, and CLI exit 6 for reserved values.
- **F-002:** Contract tests pin the complete nested built-in tier matrix, IDs, versions,
  deterministic listing, custom addition, and exact whole-policy replacement.
- **F-003:** This report and `docs/current-state.md` now describe the Phase 1 baseline and final
  post-review verification accurately.
- **F-004:** `explain` now says policy resolution is not performed by that explanation and
  points to `authority resolve`.

Config reads reuse the 5 MiB descriptor-safe source boundary. Present unsafe/unreadable/
malformed config errors never fall back to built-ins. Parsed bytes, inventoried config hash,
and final config read must agree, including config appearance/disappearance. Byte-identical
replacement is consistent with the content-hash contract. Sequential observations cannot
detect every transient mutation or provide an atomic repository snapshot.

## CLI and JSON examples

```bash
uv run context-integrity authority list .
uv run context-integrity authority show architectural_intent . --format json
uv run context-integrity authority resolve delivered_behavior .
uv run context-integrity authority resolve architectural_intent . --format json --output /tmp/authority.json
```

`list/show` support text/JSON; `resolve` additionally supports an output file. No candidates
exits 0, unknown policy exits 2, output failure exits 4, config failure exits 6.

The missing-executable golden includes this subset (other metadata/candidates omitted here):

```json
{
  "schema_version": 1,
  "status": "candidates_found",
  "highest_observed_tier": 1,
  "missing_stronger_tiers": [{"index": 0, "classes": ["executable_truth"]}]
}
```

Complete examples are `tests/fixtures/authority-v1-{architecture,missing-executable,config}.json`.
The explicit JSON contract includes repository identity/Git metadata, policy tiers/origin/
version/config hash, resolution config hash, status, source IDs/paths/kinds/classes/lifecycle/
revisions, highest and lower candidates, exclusions with reasons, and warnings. Every
inventoried source is accounted for, including `not_in_policy`. Human output summarizes that
exclusion count. Stable output contains no source bodies, absolute root, or timestamps and
ends with a newline. Inventory v1 gains no keys.

## Verification

Exact full gate, after the post-implementation review corrections:

```bash
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check
```

Baseline before Phase 1: Ruff lint/format and **129 tests passed**. Phase 1 post-review
working tree: Ruff lint/format and **226 tests passed**, Python 3.12.13/macOS. This gate ran
on the complete corrected tree immediately before its single follow-up commit, based on
reviewed delivery `9efd5fb`. Tests require no network, credentials, or database. All three
original Phase 0 JSON goldens pass byte-for-byte without modifications.
Intermediate failures were resolved: the existing exhaustive rule table needed the added
config rule, the three new goldens had to be generated, and a fault-injection test needed to
patch reads after repository discovery so it did not affect subprocess pipe reads.

Real-checkout smoke commands used the same offline/cache environment:

```bash
uv run context-integrity authority list . --format json
uv run context-integrity authority show architectural_intent .
uv run context-integrity authority resolve delivered_behavior .
```

All succeeded. With no config, this checkout's delivered-behavior candidates are currently
current-state derivative evidence (tier 2); executable truth and verification evidence are
reported missing. Implementation reports retain Phase 0's provisional other-document/unknown
classification; no semantic body interpretation or broad classification change was made.
Synthetic fixtures explicitly exercise verification evidence as tier 1. ADR templates still
look like decisions by convention until explicit metadata excludes them.

## Acceptance evidence

Each Phase 1 plan §23 checkbox is mapped below. “Verified” means implementation checks, not
independent architectural review. Paths for test names are `tests/test_authority.py` (A),
`tests/test_configuration.py` (C), and existing Phase 0 tests where named.

### Domain / Semantics

| Acceptance criterion | Verification evidence |
| --- | --- |
| `AuthorityClass.EXECUTABLE_TRUTH` exists. | A: `test_exact_builtin_set`; models enum. |
| `.context-integrity.toml` is represented as `SourceKind.CONFIGURATION`. | C: `test_ignored_config_still_observed`; classification config rule case. |
| authority policy is question-specific, not global. | A: `test_resolution_policies` tests each question separately. |
| policies contain ordered equal-precedence tiers. | A: `test_equal_tier_and_no_recency`; `test_invalid_tier`. |
| multiple top-tier candidates are not treated as contradictions. | A: `test_resolution_policies[architectural_intent]` returns both ADRs. |
| historical lifecycle excludes active authority candidacy. | A: `test_metadata_and_policy_merge`; historical check precedes eligibility. |
| missing stronger tiers are explicit. | A: `test_resolution_policies[delivered_behavior]`; `test_no_candidates`. |
| "highest observed" is never represented as "correct truth". | `AuthorityResolution` fields/status; A: text disclaimer and golden/projection tests. |
| no recency/mtime/Git-time authority inference exists. | A: `test_equal_tier_and_no_recency`; resolver reads only role/lifecycle/eligibility/path. |

### Built-In Policies

| Acceptance criterion | Verification evidence |
| --- | --- |
| `delivered_behavior` implemented exactly as specified. | A: `test_exact_builtin_set` and `test_resolution_policies`. |
| `architectural_intent` implemented exactly as specified. | A: `test_exact_builtin_set` and `test_resolution_policies`. |
| `operating_instructions` implemented exactly as specified. | A: `test_exact_builtin_set` and `test_resolution_policies`. |
| `implementation_status` implemented exactly as specified. | A: `test_exact_builtin_set` and `test_resolution_policies`. |
| `future_work` implemented exactly as specified. | A: `test_exact_builtin_set` and `test_resolution_policies`. |
| built-in policy version is explicit/stable. | A: `test_exact_builtin_set` asserts builtin-v1. |

### Configuration

| Acceptance criterion | Verification evidence |
| --- | --- |
| optional `.context-integrity.toml` supported. | C: `test_config_absent_and_valid`. |
| no config preserves Phase 0 behavior. | Existing `tests/test_rendering.py` three unmodified inventory goldens. |
| schema version validated. | C: `test_invalid_config` includes absent, boolean, string, unsupported schema. |
| repository policy can replace built-in by ID. | A: `test_metadata_and_policy_merge` checks whole replacement. |
| repository policy can add custom ID. | A: `test_custom_policy_addition`; config custom-policy merge. |
| invalid/duplicate tiers fail. | C: `test_invalid_config`; A: `test_invalid_tier`, `test_duplicate_class_across_tiers`. |
| `historical` and `unknown` cannot be active policy tiers. | C: `test_invalid_config`; A: `test_invalid_tier`. |
| source authority-class override supported for allowed document roles. | A: `test_metadata_and_policy_merge`, `test_unknown_override_allowed`; C rejects reserved values. |
| source authority eligibility supported. | A: `test_metadata_and_policy_merge`, `test_eligibility_omission_defaults_true`. |
| override reason required. | C: `test_invalid_config` missing/blank reasons. |
| stale metadata path emits structured warning. | A: `test_metadata_and_policy_merge` structured warning. |
| lifecycle override is not supported. | C: `test_invalid_config` rejects lifecycle/kind keys and historical authority metadata. |
| document metadata cannot synthesize executable truth. | A/C: reserved-class regressions; delivered behavior keeps tier 0 missing absent executable evidence. |
| config is safely read and hashed. | C: valid hash, symlink/directory/oversize, unreadable, read failure/growth, open race, revision consistency tests. |
| unsafe/invalid config fails with exit 6. | A: `test_cli_config_error_exit_6`, `test_cli_config_symlink_exit_6`. |

### CLI / Output

| Acceptance criterion | Verification evidence |
| --- | --- |
| `authority list` works. | A: `test_cli_commands` text and JSON variants. |
| `authority show` works. | A: `test_cli_commands` text and JSON variants. |
| `authority resolve` works. | A: `test_cli_commands` text and JSON variants. |
| text resolution clearly states its semantic limitation. | A: `test_cli_commands`; `test_rendering_terminal_controls`; mandatory renderer disclaimer. |
| authority JSON has schema version 1. | A: `test_authority_golden`; explicit schema_version=1. |
| JSON uses explicit projection. | A: `test_authority_projection_explicit` adds private dataclass field and asserts public key sets. |
| JSON is deterministic. | A: `test_equal_tier_and_no_recency`, `test_authority_golden`. |
| JSON contains no absolute root or source body. | A: `test_authority_projection_explicit`. |
| no-candidate resolution exits 0. | A: `test_cli_output_and_errors`. |
| unknown policy exits 2. | A: `test_cli_output_and_errors` resolve and show. |
| config error exits 6. | A: `test_cli_config_error_exit_6` covers scan, explain, list, show, resolve. |

### Integration / Regression

| Acceptance criterion | Verification evidence |
| --- | --- |
| `scan` applies explicit authority-class metadata. | A: `test_cli_scan_and_explain_metadata`. |
| `explain` shows explicit authority metadata/eligibility. | A: `test_cli_scan_and_explain_metadata`; `test_metadata_and_policy_merge`. |
| config source is inventoried. | C: `test_ignored_config_still_observed`; A: config golden. |
| Phase 0 no-config JSON goldens remain byte-identical. | Existing three inventory golden files unchanged; `tests/test_rendering.py` passes. |
| existing security/repository protections remain intact. | All existing acquisition/repository/CLI tests pass; shared descriptor boundary retained. |
| no database added. | Unchanged pyproject.toml/uv.lock; source inspection: no persistence added. |
| no LLM/model dependency added. | Unchanged dependencies; source inspection: no model/provider calls. |
| no Codebase Intelligence dependency added. | Unchanged dependencies/evidence.py; source inspection: no engine integration. |
| no claim model/extraction added. | New types contain sources/policies only; no claim extraction or body parsing. |
| no supersession graph added. | Lifecycle vocabulary unchanged; historical exclusion only. |

### Testing / Docs

| Acceptance criterion | Verification evidence |
| --- | --- |
| built-in policy contract is exact and listing deterministic. | A: `test_exact_builtin_set` pins IDs, every class in every tier, versions, and sorted output. |
| config validation thoroughly tested. | C: parser matrix, safe-read failures, ignored config, revision race cases. |
| authority golden JSON tests pass. | A: `test_authority_golden` all three scenarios. |
| Phase 0 regression suite passes. | All baseline tests retained; additive config case and rule ID in classification tests. |
| full offline `make check` passes after review fixes. | Offline make check: lint, format, 226 tests passed on the corrected tree immediately before commit. |
| README documents Phase 1 behavior and limitations. | README: authority semantics/table/config/commands/limitations/exit codes. |
| Phase 1 implementation report maps every acceptance criterion. | This table maps all 58 checkboxes in plan §23. |
| current-state updated only after verification. | Current-state edited after the 226-test gate passed. |


## Security acceptance evidence (plan §22)

| Criterion | Evidence |
| --- | --- |
| No shell execution | Existing repository runner remains argument-array only; no shell=True added. |
| Config parsing executes no code; no includes/imports/network | tomllib plus strict allowed-key tables; unknown include keys fail; no network imports or new dependencies. |
| Symlink/path escape fails closed | C: symlink, traversal, duplicate normalized paths, open replacement, unsafe read tests. |
| Safe read boundary reused | acquisition.read_source_bytes calls the same descriptor-based _read_source as inventory hashing. |
| Invalid config never ignored | C: parser matrix; A: CLI exit-6 matrix. |
| Policy hash equals observed config | C: test_config_revision_consistency (replace/remove/symlink/appear/after_read); ignored-config hash assertion. |
| Metadata paths remain in repository | C: invalid absolute/traversal/Windows/empty paths; no metadata-driven filesystem reads. |
| No source body/absolute root in authority JSON | A: test_authority_projection_explicit; three goldens. |
| Terminal controls escaped; policy descriptions safe | A: test_rendering_terminal_controls; display() for paths, reasons, descriptions. |

## Decisions, deviations, and limitations

No phase scope or built-in ordering deviations were required. Review correction and small
implementation choices:

- Unknown config keys are rejected, as recommended. Source class overrides may set unknown;
  `executable_truth` and `historical` are reserved from Phase 1 source metadata.
- Repository config is inventoried even when ignored by Git, because it still controls
  interpretation. Its per-file Git status is unknown in that case, avoiding an unsupported
  assertion that it is tracked-clean. Other ignored-source behavior is unchanged.
- Internal source and manifest fields retain metadata/config for explain and authority
  commands. Explicit projections prevent these fields from expanding inventory schema v1.
- list/show use the same full validated inventory path as resolve; there is no separate
  partial policy-loading flow. Config consistency and stale metadata detection therefore
  apply to all three commands.
- All exclusions appear in authority JSON. Human output summarizes not_in_policy sources.
- Safe reads remain POSIX only. Scans are sequential; content-hash checks cannot detect
  arbitrary transient changes between observations. No global atomic snapshot is claimed.
- Implementation reports still use existing Phase 0 classification rules. Bodies, ADR
  acceptance, semantic agreement, and active/superseded state remain uninterpreted.

The offline quality gate passed after F-001–F-004 were addressed. The Phase 1 plan remains
unchanged; its source-metadata class list was underspecified, and the reserved-class rule is
captured here and in regression tests. Phase 2 has not started.

## Deferred and inputs for Phase 2

Phase 2 should supply explicit lifecycle/supersession decisions at the resolver's existing
historical eligibility seam while preserving equal-tier and missing-stronger semantics.
It must not infer supersession from dates. Keep SourceId plus raw-byte revision dependencies
when adding richer lifecycle decisions. Later evidence integration can populate executable
truth without changing the delivered_behavior ordering. Claims and agreement remain separate
from source-role resolution; no Phase 2/3 infrastructure was introduced here.
