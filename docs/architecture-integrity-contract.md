# Architectural integrity contract v1

Phase 8 evaluates explicit repository policy against observed structural relations.
Context Integrity owns policy and findings. Context Engine supplies descriptive evidence
through its public CLI; there is no shared database, Rust import, parser duplication or LLM.

## Configuration v8

Schemas v1–v7 retain their behavior and reject the new key. Unknown configuration keys fail
closed. Direct model construction validates the same Phase 8 version, type and linkage rules.

```toml
schema_version = 8

[[claims]]
id = "application-storage-boundary"
claim_type = "architecture_invariant"
subject = "application"
predicate = "must_not_depend_on"
value = "storage"
depends_on = ["docs/architecture.md"]

[[architecture_invariants]]
id = "application-storage-boundary"
claim_id = "application-storage-boundary"
rule = "forbid_relation"
relation_kinds = ["imports", "references"]
source_path_prefixes = ["src/application/"]
target_path_prefixes = ["src/storage/"]
target_names = ["storage.Storage", "Storage"]
```

Each invariant has a unique bounded identifier, a configured claim of type
`architecture_invariant`, predicate `must_not_depend_on`, and the sole supported rule
`forbid_relation`. Both selector sides and at least one relation kind are required.
`contains` is descriptive graph structure, not an executable dependency rule.

Supported selector families are `source_paths`, `source_path_prefixes`, `source_symbols`,
`target_paths`, `target_path_prefixes`, `target_symbols`, and `target_names`. Values within
and across families on a side combine with OR; source side, relation kind and target side
combine with AND. Paths are already-normalized repository-relative POSIX identities.
Directory prefixes end in `/`: `src/application/` excludes `src/application_old/`.
Path metacharacters `*?[]` are rejected; there is no glob/regex language. Symbols match
exact qualified names, and symbols retain their owning file for path selectors.

Resolved targets match paths, prefixes or qualified symbols. Unresolved targets match only
exact `target_names`; a relative path-shaped name remains a name, with no inferred target
path. Names/identifiers are bounded and reject control characters and absolute path forms.
Claims provide intent and provenance, never selectors parsed from prose. Missing claim
provenance dependencies remain visible but do not disable the explicit rule. Claim validity
remains `unverified`; authority, lifecycle, supersession, contracts and compilation are unchanged.

## Independent relation evidence seam

`RelationEvidenceProvider.relations(EvidenceRelationRequest) -> EvidenceRelationBatch` is
separate from the Phase 7 `EvidenceProvider.context_candidates` protocol. Existing replacement
context providers need no relation method. Requests contain a runtime-only root and repository
observation. Typed results in `relations.py` contain stable file/symbol entities, resolved entity
or unresolved name targets, import/reference facts, source points/ranges, resolution, language,
derivation, provider descriptor, root-free snapshot and coverage/file states.

The normalized entity inventory is exhaustive for the provider's declared graph snapshot:
every covered path has exactly one file entity; symbols belong to one of those paths; every
relation source and resolved target must appear in that inventory. `coverage.files` therefore
means all indexed file entities, including files with no relations. Unresolved names are not
invented as entities. These checks belong to `EvidenceRelationBatch`, so replacement providers
follow the same endpoint contract as Context Engine.

The Context Engine adapter consumes **schema-v1 `ctx graph ROOT --format json`**, preceded by
bounded `ctx --version`. It uses the same finite, no-shell, closed-stdin subprocess runner as
context acquisition (30 seconds per invocation; 64 MiB stdout / 64 KiB stderr; version stdout
4 KiB). Errors are sanitized typed codes; diagnostics, warning prose and stderr are discarded.
There is no install, network request or direct cache/database access by Context Integrity.

Envelope version/command, root, known HEAD/dirty coherence, unique numeric IDs, referenced
entity existence, safe paths, ranges, resolution/derivation vocabulary and graph/file counts
are validated. Numeric IDs are decode-local only. Containment is validated and discarded;
imports/references are normalized and deterministically sorted. Exact duplicate facts collapse.
Unknown external fields are ignored, never copied to output. Lossy graph paths fail closed.

