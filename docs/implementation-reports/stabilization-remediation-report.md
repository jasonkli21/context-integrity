# Stabilization remediation — implementation evidence

Date: 2026-10-26 Pacific. This is an implementation report, **not independent review or
Phase 11/overall acceptance**. Scope: the supplied 1B prompt's four findings in Context Integrity
only, after Phase 11. No Phase 12 or evidence-v1 consumer was introduced. No subagents were used.

## Baseline, inputs and commits

The initial branch was `main`, HEAD `b03d707c570b2ad66b12e88dc789006ebc82b3cc`, with a clean
working tree. This exactly matches both audits' Integrity baseline; no reset or historical
checkout was needed. Recent history was `b03d707` (Phase 11 fixes), `fdf59c8` (Phase 11),
`59b90c0` (Phase 10 fixes), `c24f15d` (Phase 10), `61ca157` (Phase 9 fixes), `eedc972` (Phase 9).
The active phase remains Phase 11, with `docs/plans/phase-11-implementation-plan.md` as its plan.
AGENTS, current state, relevant PRD/architecture sections, Phase 6 compiler requirements,
Phase 6–11 boundaries/contracts, review-fix reports and prior review findings informed the work.
No accepted ADR beyond the index/template was present. Historical reports did not establish
independent acceptance.

The three supplied files were read as task instructions (1B) and independent evidence (audits),
respectively. The audits remain unedited external inputs; checksums identify their exact bytes:

| Input filename | SHA256 |
| --- | --- |
| `1B-context-integrity-stabilization-implementation.md` | `0c64f7166633a3fafcece06870edbc61d658063dfcb69b4298f6e949fa54368f` |
| `repo-wide-stabilization-audit(1).md` | `8e24269c7312ecaa15422579e9f939f613ce54f0c7886dc7848b092636c66aa7` |
| `cross-project-boundary-audit.md` | `e6ea0a0af8f53d2b280f7304521683b0d7a23a4ee6e36b6c81da0a1d10971099` |

Local branch: `codex/stabilization-remediation`. Implementation commits:

| Exact new SHA | Change / finding |
| --- | --- |
| `ad157678d4b7f75e6f09b15c5f0b74957596b37f` | Strict committed inventory/config binding; RWA-001 |
| `14d46dc8ddf475dc981e1cb10ad8a70a5286bb32` | Bounded exact compiler repair; RWA-002 |
| `56cd28a5a4f98fb6e3cf4e04580f8ec2958994a5` | Qualified symbols and safety coverage; CI-BND-01/02; dangling `contains` fixtures |

The subsequent documentation/verification commit contains this report, verified current-state/
navigation updates and strengthened legacy-check assertions; the code tested is the three commits above. No push, PR, merge, production CI activation,
remote-policy change or user-data deletion occurred. Disposable fixtures were outside the checkout.

## Required finding disposition at the current tree

All four defects were present at the exact audited baseline; none was already fixed.

| ID | Baseline reproduction | Fix and current regression evidence | Disposition |
| --- | --- | --- | --- |
| RWA-001 P1 | Real Git, ignored config, clean porcelain and HEAD..HEAD: canonical AGENTS allowed; canonical GEMINI changed the live gate. The corrected subprocess regression initially observed exit 0 where strict exit 6 was required. | Verify every live context inventory input against its target Git blob, plus exact inventory membership and config presence. Compare evaluated SHA256s again after evaluation, then recheck every strict target before constructing the report. Ignored config fails with sanitized exit 6, regardless of incomplete policy, with no stdout or saved report. | Implemented; self-tests pass; independent review requested. |
| RWA-002 P1 | Actual Git CLI fixture with 32 one-byte documents, minimum 12 and budget 10 timed out after 3 seconds before producing a result. | Per-rule capacity/cheapest-deficit lower bounds prune impossible branches without double-counting overlap. Iterative exact search charges at most 250,000 work units. Exhaustion preserves the incomplete greedy required package and an explicit warning, without optional fill or an infeasibility claim. | Implemented; self-tests pass; independent review requested. |
| CI-BND-01 P1 | Five producer-shaped qualified-name fixtures failed entire normalization with `invalid_response`, including Rust, Python, mixed case, accents and CJK. | Separate bounded exact qualified identifier grammar from reason/kind tokens; preserve names verbatim. Rust `::`, Python `.`, Unicode identifiers and per-component Rust raw identifiers are accepted. Strict token/schema/hash/span/privacy checks remain. | Implemented; fixtures and existing real binary smoke pass; fresh current-build review/matrix remains. |
| CI-BND-02 P2 | Setting upstream `sensitive_files_omitted=7` yielded no normalized signal (`KeyError` in the new regression). | Retain the bounded optional counter through normalization and public compiled v3 projection; absence remains absent for older v1 producers. Intentional safety exclusion is a caveat, not material truncation by itself. | Implemented; projection/bounds/golden and real safety-exclusion smoke pass. |

