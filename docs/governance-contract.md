# Governance policy and report v1

Phase 11 adds a separate, explicit local decision layer over existing typed evaluators.
It does not change config v1–v8, integrity JSON v2, compiled JSON v3, workspace v1 or
receipt/result v1. Policy, owner, review reference and waiver are unauthenticated declarations.
A passing gate means the declared policy permits these observations. It never establishes
semantic correctness, API compatibility, claim truth, exhaustive coverage or approval.

## CLI and scope

```bash
uv run context-integrity governance check governance.toml --format json
uv run context-integrity governance check governance.toml \
  --diff app=BASE..HEAD --as-of 2026-10-24 --compare-to previous.json \
  --output /private/tmp/new-governance.json
```

`POLICY` is mandatory; nothing is discovered implicitly. Repeat `--diff TARGET=BASE..TARGET`
only for distinct declared repository targets. These use the existing `changed_paths` local
Git range implementation (no rename inference). With no range, repository checks use current
working-tree status. Findings inspect current working-tree bytes even with a Git range;
this is change-review scoping, not a historical checkout evaluator. No PR base is guessed.
Resolved immutable endpoints and HEAD/dirty observations are explanatory, not content pins.

`--evidence-provider context-engine` explicitly enables the existing local relation adapter
for repository targets; `--context-engine-bin` requires that option. Missing/broken provider
adds a coverage gap while inventory checks still run. No installation, network, model,
credential, database, source/index/receipt/lock/policy mutation or automatic waiver refresh
is performed. A provider executable is explicitly trusted runtime code; its own external
side effects are outside this program's guarantees.

Default output is stdout. `--format text` adds a short summary to exactly the complete JSON
payload, preserving parity. `--output` uses cwd-relative or absolute paths, existing no-follow
parents, exclusive publication and mode 0600. It must be outside every declared/observed
repository root and cannot collide with policy/baseline input. No overwrite or append.
The full report is validated and bounded before any output. Ordinary failures clean temporary
files and roll back publication; process loss or filesystem cleanup failures can leave orphans.
No cross-repository snapshot or crash transaction is promised. POSIX/macOS is verified;
Windows descriptor semantics have not been verified.

## Complete policy grammar

UTF-8 TOML, at most 256 KiB, exact integer `governance_schema_version = 1`.
Unknown fields and TOML duplicate keys fail closed. All tables below reject extra keys.
All targets are required; `on_inconclusive` handles their incomplete coverage globally.

| Table | Required fields | Optional fields |
| --- | --- | --- |
| Root | `governance_schema_version`, `policy_id`, `owner`, `fail_on`, `on_inconclusive`, `targets` | `rule_policies`, `waivers` |
| Repository target | `id`, `kind="repository"`, `root` | `repository_id`, `require_architecture` (boolean, default false) |
| Workspace target | `id`, `kind="workspace"`, `manifest`, `review_severity` | none |
| Derived target | `id`, `kind="derived"`, `root`, `receipt`, `review_severity` | `repository_id` |
| Rule policy | `target`, `rule_id`, `severity`, `owner`, `reason`, `review_ref` | none |
| Waiver | `id`, `target`, `finding_fingerprint`, `owner`, `reason`, `review_ref`, `expires_on` | none |

`fail_on`, `severity`, `review_severity`: `low`, `medium`, `high`, in increasing enforcement
severity. `on_inconclusive`: exactly `fail` or `warn`, explicitly required. Native repository
findings retain intrinsic severity. Non-native workspace/derived review findings require the
target's declared default. An exact `(target,rule_id)` override replaces severity/owner and
records `owner_basis="rule_policy"`; otherwise the policy owns the finding. Overrides require
reason and review reference; their existence does not prove review. Unused overrides are visible.
There are no wildcards, regex suppressions or authority-class severity rankings.

