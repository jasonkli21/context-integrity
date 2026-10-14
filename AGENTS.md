# AGENTS.md — Canonical Repository Instructions

This file is the **single canonical AI/developer instruction source** for this repository.

Model-specific instruction files should point here rather than duplicate these rules. If a local `AGENTS.md` is added under a subtree later, it must contain only additive/local constraints and must not copy the root file wholesale.

---

## 1. First principle

Treat repository context according to its role.

**Do not conflate:**

- what is implemented;
- what is intended;
- what is planned;
- what was reviewed;
- what is historical;
- what an agent was told in a prior session.

Plans do not prove delivery. Reviews do not automatically become requirements. Generated summaries do not outrank primary evidence.

---

## 2. Minimal context loading order

Do **not** read the entire repository documentation by default.

For implementation work, load context in this order:

1. `docs/current-state.md`
2. the active phase plan named there
3. `docs/architecture.md`
4. relevant ADR(s), if any
5. the code/tests directly involved in the task
6. `docs/prd.md` only when product scope, long-term intent, or downstream alignment matters

Read prior implementation reports or reviews only when:

- the task explicitly refers to them;
- current-state identifies an unresolved finding;
- a relevant invariant originated there and has not yet been moved into architecture/ADR/tests.

This keeps stale or historical evidence from dominating the working context.

---

## 3. Source roles

Use these practical defaults when reasoning about the repository.

### Delivered behavior

Prefer:

1. code;
2. executable tests;
3. schemas/migrations if relevant;
4. verified implementation evidence.

A plan or README is not proof that behavior exists.

### Intended architecture

Prefer:

1. accepted ADRs for specific durable decisions;
2. `docs/architecture.md` for system-wide invariants;
3. `docs/prd.md` for product intent.

### Current implementation phase

Prefer:

1. `docs/current-state.md` for navigation/status;
2. the active phase plan for normative phase requirements.

Verify delivered claims against code/tests.

### Reviews

`docs/reviews/` contains findings and analysis. A review is evidence, not automatically a new source of product requirements. Accepted review fixes should be reflected in code/tests and, if durable, moved into architecture, an ADR, or the relevant plan.

### Implementation reports

`docs/implementation-reports/` documents what an implementation session says it changed and verified. Reports are useful evidence but do not outrank the repository itself.

---

## 4. Phase discipline

Every implementation change should belong to the active phase unless the task explicitly says otherwise.

Do not pull future-phase functionality forward just because the architecture anticipates it.

For Phase 0 specifically, do not add:

- LLM calls;
- database persistence;
- claim extraction;
- authority precedence resolution;
- supersession graphs;
- contradiction detection;
- architecture drift;
- Codebase Intelligence integration;
- MCP/API servers;
- embeddings/vector search.

If a future capability is needed to complete the current requirement, surface the conflict rather than silently expanding scope.

---

## 5. Architecture invariants

Preserve these unless an explicit architecture/ADR change accompanies the code change:

- Context Integrity owns normative interpretation; Codebase Intelligence owns structural code observation.
- Code evidence and context policy remain separate.
- Authority class is not a universal scalar ranking.
- Canonical truth remains in canonical sources; indexes are derived state.
- Derived artifacts retain provenance/dependencies.
- Plans never prove implementation.
- Generated summaries are not authoritative by default.
- Recency does not silently imply supersession.
- Deterministic checks precede LLM reasoning when sufficient.
- Provider/model-derived facts must identify their derivation.
- Stable machine-readable output uses repository-relative paths.
- Dirty working-tree content is identified by content hash, not HEAD alone.
- No shared database with the separate Codebase Intelligence project is assumed.

If a task appears to require violating one of these, stop the local implementation path and document the architectural decision first.

---

## 6. Coding workflow

Before editing:

- identify the active phase and acceptance criteria;
- inspect existing code before assuming the plan describes the current implementation;
- identify the smallest architectural seam that satisfies the requirement.

During editing:

- keep changes phase-bounded;
- prefer straightforward code over speculative abstraction;
- do not create a framework for a single implementation;
- keep I/O, domain models, classification/policy, and rendering separated;
- add tests alongside behavior;
- avoid broad cleanup unrelated to the task.

After editing:

- run `make check`;
- map the result back to phase acceptance criteria;
- update docs only where the source of truth actually changed;
- create/update the implementation report for substantive phase work;
- update `docs/current-state.md` only after delivered state is verified.

---

## 7. Testing expectations

Tests should prove behavior at the lowest useful level.

Prefer:

- table-driven classification tests;
- synthetic repository fixtures;
- deterministic golden JSON for machine-readable contracts;
- CLI integration tests around stable behavior.

Do not rely primarily on mocks for repository-level semantics.

Tests must run without:

- network;
- model/API credentials;
- external databases.

---

## 8. Context hygiene

### Avoid duplicated instructions

Do not copy root instructions into `CLAUDE.md`, Copilot instructions, prompts, or local docs. Point to this file.

### Avoid temporary artifacts in canonical docs

Scratch notes belong in `.scratch/` (gitignored) or outside the repository.

Do not put temporary analysis in:

- `docs/architecture.md`;
- `docs/prd.md`;
- ADRs;
- `docs/current-state.md`.

### Avoid giant generated fixtures

Large fixtures must have a specific evaluation purpose, generation mechanism, and README/metadata explaining why they exist. Prefer generated-at-test-time data when practical.

### Avoid context archaeology

If a durable lesson exists only in an old review or implementation report, promote it into:

- a test;
- architecture;
- ADR;
- or active plan.

Do not require future agents to rediscover important invariants from historical prose.

---

## 9. Documentation lifecycle

### `docs/prd.md`

Product intent and long-term roadmap. Update infrequently.

### `docs/architecture.md`

Durable system structure and invariants. Update when architecture changes, not for every implementation detail.

### `docs/current-state.md`

Short, current navigation/status snapshot. Keep it concise.

It should answer:

- current phase;
- what is actually delivered;
- active plan;
- known blockers/findings;
- next expected step.

### `docs/plans/`

Normative future/current implementation requirements.

Once completed, retain plans as historical planning evidence; do not edit them to pretend they described later reality.

### `docs/implementation-reports/`

Implementation evidence for a phase/change.

### `docs/reviews/`

Independent review findings.

### `docs/adr/`

Durable decisions that should survive phase completion.

---

## 10. AI handoff format

Do not create handoff files routinely.

If a substantial task must be transferred between sessions, the handoff should contain only:

- objective;
- current verified state;
- active branch/commit if relevant;
- work completed;
- work remaining;
- blockers;
- exact tests run;
- links/paths to canonical docs.

Do not restate the PRD or architecture in a handoff.

Delete or archive handoffs when no longer useful.

---

## 11. Review workflow

For a completed phase or significant implementation:

1. implementation session produces code/tests + implementation report;
2. independent review compares code against:
   - active phase plan;
   - architecture;
   - relevant ADRs;
   - actual repository state;
   - downstream seams where material;
3. review findings are written under `docs/reviews/`;
4. fixes are implemented separately;
5. final verification determines whether findings are actually resolved;
6. durable lessons are promoted to tests/architecture/ADR rather than left only in the review.

Do not ask the implementing agent to grade its own architectural correctness as the only review.

---

## 12. Dependency and tooling policy

- Keep runtime dependencies minimal.
- Prefer standard library when it is sufficient.
- Add dependencies for clear product value, not convenience alone.
- Pin/lock dependencies for reproducibility.
- Do not add infrastructure merely because a later phase may need it.

Current default tooling:

- Python 3.12+
- `uv`
- Typer
- pytest
- Ruff

---

## 13. Definition of a good AI-assisted change

A strong change is:

- scoped to the requested phase/task;
- grounded in current code rather than assumed state;
- architecturally consistent;
- small enough to review;
- tested;
- documented at the correct authority layer;
- explicit about deviations;
- free of duplicated context/instructions;
- easy for the next session to understand from canonical sources alone.
