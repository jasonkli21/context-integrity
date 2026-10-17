# Evidence contract v1

Context Engine supplies descriptive code relevance. Context Integrity owns role mapping,
authority, lifecycle, contracts, exclusions, and selection. Neither project shares storage
or imports the other's implementation. The implemented Python boundary is
`EvidenceProvider.context_candidates(EvidenceContextRequest) -> EvidenceContextBatch` in
`src/context_integrity/evidence.py`. Another provider may implement that method without
changing the compiler. Phase 8 adds the separate `RelationEvidenceProvider.relations` protocol
in `src/context_integrity/relations.py`; impact methods remain future work. See
[architectural integrity contract](architecture-integrity-contract.md) for graph evidence and policy.

## Request and result

Requests carry a runtime-only repository root, the observed `RepositoryRef`, nonblank task,
acquisition byte budget, and optional change range. Results carry a provider descriptor
(identity, executable version, evidence contract version, capabilities and adapter derivation),
a root-free repository snapshot, query/ranker metadata, coverage, warnings, and body-free
`CompilerCandidate`s. Version 1 supports `context_candidates`, optional `change_context`, and the independent
`relations` capability. Relation-only providers need not implement context acquisition.

The snapshot records repository ID, HEAD/dirty metadata, external schema and command.
Every candidate identifies its origin, provider/version, deterministic repository/path source
ID, content SHA-256, size, provider rank, score components, sorted reason codes, matched entity
qualified names/kinds/byte spans, omitted entity count and graph/change distances. Index-local
file/symbol IDs are discarded. Matched entities describe syntax, not compiler-grade binding.

The Context Integrity adapter maps `source`, `test`, `schema`, `migration` to `source_code`,
`test`, `schema`, `migration`, with `executable_truth` authority and `unknown` lifecycle.
Other roles are skipped. A normalized `SourceRecord` is an evidence adapter payload;
`manifest.sources` remains the ordinary context inventory. Clean Git metadata permits
`tracked_clean`; otherwise candidate Git status is `unknown`.

Every provider must satisfy the same normalized domain invariants: relevance scores, distances,
omission counts, identifiers and sorted collections are typed and bounded; matched entity byte
spans fit within candidate size; provenance locations are repository-relative; derivation is a
stable identifier; and classification must agree with the normalized role/authority/lifecycle.
Provider classification basis text and source metadata are not accepted. Provider state uses
the supported capability, change, fallback and warning vocabulary. These checks live at the
generic batch/model boundary, so replacements do not rely on the Context Engine adapter for
privacy or determinism.

## Context Engine transport

The adapter executes these argv lists with no shell, network, installation or database access:

```text
ctx --version
ctx context ROOT --task TASK --budget BYTES --format json [--change BASE..HEAD]
ctx graph ROOT --format json
```

An executable override is runtime-only. The version response must be `ctx VERSION` with a
bounded identifier. The JSON envelope must have integer `schema_version = 1` and
`command = "context"`. Required consumed fields have strict types; duplicate JSON keys,
nonfinite values, malformed metadata and inconsistent byte accounting fail closed. Unknown
external fields are ignored rather than copied into stable output.

Each invocation has a 30-second deadline, a 64 MiB stdout ceiling (4 KiB for version), and a
64 KiB stderr ceiling. Pipes are drained incrementally with bounded reads; exceeding a bound
or deadline kills the process group, including descendants holding pipes. Provider diagnostics
are discarded. Errors expose fixed codes through `EvidenceProviderError`, mapped to CLI exit 7.
There is no inventory-only fallback on provider failure. These process controls target POSIX,
matching the existing safe source acquisition implementation.

The acquisition budget defaults to 1 MiB and accepts 1–16 MiB, independently of the final
contract/CLI compilation budget. Upstream acquisition skips remain visible.

## Coherence, content and safety

The external absolute root is used only to compare resolved roots. Provider HEAD/dirty state
must match the inventory observation when both sides know those fields. Unknown upstream
metadata remains nullable; if local metadata is known, a warning identifies the gap. Non-Git
mode uses content hashes. Observations are sequential, with no atomic snapshot guarantee.
Change mode validates the echoed query, immutable base/head hashes, current provider HEAD
and clean state, and retains mapping counts/ambiguity. It performs no architecture evaluation.

Paths must be exact POSIX repository-relative identities. Absolute paths, traversal, repeated
or dot components, drive/backslash ambiguity, NUL/control/surrogate/replacement characters
are rejected. Individually flagged lossy identities are omitted with explicit coverage;
the adapter does not invent replacement paths. Duplicate paths/ranks fail closed. Any
provider/inventory path collision fails, even when hashes match; no implicit merge exists.

For every selected upstream item, validate the full content string, encode UTF-8, verify
`content_bytes`, derive SHA-256 and discard the body. Total bytes must match the provider's
reported budget use. Unsupported roles and lossy candidates are discarded after accounting.
Only normalized metadata crosses the adapter boundary. Compiled output contains no source
bodies, raw stderr, absolute root, timestamps or internal index identities.

## Policy and deterministic compilation

Configuration v7 adds the four provider-backed contract kinds; schemas v1–v6 reject them.
Provider selection and executable paths are never repository configuration keys. Inventory
acquisition and all earlier JSON surfaces remain unchanged.

The existing compiler combines inventory and provider candidates, sorts by path, applies
exclusions, lifecycle and rule-scoped authority before relevance, then enforces coverage,
priorities, maxima and unique byte budgets. Within policy-equivalent groups, provider slots
in the lexical ordering are filled by provider rank/path; inventory documents keep their
positions and receive no invented rank. Optional fill uses the same local ranking. Required
feasibility repair still minimizes bytes then paths; relevance cannot override feasibility.

Final validation uses `validate_contract_sources` with the exact mixed universe. The original
`validate_contract` stays inventory-only. Both require the exact config-bound contract.
Compiled-context JSON advances to v3, adding explicit origins, relevance and provider states;
inventory/authority/lifecycle/claims/contract-validation projections
remain at their previous versions. Phase 8 intentionally advances integrity output to v2. Rebuilding derived compiled output is the v2-to-v3 migration.
The v3 renderer projects provider and relevance fields through explicit whitelists so internal
dataclass fields cannot silently become public JSON fields. Direct `RepositoryConfig`
construction enforces the same supported schema-version set as TOML parsing.

## Coverage and limitations

Provider state retains typed sorted signal pairs: analysis incompleteness, lossy paths,
diagnostics/scan warning counts, task/root/traversal/fallback truncation, content load
attempts/failures/safety omissions, acquisition budget skips, skipped/selected candidate
omissions, matched-entity omissions and change ambiguity/unavailability counts. Material
incompleteness produces `provider_incomplete` in provider state and compiled warnings.
Supported-role filtering does not assert that the provider found all potentially relevant code.

`CompilationStatus.COMPLETE` means the package satisfies the declared contract over acquired
candidates. It does not mean the provider analyzed all code or that code is semantically correct.
An incomplete provider can supply a contract-complete package. Current Context Engine syntax,
relation-resolution and ranking limitations continue to apply. No parser/indexer, claim verification, token budgets, LLM, persistence or cross-repository
support is introduced. Phase 8 consumes graph facts through a separate typed protocol;
Context Integrity owns invariant selection and judgment. Relation snapshots use command
`graph`; context provider states still require command `context`. Graph normalization discards
index-local IDs and source/diagnostic bodies, validates counts and references, and exposes
conservative coverage. Dirty graph observations have no provider content identity; local
post-graph hash observations are labeled separately. See the architecture-integrity contract.
