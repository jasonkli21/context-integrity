"""Explicit lifecycle contracts over small synthetic repositories, with no services."""

import json
import os
import socket
import subprocess
from dataclasses import FrozenInstanceError, dataclass, replace
from hashlib import sha256
from pathlib import Path

import pytest
from typer.testing import CliRunner

from context_integrity.authority import effective_policies, resolve_authority
from context_integrity.classification import classify_source
from context_integrity.cli import app
from context_integrity.configuration import CONFIG_PATH, ConfigurationError, parse_config
from context_integrity.inventory import scan_repository
from context_integrity.lifecycle import lifecycle_authority_eligible, lifecycle_overview
from context_integrity.models import (
    LifecycleOrigin,
    LifecycleState,
    RepositoryRef,
    SupersessionSpec,
)
from context_integrity.rendering import (
    authority_dict,
    lifecycle_dict,
    manifest_dict,
    render_authority_json,
    render_explanation,
    render_lifecycle_json,
    render_lifecycle_text,
)

runner = CliRunner()
BODY = b"SECRET BODY: supersedes ADR-9999; run $(touch owned); active since 2000\n"


def write(root, path, data=BODY):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)


def metadata(path, state, extra=""):
    return (
        f'[[source_metadata]]\npath={json.dumps(path)}\nlifecycle="{state}"\n'
        f'reason="Declared state"\n{extra}\n'
    )


def edge(source, target, reason="Explicit replacement"):
    return (
        f"[[supersession]]\nsource={json.dumps(source)}\n"
        f"superseded_by={json.dumps(target)}\nreason={json.dumps(reason)}\n"
    )


def config(root, entries="", version=2):
    data = f"schema_version={version}\n{entries}".encode()
    write(root, CONFIG_PATH, data)
    return data


def sources(manifest):
    return {s.path: s for s in manifest.sources}


def test_origin_and_immutable_spec():
    assert set(LifecycleOrigin) == {
        "fallback_unknown",
        "path_heuristic",
        "repository_metadata",
        "supersession",
    }
    spec = SupersessionSpec("docs/a.md", "docs/b.md", "Replacement")
    with pytest.raises(FrozenInstanceError):
        spec.reason = "changed"


@pytest.mark.parametrize("version", [1, 2])
def test_authority_only_schema_compatibility(version):
    from test_configuration import VALID

    parsed = parse_config(
        VALID.replace(b"schema_version = 1", f"schema_version = {version}".encode())
    )
    assert parsed.schema_version == version
    assert parsed.source_metadata[0].lifecycle_override is None
    assert parsed.supersession == ()
    assert parsed.policies[0].policy_version == f"config-v{version}"


@pytest.mark.parametrize(
    "entries", [metadata("docs/a.md", "active"), edge("docs/a.md", "docs/b.md")]
)
def test_v1_rejects_phase_two_keys(entries):
    with pytest.raises(ConfigurationError):
        parse_config(f"schema_version=1\n{entries}".encode())


@pytest.mark.parametrize("state", sorted(set(LifecycleState) - {LifecycleState.UNKNOWN}))
def test_explicit_state_matrix(tmp_path, state):
    write(tmp_path, "docs/adr/a.md")
    before = classify_source("docs/adr/a.md")
    data = config(tmp_path, metadata("docs/adr/a.md", state))
    manifest = scan_repository(tmp_path)
    source = sources(manifest)["docs/adr/a.md"]
    assert source.lifecycle == state == source.classification.lifecycle
    assert source.kind == before.kind
    assert source.classification.confidence == before.confidence
    assert "lifecycle.metadata.repository_override" in source.classification.matched_rules
    match = source.classification.basis[-1]
    assert (match.dimension, match.confidence, match.basis) == (
        "lifecycle",
        "explicit",
        "Declared state",
    )
    overview = lifecycle_overview(manifest)
    entry = next(e for e in overview.sources if e.source.path == source.path)
    assert entry.origin == "repository_metadata"
    assert entry.reason == "Declared state"
    assert overview.config_sha256 == sha256(data).hexdigest()
    assert source.revision.content_sha256 == sha256(BODY).hexdigest()