There must be 1–16 targets, at most 128 rule policies and 256 waivers. IDs, rule IDs and target
references use `[A-Za-z0-9_][A-Za-z0-9_.+-]{0,99}`. Owners add `:` to the latter character set.
Reasons are 1–512 printable ASCII characters with non-whitespace content; reports retain their
SHA256, with the original explanation available in the explicit policy. Review references are
1–256 characters from `[A-Za-z0-9_.:+/-]`, begin with an alphanumeric/underscore, contain no
`..`, and use `https://` if a colon is present. No credentials, query, fragment or whitespace
is accepted. References are never fetched. User-supplied IDs/owners/references are metadata;
do not put secrets in them. Repository IDs optionally bind the discovered identity and use
`repo_` plus 32 lowercase hex digits.

Policy-relative `root` and `manifest` resolve against the policy's directory; receipts resolve
against their declared root. Root `.` is allowed. All other policy paths use 1–512 printable
ASCII characters, exact relative POSIX components, with no empty/dot/parent components,
`.git` in any case, backslashes, colons or `*?[]`. Parent traversal is deliberately rejected:
place a multi-repository policy in the common parent. Root discovery must return the exact
requested root, preventing accidental subdirectory rebinding. All ancestor/source reads reject
symlinks and require stable regular-file observations. Existing workspace manifest v1 relative
root grammar is retained inside an explicitly named manifest; its checked no-follow ancestors
are validated before normalization.

Duplicate target IDs, identical `(kind,root,manifest,receipt)` scopes, override pairs, waiver
IDs and waiver `(target,fingerprint)` pairs are errors. Reusing one physical repository for
repository/derived/workspace subjects is allowed. Binding one observed repository ID to distinct
roots is rejected; two same-origin checkouts cannot impersonate distinct logical repositories.

Start with [the policy template](examples/governance-policy.toml), copy it to the repository
root and review it before use. A workspace target can instead name a manifest placed under the
policy directory. A derived target must name an existing receipt created by `derived capture`
or `compile --receipt-output`; governance never manufactures missing evidence.

## Typed adaptation and coverage

`governance_adapters.py` calls `integrity_overview`, `Workspace.check`, and `Checker.evaluate`.
No rendered legacy report, raw source body or verbose claim declaration crosses the seam.

- Repository findings retain native rule/code/severity and byte/provenance references. Warnings,
  unavailable changes, unknown schema/code and insufficient finding evidence are coverage gaps.
  Architecture observations retain invariant status/caveats and provider version/derivation and
  coverage summary. Configured architecture invariants require actual evidence even when
  `require_architecture=false`; true additionally requires at least one configured invariant.
  With no configured architecture, `no_architecture_rules` explicitly limits coverage.
- Each declared workspace check runs independently. Native signal and reason codes survive;
  `review_required` and `declared_disagreement` are definite review findings, never verified
  incompatibility or contradiction. `not_established`, missing/unobservable sources, malformed
  lock checks and zero checks produce independent coverage gaps. A definite missing source can
  also require review; missing evidence remains unwaivable. Repository identities qualify paths.
  Claims remain unverified; historical dependency freshness is not established.
- Derived reasons retain original artifact/path/code and effect. `review` becomes a finding;
  `uncertainty` is a coverage gap; `caveat` stays a caveat. `unchanged_observed_inputs` is recorded
  as observation, not semantic truth. Original transitive reason identities survive. Observed
  input hashes appear once under `derived.inputs.v1`; reason-specific material digests also bind
  those inputs and pinned/observed reason hashes. Top-level missing/malformed receipts become
  failed subjects, not successful checks. Governance opts into stable receipt/source reads;
  legacy defaults remain unchanged.

All declared subjects and workspace checks are attempted. Per-target evaluator exceptions are
sanitized into `target_evaluation_failed` with `evaluated=false`; per-check failures and provider
failures are independent gaps. Unknown codes/statuses/schema never become complete coverage.
Fatal policy/report/resource failures produce no partial report. Complete means no reported
coverage gaps in this declared evaluation, not all possible rule families or product compliance.

## Fingerprints and waivers

