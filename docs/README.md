# Documentation map

This directory is organized by **authority and lifecycle**, not merely topic.

The goal is to let a human or agent load the minimum context needed for a task without treating every Markdown file as equally current or authoritative.

## Default reading path

For implementation work:

```text
current-state.md
      ↓
active phase plan
      ↓
architecture.md
      ↓
relevant ADR(s)
      ↓
code + tests
      ↓
PRD only when needed for product/roadmap intent
```

Historical implementation reports and reviews are **not** part of the default context path.

## Documents

### `prd.md`

Long-term product requirements and phased roadmap.

Use for:

- product thesis;
- long-term capabilities;
- phase boundaries;
- relationship to Codebase Intelligence.

Do not use it as proof that a feature is implemented.

### `architecture.md`

Durable system boundaries, data concepts, and architecture invariants.

Use for:

- module ownership;
- domain boundaries;
- evidence/provider separation;
- canonical vs derived state;
- constraints that should survive a phase.

### `evidence-contract.md`

Implemented EvidenceProvider v1 boundary, Context Engine CLI transport, snapshot/content
validation, coverage, mixed compiler semantics and safety limits.

### `architecture-integrity-contract.md`

Implemented Phase 8 policy and relation-evidence boundary, source-selector applicability,
coverage semantics, finding statuses, output guarantees and evaluation limits.

### `derived-context-contract.md`

Implemented Phase 9 receipt/result v1, explicit capture/check and compiler receipt workflows,
transitive revalidation, status/coverage semantics, safe output lifecycle and resource bounds.

### `workspace-integrity-contract.md`

Implemented Phase 10 workspace/lock/check/context v1, explicit qualified identities, deterministic
alignment semantics, independent compilation, no-follow acquisition and exclusive output bounds.

### `governance-contract.md`

Implemented Phase 11 explicit policy v1/v2 and report v2, typed evaluator composition, separate CI gates,
exact dated waivers, scoped metrics, advisory comparison and bounded safe publication.
Examples live under `examples/`; independent acceptance is tracked in current-state.

### `current-state.md`

Short navigation/status snapshot.

It should be continuously useful and intentionally small.

### `plans/`

Normative implementation requirements for phases.

An active plan says **what should be built**, not what already exists.

Completed plans remain historical planning evidence rather than being rewritten to match later reality.

### `adr/`

Accepted durable decisions.

If a review discovers an architectural lesson that must persist, promote it here or into `architecture.md` rather than requiring future agents to read the old review.

### `implementation-reports/`

Evidence produced after implementation.

Reports should distinguish:

- implemented;
- verified;
- deferred;
- deviations.

### `reviews/`

Independent review findings.

A finding becomes durable only when resolved into code/tests or promoted into an authoritative architecture/ADR/plan source.

### `ai/`

How to work efficiently with AI coding agents in this repository.

`AGENTS.md` remains the canonical instruction file.

## Avoiding documentation drift

Do not create a new document when an existing canonical source should simply be updated.

Before adding a file, ask:

1. Is this a durable decision? → ADR.
2. Is this system-wide architecture? → architecture.
3. Is this current navigation/status? → current-state.
4. Is this future phase work? → plan.
5. Is this evidence of implementation? → implementation report.
6. Is this review analysis? → review.
7. Is this temporary session state? → do not commit it unless a handoff is genuinely needed.