@pytest.mark.parametrize(
    "entries",
    [
        metadata("docs/a.md", "unknown"),
        metadata("docs/a.md", "bogus"),
        metadata("docs/a.md", "active").replace('reason="Declared state"\n', ""),
        metadata("docs/a.md", "active").replace('reason="Declared state"', 'reason="  "'),
        metadata("./.context-integrity.toml", "active"),
        metadata("docs/a.md", "active", 'kind="architecture"'),
        metadata("docs/a.md", "active", 'authority_class="executable_truth"'),
        metadata("docs/a.md", "active", 'authority_class="historical"'),
        edge("docs/a.md", "docs/a.md"),
        edge("docs/a.md", "docs/b.md") + edge("docs/a.md", "docs/c.md"),
        edge("docs/a.md", "docs/b.md") * 2,
        edge("docs/a.md", "docs/b.md") + edge("docs/b.md", "docs/a.md"),
        edge("docs/a.md", "docs/b.md")
        + edge("docs/b.md", "docs/c.md")
        + edge("docs/c.md", "docs/a.md"),
        edge(CONFIG_PATH, "docs/a.md"),
        edge("docs/a.md", "./" + CONFIG_PATH),
        edge("docs/a.md", "docs/b.md").replace('reason="Explicit replacement"\n', ""),
        edge("docs/a.md", "docs/b.md").replace('reason="Explicit replacement"', 'reason=" "'),
        edge("docs/a.md", "docs/b.md") + 'command="run"\n',
        "supersession={}\n",
    ],
)
def test_invalid_v2_config(entries):
    with pytest.raises(ConfigurationError):
        parse_config(f"schema_version=2\n{entries}".encode())


@pytest.mark.parametrize(
    "path", ["../a.md", "/a.md", "docs/../a.md", "C:/a.md", "a\\b.md", ".", "a/", ""]
)
@pytest.mark.parametrize("dimension", ["metadata", "source", "target"])
def test_unsafe_paths(path, dimension):
    entries = (
        metadata(path, "active")
        if dimension == "metadata"
        else edge(path, "docs/b.md")
        if dimension == "source"
        else edge("docs/a.md", path)
    )
    with pytest.raises(ConfigurationError):
        parse_config(f"schema_version=2\n{entries}".encode())


@pytest.mark.parametrize("state", ["draft", "active", "historical", "expired", "invalid"])
def test_conflicting_lifecycle(state):
    entries = metadata("docs/a.md", state) + edge("docs/a.md", "docs/b.md")
    with pytest.raises(ConfigurationError):
        parse_config(f"schema_version=2\n{entries}".encode())


def test_normalized_paths_and_deep_graph():
    parsed = parse_config(f"schema_version=2\n{edge('./docs//a.md', 'docs/./b.md')}".encode())
    assert parsed.supersession[0].source_path == "docs/a.md"
    assert parsed.supersession[0].superseded_by_path == "docs/b.md"
    # Graph validation must not depend on Python's recursion limit.
    chain = "".join(edge(f"{i}.md", f"{i + 1}.md") for i in range(1500))
    assert len(parse_config(f"schema_version=2\n{chain}".encode()).supersession) == 1500
    with pytest.raises(ConfigurationError):
        parse_config(f"schema_version=2\n{chain}{edge('1500.md', '0.md')}".encode())


