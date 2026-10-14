# Contributing

Context Integrity is in early development. Contributions should preserve the repository's explicit phase boundaries and context-authority model.

## Development setup

```bash
uv sync --group dev
make check
```

## Before changing code

Read:

- `AGENTS.md`
- `docs/current-state.md`
- the active phase plan
- relevant sections of `docs/architecture.md`

Use the PRD for product intent rather than as a substitute for inspecting the current implementation.

## Pull requests

A pull request should:

- identify the phase or requirement it satisfies;
- explain material architectural choices;
- include tests;
- state deviations from the plan;
- avoid unrelated refactors;
- update current-state or implementation evidence only when appropriate.

For substantial phase implementation, add an implementation report under `docs/implementation-reports/`.

## Documentation

Use the documentation roles described in `docs/README.md`. Avoid duplicating canonical instructions or architecture across multiple files.

## License

A project license has not yet been selected. External contributions should wait until the repository owner has selected and added a license.
