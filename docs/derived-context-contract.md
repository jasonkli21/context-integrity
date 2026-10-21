# Derived context receipt and result v1

Phase 9 records **declared observations**, not authenticated provenance, semantic truth,
exhaustive source closure, or authority. Summaries, handoffs and compiler packages remain
rebuildable derived state. Claims retain `unverified` validity. Checks never refresh pins,
rewrite artifacts, execute their contents or query a model/provider/network/database.

## Commands and lifecycle

From the repository root, with an existing `docs/handoff.md`:

```bash
uv run context-integrity derived capture docs/handoff.md . \
  --id handoff-a --kind handoff --derivation model --producer agent \
  --depends-on AGENTS.md --depends-on docs/prd.md \
  --receipt-output docs/handoff.provenance.json
uv run context-integrity derived check docs/handoff.provenance.json . --format json
```

`--depends-on` and `--upstream-receipt` repeat. Explicit dependencies can be code files
outside the documentation inventory. `--producer-version` is optional. Kind defaults to
`summary`, derivation to `manual`, producer to `user`, ID to `derived-context`; IDs must be
unique within a receipt graph, so distinct artifacts should use explicit IDs.
Upstream receipts must currently yield `unchanged_observed_inputs` at capture time;
uncertain or stale upstream provenance is refused rather than adopted. Capture with no
sources/parents is allowed but explicitly incomplete and checks inconclusive.

For an existing configured contract:

```bash
uv run context-integrity compile work . --format json --output docs/saved-context.json \
  --receipt-output docs/saved-context.provenance.json
```

The additive option requires saved JSON. Compiled context stays schema v3, including its
existing task representation; the **receipt** contains only the task digest. The receipt
uses typed selected decisions, checks their actual local bytes against their compile-time
hashes and preserves provider origin/version/derivation. It does not parse rendered JSON.
All selected inventory and provider candidates are pinned. Contract completeness is separate
from provenance completeness. Compiler incompleteness and observed inventory/provider gaps are recorded
conservatively. Provider context always yields `provider_not_revalidated` on recheck: this phase
does not replay provider queries or compare present relevance/coverage.

`derived check` supports `--format text|json` and optional `--output`. All new explicit
outputs must be inside the root, have existing non-symlink parents, use non-inventory paths
(for example `.json`), and not collide with any artifact, config, dependency or receipt input.
This prevents output itself from changing an upstream compiler selection universe. Relative
output paths are relative to the discovered repository root; absolute paths inside that root
are accepted as output destinations and serialized relatively. Inputs are exact relative paths.

Outputs never replace existing files. Choose a new path when deliberately recapturing;
updating downstream receipts is explicit as well. Artifact removal yields a review result;
no expiration/deletion/regeneration is automated. Receipts are optional, ordinary derived
sidecars; there is no registry or hidden state directory.

## Exact receipt schema

All keys below are required (including nullable fields), unknown keys and duplicate JSON
object keys are rejected at every level. Arrays are sorted by path or provider ID on output.
Constructors enforce the same invariants as deserialization.
A concrete complete example is [the receipt golden](../tests/fixtures/derived-receipt-v1.json). Integers reject booleans.

| Object | Fields |
| --- | --- |
| Root | `derived_receipt_schema_version` = integer 1; `artifact`; `repository`; `provenance_scope`; nullable `config_sha256`; `dependencies`; `upstream_receipts`; `provider_context`; nullable `compilation`; boolean `known_incomplete` |
| `artifact` | `id`, `kind` (`summary`, `handoff`, `compiled_context`), `path`, `content_sha256`, `derivation` |
| `derivation` | `kind` (`manual`, `tool`, `model`), `producer`, nullable `version` |
| `repository` | `id`, nullable `git_head`, nullable boolean `git_dirty` |
| Each source dependency | `path`, `source_id`, `content_sha256`, nullable `observed_lifecycle`, nullable `observed_authority`, nullable `metadata_sha256`, `observation_basis`, nullable `provider_id`, nullable `provider_version`, nullable `derivation` |
| Each upstream receipt | `path`, `receipt_sha256`, `artifact_id`, `artifact_path`, `artifact_sha256` |
| Each provider | `id`, `version`, `derivation`, integer `contract_version` = 1, integer `provider_schema_version` = 1, nullable `git_head`, nullable boolean `git_dirty`, `coverage_sha256`, `context_sha256`, boolean `incomplete` |
| `compilation` | `contract_id`, `contract_sha256`, `policies_sha256`, `selection_sha256`, nullable `task_sha256`, nullable positive integer `budget_bytes`, `status` (`complete`, `incomplete`), `integrity_status` (`evaluated`, `not_evaluated`), array of token `warnings`, `compiler_version` |

