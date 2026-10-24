# Phase 10 Review Fixes Report

Date: 2026-10-24 Pacific. Follow-up implementation evidence, not independent acceptance.
Reviewed delivery: `c24f15d411d94a3ea61f6ed8efaa042f27acc41b`.
Review: [`../reviews/phase-10-independent-review.md`](../reviews/phase-10-independent-review.md).

## Findings addressed

- **F10-001:** Workspace JSON and text reports now have an 8 MiB serialized-output ceiling.
  A bounded `JSONEncoder.iterencode` preflight counts canonical JSON bytes before the complete
  report string is allocated. Oversized output raises the fixed diagnostic
  `workspace_report_limit_exceeded` with exit 6. Rendering completes before stdout or saved-file
  publication, so no partial report is emitted and reports are not truncated.
- **F10-002:** Repository discovery warnings are snapshotted when the workspace is created.
  Explicit file reads collect warnings on an operation-local context; each inventory runs with a
  fresh warning list seeded only by repository discovery. Inventory warnings still affect claim
  and context coverage, while a separate failed check cannot alter another rule's result.
- **G10-001:** Claim findings expose `claim_dependency_freshness: not_established`; report coverage
  carries `claim_dependency_freshness_not_established` when claims are checked. Declaration equality
  remains distinct from historical freshness, and claim validity remains `unverified`.
- **G10-002:** Check and context coverage disclose `claim_literals_may_be_sensitive` when claim
  checks are present. The contract now warns that explicit claim literals are retained verbatim
  and should be reviewed before reports are shared or passed to another agent.
- The architecture's cross-repository overview now identifies explicit workspace v1 as delivered
  and graph federation/semantic analysis as future work. The supplied review is preserved and
  indexed under `docs/reviews/`.

## Verification status

Automated tests and `make check` were not run for this change. The review's two reproduction
scenarios should be independently rerun along with the full offline gate before Phase 10 is marked
accepted. Phase 4, 7, 8 and 9 pending review statuses remain unchanged.

## Changed files

`src/context_integrity/workspace.py`, `src/context_integrity/workspace_output.py`, and
`src/context_integrity/cli.py` implement the behavior changes. The workspace contract, current
state, architecture overview, review index, preserved review, and workspace v1 golden fixtures
document the revised contract and reviewed baseline.