Fingerprint version 1 hashes the existing canonical JSON encoding (sorted keys, two-space indent,
ASCII escaping, finite JSON, one final newline) with SHA256. The public preimage fields are:
`fingerprint_version=1`, `target={id,kind}`, sorted actual `repositories` IDs, `rule_id`, `code`,
`entity`, `signal`, `material_sha256`, and ordered `evidence` objects. Evidence fields are
`repository_id`, repository-relative `path`, `state`, nullable `sha256`, and `basis`.

Native material hashes bind config content, dependency/invariant/claim IDs, stable structural
edge identities, provider identity/version/derivation/coverage digest and effective source
kind/lifecycle/authority. Workspace material hashes bind
check declaration, qualified claim IDs, accepted revision and source lifecycle/authority;
claim source/config bytes bind the declarations without exposing values. Derived material hashes
bind all current read observations and pinned/observed reason hashes. Absolute roots, evaluation
date, HEAD, owner, effective severity, waivers and rendered prose are excluded. Native entity IDs
can reflect grouped evidence paths/structural identities; material bytes still determine change.
This is exact evidence identity, not rename/edit lineage or cryptographic authentication.

Only definite findings with sufficiently observed material evidence receive a fingerprint and
`waiver_eligible=true`. Missing native/workspace content and dirty provider graph identity are
insufficient: fingerprint is null, coverage remains explicit, and no waiver can match. Native
provider edges additionally require a clean provider snapshot; local hashes alone do not certify
which dirty bytes were analyzed. Derived observed absence is a meaningful pin state; uncertainty
reasons still remain independently unwaivable.

A waiver matches exactly one `(target,fingerprint)`, with declared owner/reason/review and expiry.
`expires_on` is a quoted `YYYY-MM-DD` calendar date, valid **through** that UTC date. The next UTC
date is expired. One UTC date is captured per invocation; `--as-of` provides explicit test/replay
time. Neither machine time nor declared ownership is an approval trust anchor.

Waiver statuses: `applied`, `expired`, `unused`, `ambiguous`. Stale evidence and cross-target
fingerprints are unused; expired takes precedence even if unused. Duplicate policy pairs fail
parsing rather than choosing a winner. Unused/expired/ambiguous waivers remain visible but do
not themselves block. Nothing can waive uncertainty, an exception, a skipped required check,
policy parsing or report failure. Waiving a definite finding cannot remove a separate gap.

## Report v1 and metrics

`governance_report_schema_version=1` is separate from all predecessor schemas. Exact root keys:
`policy`, `evaluation`, `observations`, `waivers`, `gate`, `metrics`, `comparison`, `limitations`,
and the schema version. The complete [golden report](../tests/fixtures/governance-report-v1.json)
is executable contract evidence. All keys are required, including nulls. Public projectors
allowlist fields; no implicit full dataclass or legacy workspace report export occurs.

- `policy`: `id`, `owner`, raw-byte `sha256`, `fail_on`, `on_inconclusive`, `rule_policies`.
  Each override includes target/rule/severity/owner, reason hash, review reference and `used`.
- `evaluation`: `as_of_utc_date`, sorted `subjects`. Each subject has `id`, `kind`, qualified
  `repositories`, nullable `config_sha256` and `review_severity`, boolean `require_architecture`,
  `scope`, `evaluated`, `complete`, `limitations`.
  Repository descriptors contain alias (nullable), ID, identity basis, HEAD and nullable dirty.
  Repository scope has kind, change scope, resolved base/target, and architecture status,
  invariant count and nullable provider summary. Workspace scope has kind/check count; its
  config hash is the manifest digest. Derived scope has kind, receipt, artifact ID/path,
  provenance scope and observed receipt count. Failed scopes contain kind only.
- `observations`: sorted `(target,rule_id,code,entity,fingerprint)` records for all effects.
  Each includes these identities, `signal`, `effect` (`finding`, `uncertainty`, `caveat`,
  `observation`), intrinsic/effective nullable severity, owner and `owner_basis`, evidence,
  material digest, nullable pinned/observed digests, related claim/invariant/dependency/artifact
  IDs, reason codes, nullable fingerprint, waiver eligibility/ID and blocking flag.
  A finding's effective severity is required; other effects cannot block or be waived.
