# Phase 3 implementation evidence — Claims and Provenance

Date: 2026-10-15. Implementation evidence only; independent review pending.

## Baseline and implementation revision

Actual baseline: `14ce25d6fcc3ecf65a8aaf79c177323ac3cb5772`
(`fix phases 0-2 independent review findings`). Baseline offline `make check` passed
Ruff lint/format and **353 tests** on Python 3.12.13/macOS. HEAD matched the plan's
reference baseline. The working tree had only the supplied, untracked
`docs/plans/phase-3-implementation-plan.md`; it is included with trailing whitespace removed for the diff check; requirements are unchanged.
No prerequisite Phase 0–2 fixes were needed.

Implementation revision: the single commit `implement phase 3 claims and provenance`
that adds this report. Resolve its exact SHA with:

```bash
git log --diff-filter=A --format=%H -- docs/implementation-reports/phase-3-implementation-report.md
```

The resulting SHA is reported at task completion. A literal self-referencing SHA cannot
be embedded in the same commit's contents.

## Delivered behavior and acceptance evidence

- `models.py`: stable explicit `ClaimId`; immutable claim specification, declaration
  provenance, dependencies, records, and overview; distinct `ClaimValidity` whose only
  Phase 3 value is `unverified`.
- `configuration.py`: strict schema v3 adds `[[claims]]` to all v2 behavior. v1 remains
  authority-only and v2 retains lifecycle/supersession; both reject even empty claim arrays.
  Required statement strings are nonblank; IDs/types use `[a-z][a-z0-9_-]*`. Optional scope
  is nonblank; dependencies default empty. Duplicate IDs, unknown keys, malformed values,
  unsafe paths, duplicate normalized paths, and config self-dependency fail closed with
  sanitized configuration errors. Claim types need not name authority policies.
- `claims.py`: pure resolution after verified inventory. Declaration provenance uses the
  actual config SourceId/raw-byte SourceRevision, `claim:<id>` locator,
  `repository_config_explicit`, and `claims-v1`. A missing/inconsistent declaration revision
  fails closed. Dependencies use existing observed source identities/revisions without
  filesystem reads, source-body parsing, authority resolution, or lifecycle interpretation.
- Missing/non-inventoried dependencies retain their claim, expose `resolved = false` with
  null identity/revision, set provenance incomplete, and warn `claim_dependency_missing`.
  An observed dependency without trustworthy content revision retains available metadata,
  stays unresolved, and warns `claim_dependency_revision_unavailable`. Every warning
  identifies the claim in its message and the dependency in its path.
- Dirty config and dependency bytes have their own content hashes while retaining logical
  identity and separate Git HEAD/status. Validity is always `unverified`, including active,
  historical, superseded, missing, and unavailable dependency observations. Complete
  provenance also never verifies an assertion.
- `claims list [PATH]` and `claims show CLAIM_ID [PATH]` support text/JSON and `--output`.
  Text list is concise; show exposes the statement and declaration/dependency revisions.
  Unknown claim exits 2, output failure exits 4, config errors exit 6; normal success exits 0.
  Show uses the same JSON schema with one claim and all observation warnings.
- Separate explicit claims JSON v1 projects statements/scope, validity, completeness,
  declaration provenance, dependency identities/revisions/resolution, config hash,
  repository metadata, and warnings. Claims sort by ID, dependencies by normalized path,
  and warnings by path/code/message. Output ends in a newline and contains no automatic
  timestamps, absolute root, source bodies, or arbitrary dataclass fields. Human rendering
  uses the existing terminal escaping for repository-controlled fields.

## Files and tests

Implementation: `src/context_integrity/{models,configuration,claims,rendering,cli}.py`.
Tests: `tests/test_claims.py`, extended v3 consistency coverage in
`tests/test_configuration.py`, and `tests/fixtures/claims-v1-{basic,unresolved}.json`.
Documentation: README, current-state, this report, and the supplied Phase 3 plan.

Passing commands run from the repository root:

```bash
# Before implementation: 353 tests.
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check

# Focused development gate: initially 119, finally 121 tests.
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 uv run pytest tests/test_claims.py tests/test_configuration.py -q

# Final full gate: Ruff lint/format, 419 tests.
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check

# Real-checkout empty list plus synthetic v3 CLI smoke program.
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 uv run python /tmp/context-integrity-phase3-smoke.py

git diff --exit-code HEAD -- tests/fixtures/inventory-v1*.json tests/fixtures/authority-v1-*.json tests/fixtures/lifecycle-v1-*.json
git diff --check
git status --short
```

Final full result: **419 passed in 15.68s**; Ruff passed, 53 Python files formatted.
The 66 additional cases comprise 61 focused claim tests and five new v3 configuration
consistency cases. The unsupported-schema regression now uses schema 4 instead of 3.

Focused evidence includes strict field/path validation, optional fields, v2 features in
v3, empty/no config, raw-byte dirty provenance, stable logical IDs, lifecycle separation,
missing/ignored/deleted/non-inventoried/symlink dependencies, unavailable revisions,
resolver no-I/O behavior, fail-closed declaration provenance, deterministic golden JSON,
explicit projections, control escaping, CLI modes/output/errors, and default paths.
Existing config mutation/race cases now also exercise v3 with explicit claims.

All original inventory, authority, and lifecycle golden fixtures remain byte-identical and
pass their tests. Additional comparison proves the same manifest's old JSON projections
are unchanged when claim specifications are present versus absent.

The temporary smoke program created a disposable repository directory with a v3 assertion,
a historical dependency, and a missing dependency. It invoked list/show in JSON and show
in text, repeated JSON for byte equality, checked file output, raw provenance and unverified
validity, and asserted that the temporary absolute root and dependency body were absent.
It also exercised `claims list . --format json` on this actual checkout (empty claims).
No actual root configuration was created or modified. Equivalent stable smoke coverage is
retained in `tests/test_claims.py`; the temporary program is outside the repository.

## Deviations, boundaries, and limitations

No substantive plan deviations. Only trailing whitespace in the supplied plan was normalized. The illustrative JSON field names are retained; unresolved
state is represented by each dependency's `resolved` flag and nullable metadata. The
resolver defensively rejects unavailable/inconsistent declaration provenance even for
manually constructed manifests; normal inventory already guarantees that invariant.

No architecture/PRD or completed Phase 0–2 plan changes were needed. No dependency,
network/model/database facility, evidence provider framework, ordinary-code parser,
claim authority selection, automatic validity/staleness/supersession, prose extraction,
contradiction/drift evaluation, mutation command, or Codebase Intelligence integration
was introduced. `inventory.py`, `authority.py`, `lifecycle.py`, and `evidence.py` are unchanged.

Claims are explicit assertions in config only. Dependencies resolve only to observed
inventory candidates; a file existing on disk does not guarantee it is inventoried.
Observations remain sequential rather than atomic, and descriptor-safe reads target POSIX.
Raw revisions allow later comparison but Phase 3 performs no revalidation judgment.
Independent architectural review and verification remain the next step.
