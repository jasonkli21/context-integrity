# Phase 9 implementation evidence

Date: 2026-10-21. Role: implementation evidence, **not independent acceptance**.
Baseline and initial HEAD: `917a9d318824d4fa67a7206dd3784068dabc7a21` on `main`, matching
the supplied prompt. Initial status contained only the user-supplied untracked
`docs/plans/phase-9-implementation-plan.md`; that plan is included with five Markdown hard breaks normalized from trailing spaces
to equivalent backslash syntax for staged whitespace validation. Its requirements are unchanged. Delivery is
one commit containing this report; its exact resulting hash is reported by the implementation
session (a commit cannot embed its own hash). No unrelated files were overwritten.

## Reconciliation and implemented seam

The current-state baseline designated Phase 8, remediated but awaiting fresh independent
re-review. The user's explicit Phase 9 request supplies the separate phase scope. Relevant
architecture, PRD generated-context/user-goal/roadmap sections, evidence and architecture
contracts, source models, safe acquisition, repository discovery, inventory/configuration,
compiler/rendering/CLI, provider adapter and existing regression tests were inspected before
implementation. No accepted ADR added constraints beyond those contracts.

The bounded seam is a standalone receipt sidecar, not a new config version or global index:

- `derived_models.py`: frozen validated receipt/pin types; strict duplicate-key decoder,
  explicit JSON/text projectors; receipt v1 and fixed shape/resource ceilings.
- `derived.py`: typed observations/reasons/results; pure pin comparison and aggregate
  precedence; actual-byte manual/compiler capture; bounded, memoized receipt graph checker;
  explicit result v1 JSON/text projectors.
- `derived_output.py`: repository-relative exclusive no-follow publication, pair preparation,
  ordinary-failure rollback and sanitized partial-output/cleanup failure reporting.
- `acquisition.py`: additive optional smaller read ceilings, preserving runtime default
  limits and descriptor-relative no-follow behavior.
- `inventory.py`: optional count/observation ceilings for new workflows; ordinary inventory
  calls preserve their prior call path. Metadata classification/supersession stays centralized.
- `cli.py`: `derived capture`, `derived check`, additive `compile --receipt-output`.
  No new option changes existing compile selection, contract validation or output versions.
- `tests/test_derived.py`, `tests/test_derived_cli.py`: synthetic files, actual Git commits,
  staged/unstaged edits and a linked Git worktree, plus adversarial schema/graph/I/O tests.
  Fixed small goldens: `tests/fixtures/derived-receipt-v1.json` and `derived-result-v1.json`.
- Documentation: `docs/derived-context-contract.md`, README/docs navigation, durable
  architecture boundary, the architecture-integrity contract’s stale Phase 9 deferral,
  current-state and this report. The supplied Phase 9 plan is retained
  as normative planning input, not rewritten as implementation evidence.

## Delivered journeys and schema boundaries

For an existing handoff:

```bash
uv run context-integrity derived capture docs/handoff.md . \
  --id handoff-a --kind handoff --derivation model --producer agent \
  --depends-on AGENTS.md --depends-on docs/prd.md \
  --receipt-output docs/handoff.provenance.json
uv run context-integrity derived check docs/handoff.provenance.json . --format json
```

For an existing configured `work` contract:

```bash
uv run context-integrity compile work . --format json --output docs/saved-context.json \
  --receipt-output docs/saved-context.provenance.json
```

`--upstream-receipt` links explicit same-repository derivatives. A source change propagates
through an unchanged intermediate artifact; a tampered receipt never supplies trusted new
pins. Diamond traversal memoizes shared receipts. Capture refuses stale, unknown or conflicting
upstream declarations. Explicit code paths outside the documentation inventory are supported.
The checked-in receipt/result goldens are complete concrete JSON examples with real digests.

Receipt v1 pins actual artifact/source bytes, repository/HEAD/dirty explanatory metadata,
derivation declarations, config absence/presence, effective source metadata, upstream receipt
and artifact identities/hashes. Compiler scope additionally pins full contract, referenced
policies, inventory selection context, effective budget, task digest, compiler status/version,
warning tokens and validated provider snapshot/coverage/context fingerprints. Selected provider
files preserve provider/version/derivation and must match current local bytes at capture.

Status precedence: `review_required` for a definite change/missing input, otherwise
`inconclusive` for material observation/provenance gaps, otherwise
`unchanged_observed_inputs`. Original uncertainty remains visible alongside definite changes.
Equality is explicitly no semantic correctness, authority or source-closure proof. No provider
re-query is performed; any provider context remains inconclusive unless a stronger change
already requires review. Claims remain `unverified`.

Config v1–v8, compiler JSON v3, inventory/claims/contracts and integrity JSON v2 are retained.
No runtime/test dependency, database, model call, network access, watcher or Context Engine
installation was added. The fake executable test exercises the existing validated public
provider adapter without requiring a real engine.

## Plan defects corrected and defended choices

1. **Incorrect baseline assumption about compiler dependencies.** The prompt/plan describe
   `CompiledContext.dependencies` as excluding provider selections. At this exact baseline,
   `compile_context` adapts provider candidates to `SourceRecord`s and includes those selected
   records in `chosen` and `dependencies`. Tests prove that behavior; no repair to selection
   was needed. Receipt construction still uses typed decisions because dependency records
   alone omit provider origin/version/derivation and coverage context.
2. **Selected hashes do not cover a changed selection universe.** A conservative fingerprint
   of inventory candidates/content/effective metadata detects added or changed candidates,
   rather than implying a closed world from selected files alone. It can require review for
   an unselected document change; provider candidate universe/ranking remains unrevalidated.