`provenance_scope` is `declared` for manual capture or `compiler_selection` with a compilation
object and a tool-derived `compiled_context` artifact. `known_incomplete` must be true when
the compiler status is incomplete or a provider declares incompleteness. It cannot suppress
the unconditional provider caveat or the empty-provenance check.

Source observation basis is `inventory`, `explicit_file`, or `provider`. Inventory pins have
non-null lifecycle/authority and metadata digests; explicit file pins have null metadata and
no invented classification. Provider pins require matching provider identity/version and
non-null derivation/lifecycle/authority, with null inventory metadata digest. Lifecycle and
authority values use the existing domain enums; they are not a universal authority ranking.

Duplicate paths, provider IDs, upstream artifact IDs/paths and conflicting source/parent
artifact digests fail closed. Self-artifact dependencies and direct own-receipt dependencies
are forbidden. Graph traversal additionally rejects cycles, repeated artifact identities
across different receipts, repository mismatches and inconsistent upstream identity/hash links.

## Identity, hashing and comparisons

All digests are SHA256 of actual raw bytes, expressed as 64 lowercase hex characters.
Upstream receipt digests pin exact serialized bytes (even whitespace changes are material).
JSON projection uses sorted keys, two-space indentation, ASCII escaping, finite values and
one trailing newline. Internal structured fingerprints use that same canonical encoding:

- Source metadata hashes kind, effective authority/lifecycle, explicit source metadata and
  relevant supersession edges (endpoint paths, reason and config digest). HEAD is excluded.
- The compiler contract hash covers the complete typed contract, including priorities,
  authority selectors and configured budget. Policies hash the sorted policies referenced
  by its rules, including built-in policy versions.
- Selection context hashes a path-keyed inventory of source content/metadata hashes. This
  conservative fingerprint detects newly eligible documents and other candidate changes;
  it can require review even for an unselected changed document. It does not replay selection.
- Provider coverage/context hashes cover validated typed coverage and state respectively,
  including snapshot, ranker, acquisition settings and query. Only the digests are persisted;
  the task text and arbitrary diagnostic/source prose are never copied into the receipt.
- Task digest hashes UTF-8 task bytes, distinguishing null task from the empty string.
  Effective budget is pinned separately. Compiler implementation version is recorded.

Repository/source identity reuses existing discovery and `make_source_id`: source IDs are
`src_` plus the first 32 hex characters of SHA256 of `repository_id + NUL + path`.
Repository identity is `repo_` plus 32 hash characters of the normalized local origin, or
existing local-root fallback. Remote identity normalization excludes credentials. Equivalent
checkouts with the same origin share identity; repositories without an origin have existing
location-dependent identity and receipts are not portable between them. Identity is not
cryptographic repository authentication. Compiler artifact IDs use `compiled-` plus 24 hex
characters of SHA256 of the relative artifact path. Manual IDs are human declarations.

HEAD/dirty metadata explain the capture snapshot but do not themselves invalidate it.
Raw current bytes detect staged and unstaged edits under the same HEAD. Reverting to the
same bytes restores equality. Renames remain missing old paths, with no similarity inference.
Config absence is pinned as null, distinctly from the hash of a present empty file. Invalid
current config prevents effective metadata evaluation, while a provable config byte change
still requires review. Source lifecycle/authority/supersession changes are material even when
document bytes match. Sequential observations do not provide a repository-wide atomic snapshot.

## Result schema and status matrix

The explicit result projector emits `derived_result_schema_version` = 1, `artifact_id`,
`artifact_path`, `provenance_scope`, `status`, `receipts_observed`, and sorted, deduplicated
`reasons`. `receipts_observed` counts successfully decoded, identity-accepted receipts.
Each reason contains `code`, `path`, `artifact_id`, `effect`, nullable
`pinned_sha256` and nullable `observed_sha256`. Paths and upstream artifact identities survive
transitive propagation. A diamond is memoized rather than evaluated repeatedly.

| Status | Meaning |
| --- | --- |
| `unchanged_observed_inputs` | Every required declared pin was observed equal, without material uncertainty. No semantic correctness, exhaustive provenance or authority claim. |
| `review_required` | At least one definite material change or missing required input. Simultaneous observation gaps are retained. |
| `inconclusive` | No definite change was established, but required evidence could not be established or capture/provider provenance is incomplete. |

