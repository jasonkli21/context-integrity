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


## Review index

Original external reviewer content is retained with trailing whitespace normalized. Their instructions, findings,
and status describe the reviewed revisions; implementation reports record subsequent fixes.
Finding IDs are scoped to each review.

| Review | Reviewed delivery | Fix evidence |
| --- | --- | --- |
| [Phase 0 independent review](phase-0-independent-review.md) | `240dc93458ed11db901ede9cc264eb3e98a09594` | [Phase 0 report](../implementation-reports/phase-0-implementation-report.md), fix `d5b62adc9de40416fd715983b2ec629378a4b5c0`; Phase 1 baseline |
| [Phase 1 independent review](phase-1-independent-review.md) | `9efd5fbc509adffbc11a1100ac2bb31caf8f1b6e` | [Phase 1 report](../implementation-reports/phase-1-implementation-report.md), fix `36d150af6cf67b8bab41c528b4304fa83da51309`; Phase 2 baseline |
| [Phase 2 review and cumulative Phase 0–2 audit](phase-2-independent-review.md) | `3ae38a6dc1fec72b24a64e3a0ccd8f6c2f7195d5` | [Phase 2 report](../implementation-reports/phase-2-implementation-report.md), cumulative F-001–F-005 corrections; final independent verification pending |

Phase 0/1 records were recovered from their original external artifacts during cumulative
review remediation, rather than reconstructed from implementation summaries.
