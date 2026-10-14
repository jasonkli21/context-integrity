# AI-assisted development workflow

The repository is intentionally organized for long-running AI-assisted development without making model transcripts or generated summaries the source of truth.

`AGENTS.md` is the canonical instruction file. This document explains the workflow rather than duplicating those rules.

## Context budget philosophy

The default agent context should be **small and authoritative**.

Recommended start:

```text
docs/current-state.md
        ↓
active phase plan
        ↓
relevant architecture sections
        ↓
relevant ADRs
        ↓
target code/tests
```

Only expand to the full PRD, prior reviews, old plans, or implementation reports when the task requires them.

This prevents a common failure mode from large AI-built repositories: the model receives thousands of lines of historical planning/review material and cannot distinguish current invariants from obsolete context.

## Session types

### Implementation session

Goal: satisfy a bounded active-phase requirement.

Expected output:

- code;
- tests;
- implementation report for substantial work;
- current-state update after verification.

### Review session

Goal: independently evaluate the implementation rather than continue coding by default.

Read:

- phase plan;
- architecture;
- code/tests;
- relevant ADRs;
- implementation report as evidence, not truth.

Output findings under `docs/reviews/`.

### Fix session

Goal: resolve accepted review findings.

Input should be the finding set plus only the canonical context necessary to implement it.

### Verification session

Goal: prove that fixes/requirements hold.

Prefer test/code evidence over prose.

## Durable knowledge promotion

When a useful lesson appears in an AI session, ask where it belongs:

```text
behavioral guarantee       -> test
durable architecture       -> architecture or ADR
future implementation work -> phase plan
current navigation/status  -> current-state
delivery evidence          -> implementation report
review concern             -> review
temporary reasoning        -> do not persist
```

This is the primary anti-context-drift mechanism.

## Local instructions

Do not add local `AGENTS.md` files simply to make agents "more aware."

Add one only when a subtree has genuinely different constraints, such as:

- security-sensitive adapter;
- generated code;
- fixture corpus with special rules;
- external protocol compatibility layer.

Local instructions should be additive and concise.

## Large files and fixtures

Before committing a large generated fixture:

1. explain the evaluation need;
2. prefer a generator if reproducible;
3. keep the generator and expected summary near the fixture;
4. document why a smaller fixture is insufficient.

Agents should inspect fixture metadata before loading huge files into context.

## Handoffs

Prefer canonical state over handoffs.

A handoff is justified only when work is genuinely interrupted mid-task. It should be short and point to canonical docs rather than restating them.

Once the task is complete, the handoff should not remain the only source of important information.

## AI-generated changes

AI authorship does not lower or raise the acceptance bar.

Every change still requires:

- scope discipline;
- architecture consistency;
- tests;
- reviewability;
- explicit deviations;
- correct documentation authority.
