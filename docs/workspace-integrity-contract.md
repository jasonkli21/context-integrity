# Workspace integrity v1

Phase 10 observes **explicit local alignments** across independently identified repositories.
A matching revision is not API compatibility, a policy winner, semantic truth, consumer code
conformance or product-wide compliance. Claims remain `unverified`. No network, provider,
model, database, fetch, auto-refresh or repository mutation is part of these commands.

## Commands and valid example

```bash
uv run context-integrity workspace check workspace.context-integrity.toml --format json
uv run context-integrity workspace compile workspace.context-integrity.toml \
  --task "Update API consumer" --format json --output workspace-context.json
```

The manifest is explicit, with no ambient workspace discovery. Outputs default to stdout.
`compile` requires `--task` (empty text is supported) and at least one context target.
Provider options are deliberately unavailable. Find actual repository IDs using `scan ROOT
--format json`; declare those exact IDs before checking. The following is a complete valid
manifest for repositories with the illustrated IDs; IDs are declarations checked against
actual discovery, not arbitrary labels. The executable synthetic fixture in
[`test_workspace.py`](../tests/test_workspace.py) creates independent Git roots with matching
real IDs, locks, claims and contracts. The checked-in [manifest fixture](../tests/fixtures/workspace-v1.toml),
[lock golden](../tests/fixtures/contract-lock-v1.json),
[check golden](../tests/fixtures/workspace-check-v1.json), and
[context golden](../tests/fixtures/workspace-context-v1.json) are complete valid JSON examples
from that fixture (only Git HEADs are replaced with a fixed valid hash in result goldens).

```toml
workspace_schema_version = 1

[[repositories]]
alias = "api"
root = "../api"
repository_id = "repo_0123456789abcdef0123456789abcdef"

[[repositories]]
alias = "web"
root = "../web"
repository_id = "repo_fedcba9876543210fedcba9876543210"

[[checks]]
id = "public-api"
kind = "contract_pin"
producer_repo = "api"
producer_path = "spec/openapi.json"
consumer_repo = "web"
consumer_path = "contracts/public-api.lock.json"

[[checks]]
id = "shared-schema"
kind = "mirror_bytes"
left_repo = "api"
left_path = "schemas/message.json"
right_repo = "web"
right_path = "schemas/message.json"

[[checks]]
id = "region"
kind = "claim_match"
left_repo = "api"
left_claim_id = "data_region"
right_repo = "web"
right_claim_id = "data_region"

[[context_targets]]
repo = "api"
contract_id = "service-work"
budget_bytes = 12000

[[context_targets]]
repo = "web"
contract_id = "service-work"
budget_bytes = 12000
```

An example consumer-owned `contracts/public-api.lock.json`, accepting an empty producer file
(SHA256 below is the digest of zero bytes):

```json
{
  "contract_lock_schema_version": 1,
  "producer_repository_id": "repo_0123456789abcdef0123456789abcdef",
  "producer_path": "spec/openapi.json",
  "accepted_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
}
```

Each repository independently configures any claims/contracts it uses. A complete minimal
`.context-integrity.toml` for the example claim/context target is:

```toml
schema_version = 6
[[source_metadata]]
path = "docs/architecture.md"
lifecycle = "active"
reason = "Current product policy"
[[claims]]
id = "data_region"
claim_type = "policy"
subject = "product"
predicate = "stores_in"
scope = "customer_data"
value = "us"
depends_on = ["docs/architecture.md"]
[[context_contracts]]
id = "service-work"
task_class = "implementation"
description = "Required architecture"
[[context_contracts.rules]]
id = "architecture"
mode = "required"
paths = ["docs/architecture.md"]
```

## Exact declaration grammar

Unknown keys and wrong primitive types fail closed; booleans are never integers. TOML
rejects duplicate keys. Lock JSON rejects duplicate keys at every level, malformed encoding,
unknown fields, non-object roots and unsupported versions. No interpretation of arbitrary
prose occurs. Manifest and lock versions are separate from repository config v1–v8.