- `waivers`: sorted ID/target/fingerprint/status/owner/reason hash/review/expiration records.
- `gate`: `outcome`, independent `has_blocking_findings` and `has_incomplete_coverage`, `exit_code`.
- `limitations`: explicit declared-scope, semantic, authentication and sequential-snapshot limits.

Metrics derive only from these records: requested/evaluated/incomplete target counts; finding,
blocking, waived/unwaived and coverage-gap counts; findings by effective severity, rule and target;
number of declared derived targets requiring review; workspace claim-disagreement finding count.
`targets_evaluated` means an evaluator returned, even if coverage is incomplete. Derived count
is per target, not a transitive artifact census. Gaps count distinct normalized records, not an
estimate of omitted work. No persistent monitoring, global contradiction count or hosted dashboard
is delivered. Strict baseline validation recomputes counters and gate factors; booleans cannot
masquerade as integer counters.

## Comparisons

`--compare-to` is explicit local JSON, at most 8 MiB, stable no-follow read, duplicate keys and
nonfinite values rejected. Malformed v1/schema types/fields/counters fail input validation (6).
An unsupported integer report version is `incomparable: unsupported_schema`; its data is ignored.

Comparability requires schema v1, identical policy ID and raw policy hash, identical sorted target
IDs/kinds/observed repository IDs, same repository change-scope mode, same derived receipt and
same workspace manifest hash. A failed/unobserved scope is incomparable. Changed config bytes
within a repository are current evidence, not automatically incompatible scope. Policy whitespace
or waiver edits change the policy hash. Comparisons intentionally refuse to bridge those changes.

`comparison.status`: `not_requested`, `incomparable` (reason codes), or `comparable` with
`metric_deltas` (current minus prior), sorted fingerprint `added`, `removed`, `persisting` arrays.
Null/unwaivable fingerprints do not acquire invented continuity. Date differences can change
waiver/gate counts; fingerprints exclude dates. Prior reports are unauthenticated advisory data
and **never** change current finding decisions, waivers, coverage or exit status.

## Limits and errors

Each inventory has 64 MiB/4,096-source ceilings. Each workspace retains predecessor separate
64 MiB explicit and inventory budgets; each derived DAG retains 128 receipts/16 depth and
64 MiB/4,096 reads plus independently bounded inventory. At most 16 targets bound aggregate
work even with repeated roots; observations are sequential, without shared global caching.
Existing config/Git enumeration/provider limits still apply; this is not a global process-memory
or CPU sandbox. Governance normalization caps 4,096 observations and 16,384 evidence references
across targets; per-subject collectors enforce those caps before accumulating repeated output.
Exhaustion refuses the complete report with exit 6, never truncating evidence into a pass.

JSON/text serialization is capped at 8 MiB, including text prefix. Incremental encoder preflight
runs before the final string allocation. Paths, metadata and record counts are independently
bounded. Legacy claim literals are never projected, preventing their repeated serialization.
Reports contain no source body, raw claim value, task text, OS exception prose or absolute roots.
Content/reason hashes can still disclose equality and permit guessing low-entropy input; this
is metadata, not a secrecy mechanism. Review declared policy metadata before sharing reports.

| Exit | Meaning |
| --- | --- |
| 0 | Allowed; explicit `warn` can yield `allow_with_incomplete`, visibly incomplete |
| 8 | At least one definite unwaived threshold finding; dominates simultaneous gaps |
| 9 | Fail-on-incomplete coverage with no definite blocker |
| 2 | CLI usage, option/date/diff assignment error |
| 4 | Explicit output safety/publication failure |
| 6 | Policy/baseline/report input or resource-limit error; no partial report |

Governance per-subject discovery/config/provider failures are report gaps rather than early exits
3/6/7, so other findings survive. This is an intentional orchestration deviation from individual
command errors. Legacy commands preserve exits 2/3/4/6/7 and ordinary non-gating success behavior.
No acceptance of Phase 10 or earlier phases is implied by governance self-tests.