3. **Two-file atomicity needs an honest boundary.** Independent POSIX names cannot be
   committed in a single atomic rename. Both payloads are prepared/fsynced before exclusive
   publication; ordinary second-write/link failure rolls back our files. Rollback/cleanup
   failure explicitly reports possible retained outputs. Process/power loss can leave orphaned
   files, and this implementation does not claim crash-atomic transactions.
4. **Outputs can invalidate provenance themselves.** New workflow outputs are inside the
   root, non-inventory paths, exclusive and non-overlapping. This is stricter than ordinary
   legacy `--output`, which remains unchanged. Unicode/noncanonical input identities are
   deliberately rejected by receipt v1 rather than guessed or normalized lossily.
5. **Bound both graph reads and metadata inventory.** Graph reads reserve 64 MiB/4,096
   attempts, individual files 5 MiB and receipts 1 MiB. Receipt graphs cap 128 observations,
   16 levels, 256 direct sources, 16 parents and 4 providers per node. Metadata inventory has
   its own 64 MiB/4,096 candidate ceiling. Current metadata failure is an observation gap;
   known changed config/source bytes still dominate it. Existing Git listing and config
   parser bounds are separate, not falsely advertised as a command-wide atomic resource cap.
6. **Malformed top-level vs upstream inputs.** Invalid/missing/foreign top-level receipts
   exit 6. An upstream whose unchanged pinned bytes fail strict graph/schema/identity checks
   yields `upstream_receipt_untrusted` uncertainty; missing/tampered receipt bytes require
   review. Unreadable, symlinked and oversized inputs are unobservable, not absent/equal.

## Acceptance evidence and regression coverage

- Strict constructors/parser: unsupported versions and bool-as-integer, unknown/extra/missing
  keys, duplicate JSON keys/dependencies, invalid digests/enums/IDs/paths, nonfinite/malformed/
  recursive/oversized JSON, null context distinctions, bounded arrays and explicit projectors.
- Actual Git bytes: dirty/staged changes without HEAD movement, byte reversion, unrelated
  committed HEAD changes, source/artifact mutation, deletion/rename, unreadability, symlinks
  including ancestor escapes, oversized files, non-inventory code and no-source captures.
- Config creation/deletion/invalid replacement and lifecycle/authority/supersession changes
  with source bytes unchanged; every shipped config schema; source metadata fields compared
  directly as well as by composite digest. Supersession hashing excludes irrelevant HEAD.
- Transitive source drift, diamond reuse, uncertain parent, missing/tampered/unsupported/
  foreign/identity-conflicting parents, self pointers, cycle guards, conflicting graph
  declarations, depth/count/read budgets and deterministic reason propagation.
- Compiler v3 byte-for-byte compatibility, selected inventory/provider hashes, task redaction,
  effective contract/policy/config selection pins, newly eligible document detection,
  incomplete package coverage and provider uncertainty/change precedence.
- CLI flag/exit behavior, no-overwrite and collisions, write/link/rollback/cleanup failures,
  output privacy, equivalent checkout roots with the same origin, reordered inputs and goldens.

## Verification

Final execution: macOS (`darwin`), Python 3.12.13, pytest 9.1.1. No tests skipped;
no network, API credentials, database or real Context Engine installation required.

```text
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 uv run pytest -q tests/test_derived.py tests/test_derived_cli.py
102 passed in 59.00s

UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check
Ruff: All checks passed!
Formatting: 91 files already formatted
pytest: 1067 passed in 129.27s (0:02:09)

git diff --check
Passed (no output)
```

`git status --short` was inspected at entry and before staging; it contained only the
implementation/doc/test changes and the supplied plan. Staged whitespace validation and
post-commit clean status are checked separately by the implementation session. Staged
validation initially found the supplied plan’s five trailing-space hard breaks; only those
line-break spellings were normalized, preserving the plan’s rendered content and requirements.

Initial broad regression testing
found 13 failures (the default read ceiling was frozen at function definition and new optional
keywords bypassed existing configuration race-test wrappers); the defaults/call shape were
restored rather than weakening those tests. One intermediate new output-collision test was
updated to expect output-error exit 4 for the new earlier destination guard. The mistaken
provider-dependency assertion was corrected against actual compiler code as described above.

## Review handoff and limits

The final offline gate passed; ready for independent review; this report is not architectural
acceptance. Phase 8 remediation's fresh independent re-review remains pending. Earlier Phase 4
final verification and Phase 7 fresh independent review remain pending as recorded previously.
Review should concentrate on graph identity conflicts/limits, source metadata and selection
fingerprints, safe output publication under failures, and conservative provider treatment.

Receipts are forgeable local declarations; they cannot authenticate a producer or prove the
summary is factually correct. Hash observations are sequential and can race repository edits.
Manual source closure is never proven. Provider replay and Unicode path support are not
implemented; POSIX/macOS behavior is verified locally, not Windows/cross-platform operation.
No automatic receipt migration/refresh/recovery or CI gating is claimed. See the durable
[derived context contract](../derived-context-contract.md) for exact fields/reasons/limits,
[architecture](../architecture.md), [evidence contract](../evidence-contract.md) and
[Phase 9 plan](../plans/phase-9-implementation-plan.md) for review scope.

## Complete changed-file inventory

```text
README.md
docs/README.md
docs/architecture-integrity-contract.md
docs/architecture.md
docs/current-state.md
docs/derived-context-contract.md
docs/implementation-reports/phase-9-implementation-report.md
docs/plans/phase-9-implementation-plan.md
src/context_integrity/acquisition.py
src/context_integrity/cli.py
src/context_integrity/derived.py
src/context_integrity/derived_models.py
src/context_integrity/derived_output.py
src/context_integrity/inventory.py
tests/fixtures/derived-receipt-v1.json
tests/fixtures/derived-result-v1.json
tests/test_derived.py
tests/test_derived_cli.py
```