| Object | Required fields | Optional fields / bounds |
| --- | --- | --- |
| Manifest | integer `workspace_schema_version=1`, `repositories` | `checks=[]`, `context_targets=[]` |
| Repository | `alias`, `root`, `repository_id` | 2–8 entries |
| `contract_pin` check | `id`, `kind="contract_pin"`, `producer_repo`, `producer_path`, `consumer_repo`, `consumer_path` | No other fields |
| `mirror_bytes` check | `id`, `kind="mirror_bytes"`, `left_repo`, `left_path`, `right_repo`, `right_path` | No other fields |
| `claim_match` check | `id`, `kind="claim_match"`, `left_repo`, `left_claim_id`, `right_repo`, `right_claim_id` | No other fields |
| Context target | `repo`, `contract_id`, integer `budget_bytes` | Positive; each and summed budgets ≤64 MiB |
| Consumer lock | integer `contract_lock_schema_version=1`, `producer_repository_id`, `producer_path`, `accepted_sha256` | All required; ≤16 KiB |

Tokens (aliases, check IDs, referenced claim/contract IDs) match
`[A-Za-z0-9_][A-Za-z0-9_.+-]{0,99}`. Existing repository declarations retain their stricter
claim/contract identifier rules. Repo IDs match `repo_[0-9a-f]{32}`; digests match
`[0-9a-f]{64}`. Duplicate aliases, expected IDs, check IDs and `(repo,contract_id)` targets
are rejected. Every reference names a declared alias; a check must connect different aliases.
At most 128 checks, 16 targets and 256 distinct declared `(alias, reference)` check endpoints
are accepted (claim IDs count toward that endpoint bound).

Source/lock paths use exact POSIX relative components, 1–512 printable ASCII characters.
Empty/dot/traversal components, absolute paths, backslashes, colons, `*?[]`, control/Unicode
characters and `.git` in any casing are rejected. No normalization repairs malformed source
identities. Claim dependency and inventoried paths entering workspace results obey the same
narrow grammar; unsafe inventory paths cause an input error.

Root strings are local configuration only: 1–512 printable ASCII characters, ≤32 components,
relative to the manifest parent. `.` and `..` components are allowed for explicit sibling
locations; empty components, absolute/URL/UNC roots, `.git`, backslashes, colons and `*?[]`
are forbidden. Every ancestor is opened descriptor-relative with no-follow, including before
processing `..`. Manifest ancestors and file must also be safe. Explicit CLI manifest/output
locations may be absolute; canonical host paths must be used instead of symlink aliases such
as `/tmp` on macOS (use `/private/tmp`). Roots never appear in results.

Discovery must return the exact declared boundary, not an enclosing Git repository. Duplicate
or nested roots and duplicate observed IDs are rejected. Two checkouts with the same normalized
origin cannot represent distinct workspace repositories. Origin IDs are observations, not
cryptographic authentication. No-origin/filesystem roots use `local_fallback`, with
`local_identity_nonportable` disclosed: identity changes with location. Unknown Git metadata
is retained; it is not silently replaced with clean metadata.

## Rule semantics, status and coverage

Every finding has a typed kind and `workspace.KIND.v1` rule ID, check ID, signal, evaluation
status, structured reason codes, source/claim observations and nullable accepted digest.
Source observations contain `(repo_alias,repository_id,path)`, scoped source ID, read state,
raw-byte SHA256, and nullable observed lifecycle/authority. Claim observations retain the
qualified claim ID, explicit declaration fields (including original scope/value), `unverified`
validity, extraction provenance/revision, qualified provenance/dependency observations and
local uncertainty codes. Each `claim_match` finding also reports
`claim_dependency_freshness: not_established`; declaration equality and historical freshness
remain separate dimensions. Coverage lists `claim_dependency_freshness_not_established` and
`claim_literals_may_be_sensitive` when claim checks are present. These explicit declarations are
structured metadata, not source-body bundles. Warning/error prose, classification prose and
remote URLs are not copied.

| Rule | Aligned evidence | Review evidence | Inconclusive |
| --- | --- | --- | --- |
| `contract_pin` | Observed producer hash equals consumer-accepted hash | `producer_contract_revision_changed`; deterministic missing input | Unsafe/unreadable/oversized/unstable/budget-limited input |
| `mirror_bytes` | Both observed raw-byte hashes equal | `mirror_bytes_diverged`; deterministic missing input | Unsafe/unreadable/oversized/unstable/budget-limited input |
| `claim_match` | Comparable declarations exactly equal | Comparable values differ: `declared_claim_disagreement` | Different type/subject/predicate/scope; missing claim, unavailable/changed dependency, ineligible lifecycle or inventory gaps |