Precedence is review > uncertainty > equality. `effect` is `review`, `uncertainty` or
`caveat`. Manual source-list incompleteness as a general possibility is a caveat; an explicit
known gap, empty list without parents, or provider context is material uncertainty.

Stable reason codes:

- For each of `artifact`, `source`, `config`, `upstream_receipt`: suffix `_changed` or
  `_missing` requires review; `_unobservable` or `_budget_exceeded` is uncertainty.
  Missing config equals an absent config pin; unreadable/unsafe config never equals absence.
- `source_metadata_changed`, `contract_changed`, `contract_missing`, `policies_changed`,
  `selection_context_changed`, `compiler_version_changed`: review.
- `source_metadata_unobservable`, `compilation_context_unobservable`,
  `provenance_incomplete`, `provider_not_revalidated`, `upstream_receipt_untrusted`,
  `upstream_inconclusive`: uncertainty.
- `upstream_review_required`: review, with original upstream reasons retained.
- `declared_inputs_not_semantic_validation`, `selection_not_replayed`: caveats.

A missing/tampered upstream receipt is visible and its new pins are never adopted. If its
bytes still match the declared receipt pin but parsing, repository/identity checks, graph
limits or cycle checks fail, `upstream_receipt_untrusted` is inconclusive. Top-level malformed,
unsupported, missing, unsafe or wrong-repository receipts are input errors (exit 6).

Ordinary check outcomes exit 0. Repository/discovery and capture inventory-budget failures
exit 3; explicit output failures exit 4; config/capture/receipt input errors exit 6. Existing
provider failures remain exit 7. Invalid CLI flag combinations exit 2. No CI gating is implied.

## Bounds and trust boundary

- Artifact/source input: at most 5 MiB each. Receipt: at most 1 MiB.
- At most 256 source pins and 16 upstream pins per receipt, 4 providers, 256 warning tokens;
  graph maximum 128 receipt observations (including rejected loads) and 16 levels including the root.
- Graph observation reservation budget: 64 MiB and 4,096 distinct read attempts, shared
  across the DAG. Failed reads conservatively reserve their requested allowance. Repeated
  reads of the same path/limit are memoized; only receipt bodies are retained in memory.
- Inventory observation independently caps 4,096 candidates and 64 MiB for new workflows.
  Current metadata failure yields uncertainty on check, while available byte evidence is
  still evaluated. Existing Git enumeration/discovery bounds and per-config parsing apply;
  this is not a global bound on Git listing memory or existing compiler search work.
- IDs/version tokens: 1–100 ASCII identifier characters (`[A-Za-z0-9_][A-Za-z0-9_.+-]*`).
  Provider source derivation: 1–200 restricted token/colon characters. Paths: 1–512 printable
  ASCII characters, exact POSIX relative components; reject traversal, dot/empty components,
  drive/colon/backslash/glob ambiguity, control/lossy characters and `.git` in any casing.
  Unicode filenames are deliberately unsupported by receipt v1.
- Reads use existing bounded, descriptor-relative no-follow acquisition for every component;
  symlinks, non-regular files, unreadable and oversized inputs cannot produce equality.
  Receipt JSON is byte-bounded before decoding; recursion/malformed values fail sanitized.
  Fixed schema nesting rejects opaque arrays/blobs and extra keys.

New files use exclusive descriptor-relative publication with mode 0600. All outputs are
prepared and flushed first; no existing target (including symlinks) is replaced. Ordinary
publication failure rolls back only inodes created by this operation. Rollback failure is
reported explicitly as possible retained partial outputs. Two independent POSIX names cannot
be committed atomically: process/power loss can leave a prepared temporary file or an orphaned
artifact/receipt. Inspect and deliberately remove or recapture such files; no silent recovery
or auto-refresh is attempted. Observed directory descriptors prevent following swapped links,
but concurrent repository mutation is not a supported atomic-snapshot/transaction guarantee.

Receipts are locally editable, unauthenticated declarations. Someone who rewrites both pins
and content can forge equality. A matching digest establishes byte identity relative to those
pins only. Output contains no bodies, raw task text, absolute roots, timestamps, raw stderr,
credentials or provider raw JSON. Existing compiled JSON v3 is unchanged. Config v1–v8,
inventory/claims/contracts projections and integrity JSON v2 retain their existing versions.
Semantic verification, provider replay, cross-repository chains, persistence, watchers,
LLMs, automatic fixes and enforcement remain out of scope.