Coverage retains summary counts, per-file symbol and relation statuses, syntax errors,
unresolved counts, unsupported candidates, and fixed diagnostic/scan-warning/snapshot categories.
Missing relation-file analysis is explicit `not_analyzed`. Unknown snapshots and dirty graph
snapshots are incomplete: graph JSON does not expose provider content fingerprints. Separately
labeled local post-graph SHA-256 observations use descriptor-safe bounded reads, discard bodies,
and reserve at most 64 MiB (5 MiB per attempted file, in path order). Omitted/unreadable hashes
are null. These local hashes do **not** certify which bytes the provider analyzed. Observations
are sequential and never an atomic snapshot; HEAD alone does not identify dirty content.

## Findings and result semantics

A matching prohibited edge produces a HIGH finding. Results distinguish:

| Status | Meaning |
| --- | --- |
| `violated` | One or more prohibited structural edges were observed. |
| `no_violation_observed` | No matching edge appeared, at least one normalized source entity matched the selector, and coverage reports no material gaps; this is no architecture compliance proof. |
| `inconclusive` | No matching edge appeared, but coverage is incomplete or no normalized source entity matched the selector. |
| `not_evaluated` | No relation provider was selected; the explicit invariant was not checked. |

Each evaluated invariant reports `source_entity_count`, the number of normalized file/symbol
entities selected by its source selector. A zero count adds the `source_selector_unmatched`
caveat and yields `inconclusive`, even when graph coverage otherwise appears complete. This makes
misspelled, renamed, or absent policy scopes visible without treating a relation as proof that a
source exists. A source entity can match even when it has no relations; such a result may be
`no_violation_observed` only when global structural coverage is complete. Missing source symbols
and unavailable symbol analysis remain subject to the same conservative coverage rule.

Phase 8 deliberately uses **global conservative coverage**: any reported graph/file gap can
make every otherwise unviolated invariant inconclusive, even if it appears unrelated. It does
not attempt to prove gaps irrelevant using missing graph facts. Violations remain valid despite
coverage gaps. Unknown/unsupported languages, skipped files, syntax recovery, unresolved imports
and conservative same-file reference resolution are structural limitations, not policy judgments.

Evaluation compiles selector membership sets once and indexes source entities by path/qualified
symbol and relations by source entity/relation kind. Configuration accepts at most 128
invariants and 16,384 selector values across them. One evaluation is capped at 250,000
entity/relation index entries, source-entity selector visits and candidate relation/target
checks. Exceeding that deterministic work budget fails with `evaluation_budget_exceeded` (CLI
exit 7); it does not omit checks or return partial results. These limits bound policy matching
after graph acquisition; they do not certify provider runtime or semantic completeness.

Occurrences group by relation kind and stable source/target entity descriptors. Entity kind,
path, qualified name, symbol kind/language and symbol definition range distinguish entities;
relation syntax occurrence ranges do not create separate architectural edges. All sorted
occurrences remain under one finding, bounded by provider output acquisition. Distinct source
entities/targets and different relation kinds remain distinct findings.

IDs hash rule version, invariant ID, claim ID, relation kind and stable source/target descriptors.
They exclude numeric provider IDs, messages, occurrence order, absolute roots and timestamps.
Symbol definition movement can change identity; no edit-lineage guarantee is made.

## Integrity JSON v2 and CLI

`check` always emits integrity schema **v2**, including legacy checks. It retains Phase 4 fields
and adds structured architecture provider/snapshot/coverage/results, explicit executable policy,
claim provenance/dependencies, and typed structural finding evidence. Inventory, claims,
contracts and compiled-context schema versions remain unchanged. Explicit projectors whitelist
output; there are no source bodies, absolute roots, raw stderr, timestamps or graph numeric IDs.
Rebuilding the integrity report is the v1-to-v2 migration. Text explains all four result states.

```bash
uv run context-integrity check . \
  --evidence-provider context-engine --context-engine-bin /path/to/ctx --format json
```

Provider selection and executable override are runtime-only; no task/budget is required.
Omitting the provider still runs Phase 4 checks and visibly marks configured invariants
`not_evaluated`. Provider failure exits 7; configuration errors exit 6. Findings exit 0, including
HIGH violations. Text, JSON and output-file behavior remain supported. CI thresholds and waivers
are available through the separate Phase 11
[governance contract](governance-contract.md); this command stays non-gating. Positive dependency
proofs, semantic contradiction reasoning, automatic fixes and persistence remain deferred.
Phase 10 explicit cross-repository checks have a separate workspace contract. Phase 9 revalidation
is delivered separately in
[the derived context contract](derived-context-contract.md).