Malformed **observable** lock JSON or producer ID/path mismatch is an input error (exit 6),
even if the producer is missing. Unobservable locks are findings with uncertainty. The lock
hash and producer hash remain independently observable; the accepted digest is never advanced.
Matching locks retain `consumer_implementation_not_verified`. Mirrors retain
`byte_comparison_not_semantic_validation`.

Claim comparison uses exact Python string equality, with no case, whitespace, Unicode or
semantic normalization. IDs only locate declarations. Config source cannot manage its own
lifecycle: existing eligibility accepts `unknown` or `active`; other lifecycle states on
provenance/dependencies yield `claim_provenance_not_active`. Repository-discovery and
inventory-acquisition warnings conservatively prevent positive claim alignment. Explicit file
observation warnings belong to their finding and do not change a later inventory's coverage.
Unresolved dependency revisions yield
`claim_evidence_incomplete`. Changed, staged, unstaged, untracked or unknown-status dependencies
yield `claim_dependency_changed_or_unknown`, even if both claim strings are identical.
Generated-derivative dependencies yield `claim_dependency_revalidation_unavailable`; workspace
checks do not replay Phase 9 receipts. No committed historical dependency pin exists in explicit
claims, so `dependency_history_not_pinned` remains an unconditional caveat, alongside
`claims_unverified`. Clean current declarations can agree; this is not a freshness claim.

Source states: `observed`, `missing`, `unobservable`, `too_large`, `budget_exceeded`.
Source uncertainty reasons use `ALIAS:source_STATE`; each observation carries full ownership.
Other stable codes are `accepted_revision_observed`, `byte_equality_observed`,
`declarations_agree`, `not_comparable`, `claim_missing`, `claim_inventory_unavailable`,
`claim_inventory_incomplete`, and the codes described above.

A definite missing input wins over simultaneous source uncertainty, retaining both reasons.
Claims are compared for disagreement only with sufficient observable provenance. Per-check
`evaluation_status` is `inconclusive` for `not_established`, otherwise `evaluated` (an evaluated
missing-input finding may still retain an independently unobservable input).
Aggregate precedence is `review_required` > `inconclusive` > `aligned_observed`.
No checks yields `inconclusive` and `no_checks_declared`, never global compliance.
Repository warning codes are retained independently of check signals. File equality can be
observed without complete Git metadata; claims needing dependency status cannot.

## Context composition and JSON v1

The existing configured `resolve_contract` and `compile_context` run once per target, using
that repository's policy and explicit budget. Budgets are neither pooled nor shifted.
Workspace compilation deliberately follows existing CLI budget override semantics. No provider
is queried; a provider-backed requirement can remain contract-incomplete without installing
Context Engine. Source IDs, decisions, dependencies and equal-tier alternatives stay qualified.

`workspace_check_schema_version=1` fields are `manifest_sha256`, sorted `repositories`, `status`,
`coverage`, `findings`. Coverage contains `checks_declared`, `checks_evaluated`, and limitations
`declared_checks_only`, `sequential_non_atomic_observations`, `no_semantic_validation`, plus
`claim_dependency_freshness_not_established` and `claim_literals_may_be_sensitive` when claim
checks are present, and `no_checks_declared` when appropriate. Claim findings include the
structured `claim_dependency_freshness` value. Repository descriptors contain alias, repository
ID, identity basis, HEAD/dirty, sorted warning codes and limitations; no local name/root/remote.

`workspace_context_schema_version=1` fields are `manifest_sha256`, UTF-8 `task_sha256`,
`repositories`, `selection_complete`, `checks_status`, boolean `review_required`, `status`,
`targets`, `findings`, `coverage`, `limitations`. `status` is `incomplete` if any selection is
incomplete; otherwise it equals `checks_status`. The independent flags preserve review and
uncertainty regardless of selection outcome. Each target contains qualified repo identity,
contract ID, requested budget, effective/configured/used budget, config hash, effective contract
fingerprint, used authority policy IDs/versions/tiers, selected sources, all source/rule
decisions, selected dependencies/revisions, validation codes/qualified paths, integrity status,
warning codes and inventory coverage. Contract policy is applied locally; contract fingerprint
includes selectors, priorities, authority selectors and configured budget. Warning-bearing
contract-complete selections still disclose coverage gaps. Unavailable inventory produces an
incomplete target with `inventory_unavailable`, without inventing a contract or selected files.