### RWA-001 acceptance details

`verify_committed_inventory` is an opt-in acquisition check in `inventory.py`; ordinary inventory,
configuration loading and legacy `check --diff` retain their existing working-tree behavior.
Git blob identity is recomputed from the live raw bytes, using the repository object-ID algorithm,
so status suppression and Git filters cannot make different bytes appear committed. Stable
no-follow regular-file reads are bounded to 5 MiB each, 64 MiB total and 4,096 inputs per pass.
Strict unreadable, unsafe, oversized or untracked inventory/config input refuses the report.
The `governance_diff_scope_invalid` typed error is fatal; it cannot become a waivable gap.

`test_ignored_config_cannot_flip_committed_gate` uses actual subprocess CLI runs and actual Git.
It retains ordinary working-tree governance exits 0/8 for the two configurations and requires
strict exit 6 with no saved output for both. Removing ignored config restores the valid absent
control. Other regressions exercise tracked clean, staged, unstaged, removed and symlink config,
assume-unchanged/skip-worktree edits, ignored-config creation/removal/replacement at final recheck,
and hidden source mutations. A trusted fake provider subprocess creates ignored config during
an actual CLI run; the final scope check rejects it without report publication. Existing detached
HEAD, ref/SHA, endpoint mismatch, tracked/untracked dirty and cross-target final rechecks pass.

The separately supplied governance policy remains an explicit caller-selected, SHA256-identified
input; it is not implicitly pinned to each target commit. Legacy provider graph observations
have no analyzed-content digest. They are explicitly labeled
`provider_graph_not_commit_certified` instead of promoting clean HEAD metadata into a certificate
of analyzed bytes. Graph policy ownership and independent coverage gaps remain unchanged.

### RWA-002 acceptance details

Existing feasible-overlap repair still selects `a.md`, `b.md`, `c.md` within seven bytes;
six bytes remains incomplete. A small exhaustive oracle checks multiple minima/maxima, overlap,
zero-byte costs and budgets 1–7 against the exact repair result. Existing authority, exclusions,
priority, optional fill, boundary budgets, ordering and inventory/provider goldens remain covered.
The default work cap is exercised with 100 candidates whose individually feasible minima conflict
with a shared maximum; the result retains 79 safe greedy items and emits
`compiler_search_budget_exceeded`. A forced minimal cap proves deterministic incomplete output
and preservation under source permutation. No recursion-depth limit is needed by the new search.

The cap covers node/state-copy work, candidate/rule visits and cost sorting within repair; it is
not a global bound on greedy matching, Git enumeration or arbitrary filesystem/process stalls.
An exhausted search discards any provisional solution because its byte/path minimum was not
established. Final Phase 5 validation still determines compiled complete/incomplete, with no
schema/model-status relaxation. The greedy deficit ensures an exhausted result stays incomplete.

Separate disposable actual-Git CLI probes after the fix:

| One-byte documents | Required minimum / byte budget | Wall seconds | Result |
| --- | --- | --- | --- |
| 28 | 12 / 10 | 0.937 | exit 0, incomplete, ten selected bytes/files |
| 32 | 12 / 10 | 1.017 | exit 0, incomplete, ten selected bytes/files |

These include CLI startup and concurrent local test load, not a performance guarantee. The
regression subprocess has a three-second timeout; cheap infeasibility pruning avoids enumeration.

### Legacy provider acceptance details

The production commands remain `ctx context` and `ctx graph`, both external schema v1.
Engine's additive `ctx evidence ...` evidence schema v1 remains a producer surface with **no
production Integrity consumer**. No Rust parser/index/database code or producer wire changes
were introduced. Reason/kind/score tokens remain strict lowercase tokens; qualified names use
identifier components with a 1,024-character ceiling, without case folding or normalization.
Malformed spans, controls/format characters, surrogate/replacement characters, paths, empty
components and overlong names fail closed. Existing version, snapshot, process-error and privacy
regressions remain enabled.

