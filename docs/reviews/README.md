# Reviews

This directory contains independent post-implementation review findings.

Reviews are **evidence and analysis**, not automatically normative product requirements.

A review should compare the implementation against:

- the active phase plan;
- actual code/tests;
- architecture invariants;
- relevant ADRs;
- downstream seams where material.

If a review discovers a durable rule, resolve it into:

- code/test behavior;
- `docs/architecture.md`;
- an ADR;
- or a future phase plan.

Do not force future agents to mine old review prose for system invariants.