Projectors allowlist every field. Existing compiled JSON v3 is never embedded and retains its
raw task representation for direct callers. Workspace task text, source bodies, absolute roots,
timestamps, raw provider data/stderr and credential remotes are absent. Explicit claim metadata
is retained verbatim; claim values can contain secrets or other sensitive strings. Review reports
before sharing them or passing them to another agent. The CLI does not redact claim metadata.
JSON uses sorted keys,
2-space indentation, ASCII escaping, finite values and one trailing newline. Repositories,
checks and targets sort by alias, check ID and `(alias,contract_id)` respectively. Changing
manifest declaration ordering changes its raw digest but not the sorted observations.
Text adds a brief summary to the same complete escaped JSON evidence, ensuring lossless parity.

## Acquisition, bounds, publication and exits

- Manifest ≤256 KiB; lock ≤16 KiB; explicit source ≤5 MiB; UTF-8 task ≤64 KiB.
- Fully rendered JSON or text reports are limited to 8 MiB, including the text summary. A bounded
  preflight rejects oversized reports with `workspace_report_limit_exceeded` (exit 6) before
  stdout output or file publication; reports are never truncated.
- Explicit observation budget: 64 MiB and 4,096 distinct attempts. Cache keys include observed
  repository ID, path and read limit. Only lock bodies are retained (≤16 KiB each); source
  bodies are hashed and discarded. Failures conservatively reserve the requested allowance.
- A separate shared inventory budget caps participating inventories together at 64 MiB and
  4,096 candidates/attempts, including failed/skipped reads. Exhaustion retains all checks and
  makes affected claims/targets unavailable. Cached inventories are reused per repository.
  Config loading/consistency reads retain their existing bounded limits; Git enumeration and
  compiler feasibility search retain their existing bounds, rather than a new global CPU bound.
- Reads traverse every root ancestor and source component using directory descriptors and
  no-follow. Optional stable-read verification compares open-file and final named-file
  device/inode/size/mtime/ctime after hashing; changed reads are refused. Workspace inventory,
  manifest, lock and explicit source observations use it. Existing command stable-read defaults
  remain unchanged; full-root ancestor no-follow is shared safety hardening.

These are sequential observations, not an atomic product snapshot. There is no end-of-command
revalidation, checkout-instance identity or cross-root transaction. Concurrent ancestor/repository
replacement is not an atomic snapshot guarantee; observed descriptors do not follow swapped links.
Content hashes identify staged/unstaged working-tree bytes under unchanged HEAD; HEAD movement
alone is not a divergence rule.

An explicit output must have existing safe parents, be new/exclusive, and be **outside every
participating repository root** (stricter than merely outside inventory candidates). Relative
outputs use cwd; parents are not created. Publication reuses descriptor-relative mode-0600
prepare/fsync/exclusive-link with cleanup and rollback. Existing files, symlinks, locks and
Git metadata are never replaced. Ordinary failures report whether partial outputs or temporary
files may remain. Process/power loss may leave an orphan; there is no crash-atomic filesystem
transaction or hidden recovery/cache. Parent-plus-filename relative to `/` must fit the shared
512-character safe publication grammar.

Exit 0 includes findings/incomplete selection; 2 is usage/unsupported options; 3 is discovery,
identity or boundary failure; 4 is explicit output failure; 6 is manifest/config/lock/contract
input failure. Workspace does not invoke a provider and therefore does not manufacture exit 7.
Diagnostics contain fixed codes and, once known, validated alias/ID/relative path ownership;
never OS/parser exception prose. Existing commands retain their conventions.

The consumer lock is a narrow cross-repository acceptance receipt owned by the consumer.
It is unauthenticated and editable, does not prove use by consumer code, and is not a generic
Phase 9 derived receipt. Workspace context indexes do not extend receipt v1 across roots or
prove transitive generated-artifact freshness. Semantic compatibility, authority ranking,
cross-repo structural graphs and durable workspace receipt DAGs remain deferred. Phase 11 adds
separate explicit CI enforcement in the [governance contract](governance-contract.md); workspace
commands and schemas retain their original non-gating behavior.