@pytest.mark.parametrize(
    "relations",
    [
        [("docs/a.md", "docs/b.md")],
        [("docs/a.md", "docs/c.md"), ("docs/b.md", "docs/c.md")],
        [("docs/a.md", "docs/b.md"), ("docs/b.md", "docs/c.md")],
    ],
)
def test_direction_chains_and_convergence(tmp_path, relations):
    for name in ["docs/a.md", "docs/b.md", "docs/c.md"]:
        write(tmp_path, name)
    data = config(tmp_path, "".join(edge(a, b) for a, b in reversed(relations)))
    manifest = scan_repository(tmp_path)
    observed = sources(manifest)
    outgoing = {a for a, _ in relations}
    assert {p for p, s in observed.items() if s.lifecycle == "superseded"} == outgoing
    for p in {b for _, b in relations} - outgoing:
        assert observed[p].lifecycle == "unknown"  # target is never inferred active
    assert [(e.source.path, e.superseded_by.path) for e in manifest.supersession] == relations
    for e in manifest.supersession:
        assert e.source is observed[e.source.path]
        assert e.superseded_by is observed[e.superseded_by.path]
        assert e.config_sha256 == sha256(data).hexdigest()
    overview = lifecycle_overview(manifest)
    for entry in overview.sources:
        expected = sorted(a for a, b in relations if b == entry.source.path)
        assert [e.source.path for e in entry.supersedes] == expected


@pytest.mark.parametrize("present", [[], ["docs/a.md"], ["docs/b.md"]])
@pytest.mark.parametrize("explicit", [False, True])
def test_missing_endpoints_never_activate_edge(tmp_path, present, explicit):
    for name in present:
        write(tmp_path, name)
    config(
        tmp_path,
        edge("docs/a.md", "docs/b.md") + (metadata("docs/a.md", "superseded") if explicit else ""),
    )
    manifest = scan_repository(tmp_path)
    assert manifest.supersession == ()
    codes = {w.code for w in manifest.warnings}
    assert ("supersession_source_missing" in codes) == ("docs/a.md" not in present)
    assert ("supersession_target_missing" in codes) == ("docs/b.md" not in present)
    if "docs/a.md" in present:
        source = sources(manifest)["docs/a.md"]
        assert source.lifecycle == ("superseded" if explicit else "unknown")
        assert "lifecycle.supersession.explicit" not in source.classification.matched_rules


@pytest.mark.parametrize("state", ["active", "draft", "expired", "invalid", "superseded"])
@pytest.mark.parametrize("authority_override", [False, True])
def test_historical_override(tmp_path, state, authority_override):
    path = "docs/history/architecture.md"
    write(tmp_path, path)
    builtin = sources(scan_repository(tmp_path))[path]
    assert (builtin.kind, builtin.lifecycle, builtin.authority_class) == (
        "architecture",
        "historical",
        "historical",
    )
    extra = 'authority_class="decision"' if authority_override else ""
    config(tmp_path, metadata(path, state, extra))
    observed = sources(scan_repository(tmp_path))[path]
    assert observed.lifecycle == state
    assert observed.authority_class == (
        "decision" if authority_override else "architecture_product"
    )
    assert observed.kind == builtin.kind
    assert observed.classification.confidence == builtin.classification.confidence
    assert (
        observed.classification.basis[: len(builtin.classification.basis)]
        == builtin.classification.basis
    )


def test_supersession_historical_override_and_metadata_precedence(tmp_path):
    path = "docs/history/architecture.md"
    for p in [path, "docs/b.md"]:
        write(tmp_path, p)
    config(tmp_path, edge(path, "docs/b.md") + metadata(path, "superseded"))
    manifest = scan_repository(tmp_path)
    entry = next(e for e in lifecycle_overview(manifest).sources if e.source.path == path)
    assert entry.source.authority_class == "architecture_product"
    assert entry.origin == "supersession"
    assert entry.reason == "Explicit replacement"
    explanation = render_explanation(entry.source, entry)
    for value in [
        "historical",
        "Explicit lifecycle metadata",
        "superseded",
        "docs/b.md",
        "Explicit replacement",
    ]:
        assert value in explanation


