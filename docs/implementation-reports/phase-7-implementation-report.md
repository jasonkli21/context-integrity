# Phase 7 implementation report

**Date:** 2026-10-16
**Status:** Implemented; local verification recorded below; independent review required.
**Active plan:** `docs/plans/phase-7-implementation-plan.md`

## Repository and scope

Start HEAD: `ce97e04c07ede75e91ad137b97ba1079ff0030bb` on `main`.
The only pre-existing working-tree change was the user-supplied, untracked Phase 7 plan;
it is included in this phase's single commit with trailing whitespace normalized;
its requirements are unchanged. No reset or branch replacement
was performed. End of implementation/pre-commit verification HEAD is the same
`ce97e04c07ede75e91ad137b97ba1079ff0030bb`; the resulting end HEAD is the single commit
containing this report, resolvable with:

```bash
git log -1 --format=%H -- docs/implementation-reports/phase-7-implementation-report.md
```

A commit cannot embed its own final hash. The final response records that resulting hash.

Context Engine inspected: `5e3ae18d1510501e177aac2d9021fc01d8534435`, executable
`ctx 0.1.0`, ranker `file-ranker-v1`. Its current-state/integration docs and public CLI/JSON
renderer/DTOs were inspected as an external contract. No Context Engine sources/docs were
modified. No network, credentials, dependency changes, storage sharing or parser duplication
were needed. The separately pending Phase 4 independent verification remains separate.

## Implemented

- Generic evidence contract v1 in `evidence.py`: replaceable `EvidenceProvider` Protocol,
  descriptor/capabilities, explicit request, repository snapshot, typed coverage, provider
  state, normalized candidate batch and sanitized typed failures. A replacement-provider
  test exercises compilation without the Context Engine transport.
- `context_engine.py` executes local argv lists with `shell=False`, closed stdin,
  incremental bounded pipe reads, finite deadlines and process-group cleanup. Limits are
  30 seconds per invocation, 64 MiB context stdout, 4 KiB version stdout and 64 KiB stderr.
  Output-limit/timeout/executable/process/version failures are typed and sanitized.
- Strict consumed schema-v1 context envelope, task echo, root, known HEAD/dirty metadata,
  budget accounting, change identity, ranks/scores/reasons and structural entity validation.
  Duplicate JSON keys/paths/ranks and malformed, unsafe or conflicting evidence fail closed.
  Lossy candidate identities are omitted with explicit coverage. Inventory collisions fail
  without implicit shadowing or merging. Unknown snapshot fields stay nullable and gaps
  relative to known inventory metadata generate warnings.
- Full content is UTF-8 byte-validated, SHA-256 hashed and discarded. Source bodies,
  absolute roots, raw stderr and index-local IDs never enter normalized batches or output.
  Role mapping is owned here: source/test/schema/migration map to the four new kinds with
  executable-truth authority and unknown lifecycle. Other roles are skipped.
- Strict configuration v7 permits `source_code`, `test`, `schema`, `migration` in contract
  rules. The central `RepositoryConfig` gate prevents old schemas from gaining those
  semantics, including direct domain construction. Existing schema behaviors/projections
  remain intact; unsupported-version tests now use v8. Host-specific provider configuration
  remains rejected.
- `validate_contract_sources` shares the Phase 5 evaluator with inventory-only
  `validate_contract`; both retain exact bound-contract enforcement. The compiler supplies
  its exact mixed universe without mutating the inventory. Standalone validation regression
  tests still report provider paths unavailable.
- The existing compiler retains exclusions, lifecycle, rule-scoped authority, overlap
  restrictions, required-first coverage, maxima, unique-byte budgets, exact feasibility
  repair and optional fill. Relevance only orders policy-equivalent provider slots in an
  otherwise lexical sequence; inventory documents retain their positions. Optional ranking
  excludes already-selected/ineligible candidates before assigning slots. A regression
  prevents ineligible provider slots from indirectly demoting documentation.
- Provider completeness remains separate from contract completeness, with material
  analysis/ranking/content-load/acquisition/change gaps preserved in typed signal pairs,
  provider state and warnings. Complete/incomplete contracts retain exit 0.
- Compiled-context JSON v3 adds explicit candidate origins, provider identity/version,
  rank/score/reasons/entity spans/distances, provider snapshots/query/ranker/coverage and
  change metadata. Selected provider records retain content revisions and dependencies.
  Text adds provider identity/ranker, snapshot, coverage and ranks. Earlier JSON surfaces
  are unchanged. The old v2 golden remains historical; new v3 inventory/mixed goldens
  exercise the current contract. The mixed golden normalizes only runtime repository/source
  identities so it remains portable across fixture locations.
- CLI options: `--evidence-provider context-engine`, `--context-engine-bin`,
  `--evidence-budget-bytes`, `--evidence-change`. Nonblank task required in provider mode;
  provider-only options require explicit provider selection. Acquisition defaults to 1 MiB
  (maximum 16 MiB), independently of final contract budget. Provider failure is exit 7,
  with no silent fallback. Output-file/text/JSON paths remain supported.

## Acceptance and verification

Focused offline suite:

```bash
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 uv run pytest \
  tests/test_evidence.py tests/test_context_engine.py tests/test_compiler.py \
  tests/test_contracts.py tests/test_configuration.py tests/test_cli.py -q --tb=short
```