Sensitive omissions retain their reported count even when the package satisfies its acquired
contract. Nonzero alone does not set provider incomplete or emit `provider_incomplete`; this is
intentional safety exclusion, distinct from material truncation. The actual safety filter stays
in Engine. Older responses omitting the optional counter remain accepted without inventing zero.
The strict producer-shaped compiled v3 golden was deliberately extended with the reported zero
signal; v3 object keys, decisions and status grammar are unchanged.

## Verification performed

Host: Darwin arm64, macOS 27.0.1, Python 3.12.13, uv 0.11.13, pytest 9.1.1, Ruff 0.17.0,
Git 2.39.5 (Apple Git-154). Tests used no network, credentials, model or external database.
The initial default uv cache was unreadable under sandboxing; the existing writable offline
cache below worked. An initial full check stopped on import ordering in the new test; Ruff fixed
it before the final run. The initial probe used `python -m ...` before discovering governance's
module-entry ordering; the actual CLI probe uses `python -c 'from context_integrity.cli import app;
app()'`, as existing subprocess tests do. That tooling correction is not a stabilization fix.

Exact final/full and focused commands (all use the existing offline cache):

```sh
UV_CACHE_DIR=/tmp/context-integrity-phase11-fix-uv-cache UV_OFFLINE=1 make check
# PASS: Ruff lint; formatting (115 files); 1,316 tests in 472.84s (7m52s).

UV_CACHE_DIR=/tmp/context-integrity-phase11-fix-uv-cache UV_OFFLINE=1 uv run pytest -q tests/test_compiler.py tests/test_context_engine.py tests/test_evidence.py
# 251 passed in 48.67s; later cap/older-response additions are included in the full gate.

UV_CACHE_DIR=/tmp/context-integrity-phase11-fix-uv-cache UV_OFFLINE=1 uv run pytest -q tests/test_governance.py tests/test_graph_adapter.py tests/test_models.py tests/test_architecture.py tests/test_workspace.py tests/test_workspace_cli.py tests/test_derived.py tests/test_derived_cli.py tests/test_integrity.py
# 530 passed in 281.97s; the subsequent provider-mutation test passed separately (1 in 4.61s).

git diff --check
# passed; final staged/committed checks recorded at delivery.
```

After the full-gate test collection, the ignored-config regression was strengthened with four
legacy `check`/`check --diff` assertions; its focused rerun passed (1 test in 15.75s), with Ruff
lint/format checks passing. No production source changed after full-gate collection. CLI
`UV_CACHE_DIR=/tmp/context-integrity-phase11-fix-uv-cache UV_OFFLINE=1 uv run context-integrity governance --help`
passed, as did the analogous `context-integrity check . --format json`: exit 0, integrity v2,
working-tree scope, zero findings and warnings.

The broad focused suite includes Phase 8 unmatched-source and endpoint coverage/work-budget
counterexamples, Phase 9 unlinked-derived dependencies, compiler source fingerprint, empty
compiler selection and budget reasons, Phase 10 report amplification and warning isolation,
and Phase 11 waiver severity/owner/threshold context, independent gaps, explicit ranges,
changed diff base and baseline fingerprint/waiver-corruption cases. These are regression
self-tests, not a renewed independent phase review. The two dangling `contains` endpoint
fixtures reject with `dangling_entity`; they do not certify full containment endpoint/range
semantics or establish the audit hypothesis as a policy false-green.

### Actual Context Engine smoke

An existing local release executable, `ctx 0.1.0`, was available. Its SHA256 is
`98c612d74c512ea80784647fa4136db7159511b5caa378fc693e501a4832e45f`.
The adjacent Engine checkout was `231c0256500fad1599259f9c97284ce74285946d`; the existing binary
was **not rebuilt or proven to derive from that exact SHA**. Engine source/tree was not changed.