@pytest.mark.parametrize("state", list(LifecycleState))
@pytest.mark.parametrize("explicitly_ineligible", [False, True])
def test_authority_lifecycle_matrix(tmp_path, state, explicitly_ineligible):
    path = "docs/adr/a.md"
    write(tmp_path, path)
    entries = (
        metadata(path, state, f"authority_eligible={str(not explicitly_ineligible).lower()}")
        if state != "unknown"
        else (
            f'[[source_metadata]]\npath="{path}"\n'
            f'authority_eligible={str(not explicitly_ineligible).lower()}\nreason="Eligibility"\n'
        )
    )
    config(tmp_path, entries)
    manifest = scan_repository(tmp_path)
    policy = next(
        p for p in effective_policies(manifest.repository_config) if p.id == "architectural_intent"
    )
    result = resolve_authority(manifest, policy)
    eligible = state in {"unknown", "active"}
    assert lifecycle_authority_eligible(state) == eligible
    if eligible and not explicitly_ineligible:
        assert [c.source.path for c in result.highest_candidates] == [path]
    else:
        exclusion = next(e for e in result.excluded if e.source.path == path)
        assert exclusion.reason == ("explicitly_ineligible" if eligible else f"{state}_lifecycle")


def test_stale_metadata_warnings_by_dimension(tmp_path):
    config(
        tmp_path,
        metadata("docs/a.md", "active")
        + metadata("docs/b.md", "active", "authority_eligible=false"),
    )
    manifest = scan_repository(tmp_path)
    assert [(w.path, w.code) for w in manifest.warnings] == [
        ("docs/a.md", "lifecycle_metadata_source_missing"),
        ("docs/b.md", "authority_metadata_source_missing"),
        ("docs/b.md", "lifecycle_metadata_source_missing"),
    ]


def test_no_inference_execution_network_or_shell(tmp_path, monkeypatch):
    for p in ["docs/adr/0001.md", "docs/adr/9999-v2-newest.md"]:
        write(tmp_path, p)
    config(tmp_path, metadata("docs/adr/0001.md", "active"))
    original = subprocess.run
    calls = []

    def guarded(args, **kwargs):
        assert isinstance(args, list) and args[0] == "git"
        assert kwargs.get("shell", False) is False
        calls.append(args)
        return original(args, **kwargs)

    def forbidden(*args, **kwargs):
        pytest.fail("Network or shell execution attempted")

    monkeypatch.setattr(subprocess, "run", guarded)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(os, "system", forbidden)
    before = render_lifecycle_json(lifecycle_overview(scan_repository(tmp_path)))
    os.utime(tmp_path / "docs/adr/9999-v2-newest.md", (1, 1))
    after = render_lifecycle_json(lifecycle_overview(scan_repository(tmp_path)))
    assert before == after
    data = json.loads(before)
    assert data["supersession"] == []
    assert next(s for s in data["sources"] if "9999" in s["path"])["lifecycle"] == "unknown"
    assert not (tmp_path / "owned").exists()
    assert calls  # Git discovery used argument arrays only.


@pytest.fixture
def lifecycle_repo(tmp_path):
    for p in ["docs/adr/a.md", "docs/adr/b.md", "docs/adr/c.md", "docs/history/architecture.md"]:
        write(tmp_path, p)
    return tmp_path


def scenario_config(root, scenario):
    if scenario == "states":
        entries = ""
        for state in sorted(set(LifecycleState) - {LifecycleState.UNKNOWN}):
            path = f"docs/{state}.md"
            write(root, path)
            entries += metadata(path, state)
    elif scenario == "chain":
        entries = (
            edge("docs/adr/a.md", "docs/adr/b.md")
            + edge("docs/adr/b.md", "docs/adr/c.md")
            + metadata("docs/adr/c.md", "active")
        )
    else:
        entries = metadata("docs/history/architecture.md", "active") + edge(
            "docs/adr/a.md", "docs/missing.md"
        )
    config(root, entries)


def fixed_manifest(root):
    manifest = scan_repository(root)
    # Rebuild edges using final fixture identities, not temporary directory-derived IDs.
    observed = {s.path: replace(s, id="src_" + s.path) for s in manifest.sources}
    return replace(
        manifest,
        repository=RepositoryRef("repo_fixture", "lifecycle-fixture", "fixture", False, None, None),
        sources=tuple(observed.values()),
        supersession=tuple(
            replace(e, source=observed[e.source.path], superseded_by=observed[e.superseded_by.path])
            for e in manifest.supersession
        ),
    )


