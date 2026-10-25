# Context Integrity

**Context Integrity** is a local-first developer tool for keeping software-development context accurate, authoritative, current, and task-appropriate over time.

Modern AI-assisted repositories accumulate architecture docs, ADRs, plans, reviews, handoffs, current-state files, agent instructions, generated summaries, code, tests, schemas, and other artifacts. The hard problem is no longer just finding information—it is knowing **what is current, what is authoritative, what has been superseded, what conflicts, and what context a task should actually receive**.

Context Integrity is being built around the idea that:

> **Context should be managed like code: indexed, typed, versioned, linted, tested, compiled, observed, and continuously improved.**

## Status

**Phase 11 local governance implemented; independent acceptance remains pending.**
Phase 8 remediation is offline-verified; its independent re-review also remains pending.

The local CLI inventories context documents, hashes their raw bytes, records Git revision/status when available, and explains deterministic provisional classifications. It runs offline and keeps inventory data in memory; an explicit output option can write a manifest.

Question-specific authority policies now identify the highest observed eligible source tier and missing stronger tiers. Source-role precedence does not establish claim correctness or agreement. Explicit lifecycle metadata and directional supersession now determine source lifecycle and active-authority eligibility. Explicit claims retain declaration and dependency revisions, with independent unverified validity. Deterministic integrity checks now surface structural instruction references, current-state navigation and delivery-evidence gaps, and explicit document review dependencies on changed paths. Repository-defined Context Contracts validate explicitly supplied source packages against metadata selectors and source-count constraints. The compiler selects a bounded context manifest from an explicit contract, applying lifecycle and rule-scoped authority policy before deterministic selection. Explicit architectural invariants now evaluate descriptive relation evidence with conservative coverage. Derived receipt v1 detects changes to declared summary/handoff/compiler inputs. Explicit workspace v1 declarations now check consumer contract pins, exact file mirrors and paired unverified claims, and compile independent repository context indexes. Contradiction detection and LLM-assisted analysis remain deferred.

See [`docs/current-state.md`](docs/current-state.md) for the exact current state.

## What the project will do

At maturity, Context Integrity is intended to help answer questions such as:

- Which source is authoritative for this question?
- Is this implementation plan future intent or proof of delivery?
- Has an ADR been superseded?
- Does current code still match the architecture documentation?
- Are two active sources making contradictory claims?
- Did a generated handoff become stale because one of its inputs changed?
- What context must an agent receive for this task?
- What context should be excluded because it is historical, redundant, or invalid?

The long-term model is not "RAG over repository files." It is a structured graph of **sources, claims, evidence, authority, lifecycle, dependencies, and integrity findings**.

## Relationship to the Codebase / Context Intelligence Engine

Context Integrity is designed to remain separate from a companion **Codebase / Context Intelligence Engine**.

```text
Codebase / Context Intelligence Engine
"What is observably true in code?"
              |
              | revision-scoped structural evidence
              v
        Context Integrity
"What should be trusted, current,
authoritative, compatible, or required?"
```

Context Engine now supplies ranked code candidates through a versioned local CLI/JSON evidence boundary. Context Integrity applies authority, lifecycle, exclusions, contracts and budget policy. Explicit architectural evaluation uses the separate relation adapter. See [the evidence contract](docs/evidence-contract.md) and [architecture integrity contract](docs/architecture-integrity-contract.md).

The projects intentionally do **not** share a database or implementation lifecycle today.

## Design principles

- **Deterministic first.** Use explicit metadata, parsing, Git, and rules before model reasoning.
- **Evidence before judgment.** Findings should be traceable to sources and revisions.
- **Authority is contextual.** Code, ADRs, plans, and operating instructions are authoritative for different kinds of questions.
- **Plans do not prove delivery.**
- **Generated summaries are derived context, not primary truth.**
- **Recency does not silently imply supersession.**
- **Local-first.** The core should work without cloud services or paid model APIs.
- **LLMs are optional enrichment.** Model-derived assertions must remain distinguishable from deterministic evidence.
- **AI-development context is itself governed.** This repository is organized so agents can find the minimum authoritative context for a task without loading the entire documentation tree.

## Repository map

```text
.
├── AGENTS.md                         # canonical AI/developer operating instructions
├── CLAUDE.md                         # compatibility pointer; no duplicated rules
├── README.md
├── CONTRIBUTING.md
├── pyproject.toml
├── Makefile
├── src/context_integrity/            # application package
├── tests/                            # tests + synthetic repository fixtures
├── docs/
│   ├── README.md                     # documentation map and authority guidance
│   ├── prd.md                        # product intent and phased roadmap
│   ├── architecture.md               # system boundaries and architecture invariants
│   ├── current-state.md              # concise status snapshot
│   ├── plans/
│   │   ├── phase-0-implementation-plan.md … phase-10-implementation-plan.md
│   │   └── phase-11-implementation-plan.md # current phase plan; see current-state.md
│   ├── adr/                          # durable architectural decisions
│   ├── implementation-reports/       # evidence of what an implementation session changed
│   ├── reviews/                      # independent review findings
│   └── ai/                           # AI-development workflow guidance
└── .github/
    ├── workflows/ci.yml
    ├── PULL_REQUEST_TEMPLATE.md
    └── copilot-instructions.md       # compatibility pointer
```

