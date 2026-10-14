# Repository fixtures

Repositories are generated in pytest temporary directories rather than checked in as
nested Git repositories. `tests/conftest.py` provides the `git` helper and `git_repo`
fixture. No external repositories or credentials are used.

| Case | Generator / tests | Purpose |
| --- | --- | --- |
| basic-context | `git_repo`; `test_basic_context_repository`; rendering/CLI tests | Instructions, architecture, stable manifest, unborn Git HEAD |
| history | `test_history_repository_inventory`; classification table | Historical architecture/ADR overlay, unknown generic document |
| git-ignore | `test_git_ignore_dirty_and_raw_bytes` | Tracked sources, ignored and untracked files, ordinary code exclusion |
| dirty | Same test; worktree/rename test | Clean HEAD compared to modified raw bytes; staged rename |
| warnings | Acquisition safety tests; CLI warning test | Symlinks, size limit/growth, unreadability, hash/metadata failures |

The checked-in `tests/fixtures/inventory-v1*.json` manifests cover basic-context, dirty,
and historical repositories.
Its remote identity is fixed, branches/commit metadata and file bytes are fixed, so it contains
no temporary paths or observation timestamps. Update it only for an intentional schema/output change
and inspect the resulting contract. Fixtures contain synthetic text only.