@pytest.mark.parametrize("scenario", ["states", "chain", "override-warning"])
def test_lifecycle_goldens(lifecycle_repo, scenario):
    scenario_config(lifecycle_repo, scenario)
    manifest = fixed_manifest(lifecycle_repo)
    overview = lifecycle_overview(manifest)
    rendered = render_lifecycle_json(overview)
    golden = Path(__file__).parent / "fixtures" / f"lifecycle-v1-{scenario}.json"
    assert rendered == golden.read_text()
    assert (
        render_lifecycle_json(
            lifecycle_overview(replace(manifest, sources=tuple(reversed(manifest.sources))))
        )
        == rendered
    )
    if scenario == "chain":
        policy = next(p for p in effective_policies() if p.id == "architectural_intent")
        result = resolve_authority(manifest, policy)
        assert (
            render_authority_json(result)
            == (golden.parent / "authority-v1-lifecycle.json").read_text()
        )


def test_explicit_projection_and_compatibility(lifecycle_repo):
    scenario_config(lifecycle_repo, "chain")
    manifest = scan_repository(lifecycle_repo)
    overview = lifecycle_overview(manifest)

    @dataclass(frozen=True)
    class ExtendedOverview(type(overview)):
        private_body: str = "Never serialize this"

    extended = ExtendedOverview(
        overview.repository,
        overview.config_sha256,
        overview.sources,
        overview.supersession,
        overview.warnings,
    )
    data = lifecycle_dict(extended)
    assert set(data) == {
        "schema_version",
        "repository",
        "config_sha256",
        "sources",
        "supersession",
        "warnings",
    }
    assert set(data["sources"][0]) == {
        "source_id",
        "path",
        "kind",
        "authority_class",
        "lifecycle",
        "revision",
        "lifecycle_origin",
        "lifecycle_reason",
        "lifecycle_authority_eligible",
        "superseded_by",
        "supersedes",
    }
    rendered = render_lifecycle_json(extended)
    assert rendered.endswith("\n")
    for forbidden in [
        str(lifecycle_repo),
        "SECRET BODY",
        "Never serialize",
        "observed_at",
        "resolved_root",
    ]:
        assert forbidden not in rendered
    old_inventory = manifest_dict(manifest)
    assert set(old_inventory) == {"schema_version", "repository", "sources", "summary", "warnings"}
    assert set(old_inventory["sources"][0]) == {
        "id",
        "path",
        "kind",
        "authority_class",
        "lifecycle",
        "revision",
        "classification",
        "size_bytes",
    }
    policy = effective_policies()[0]
    data = authority_dict(resolve_authority(manifest, policy))
    for record in data["excluded"] + data["highest_candidates"] + data["lower_candidates"]:
        assert "superseded_by" not in record and "lifecycle_origin" not in record


def test_terminal_safety(tmp_path):
    hostile = "docs/hostile\x1b[31m\nrow.md"
    reason = "Replacement\x1b[31m\nrow"
    write(tmp_path, hostile)
    write(tmp_path, "docs/b.md")
    config(tmp_path, edge(hostile, "docs/b.md", reason))
    manifest = scan_repository(tmp_path)
    overview = lifecycle_overview(manifest)
    text = render_lifecycle_text(overview, detail=True)
    text += "".join(render_explanation(e.source, e) for e in overview.sources)
    assert "\x1b" not in text
    assert r"\u001b" in text
    assert "\nrow" not in text
    assert json.loads(render_lifecycle_json(overview))["supersession"][0]["reason"] == reason


@pytest.mark.parametrize("format", ["text", "json"])
@pytest.mark.parametrize("command", [["lifecycle", "list"], ["lifecycle", "show", "docs/adr/b.md"]])
def test_lifecycle_cli(lifecycle_repo, command, format):
    scenario_config(lifecycle_repo, "chain")
    result = runner.invoke(app, [*command, str(lifecycle_repo), "--format", format])
    assert result.exit_code == 0, result.output
    if format == "json":
        data = json.loads(result.stdout)
        assert data["schema_version"] == 1
        assert len(data["sources"]) == (1 if "show" in command else 5)
    else:
        for value in ["superseded", "supersession", "docs/adr/b.md", "Explicit replacement"]:
            assert value in result.output
        if "show" in command:
            for value in ["sha256:", "git status:", "lifecycle authority eligibility: false"]:
                assert value in result.output


