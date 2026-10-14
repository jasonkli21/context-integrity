import json
from dataclasses import replace
from pathlib import Path

import pytest

from context_integrity.inventory import scan_repository
from context_integrity.models import ScanWarning
from context_integrity.rendering import manifest_dict, render_json, render_text

GOLDEN = Path(__file__).parent / "fixtures/inventory-v1.json"


def test_golden_json(git_repo):
    manifest = scan_repository(git_repo)
    rendered = render_json(manifest)
    assert rendered == GOLDEN.read_text()
    data = json.loads(rendered)
    assert data["schema_version"] == 1
    assert [s["path"] for s in data["sources"]] == ["AGENTS.md", "docs/architecture.md"]
    assert data["summary"]["source_count"] == 2
    assert data["summary"]["by_authority_class"] == {
        "architecture_product": 1,
        "operating_instruction": 1,
    }
    assert str(git_repo) not in rendered
    assert "observed_at" not in rendered
    assert "runtime_meta" not in data
    assert "Instructions" not in rendered
    assert rendered.endswith("\n")
    assert render_json(scan_repository(git_repo)) == rendered


def test_schema_v1_uses_explicit_key_sets(git_repo):
    manifest = scan_repository(git_repo)
    manifest = replace(
        manifest,
        warnings=(ScanWarning("test_warning", "AGENTS.md", "Fixture warning."),),
    )

    data = manifest_dict(manifest)
    source = data["sources"][0]
    classification = source["classification"]

    assert set(data) == {"schema_version", "repository", "sources", "summary", "warnings"}
    assert set(data["repository"]) == {"id", "name", "identity_basis", "git"}
    assert set(data["repository"]["git"]) == {"available", "head", "dirty"}
    assert set(source) == {
        "id",
        "path",
        "kind",
        "authority_class",
        "lifecycle",
        "revision",
        "classification",
        "size_bytes",
    }
    assert set(source["revision"]) == {
        "content_sha256",
        "git_head",
        "git_status",
        "observed_revision_basis",
    }
    assert set(classification) == {
        "kind",
        "authority_class",
        "lifecycle",
        "confidence",
        "matched_rules",
        "basis",
    }
    assert set(classification["basis"][0]) == {
        "rule_id",
        "dimension",
        "result",
        "confidence",
        "basis",
    }
    assert set(data["summary"]) == {
        "source_count",
        "by_kind",
        "by_authority_class",
        "by_lifecycle",
        "warning_count",
        "unclassified_kind_count",
        "unclassified_authority_count",
    }
    assert set(data["warnings"][0]) == {"code", "path", "message"}
    with pytest.raises(ValueError, match="Unsupported inventory schema version: 2"):
        manifest_dict(replace(manifest, schema_version=2))


def test_runtime_and_text(git_repo):
    manifest = scan_repository(git_repo)
    rendered = render_json(manifest, {"resolved_root": str(git_repo), "observed_at": "test"})
    assert json.loads(rendered)["runtime_meta"]["resolved_root"] == str(git_repo)
    full, summary = render_text(manifest), render_text(manifest, summary_only=True)
    assert "AGENTS.md | agent_instruction" in full
    assert "PATH |" not in summary
    for label in [
        "Sources: 2",
        "By kind",
        "By authority class",
        "Lifecycle",
        "Warnings: 0",
        "Unclassified kind: 0",
        "Unclassified authority: 0",
    ]:
        assert label in summary


def test_control_characters_are_escaped(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/new\nline\x1b.md").write_text("secret")
    manifest = scan_repository(tmp_path)
    assert "docs/new\\nline\\u001b.md" in render_text(manifest)
    assert json.loads(render_json(manifest))["sources"][0]["path"] == "docs/new\nline\x1b.md"


def test_dirty_golden_json(git_repo, git):
    git(git_repo, "add", ".")
    git(git_repo, "commit", "-m", "fixture")
    (git_repo / "AGENTS.md").write_bytes(b"dirty\r\n")
    (git_repo / "docs/untracked.md").write_bytes(b"\xff\r\n\x00")
    result = render_json(scan_repository(git_repo))
    assert result == GOLDEN.with_name("inventory-v1-dirty.json").read_text()


def test_history_golden_json(git_repo):
    for name in ["docs/history/old-architecture.md", "docs/history/adr/0001.md"]:
        path = git_repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"historical\n")
    result = render_json(scan_repository(git_repo))
    assert result == GOLDEN.with_name("inventory-v1-history.json").read_text()