The repository deliberately avoids model-specific copies of the same instructions. [`AGENTS.md`](AGENTS.md) is canonical; compatibility files point to it.

## Getting started

This project uses Python 3.12+ and [`uv`](https://docs.astral.sh/uv/).

```bash
# From this checkout
uv sync --group dev
uv run context-integrity --help
uv run pytest
uv run ruff check .
```

Convenience targets:

```bash
make setup
make test
make lint
make format
make check
```

## Using the inventory

```bash
uv run context-integrity scan .
uv run context-integrity scan . --format json --output /tmp/inventory.json
uv run context-integrity scan . --summary-only
uv run context-integrity explain AGENTS.md
uv run context-integrity explain docs/architecture.md --root .
uv run context-integrity version
```

For example, `explain AGENTS.md` includes these actual fields:

```text
Source: AGENTS.md

kind: agent_instruction
authority_class: operating_instruction
lifecycle: unknown
confidence (kind): strong
```

It also lists the stable matched rule IDs, per-dimension confidence and basis, raw-byte
SHA-256, Git HEAD/status, and the semantics intentionally left uninferred.

Classifications are **provisional path/name conventions**, not a judgment that a document's
claims are true. Authority precedence depends on the question and can be inspected with
`authority resolve`. Without lifecycle configuration, historical directory conventions produce
`historical`; otherwise lifecycle is `unknown`. Schema v2 adds explicit lifecycle and supersession.
Recency never implies supersession. Exact known filenames
precede directory rules, so `docs/adr/README.md` remains a README.

Git mode includes tracked and untracked nonignored context files. The root authority config
is always observed if present, including when ignored by Git (its Git file status is then
`unknown`). Non-Git mode skips
common vendor/build directories and does not interpret `.gitignore`. Ordinary code files
are excluded. Tracked files deleted from the working tree remain part of the repository's
dirty status but are omitted from the current source inventory. A candidate that disappears
during a scan is omitted with a structured warning. Symlinks are skipped with warnings;
files exceeding 5 MiB retain records with null hashes and warnings. Every readable source
within the limit has a raw-byte hash, which identifies observed working-tree bytes
independently of HEAD.

Stable JSON uses schema version 1, sorted repository-relative paths, and no source bodies,
absolute root, or timestamp. `--include-runtime-meta` adds the resolved root, UTC observation
time, and application version. `--summary-only` omits only the human source table.
Warnings appear in both output formats. `--fail-on-warning` returns 5 after rendering.
Other exits are 0 for success (including no authority candidates), 2 for usage/invalid
source/unknown policy, 3 for a failed scan, 4 for an output write failure, and 6 for invalid,
unsafe, or inconsistent repository configuration.

Repository identity prefers a normalized repository-local `origin` network remote
(credentials are removed). Global/system/command-scope origin values cannot supply identity.
Inherited Git ceiling and cross-filesystem discovery controls are ignored; Git security
configuration remains in effect.
The local fallback hashes the repository name plus resolved location; moving a local-only
repository changes its ID. Source IDs hash repository ID plus normalized relative path,
so renames create new IDs. Scans are sequential observations, not atomic Git snapshots.
The current safe file-opening implementation targets POSIX platforms (macOS/Linux).

See the [implementation report](docs/implementation-reports/phase-0-implementation-report.md)
for the acceptance audit and verification evidence.

## Using authority policies

```bash
uv run context-integrity authority list .
uv run context-integrity authority show architectural_intent .
uv run context-integrity authority resolve architectural_intent .
uv run context-integrity authority resolve delivered_behavior . --format json --output /tmp/authority.json
```

`list` and `show` also support `--format text|json`. All commands use the same validated
repository config and inventory. Built-in policies have the stable version `builtin-v1`:

| Policy | Tier 0 | Tier 1 | Tier 2 |
| --- | --- | --- | --- |
| `delivered_behavior` | executable_truth | verification_evidence | generated_derivative |
| `architectural_intent` | decision | architecture_product | plan |
| `operating_instructions` | operating_instruction | architecture_product | plan |
| `implementation_status` | verification_evidence | generated_derivative | plan |
| `future_work` | plan | architecture_product | generated_derivative |

A tier can contain multiple equally preferred authority classes. Every eligible source in
the highest observed tier is returned, with lower-tier sources retained separately. No
mtime, Git time, filename number, or same-tier tie breaker determines authority. Historical
sources, drafts, superseded sources, expired sources, and invalid sources are excluded before
explicit eligibility is checked. Unknown and active lifecycle states pass this lifecycle gate. Unknown or unrelated authority
classes are excluded as `not_in_policy`; they remain valid inventory sources.

**This resolves observed source-role precedence only. It does not establish claim correctness
or agreement.** Multiple top candidates do not imply a contradiction. The scanner does not
index ordinary code, so `delivered_behavior` normally reports `executable_truth` among the
missing stronger tiers. No candidates is a successful result with all policy tiers missing.

Optionally add `.context-integrity.toml` at the repository root:

```toml
schema_version = 1

[[authority.policies]]
id = "security_posture"
description = "Repository security guidance"
tiers = [["operating_instruction", "decision"], ["architecture_product"]]

[[source_metadata]]
path = "docs/adr/0000-template.md"
authority_eligible = false
reason = "Template, not an accepted decision"

[[source_metadata]]
path = "docs/custom-verification.md"
authority_class = "verification_evidence"
reason = "Curated verification evidence"
```

A policy with an existing ID replaces the whole built-in definition; a new ID adds a
policy. IDs use lowercase ASCII letters, digits, underscores, or hyphens and start with a
letter. Tiers must be nonempty, with no repeated class anywhere in a policy; `unknown` and
`historical` cannot be active tiers. Unknown config keys fail validation. There are no
includes, imports, inheritance, commands, or remote policy fetches.

Schema v1 metadata requires a repository-relative POSIX path, at least one of `authority_class` or
boolean `authority_eligible`, and a nonblank `reason`. Authority overrides preserve kind, lifecycle,
and kind confidence, recording explicit authority evidence. Eligibility defaults to true;
false preserves the source in inventory but excludes it from authority resolution.
`explain` shows both overrides and reasons. Missing metadata paths produce the structured
warning `authority_metadata_source_missing`. Schema v1 metadata cannot override kind or lifecycle;
source metadata cannot declare `executable_truth` or `historical`. Use `authority_eligible = false`
for policy-independent exclusion. `executable_truth` remains a valid policy tier for evidence
provided through the optional EvidenceProvider boundary. ADR acceptance is not inferred from
document bodies.

Config defaults to `configuration / unknown / unknown`, with a normal source ID/hash. An
absent config preserves the Phase 0 inventory contract. A present malformed, symlinked,
unreadable, oversized, or inconsistent config fails closed with exit 6. Reads use the same
bounded POSIX descriptor boundary as source acquisition; the parsed hash must match the
inventory observation and a final config read. This detects inconsistent observations but
does not make the entire scan an atomic snapshot.

Authority JSON has a **separate schema version 1** with explicit projections: repository
identity/Git metadata, policy origin/version/tiers/config hash, status, highest observed tier,
missing stronger tiers, highest/lower candidates with source revisions, every exclusion
(including `not_in_policy`), and warnings. Stable JSON omits absolute roots, timestamps, and
source bodies and ends with a newline. Inventory schema v1 gains no new keys.

Implementation evidence and the acceptance mapping are in the
[Phase 1 report](docs/implementation-reports/phase-1-implementation-report.md).

## Using lifecycle and supersession

```bash
uv run context-integrity lifecycle list .
uv run context-integrity lifecycle list . --format json --output /tmp/lifecycle.json
uv run context-integrity lifecycle show docs/adr/0008-storage.md .
uv run context-integrity lifecycle show docs/adr/0008-storage.md . --format json
```

Both commands support `--format text|json` and `--output PATH`. `show` reports identity,
revision, effective lifecycle, origin/reason, direct successor/predecessors, and combined
active-authority eligibility. Lifecycle JSON v1 retains `lifecycle_authority_eligible` for
only the lifecycle gate, and adds `explicit_authority_eligible` (true/false/null),
`active_authority_eligible`, and `active_authority_exclusion_reason` (string/null).
The combined result applies lifecycle exclusion before explicit `authority_eligible = false`.
It does not run a question-specific authority policy or check policy membership.
Source-not-found exits 2; output failure exits 4; invalid or unsafe config exits 6.
`explain` shows built-in rules, explicit lifecycle metadata, the resolved replacement,
effective lifecycle, and lifecycle eligibility. `scan` uses the existing lifecycle field
and summary counts for effective states.

| Lifecycle | Passes active-authority lifecycle gate? |
| --- | --- |
| `unknown` | Yes; fallback means unestablished, not active |
| `active` | Yes |
| `draft`, `superseded`, `historical`, `expired`, `invalid` | No |

Other authority gates still apply. Exclusions use `<state>_lifecycle` before
`explicitly_ineligible` and `not_in_policy`; policy tiers and equal-precedence behavior
are unchanged.

Schema v1 remains supported with its authority-only behavior. Choose schema v2 to add
lifecycle metadata and supersession, alongside the same authority policy/metadata syntax:

```toml
schema_version = 2

[[source_metadata]]
path = "docs/adr/0008-storage.md"
lifecycle = "superseded"
reason = "Replaced by ADR-0019"

[[source_metadata]]
path = "docs/adr/0019-storage-v2.md"
lifecycle = "active"
reason = "Accepted current storage decision"

[[supersession]]
source = "docs/adr/0008-storage.md"
superseded_by = "docs/adr/0019-storage-v2.md"
reason = "ADR-0019 replaces ADR-0008"
```

Explicit metadata accepts the six established states; `unknown` remains fallback only.
One entry can combine `authority_class`, boolean `authority_eligible`, and `lifecycle`
with one required nonblank reason. No source-kind override is supported. Explicit lifecycle
outranks a historical path heuristic. A non-historical override restores the kind-derived
authority role unless an explicit authority-class override supplies the role.

Supersession is directional: A -> B sets A to `superseded` only when both endpoints are
observed. It never makes B active. One direct successor per source, chains, and converging
predecessors are supported; self edges, duplicate outgoing edges, cycles, and contradictory
explicit lifecycle declarations fail config validation. An outgoing edge permits explicit
`superseded` metadata only. No transitive edges are fabricated. Paths use normalized
repository-relative POSIX syntax; traversal, absolute paths, and Windows path ambiguity
are rejected. Lifecycle metadata and supersession cannot target `.context-integrity.toml`.

Missing endpoints emit `supersession_source_missing` and/or `supersession_target_missing`.
An unresolved edge alone cannot change lifecycle. Independently declared `superseded`
metadata remains effective. Missing lifecycle metadata paths emit
`lifecycle_metadata_source_missing`; combined authority metadata may also emit the existing
authority warning. Config is never rewritten, and its raw-byte hash must match the bytes
used for observation, lifecycle, and authority; inconsistent reads fail closed.

Lifecycle JSON has a separate schema version 1: repository identity/Git metadata, config
hash, source IDs/paths/kinds/authority classes/revisions, lifecycle origin/reason/eligibility,
direct `superseded_by` and `supersedes`, resolved edge list, and warnings. Edges carry both
endpoint records and their revisions, explicit reason, and config hash. `show` uses the same
schema with one source and its direct edges, retaining scan warnings. Output is deterministic,
with sorted repository-relative paths, no timestamps, absolute root, or source bodies, and
a newline at EOF. Inventory and authority JSON v1 gain no graph fields or new keys.

Lifecycle is explicit source metadata only: no dates, Git timestamps, filename numbering,
body text, or model inference establish state or supersession. Expiration is never automatic.
Lifecycle commands do not mutate configuration, evaluate claims or acquire provider evidence.
No database is included.
See the [Phase 2 implementation report](docs/implementation-reports/phase-2-implementation-report.md)
for verification and the acceptance mapping.

## Checking documentation and instruction drift

```bash
uv run context-integrity check .
uv run context-integrity check . --diff main..HEAD
uv run context-integrity check . --format json --output /tmp/integrity.json
```

`check` returns 0 after a successful evaluation, including when findings exist. Repository
or explicitly requested diff failures return 3, output failures 4, and config failures 6.
The original `check` remains descriptive and non-gating. Use the separate
[governance command](docs/governance-contract.md) for explicit CI thresholds and waivers.

Without `--diff`, change evidence includes modified, deleted, and untracked paths from
local Git status. `BASE..TARGET` resolves two local commits and compares their paths,
with renames represented as deletion plus addition. No fetch occurs. Source text and
inventory always describe the current checkout, even when change evidence uses a range.
Without Git, text/navigation rules still run and change evidence is marked unavailable.

With no instruction policy, an inventoried root `AGENTS.md` enables structural reference
checks for existing `CLAUDE.md`, `GEMINI.md`, and `.github/copilot-instructions.md` sources.
A repository using only `CLAUDE.md` is not required to adopt that convention. Local/nested
instructions are outside this automatic root policy. References establish a literal path
relationship only; they do not establish semantic agreement.

Choose schema v4 to retain v3 features and add explicit instruction and review dependencies:

```toml
schema_version = 4

[instruction_policy]
canonical = "AGENTS.md"
compatibility = ["CLAUDE.md", ".github/copilot-instructions.md"]

[[drift_dependencies]]
id = "architecture-core-model"
dependent = "docs/architecture.md"
upstream = ["src/context_integrity/models.py", "src/context_integrity/evidence.py"]
reason = "Core model/evidence changes require architecture review."
```

These are exact path dependencies; there is no glob expansion or code analysis. A changed
upstream with an unchanged dependent emits a review signal. Changing both suppresses that
simple signal without proving correctness. Missing dependent sources remain visible.
Schemas v1–v3 reject v4 policy keys.

For usable current-state sources, checks recognize the narrow `**Current phase:** Phase N`,
`**Active plan:**` followed by a backtick path, `**Status:**`, and `## Next expected step`
convention. Multiple usable candidates require resolution. A delivered status requires a
usable `phase-N-implementation-report...` verification record; a plan or generic review
cannot substitute. Later numeric phase reports signal possible navigation lag. Report
existence is evidence rather than proof of implementation correctness.

Integrity JSON v2 is a separate projection (`integrity_schema_version: 2`) containing
repository identity, config hash, change scope and commit revisions, findings, affected
paths, owned evidence, warnings, and Phase 8 architecture state. It omits source bodies, timestamps, and absolute
roots. Finding IDs are stable across content revisions when the rule, code, dependency
ID, and affected paths stay the same. Findings never mutate authority, lifecycle,
supersession, or claims; claim validity remains `unverified`.

See the [Phase 4 implementation report](docs/implementation-reports/phase-4-implementation-report.md).

## Using claims and provenance

```bash
uv run context-integrity claims list .
uv run context-integrity claims list . --format json --output /tmp/claims.json
uv run context-integrity claims show context_integrity_owns_normative_interpretation .
```

Choose configuration schema v3 to declare explicit structured claims alongside all v2
policy, metadata, lifecycle, and supersession features. Schemas v1/v2 reject `claims`.

```toml
schema_version = 3

[[claims]]
id = "context_integrity_owns_normative_interpretation"
claim_type = "architectural_intent"
subject = "context_integrity"
predicate = "owns"
value = "normative interpretation of context"
scope = "repository"
depends_on = ["docs/architecture.md", "docs/prd.md"]
```

`id`, `claim_type`, `subject`, `predicate`, and `value` are required nonblank strings.
IDs and types match `[a-z][a-z0-9_-]*`; IDs must be unique. Types may be independent of
existing authority policies. `scope` is an optional nonblank string; `depends_on` defaults
to an empty array. Dependency paths use normalized repository-relative POSIX syntax.
Unsafe paths, duplicate normalized paths, config self-dependencies, and unknown keys
are rejected. Claim strings are data and are never executed or interpreted as expressions.

Declaration provenance identifies `.context-integrity.toml`, its SourceId and observed
raw-byte SourceRevision, locator `claim:<id>`, extraction method `repository_config_explicit`,
and extractor version `claims-v1`. Editing a declaration preserves its configured ID while
changing the observed revision. Each dependency carries the already inventoried source's
identity and raw-byte revision, including dirty content hashes and separate Git metadata.
Dependencies are inputs to the assertion; they do not prove it or imply that their bodies
were parsed to extract it.

Missing, ignored, deleted, unsafe-to-read, or non-inventoried paths remain unresolved.
Ordinary code is outside the inventory and is not added by a claim reference. Claims stay
visible with `provenance_complete = false` and `claim_dependency_missing` warnings. An
observed source with an unavailable content revision retains its identity/revision metadata,
remains unresolved, and emits `claim_dependency_revision_unavailable`. **Every claim remains
`unverified`**, regardless of provenance completeness or dependency lifecycle/authority.

Both commands support `--format text|json` and `--output PATH`. List text shows ID, type,
validity, and completeness; show adds the statement, declaration, and dependency revisions.
Unknown claim exits 2, output write failure exits 4, and configuration errors exit 6.
Show JSON uses the same schema with one claim, repository observation warnings, and only
that claim's diagnostics.

Claims JSON has its own schema v1 with explicit fields for statements, validity,
provenance completeness, declaration provenance, dependencies (`resolved`, nullable
`source_id`/`revision`), repository observation warnings, and claim-scoped diagnostics with
an explicit `claim_id`. List includes diagnostics for all claims; show includes diagnostics
only for its selected claim. Claims sort by ID and dependencies by path; JSON ends with a
newline and omits timestamps, absolute roots, and dependency bodies.
Inventory, authority, and lifecycle JSON v1 contracts are unchanged. No claim verification,
authority resolution, prose extraction, or contradiction/drift evaluation runs.
See the [Phase 3 implementation report](docs/implementation-reports/phase-3-implementation-report.md).

## Context Contracts (configuration v5)

Schema v5 retains v1-v4 configuration and adds repository-defined `context_contracts`.
Older schema versions reject this key. There are no built-in contracts. For example,
add the following to `.context-integrity.toml` (use `schema_version = 5` once at the top):

```toml
schema_version = 5

[[context_contracts]]
id = "implementation-task"
task_class = "implementation"
description = "Context for active implementation work."

[[context_contracts.rules]]
id = "instructions"
mode = "required"
paths = ["AGENTS.md"]
max_count = 1

[[context_contracts.rules]]
id = "plan"
mode = "required"
kinds = ["implementation_plan"]
lifecycles = ["unknown", "active"]

[[context_contracts.rules]]
id = "architecture"
mode = "optional"
kinds = ["architecture"]
authority_classes = ["architecture_product"]
max_count = 1

[[context_contracts.rules]]
id = "historical"
mode = "excluded"
lifecycles = ["historical", "superseded", "expired", "invalid"]
```

```bash
uv run context-integrity contracts list .
uv run context-integrity contracts show implementation-task . --format json
uv run context-integrity contracts validate implementation-task . \
  --source AGENTS.md --source docs/plans/phase-5-implementation-plan.md
uv run context-integrity contracts validate implementation-task . \
  --source AGENTS.md --format json --output /tmp/contract-validation.json
```

Every command supports `--format text|json` and `--output FILE`. Validation allows an
empty package. Findings return exit 0; unknown contracts or unsafe package paths return 2,
repository failures 3, output failures 4, and configuration failures 6.

Rules match exact repository-relative `paths`, `kinds`, `authority_classes`, and
`lifecycles`: AND across dimensions, OR within a dimension. Omitted or empty dimensions
impose no constraint; at least one nonempty dimension is required. Paths use POSIX `/`
separators; harmless `./` and repeated separators normalize before resolution, while
absolute paths, traversal, drive/backslash ambiguity, NULs and trailing slashes are rejected.
Paths are literal: glob and regex expressions are never expanded. Contract, task-class,
and rule identifiers use `[a-z][a-z0-9_-]*`; rule IDs are unique per contract, contract IDs
per repository, and descriptions must be nonblank.

Required rules default to minimum 1 with no maximum; an explicit minimum must be positive.
Optional rules have minimum 0 and an optional nonnegative maximum. Excluded rules have
minimum/maximum 0; custom counts cannot weaken that exclusion. Counts must be integers,
not booleans. Selector values must be unique. Currentness is explicit through lifecycle
selectors; historical sources may satisfy rules that allow them. Authority-class matching
does not invoke repository-wide authority precedence resolution.

Sources resolve only against the current context inventory. Duplicate normalized inputs
count once and emit `duplicate_package_source` warnings. Missing or non-inventoried files
emit `package_source_unavailable`; they do not trigger extra reads. Required shortfalls,
overfilled rules, and exclusions emit `required_context_missing`, `context_rule_overfilled`,
and `excluded_context_present`. Validation never fills, ranks, rewrites, or removes context.

Contract-validation JSON v1 is separate from earlier JSON contracts. It includes the
contract/config revision, normalized package paths (including duplicates and unresolved
paths), resolved source IDs/content revisions, every rule result, findings, and observation
warnings. Contracts/rules sort by ID, paths lexically, findings by contract/rule/code/paths/ID
(all initially medium severity), and warnings by path/code/message. Finding IDs use semantic
fields rather than message prose. List/show have separate deliberate JSON v1 shapes.
Stable JSON contains no timestamps, absolute root, or source bodies. Observations are
sequential, not atomic snapshots. See the
[Phase 5 implementation report](docs/implementation-reports/phase-5-implementation-report.md).

## Task Context Compiler (configuration v6)

Schema v6 retains v1–v5 and adds a positive integer `budget_bytes` on contracts,
nonnegative integer `priority` (default 0) and optional `authority_policy` on rules.
Booleans are invalid integers; unknown keys and unknown policy IDs fail closed.
Earlier schemas reject these fields and are never silently upgraded.

```toml
schema_version = 6
[[context_contracts]]
id = "implementation-task"
task_class = "implementation"
description = "Instructions and architecture for implementation"
budget_bytes = 80000
[[context_contracts.rules]]
id = "instructions"
mode = "required"
paths = ["AGENTS.md"]
priority = 100
authority_policy = "operating_instructions"
[[context_contracts.rules]]
id = "architecture"
mode = "optional"
kinds = ["architecture"]
max_count = 2
priority = 50
authority_policy = "architectural_intent"
```

```bash
uv run context-integrity compile implementation-task .
uv run context-integrity compile implementation-task . --budget-bytes 40000
uv run context-integrity compile implementation-task . --task "Implement a change" \
  --format json --output /tmp/compiled-context.json
```

Compilation requires the exact configured contract and its observed config revision.
Without a provider, candidates come only from inventory. An omitted lifecycle selector permits `unknown` and
`active`; explicit lifecycle selectors can request historical context. Excluded rules
always win. A rule's authority policy resolves only its eligible matching candidates,
and only the highest observed tier is selectable. Equally ranked alternatives remain
visible; lexical selection does not assert semantic preference. Across overlapping rules,
a source must meet every matching rule's lifecycle/authority restriction, so selecting it
through an optional rule cannot bypass another rule's policy.

Required selection first favors sources covering more unsatisfied rules, then higher
rule priorities, then relative paths. If that greedy pass leaves required deficits, a
deterministic feasibility search repairs the set when a complete package fits, minimizing
bytes and then selected paths. Optional rules fill afterward by priority and ID.
Each source counts once toward budget and each matching rule's maximum. Extra required
matches are omitted unless they help another required or optional rule. CLI budget overrides
contract budget; otherwise selection is unbounded. The compiler never exceeds a finite
budget or falls back to lower authority to fit. Missing content hashes or observed sizes
remain inspectable omissions. If no feasible required set exists, the deterministic greedy
result remains inspectable as incomplete.

Final Phase 5 validation determines `complete` or `incomplete`; both return exit 0.
Fatal categories remain usage/unknown contract/invalid budget 2, repository 3, output 4,
configuration 6, and provider failure 7. Without a provider, task text is opaque metadata.
Provider mode requires a nonblank task and forwards it as the relevance query.

Compiled-context JSON v3 is a separate deliberate projection with structured decisions,
rule-scoped authority metadata, config/source revisions, unique dependencies, budget,
final contract validation, and explicit `integrity_state` (`not_evaluated` unless a
deterministic integrity overview is supplied). A supplied overview retains finding identity,
severity, and evidence references. Earlier JSON projections remain unchanged; use compile
output to inspect v6 compiler policy fields. Stable output contains no absolute root,
timestamps, or source bodies. This is a rebuildable selection manifest, observed
sequentially, with no source-body bundle, semantic retrieval, integrity gating, token
budgeting, cache, LLM or database. CI enforcement is available through the separate
[governance command](docs/governance-contract.md). Optional code acquisition is described below.
See the [Phase 6 implementation report](docs/implementation-reports/phase-6-implementation-report.md).

## Mixed documentation and code context (configuration v7)

Schema v7 retains all earlier configuration and permits contract kinds `source_code`,
`test`, `schema`, and `migration`. Schemas v1–v6 reject these kinds. For a mixed contract,
set `schema_version = 7`, retain your instruction/document rules, and add:

```toml
[[context_contracts.rules]]
id = "code"
mode = "required"
kinds = ["source_code"]
min_count = 1
max_count = 8
priority = 80

[[context_contracts.rules]]
id = "tests"
mode = "optional"
kinds = ["test"]
max_count = 4
priority = 70
```

```bash
uv run context-integrity compile implementation-task . --task "Update compiler selection" \
  --evidence-provider context-engine --format json --output /tmp/mixed-context.json
# Advanced runtime options:
# --context-engine-bin /path/to/ctx
# --evidence-budget-bytes 1048576
# --evidence-change BASE..HEAD
```

A locally installed compatible `ctx` is required only in provider mode; nothing is downloaded.
The default 1 MiB acquisition ceiling (maximum 16 MiB) is separate from the final contract
budget. Root/HEAD/dirty mismatches and malformed/unsafe evidence fail closed with exit 7.
Provider failures never silently compile documentation alone. Complete/incomplete packages
both retain exit 0. Provider-only options without provider selection are usage errors.

Provider rank only orders otherwise policy-equivalent code candidates. Inventory documents
receive no invented relevance score. JSON v3 adds provider versions, ranker derivation,
revision/coverage state, origins and relevance evidence to the existing decisions/dependencies.
Provider incompleteness remains inspectable independently of contract completeness. Bodies
are validated, hashed and discarded before compilation. `contracts validate` continues to
resolve only inventory sources; provider code is visible only to explicit mixed compilation.
See [the evidence contract](docs/evidence-contract.md) for process limits, role normalization,
transport replacement, safety and limitations, and the
[Phase 7 report](docs/implementation-reports/phase-7-implementation-report.md) for verification.

## Development workflow

For implementation work, start with:

1. [`docs/current-state.md`](docs/current-state.md) — what is actually true now.
2. The active phase plan — what the current phase is allowed and required to implement.
3. [`docs/architecture.md`](docs/architecture.md) — invariants and boundaries.
4. Relevant ADRs.
5. [`docs/prd.md`](docs/prd.md) only when product intent or downstream alignment is needed.

For AI-assisted work, read [`AGENTS.md`](AGENTS.md) before changing code. The repository intentionally keeps review reports, handoffs, and historical artifacts out of the default context path so they do not overpower current sources.

## Explicit local governance

Copy [the policy template](docs/examples/governance-policy.toml) to the checkout root as
`governance.toml`, review it, then run:

```bash
uv run context-integrity governance check governance.toml --format json
uv run context-integrity governance check governance.toml --diff app=BASE..HEAD
```

Policy v1/v2 supplies owner, severity threshold, required coverage handling, repository/workspace/
derived targets, reviewed rule overrides and exact expiring fingerprint waivers. V2 waivers bind
approval to effective severity, owner and threshold; legacy v1 waivers need renewal before they
can suppress a finding. Report v2 retains native signals, provenance and independent coverage gaps,
with scoped metrics and explicit prior report comparison. No source bodies or claim values are
emitted. Exit 8 means an unwaived blocker; 9 means required incomplete evidence without a definite
blocker. Explicit diff ranges require a clean checkout whose HEAD matches the range target; the
legacy `check --diff` remains unchanged. Existing check commands retain their exit behavior.
`--as-of`, `--compare-to`, `--format` and exclusive `--output` outside observed roots are supported.
Owners/reviews are declarations; a pass is not semantic compliance.

The [governance contract](docs/governance-contract.md) defines exact grammar, fingerprints,
limits, comparison and exits. The [PR recipe](docs/examples/governance-pr.yml) is an example;
the existing quality workflow remains unchanged. Phase 11 and predecessor independent review
statuses remain unresolved as recorded in [current state](docs/current-state.md).

## Roadmap

The planned progression is:

```text
Phase 0   Source identity + inventory + provisional classification
Phase 1   Authority policy
Phase 2   Lifecycle + supersession
Phase 3   Claims + provenance
Phase 4   Documentation / instruction drift
Phase 5   Context contracts
Phase 6   Context compiler
Phase 7   Codebase Intelligence evidence integration
Phase 8   Architectural integrity
Phase 9   Derived-context revalidation
Phase 10  Cross-repository integrity
Phase 11  CI / governance / observability
Phase 12+ Semantic optimization and richer intelligence
```

The roadmap is intentionally staged. Later infrastructure should not be pulled into earlier phases simply because it is part of the long-term design.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Changes should preserve phase boundaries, include tests, and update current-state / implementation evidence when they materially change delivered behavior.

## License

A license has not yet been selected. Select one before treating the repository as an open-source distribution.


## Architectural integrity (configuration v8)

Phase 8 adds explicit repository-owned `architecture_invariants`, linked to architecture
claims with predicate `must_not_depend_on`. A `forbid_relation` rule selects source and target
paths, literal directory prefixes, qualified symbols or unresolved target names, and reports
observed prohibited imports/references as HIGH findings.

```bash
uv run context-integrity check . --evidence-provider context-engine --format json
# Optional existing executable override:
uv run context-integrity check . --evidence-provider context-engine --context-engine-bin /path/to/ctx
```

No task is required. `check` now emits integrity JSON v2, preserving Phase 4 checks and adding
policy, claim linkage, provider provenance, coverage and structural evidence. Results explicitly
say `violated`, `no_violation_observed`, `inconclusive` or `not_evaluated`. No observed edge is
no compliance proof. Without a provider, configured invariants visibly remain unevaluated.
Findings exit 0; provider failures exit 7. Claim validity remains `unverified`.

See [architecture-integrity contract and config example](docs/architecture-integrity-contract.md)
and [Phase 8 implementation evidence](docs/implementation-reports/phase-8-implementation-report.md).

## Derived context receipts

Record known inputs explicitly, then recheck without changing the artifact or pins:

```bash
uv run context-integrity derived capture docs/handoff.md . \
  --id handoff-a --kind handoff --derivation model --producer agent \
  --depends-on AGENTS.md --receipt-output docs/handoff.provenance.json
uv run context-integrity derived check docs/handoff.provenance.json . --format json
```

Saved JSON compiles optionally accept `--receipt-output docs/context.provenance.json`.
Receipts report `unchanged_observed_inputs`, `review_required` or `inconclusive`; equality
does not establish semantic correctness or exhaustive provenance. Provider context remains
inconclusive without re-query. Outputs are explicit, repository-local and never overwrite
existing files. When an input is itself a generated handoff or summary, link its receipt with
`--upstream-receipt` so changes to its inputs propagate. See
[the derived context contract](docs/derived-context-contract.md).

## Cross-repository workspace

Declare 2–8 local repositories, expected IDs, explicit alignments and per-repository context
contracts/budgets in a separate manifest. See the [workspace integrity contract](docs/workspace-integrity-contract.md)
for complete examples, strict grammar, status meanings and limits.

```bash
uv run context-integrity workspace check workspace.context-integrity.toml --format json
uv run context-integrity workspace compile workspace.context-integrity.toml \
  --task "Update API consumer" --format json --output workspace-context.json
```

Saved outputs must be new files outside all participating repositories. Findings exit zero;
matching pins/declarations establish observed alignment only. Workspace commands operate
offline without Context Engine and never rewrite locks or Phase 9 receipts.