The disposable Git fixture contained Python `Sample.method`, Rust `demo::Type::method`, an
explicit `forbid_relation` policy and a source named `credentials.py`. Actual provider calls and
subprocess CLI `compile work ROOT --task 'Sample Type method' --format json --evidence-provider
context-engine --context-engine-bin BINARY` and analogous `check ROOT` passed in clean and dirty
states. Both acquired two candidates and preserved the four exact matched symbol names; the
sensitive source was excluded and `sensitive_files_omitted=1` survived normalization. Compile
returned complete (exit 0, about 0.520s each); check retained `architecture_prohibited_relation`
(exit 0, 0.529/0.539s). Legacy graph coverage remained explicitly incomplete. A clean exact
HEAD..HEAD context acquisition also passed. Public outputs contained no root, sensitive marker
or source bodies. Fixture/script metadata is scratch evidence, not a new canonical fixture.

This establishes a real binary smoke, not the audit's entire current-build cross-runtime matrix.
No Engine rebuild/verifier suite, evidence-v1 consumer/conformance test, full native rename/delete/
parser-failure/workspace matrix, live Actions, Windows or crash/concurrent-filesystem-race
verification was performed. Existing synthetic malicious/error fixtures remain separate evidence.

## Compatibility, documentation and separate backlog

Config v1–v8, compiled-context v3, integrity v2, workspace/lock/check/context v1,
derived receipt/result v1 and governance policy v1/v2/report v2 remain at their existing versions.
Strict PR inputs are deliberately more restrictive; ordinary working-tree commands remain live.
Compiled search exhaustion has an additive fixed warning and incomplete safe fallback. Coverage
has an additive optional signal. Existing compiled receipts will detect the changed installed
package fingerprint and require review as already designed. No dependencies were added.

Canonical semantics changed only in governance, compiler architecture and evidence documentation.
Current-state retains Phase 11 and predecessor debt. README/doc/review/report navigation points
to the current source of truth. PRD's original immediate steps and architecture's initial Draft v1
label are explicitly historical; historical plans/reports and the independent audits are unedited.
The documentation map's stale policy/report v1 description was corrected to v1/v2 and report v2.

| Separate ID / debt | Disposition |
| --- | --- |
| RWA-003 P2 evaluation gap | Still deferred: no independently labeled precision/recall or agent-outcome benchmark was created. Synthetic counts do not establish product-quality metrics. |
| RWA-004 P2 family floor | Existing documented starter policy remains declared-scope only, without a global required-family floor. No production gate was enabled. |
| RWA-005 P2 dependency freshness | `not_established` remains explicit; current declaration alignment is not historical claim freshness or truth. |
| RWA-006 P3 navigation | External audits are indexed via exact provenance/dispositions here. No nonexistent independent Phase 11 artifact or acceptance was invented. |
| RWA-007 P3 historical wording | PRD initialization steps and architecture original status are labeled historical with current-state navigation. |
| CE-BND-03 P2 | Engine-owned evidence-v1 digest-conformance gap is outside this repository; unchanged and not a blocker to these consumer fixes. |
| `contains` hypothesis | Two malicious dangling-endpoint fixtures added; full containment conformance remains separate, unconfirmed scope. No graph protocol redesign. |
| Phase 0–2 / 3 / 5–6 | Existing early reviews/fixes do not automatically establish final cumulative acceptance; Phase 3 independent artifact is unavailable and Phase 5–6 index-level acceptance is not established. Compiler remediation requires fresh review. |
| Phase 4 / 7 / 8 / 9 / 10 | Phase 4 final independent verification, Phase 7 fresh review, Phase 8/9 fresh re-review and Phase 10 acceptance remain pending. |
| Phase 11 | RWA-001 implementation is fixed and self-tested; original audit verdict remains CHANGES REQUIRED at its reviewed SHA. Fresh independent closure is required. |

## Independent review requested

Request a **fresh independent review of all three implementation commits and final documentation**,
covering RWA-001's strict input membership/blob binding and no-publication behavior, RWA-002's sound
pruning/work accounting and incomplete fallback, qualified-symbol interoperability, and intentional
exclusion coverage semantics. Recheck the relevant Phase 6/7/11 requirements and Phase 8–11
counterexamples against actual code, not this report's assertions. Obtain a verified current-build
Engine smoke/matrix before claiming cross-project release readiness or beginning evidence-v1
integration. Keep predecessor acceptance debt separate. All four required IDs have tested local
fixes; their architectural/independent acceptance remains unreviewed.
