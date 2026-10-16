"""Fail-closed interpretation config, including safe-read and revision regressions."""

import errno
from hashlib import sha256

import pytest

from context_integrity.configuration import (
    CONFIG_PATH,
    ConfigurationError,
    load_config,
    parse_config,
)
from context_integrity.inventory import inventory_repository, scan_repository
from context_integrity.repository import discover_repository

VALID = b"""schema_version = 1
[[authority.policies]]
id = "architectural_intent"
description = "Repository order"
tiers = [["plan", "decision"], ["architecture_product"]]
[[source_metadata]]
path = "docs/custom.md"
authority_class = "verification_evidence"
reason = "Curated evidence"
[[source_metadata]]
path = "docs/adr/template.md"
authority_eligible = false
reason = "Template"
"""


def test_config_absent_and_valid(tmp_path):
    assert load_config(discover_repository(tmp_path)).content_sha256 is None
    config = parse_config(VALID)
    assert config.content_sha256 == sha256(VALID).hexdigest()
    assert config.policies[0].config_revision == config.content_sha256
    assert config.policies[0].tiers[0].classes == ("plan", "decision")
    assert config.source_metadata[1].authority_eligible is False
    assert config.policies[0].origin == "repository_config"


@pytest.mark.parametrize(
    "data",
    [
        b"[",
        b"\xff",
        b"",
        b"schema_version = 4",
        b"schema_version = true",
        b"schema_version = '1'",
        b"schema_version = 1\ninclude = 'other.toml'",
        b"schema_version = 1\n[authority]\npolciies = []",
        b"schema_version = 1\nauthority = []",
        b"schema_version = 1\nsource_metadata = {}",
        VALID.replace(b'id = "architectural_intent"', b'id = "Bad ID"'),
        VALID.replace(b'tiers = [["plan", "decision"], ["architecture_product"]]', b"tiers = []"),
        VALID.replace(b'["plan", "decision"]', b"[]"),
        VALID.replace(b'["plan", "decision"]', b'["plan", "plan"]'),
        VALID.replace(b'["architecture_product"]', b'["plan"]'),
        VALID.replace(b'["architecture_product"]', b'["bogus"]'),
        VALID.replace(b'["architecture_product"]', b'["historical"]'),
        VALID.replace(b'["architecture_product"]', b'["unknown"]'),
        VALID.replace(b'["architecture_product"]', b'"plan"'),
        VALID.replace(b'description = "Repository order"', b"description = 3"),
        VALID.replace(b'path = "docs/custom.md"', b'path = "../secret.md"'),
        VALID.replace(b'path = "docs/custom.md"', b'path = "/secret.md"'),
        VALID.replace(b'path = "docs/custom.md"', b'path = "docs/../secret.md"'),
        VALID.replace(b'path = "docs/custom.md"', b'path = "C:/secret.md"'),
        VALID.replace(b'path = "docs/custom.md"', b"path = 'docs\\secret.md'"),
        VALID.replace(b'path = "docs/custom.md"', b'path = "."'),
        VALID.replace(b'path = "docs/custom.md"', b'path = "docs/"'),
        VALID.replace(b'authority_class = "verification_evidence"', b'authority_class = "bogus"'),
        VALID.replace(
            b'authority_class = "verification_evidence"', b'authority_class = "executable_truth"'
        ),
        VALID.replace(
            b'authority_class = "verification_evidence"', b'authority_class = "historical"'
        ),
        VALID.replace(b'authority_class = "verification_evidence"\n', b""),
        VALID.replace(b'reason = "Curated evidence"', b'reason = " "'),
        VALID.replace(b'reason = "Curated evidence"\n', b""),
        VALID.replace(b"authority_eligible = false", b'authority_eligible = "false"'),
        VALID.replace(b"authority_eligible = false", b"authority_eligible = 0"),
        VALID.replace(b"authority_eligible = false", b'lifecycle = "active"'),
        VALID.replace(b"authority_eligible = false", b'kind = "decision_record"'),
        VALID
        + b'\n[[source_metadata]]\npath="docs/./custom.md"\nauthority_eligible=true\nreason="x"',
        VALID
        + b'\n[[authority.policies]]\nid="architectural_intent"\ndescription="x"\ntiers=[["plan"]]',
    ],
)
def test_invalid_config(data):
    with pytest.raises(ConfigurationError, match=r"Invalid \.context-integrity\.toml"):
        parse_config(data)


