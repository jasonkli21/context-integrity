# Context Integrity

**Context Integrity** is a local-first developer tool for keeping software-development context accurate, authoritative, current, and task-appropriate over time.

Modern AI-assisted repositories accumulate architecture docs, ADRs, plans, reviews, handoffs, current-state files, agent instructions, generated summaries, code, tests, schemas, and other artifacts. The hard problem is no longer just finding information—it is knowing **what is current, what is authoritative, what has been superseded, what conflicts, and what context a task should actually receive**.

Context Integrity is being built around the idea that:

> **Context should be managed like code: indexed, typed, versioned, linted, tested, compiled, observed, and continuously improved.**

## Status

**Phase 0 implemented; ready for independent review.**

The local CLI inventories context documents, hashes their raw bytes, records Git revision/status when available, and explains deterministic provisional classifications. It runs offline and keeps inventory data in memory; an explicit output option can write a manifest.

The first milestone is intentionally small: inventory repository context sources, classify them conservatively, record exact observed revisions, and explain each classification. Authority resolution, claims, contradiction detection, architectural drift, context compilation, and LLM-assisted analysis come later.

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

The Codebase Intelligence project will eventually provide deterministic facts such as symbols, relationships, structural changes, impact, and code-context candidates. Context Integrity will consume those facts through an evidence boundary and apply authority, lifecycle, architectural intent, context contracts, and integrity policy.

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
│   │   └── phase-0-implementation-plan.md
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
claims are true. Authority precedence is resolved in a later phase and depends on the
question. Lifecycle is `historical` only for explicit historical directory conventions;
otherwise it is `unknown`. Recency never implies supersession. Exact known filenames
precede directory rules, so `docs/adr/README.md` remains a README.

Git mode includes tracked and untracked nonignored context files. Non-Git mode skips
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
Other exits are 0 for success, 2 for usage/invalid source, 3 for a failed scan, and 4 for an
output write failure.

Repository identity prefers a normalized `origin` network remote (credentials are removed).
The local fallback hashes the repository name plus resolved location; moving a local-only
repository changes its ID. Source IDs hash repository ID plus normalized relative path,
so renames create new IDs. Scans are sequential observations, not atomic Git snapshots.
The current safe file-opening implementation targets POSIX platforms (macOS/Linux).

See the [implementation report](docs/implementation-reports/phase-0-implementation-report.md)
for the acceptance audit and verification evidence.

## Development workflow

For implementation work, start with:

1. [`docs/current-state.md`](docs/current-state.md) — what is actually true now.
2. The active phase plan — what the current phase is allowed and required to implement.
3. [`docs/architecture.md`](docs/architecture.md) — invariants and boundaries.
4. Relevant ADRs.
5. [`docs/prd.md`](docs/prd.md) only when product intent or downstream alignment is needed.

For AI-assisted work, read [`AGENTS.md`](AGENTS.md) before changing code. The repository intentionally keeps review reports, handoffs, and historical artifacts out of the default context path so they do not overpower current sources.

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