**371 passed.** Adapter/model tests cover valid and malformed output, required fields/types,
version/command, unsafe/lossy/duplicate paths, byte/hash/body handling, coverage, revision
mismatches, non-Git observations, change metadata, missing executables, process exit,
timeout, both output ceilings, literal argv and sanitized stderr. Mixed tests cover provider
rank against policy, documentation neutrality, exact budget boundaries, optional tests,
feasibility repair, final validation, provider replacement, collisions, determinism,
privacy, v7 gates and CLI output/errors. Existing Phase 5/6 tests and inventory-only golden
behavior remain part of the regression gate.

An intermediate full gate passed **822 tests**. Final canonical gate after the additional
boundary/optional-slot regressions:

```bash
UV_CACHE_DIR=/tmp/context-integrity-uv-cache UV_OFFLINE=1 make check
git diff --check
git status --short
```

Final result: **831 tests passed** in 99.86 seconds; Ruff lint and format checks passed
(72 Python files). `git diff --check` passed. Python 3.12.13, pytest 9.1.1, macOS.
The final working tree contained only the intended Phase 7 code/tests/docs plus the supplied
plan. No independent review or phase acceptance is claimed.

## Real-provider smoke

Used the existing sibling release binary at
`/Users/jasonkli/projects/context-platform/context-engine/target/release/ctx`.
The synthetic repository was
`/var/folders/kn/djny7kpj0vl523qvdw763ppm0000gn/T/context-integrity-phase7-smoke-mbhlczgw`,
with operating instructions, a schema-v7 mixed contract and one Python source file.
Exact first command (run with the offline UV environment above):

```bash
uv run context-integrity compile work \
  /var/folders/kn/djny7kpj0vl523qvdw763ppm0000gn/T/context-integrity-phase7-smoke-mbhlczgw \
  --task sample --evidence-provider context-engine \
  --context-engine-bin /Users/jasonkli/projects/context-platform/context-engine/target/release/ctx \
  --evidence-budget-bytes 4096 --format json
```

The second command added:

```text
--evidence-change c93782adc5ee5c3638b0ed6303e12831bcde19a1..HEAD
```

after initializing the fixture as Git and making two local commits. Observed final fixture
HEAD: `5fea0f91f69710119cf51d8b4c66a2915d6fb179`, clean. Both commands exited 0 and selected
`AGENTS.md` plus `src/sample.py`, with contract status complete. The first non-Git run had
nullable snapshot metadata and visible upstream analysis incompleteness. The Git/change run
retained matching HEAD/clean metadata, immutable change endpoints and one mapped file/symbol.
Both outputs retained version/ranker/revisions and were checked to contain neither source
body nor absolute repository root. Smoke data remains outside the repository and is not a
`make check` dependency. Source bodies were not copied into this report.

## Documentation staleness sweep

Added `docs/evidence-contract.md` from implemented types/transport and updated README,
docs navigation and architecture for the actual v7/v3 behavior, process limits, mixed
validation, body handling and separate provider completeness. Removed obsolete current
claims that transport/code acquisition were deferred, and replaced architecture's obsolete
Phase 0 immediate-next-step pointer with current-state navigation. Plan/report directory
READMEs are naming/lifecycle guidance rather than exhaustive indexes, so no index rows were
needed. Historical Phase 0–6 plans/reports and the PRD were not rewritten.

Sweep command:

```bash
rg -n 'Phase 6|Phase 7|v2|through v6|future.*provider|future executable|only.*inventory|no.*integration|Integration.*Deferred|transport.*deferred' \
  README.md docs/architecture.md docs/README.md \
  src/context_integrity/{compiler,models,rendering,evidence}.py
```

Remaining Phase 6 references describe its preserved baseline; inventory-only statements
refer to standalone acquisition/validation or no-provider compilation. v2 references are
historical lifecycle schema examples. Current-state advances only after the final gate.

## Deliberate choices, limitations and Phase 8 boundary

No material scope deviations. The supplied plan allowed exact field names, process bounds
and neutral inventory/provider tie behavior to be chosen during implementation. This change
uses compact sorted signal pairs, validated structural entity byte spans, rejects all
inventory collisions and duplicate paths, and ranks only provider slots. Provider numeric
scores are retained as evidence, without becoming another selection or authority dimension.
Required feasibility repair retains its existing minimum-bytes/path tie-break.

Sequential inventory/provider observations are not atomic snapshots. Snapshot unknowns remain
explicit; content hashes scope provider candidates but do not prove files remained unchanged
between observations. Coverage describes an acquired shortlist, not exhaustive code truth.
Upstream syntax/relationship/ranking limitations persist. POSIX subprocess controls mirror
existing POSIX safe acquisition; cross-platform execution is not claimed. Only context
candidates/change relevance are integrated. Optional fill stays greedy, and exact required
repair retains its existing complexity limitations.

Phase 8 architectural-integrity policy, relation/impact consumers, claim verification,
contradictions, persistence, cross-repository work, HTTP/MCP/FFI, token budgets, LLMs and
CI/governance remain deferred. This implementation is ready for independent review after
local verification; it does not self-certify architectural acceptance.