def test_config_symlink_directory_and_oversize_fail_closed(tmp_path):
    config = tmp_path / CONFIG_PATH
    outside = tmp_path / "outside"
    outside.write_bytes(VALID)
    config.symlink_to(outside)
    with pytest.raises(ConfigurationError):
        scan_repository(tmp_path)
    config.unlink()
    config.mkdir()
    with pytest.raises(ConfigurationError):
        scan_repository(tmp_path)
    config.rmdir()
    with config.open("wb") as stream:
        stream.truncate(5 * 1024 * 1024 + 1)
    with pytest.raises(ConfigurationError):
        scan_repository(tmp_path)


def test_config_unreadable_fail_closed(tmp_path, monkeypatch):
    from context_integrity import acquisition

    (tmp_path / CONFIG_PATH).write_bytes(VALID)
    original = acquisition.os.open

    def denied(path, *args, **kwargs):
        if path == CONFIG_PATH:
            raise PermissionError(errno.EACCES, "denied")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(acquisition.os, "open", denied)
    with pytest.raises(ConfigurationError):
        scan_repository(tmp_path)


@pytest.mark.parametrize("schema_version", [1, 2, 3])
@pytest.mark.parametrize("change", ["replace", "remove", "symlink", "appear", "after_read"])
def test_config_revision_consistency(tmp_path, monkeypatch, change, schema_version):
    from context_integrity import inventory

    valid = VALID.replace(b"schema_version = 1", f"schema_version = {schema_version}".encode())
    if schema_version >= 2:
        valid += b"""
[[source_metadata]]
path="a.md"
lifecycle="active"
reason="Active"
"""
        valid += b"""
[[supersession]]
source="b.md"
superseded_by="a.md"
reason="Replacement"
"""
    if schema_version == 3:
        valid += b"""
[[claims]]
id="stable"
claim_type="custom"
subject="x"
predicate="is"
value="y"
"""
    config = tmp_path / CONFIG_PATH
    if change != "appear":
        config.write_bytes(valid)
    original = inventory.enumerate_candidates
    original_read = inventory.read_source

    def mutate():
        if change in {"replace", "after_read"}:
            replacement = tmp_path / "replacement"
            replacement.write_bytes(valid + b"\n# changed\n")
            replacement.replace(config)
        elif change == "remove":
            config.unlink()
        elif change == "symlink":
            config.unlink()
            config.symlink_to(tmp_path / "missing")
        else:
            config.write_bytes(valid)

    def enumerate_changed(context):
        paths = original(context)
        if change != "after_read":
            mutate()
        return paths

    def read_changed(context, path):
        result = original_read(context, path)
        if change == "after_read" and path == CONFIG_PATH:
            mutate()
        return result

    monkeypatch.setattr(inventory, "enumerate_candidates", enumerate_changed)
    monkeypatch.setattr(inventory, "read_source", read_changed)
    with pytest.raises(ConfigurationError):
        inventory_repository(discover_repository(tmp_path))


def test_ignored_config_still_observed(git_repo, git):
    (git_repo / ".gitignore").write_text(CONFIG_PATH + "\n")
    (git_repo / CONFIG_PATH).write_bytes(b"schema_version=1\n")
    manifest = scan_repository(git_repo)
    source = next(s for s in manifest.sources if s.path == CONFIG_PATH)
    assert source.revision.git_status == "unknown"
    assert source.kind == "configuration"
    assert source.authority_class == source.lifecycle == "unknown"
    assert source.revision.content_sha256 == manifest.repository_config.content_sha256


def test_config_read_failure_and_size_growth(tmp_path, monkeypatch):
    from context_integrity import acquisition

    (tmp_path / CONFIG_PATH).write_bytes(VALID)

    context = discover_repository(tmp_path)

    def failed_read(*args):
        raise OSError("Read failure")

    with monkeypatch.context() as patch:
        patch.setattr(acquisition.os, "read", failed_read)
        with pytest.raises(ConfigurationError):
            inventory_repository(context)
    # Force the bounded streaming path to see a file growing beyond its initial stat.
    monkeypatch.setattr(acquisition, "MAX_SOURCE_BYTES", len(VALID) + 1)
    monkeypatch.setattr(acquisition.os, "read", lambda *args: VALID)
    with pytest.raises(ConfigurationError):
        inventory_repository(context)


def test_config_replaced_by_symlink_during_open(tmp_path, monkeypatch):
    from context_integrity import acquisition

    config = tmp_path / CONFIG_PATH
    config.write_bytes(VALID)
    original = acquisition.os.open

    def swapped(path, *args, **kwargs):
        if path == CONFIG_PATH:
            config.unlink()
            config.symlink_to(tmp_path / "outside")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(acquisition.os, "open", swapped)
    with pytest.raises(ConfigurationError):
        scan_repository(tmp_path)