@pytest.mark.parametrize("command", [["lifecycle", "list"], ["lifecycle", "show", "docs/adr/a.md"]])
def test_lifecycle_cli_outputs_and_errors(lifecycle_repo, tmp_path, command):
    scenario_config(lifecycle_repo, "chain")
    output = tmp_path / "output.json"
    result = runner.invoke(
        app, [*command, str(lifecycle_repo), "--format", "json", "--output", str(output)]
    )
    assert result.exit_code == 0, result.output
    assert json.loads(output.read_text())["schema_version"] == 1
    result = runner.invoke(app, [*command, str(lifecycle_repo), "--output", str(tmp_path)])
    assert result.exit_code == 4
    config(lifecycle_repo, edge("docs/a.md", "docs/a.md"))
    assert runner.invoke(app, [*command, str(lifecycle_repo)]).exit_code == 6


def test_show_unknown_and_scan_explain(lifecycle_repo):
    scenario_config(lifecycle_repo, "chain")
    assert (
        runner.invoke(app, ["lifecycle", "show", "missing.md", str(lifecycle_repo)]).exit_code == 2
    )
    assert runner.invoke(app, ["lifecycle", "show", "../a.md", str(lifecycle_repo)]).exit_code == 2
    assert runner.invoke(app, ["lifecycle", "--help"]).exit_code == 0
    result = runner.invoke(app, ["scan", str(lifecycle_repo), "--format", "json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["summary"]["by_lifecycle"] == {
        "superseded": 2,
        "active": 1,
        "historical": 1,
        "unknown": 1,
    }
    result = runner.invoke(app, ["explain", "docs/adr/a.md", "--root", str(lifecycle_repo)])
    for value in [
        "unknown",
        "superseded",
        "supersession",
        "docs/adr/b.md",
        "lifecycle authority eligibility: false",
        "authority policy resolution in this explanation",
    ]:
        assert value in result.output


@pytest.mark.parametrize("override", [False, True])
def test_edge_alone_restores_historical_authority(tmp_path, override):
    path = "docs/history/architecture.md"
    write(tmp_path, path)
    write(tmp_path, "docs/new.md")
    entries = edge(path, "docs/new.md")
    if override:
        entries += (
            f'[[source_metadata]]\npath="{path}"\nauthority_class="decision"\n'
            'reason="Curated role"\n'
        )
    config(tmp_path, entries)
    manifest = scan_repository(tmp_path)
    source = sources(manifest)[path]
    assert source.lifecycle == "superseded"
    assert source.authority_class == ("decision" if override else "architecture_product")
    match = next(
        m for m in source.classification.basis if m.rule_id == "lifecycle.supersession.explicit"
    )
    assert "docs/new.md" in match.basis and "Explicit replacement" in match.basis


def test_git_dates_and_filename_order_do_not_set_lifecycle(git_repo, git):
    for p in ["docs/adr/9999-new.md", "docs/adr/0001-old.md"]:
        write(git_repo, p)
    git(git_repo, "add", ".")
    git(git_repo, "commit", "-m", "Later commit with older-looking filename")
    manifest = scan_repository(git_repo)
    assert manifest.repository.git_head is not None
    assert manifest.supersession == ()
    assert all(s.lifecycle == "unknown" for s in manifest.sources)


def test_unobserved_symlink_endpoint_cannot_deactivate_source(tmp_path):
    write(tmp_path, "docs/a.md")
    (tmp_path / "docs/b.md").symlink_to(tmp_path / "docs/a.md")
    config(tmp_path, edge("docs/a.md", "docs/b.md"))
    manifest = scan_repository(tmp_path)
    assert sources(manifest)["docs/a.md"].lifecycle == "unknown"
    assert manifest.supersession == ()
    assert {w.code for w in manifest.warnings} >= {"supersession_target_missing"}
