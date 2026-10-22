# Workspace v1 goldens

`workspace-v1.toml` and `contract-lock-v1.json` are complete declarations for the two independent
synthetic Git repositories constructed by `tests/test_workspace.py::workspace`. The repository
IDs derive from separate fixed example origins; source/lock digests are real SHA256 values.
`workspace-check-v1.json` and `workspace-context-v1.json` pin complete allowlisted projections.
Only observed Git HEAD fields are masked to a fixed valid hash, so fixture commit timestamps do
not affect goldens. All other identities, revisions, metadata and decisions remain exact.
These small fixtures test schema isolation, qualified ownership, byte/declaration equality,
policy decisions, context completeness and task privacy; they are not product authority.

Regenerate deliberately after a reviewed schema change, from the repository root:

```python
# Run with: UV_OFFLINE=1 uv run python
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "tests")
from test_workspace import workspace, normalize_heads
from context_integrity.derived_models import canonical_json
from context_integrity.workspace import resolve_workspace
from context_integrity.workspace_output import check_dict, context_dict

with tempfile.TemporaryDirectory() as folder:
    manifest, api, web = workspace.__wrapped__(Path(folder))
    resolved = resolve_workspace(manifest)
    findings = resolved.check()
    fixture_dir = Path("tests/fixtures")
    (fixture_dir / "workspace-v1.toml").write_bytes(manifest.read_bytes())
    (fixture_dir / "contract-lock-v1.json").write_bytes(
        (web / "contracts/api.lock.json").read_bytes()
    )
    for name, value in [
        ("workspace-check-v1.json", check_dict(resolved, findings)),
        (
            "workspace-context-v1.json",
            context_dict(resolved, findings, resolved.compile("task"), "task"),
        ),
    ]:
        (fixture_dir / name).write_text(canonical_json(normalize_heads(value)))
```
