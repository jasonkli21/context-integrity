"""Explicit declarations and raw-byte provenance, without semantic validity judgments."""

import json
from dataclasses import fields, replace
from hashlib import sha256
from pathlib import Path

import pytest
from typer.testing import CliRunner

from context_integrity.authority import effective_policies, resolve_authority
from context_integrity.claims import claims_overview
from context_integrity.cli import app
from context_integrity.configuration import CONFIG_PATH, ConfigurationError, parse_config
from context_integrity.inventory import scan_repository
from context_integrity.lifecycle import lifecycle_overview
from context_integrity.models import (
    ClaimDiagnostic,
    ClaimId,
    ClaimSpec,
    ClaimValidity,
    RepositoryRef,
    ScanWarning,
)
from context_integrity.rendering import (
    render_authority_json,
    render_claims_json,
    render_claims_text,
    render_json,
    render_lifecycle_json,
)

CLAIM = """[[claims]]
id = "owns_policy"
claim_type = "custom_category"
subject = "context_integrity"
predicate = "owns"
value = "normative interpretation"
scope = "repository"
depends_on = ["docs/architecture.md"]
"""
BODY = b"Dependency body must not leak.\r\n\xff\n"
runner = CliRunner()


def configure(root, entries=CLAIM, version=3):
    data = f"schema_version = {version}\n{entries}".encode()
    (root / CONFIG_PATH).write_bytes(data)
    return data


def write(root, path, data=BODY):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)


@pytest.mark.parametrize("version", [1, 2])
def test_older_schema_rejects_even_empty_claims(version):
    for entries in (CLAIM, "claims = []\n"):
        with pytest.raises(ConfigurationError):
            parse_config(f"schema_version = {version}\n{entries}".encode())


def test_v3_retains_v2_policy_lifecycle_and_supersession(tmp_path):
    entries = """[[authority.policies]]
id="custom"
description="custom policy"
tiers=[["plan", "decision"]]
[[source_metadata]]
path="docs/old.md"
lifecycle="superseded"
authority_eligible=false
reason="replaced"
[[supersession]]
source="docs/old.md"
superseded_by="docs/architecture.md"
reason="replacement"
"""
    write(tmp_path, "docs/old.md")
    write(tmp_path, "docs/architecture.md")
    configure(tmp_path, entries, version=2)
    v2 = scan_repository(tmp_path)
    configure(tmp_path, entries + CLAIM)
    v3 = scan_repository(tmp_path)
    assert v3.repository_config.policies[0].policy_version == "config-v3"
    assert v3.repository_config.source_metadata == v2.repository_config.source_metadata
    assert v3.repository_config.supersession == v2.repository_config.supersession
    old = next(s for s in v3.sources if s.path == "docs/old.md")
    assert old.lifecycle == "superseded"
    assert old.source_metadata.authority_eligible is False
    assert len(v3.supersession) == 1
    assert len(claims_overview(v3).claims) == 1
    assert resolve_authority(v3, v3.repository_config.policies[0]).excluded


@pytest.mark.parametrize(
    "entries",
    [
        "claims = {}",
        "claims = [1]",
        CLAIM + CLAIM,
        CLAIM.replace('id = "owns_policy"', 'id = "Bad ID"'),
        CLAIM.replace('id = "owns_policy"', 'id = "a\\nrow"'),
        CLAIM.replace('claim_type = "custom_category"', 'claim_type = "Bad Type"'),
        CLAIM.replace('subject = "context_integrity"', 'subject = " "'),
        CLAIM.replace('predicate = "owns"', "predicate = 3"),
        CLAIM.replace('value = "normative interpretation"', 'value = ["text"]'),
        CLAIM.replace('scope = "repository"', 'scope = " "'),
        CLAIM.replace('scope = "repository"', "scope = false"),
        CLAIM + 'unknown = "SENSITIVE_CONFIG_TEXT"\n',
        CLAIM.replace('["docs/architecture.md"]', '"docs/architecture.md"'),
        CLAIM.replace('["docs/architecture.md"]', "[3]"),
        CLAIM.replace(
            '["docs/architecture.md"]', '["docs/architecture.md", "docs/./architecture.md"]'
        ),
    ],
)
def test_invalid_claim_config_is_sanitized(entries):
    with pytest.raises(ConfigurationError) as error:
        parse_config(f"schema_version = 3\n{entries}".encode())
    assert str(error.value) == "Invalid .context-integrity.toml configuration."


@pytest.mark.parametrize("field", ["id", "claim_type", "subject", "predicate", "value"])
def test_required_claim_fields(field):
    lines = [line for line in CLAIM.splitlines() if not line.startswith(field + " =")]
    for replacement in (None, '" "', "3"):
        entries = "\n".join(lines)
        if replacement is not None:
            entries += f"\n{field} = {replacement}"
        with pytest.raises(ConfigurationError):
            parse_config(f"schema_version = 3\n{entries}".encode())


@pytest.mark.parametrize(
    "path",
    [
        "",
        "/outside.md",
        "../outside.md",
        "docs/../outside.md",
        "C:/file.md",
        "C:file.md",
        "//host/file.md",
        "docs\\file.md",
        "docs/",
        ".",
        "./.context-integrity.toml",
    ],
)
def test_unsafe_or_self_dependency(path):
    entries = CLAIM.replace('["docs/architecture.md"]', json.dumps([path]))
    with pytest.raises(ConfigurationError):
        parse_config(f"schema_version = 3\n{entries}".encode())


def test_optional_fields_and_normalization(tmp_path):
    entries = CLAIM.replace('scope = "repository"\n', "").replace(
        '["docs/architecture.md"]', '["docs//./architecture.md"]'
    )
    configure(tmp_path, entries)
    spec = parse_config((tmp_path / CONFIG_PATH).read_bytes()).claims[0]
    assert spec.scope is None
    assert spec.depends_on == ("docs/architecture.md",)
    configure(tmp_path, entries.replace('depends_on = ["docs//./architecture.md"]\n', ""))
    claim = claims_overview(scan_repository(tmp_path)).claims[0]
    assert claim.dependencies == ()
    assert claim.provenance_complete
    assert claim.validity == ClaimValidity.UNVERIFIED


@pytest.mark.parametrize("version", [None, 1, 2, 3])
def test_empty_claims(tmp_path, version):
    if version is not None:
        configure(tmp_path, "", version)
    overview = claims_overview(scan_repository(tmp_path))
    assert overview.claims == ()
    assert json.loads(render_claims_json(overview))["claims"] == []
    assert "Warnings: 0" in render_claims_text(overview)


def test_raw_byte_provenance_and_dirty_identity(git_repo, git):
    data = configure(git_repo)
    write(git_repo, "docs/architecture.md")
    git(git_repo, "add", ".")
    git(git_repo, "commit", "-m", "fixture")
    clean = claims_overview(scan_repository(git_repo)).claims[0]
    assert clean.provenance.revision.content_sha256 == sha256(data).hexdigest()
    assert clean.dependencies[0].revision.content_sha256 == sha256(BODY).hexdigest()
    assert clean.provenance.revision.git_status == "tracked_clean"
    write(git_repo, "docs/architecture.md", BODY + b"changed dependency")
    (git_repo / CONFIG_PATH).write_bytes(
        data.replace(b"normative interpretation", b"revised assertion")
    )
    manifest = scan_repository(git_repo)
    dirty = claims_overview(manifest).claims[0]
    observed = {s.path: s for s in manifest.sources}
    assert dirty.id == clean.id == "owns_policy"
    assert dirty.provenance.source_id == observed[CONFIG_PATH].id == clean.provenance.source_id
    assert dirty.provenance.revision == observed[CONFIG_PATH].revision
    assert dirty.dependencies[0].source_id == observed["docs/architecture.md"].id
    assert dirty.dependencies[0].revision == observed["docs/architecture.md"].revision
    assert dirty.dependencies[0].revision.git_head == clean.dependencies[0].revision.git_head
    assert (
        dirty.dependencies[0].revision.content_sha256
        != clean.dependencies[0].revision.content_sha256
    )
    assert dirty.provenance.revision.content_sha256 != clean.provenance.revision.content_sha256
    assert dirty.provenance.revision.git_status == "tracked_modified"
    assert dirty.dependencies[0].revision.git_status == "tracked_modified"
    assert dirty.provenance.path == CONFIG_PATH
    assert dirty.provenance.locator == "claim:owns_policy"
    assert dirty.provenance.extraction_method == "repository_config_explicit"
    assert dirty.provenance.extractor_version == "claims-v1"
    assert dirty.provenance_complete
    assert dirty.validity == "unverified"


@pytest.mark.parametrize("state", ["active", "historical", "superseded"])
def test_source_lifecycle_never_determines_validity(tmp_path, state):
    write(tmp_path, "docs/architecture.md")
    metadata = f'''[[source_metadata]]
path="docs/architecture.md"
lifecycle="{state}"
reason="explicit source lifecycle"
'''
    configure(tmp_path, CLAIM + metadata)
    manifest = scan_repository(tmp_path)
    assert next(s for s in manifest.sources if s.path == "docs/architecture.md").lifecycle == state
    claim = claims_overview(manifest).claims[0]
    assert claim.validity == "unverified"
    assert claim.provenance_complete


def test_unresolved_dependencies_do_not_expand_inventory(tmp_path):
    write(tmp_path, "ordinary.py", b"code is not a document")
    write(tmp_path, "docs/target.md")
    (tmp_path / "docs/link.md").symlink_to(tmp_path / "docs/target.md")
    entries = CLAIM.replace(
        '["docs/architecture.md"]', '["missing.md", "ordinary.py", "docs/link.md"]'
    )
    configure(tmp_path, entries)
    overview = claims_overview(scan_repository(tmp_path))
    claim = overview.claims[0]
    assert not claim.provenance_complete
    assert claim.validity == "unverified"
    assert all(
        not d.resolved and d.source_id is None and d.revision is None for d in claim.dependencies
    )
    diagnostics = [d for d in overview.diagnostics if d.code == "claim_dependency_missing"]
    assert {d.path for d in diagnostics} == {"missing.md", "ordinary.py", "docs/link.md"}
    assert {d.claim_id for d in diagnostics} == {"owns_policy"}


def test_unavailable_revision_is_distinct_and_resolver_does_no_io(tmp_path, monkeypatch):
    configure(tmp_path)
    write(tmp_path, "docs/architecture.md")
    manifest = scan_repository(tmp_path)
    source = next(s for s in manifest.sources if s.path == "docs/architecture.md")
    unavailable = replace(
        source,
        revision=replace(
            source.revision, content_sha256=None, observed_revision_basis="unavailable"
        ),
    )
    manifest = replace(
        manifest, sources=tuple(unavailable if s == source else s for s in manifest.sources)
    )

    def forbidden(*args, **kwargs):
        pytest.fail("claim resolver performed I/O")

    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr("os.open", forbidden)
    overview = claims_overview(manifest)
    claim = overview.claims[0]
    dependency = claim.dependencies[0]
    assert dependency.source_id == source.id
    assert dependency.revision == unavailable.revision
    assert not dependency.resolved and not claim.provenance_complete
    assert claim.validity == "unverified"
    assert [d.code for d in overview.diagnostics] == ["claim_dependency_revision_unavailable"]


@pytest.mark.parametrize("problem", ["missing", "hash_mismatch", "unavailable"])
def test_broken_declaration_provenance_fails_closed(tmp_path, problem):
    configure(tmp_path)
    manifest = scan_repository(tmp_path)
    source = manifest.sources[0]
    if problem == "missing":
        sources = ()
    else:
        revision = replace(
            source.revision, content_sha256=None if problem == "unavailable" else "0" * 64
        )
        sources = (replace(source, revision=revision),)
    with pytest.raises(ConfigurationError):
        claims_overview(replace(manifest, sources=sources))


def fixed_overview(root, scenario):
    write(root, "docs/architecture.md")
    entries = CLAIM
    if scenario == "unresolved":
        entries = entries.replace(
            '["docs/architecture.md"]', '["missing.md", "docs/architecture.md"]'
        )
    entries += """[[claims]]
id="a_no_dependencies"
claim_type="future_work"
subject="storage"
predicate="uses"
value="explicit assertion"
"""
    configure(root, entries)
    manifest = scan_repository(root)
    manifest = replace(
        manifest,
        repository=RepositoryRef("repo_fixture", "claims-fixture", "fixture", False, None, None),
        sources=tuple(replace(s, id="src_" + s.path) for s in manifest.sources),
    )
    return claims_overview(manifest)


@pytest.mark.parametrize("scenario", ["basic", "unresolved"])
def test_claims_json_goldens(tmp_path, scenario):
    overview = fixed_overview(tmp_path, scenario)
    rendered = render_claims_json(overview)
    golden = Path(__file__).parent / "fixtures" / f"claims-v1-{scenario}.json"
    assert rendered == golden.read_text()
    reordered = replace(
        overview,
        claims=tuple(
            replace(c, dependencies=tuple(reversed(c.dependencies)))
            for c in reversed(overview.claims)
        ),
        warnings=tuple(reversed(overview.warnings)),
        diagnostics=tuple(reversed(overview.diagnostics)),
    )
    assert render_claims_json(reordered) == rendered
    assert render_claims_json(claims_overview(scan_repository(tmp_path))) == render_claims_json(
        claims_overview(scan_repository(tmp_path))
    )
    assert str(tmp_path) not in rendered
    assert "Dependency body must not leak" not in rendered
    assert "observed_at" not in rendered
    assert "resolved" in rendered and rendered.endswith("\n")
    assert [c["id"] for c in json.loads(rendered)["claims"]] == ["a_no_dependencies", "owns_policy"]


def test_projection_does_not_serialize_extra_fields(tmp_path):
    overview = fixed_overview(tmp_path, "basic")
    # Future in-memory fields must not silently expand the v1 contract.
    for obj in (
        overview,
        overview.claims[0],
        overview.claims[0].provenance,
        overview.claims[1].dependencies[0],
    ):
        object.__setattr__(obj, "future_internal", "must not serialize")
    assert "must not serialize" not in render_claims_json(overview)
    with pytest.raises(ValueError):
        render_claims_json(replace(overview, schema_version=2))


def test_old_projections_are_independent_of_claim_specs(tmp_path):
    configure(tmp_path)
    manifest = scan_repository(tmp_path)
    policy = effective_policies()[0]

    def outputs(m):
        return (
            render_json(m),
            render_lifecycle_json(lifecycle_overview(m)),
            render_authority_json(resolve_authority(m, policy)),
        )

    without = replace(manifest, repository_config=replace(manifest.repository_config, claims=()))
    assert outputs(manifest) == outputs(without)
    assert "claims" not in "".join(outputs(manifest))


def test_terminal_control_safety(tmp_path):
    unsafe = "evil\nrow\r\x1b[31m\t\u202e"
    path = "docs/evil\nrow.md"
    write(tmp_path, path)
    entries = CLAIM
    for field, old in [
        ("subject", "context_integrity"),
        ("predicate", "owns"),
        ("value", "normative interpretation"),
        ("scope", "repository"),
    ]:
        entries = entries.replace(f'{field} = "{old}"', f"{field} = {json.dumps(unsafe)}")
    entries = entries.replace('["docs/architecture.md"]', json.dumps([path, "missing\nrow.md"]))
    configure(tmp_path, entries)
    overview = claims_overview(scan_repository(tmp_path))
    text = render_claims_text(overview, detail=True)
    assert unsafe not in text and "\x1b" not in text and "\r" not in text
    assert "evil\\nrow" in text and "\\u001b" in text and "\\u202e" in text
    assert "docs/evil\\nrow.md" in text and "missing\\nrow.md" in text
    assert json.loads(render_claims_json(overview))["claims"][0]["subject"] == unsafe
    # Renderer safety also covers fields normally restricted by parser validation.
    claim = overview.claims[0]
    object.__setattr__(claim, "id", ClaimId(unsafe))
    object.__setattr__(claim, "claim_type", unsafe)
    assert unsafe not in render_claims_text(replace(overview, claims=(claim,)))


@pytest.mark.parametrize("command", ["list", "show"])
@pytest.mark.parametrize("format", ["text", "json"])
def test_cli_list_show_and_output(tmp_path, command, format):
    fixed_overview(tmp_path, "unresolved")
    args = ["claims", command] + (["owns_policy"] if command == "show" else [])
    args += [str(tmp_path), "--format", format]
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    if format == "json":
        data = json.loads(result.output)
        assert len(data["claims"]) == (1 if command == "show" else 2)
        assert data["schema_version"] == 1
        assert data["diagnostics"]
        if command == "show":
            assert {d["claim_id"] for d in data["diagnostics"]} == {"owns_policy"}
    else:
        assert "owns_policy" in result.output and "unverified" in result.output
        if command == "show":
            assert "Value: normative interpretation" in result.output
            assert "claim:owns_policy" in result.output
            assert "sha256:" in result.output
            assert "resolved: false" in result.output
        else:
            assert "normative interpretation" not in result.output
    output = tmp_path / "claims.json"
    written = runner.invoke(app, [*args, "--output", str(output)])
    assert written.exit_code == 0 and written.output == ""
    assert output.read_text() == result.output
    failed = runner.invoke(app, [*args, "--output", str(tmp_path / "absent" / "output")])
    assert failed.exit_code == 4
    configure(tmp_path, CLAIM, version=2)
    bad_config = runner.invoke(app, args)
    assert bad_config.exit_code == 6


def test_cli_unknown_claim_and_default_path(tmp_path, monkeypatch):
    configure(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert runner.invoke(app, ["claims", "list"]).exit_code == 0
    assert runner.invoke(app, ["claims", "show", "owns_policy"]).exit_code == 0
    result = runner.invoke(app, ["claims", "show", "unknown\x1b[31m"])
    assert result.exit_code == 2
    assert "Unknown claim ID" in result.output and "\x1b" not in result.output
    assert runner.invoke(app, ["claims", "list", "--format", "bogus"]).exit_code == 2


def test_claim_spec_is_immutable_and_has_no_validity_input():
    spec = ClaimSpec(ClaimId("stable"), "type", "subject", "predicate", "value")
    with pytest.raises(AttributeError):
        spec.id = "other"
    assert "validity" not in {f.name for f in fields(spec)}


@pytest.mark.parametrize("field,value", [("id", "Bad ID"), ("claim_type", "Bad Type")])
def test_claim_domain_rejects_malformed_ids_and_types(field, value):
    args = [ClaimId("stable"), "type", "subject", "predicate", "value"]
    args[0 if field == "id" else 1] = ClaimId(value) if field == "id" else value
    with pytest.raises(ValueError):
        ClaimSpec(*args)


def test_claim_diagnostic_requires_valid_claim_id():
    with pytest.raises(ValueError, match="Invalid claim ID"):
        ClaimDiagnostic(ClaimId("Bad ID"), "issue", "a.md", "bad")


def test_claim_record_rejects_invalid_domain_identity(tmp_path):
    configure(tmp_path)
    claim = claims_overview(scan_repository(tmp_path)).claims[0]
    with pytest.raises(ValueError, match="Invalid claim ID"):
        replace(claim, id=ClaimId("Bad ID"))


def test_claim_aggregation_rejects_duplicate_ids(tmp_path):
    configure(tmp_path)
    manifest = scan_repository(tmp_path)
    spec = manifest.repository_config.claims[0]
    config = replace(manifest.repository_config, claims=(spec, spec))
    with pytest.raises(ValueError, match="Duplicate claim ID"):
        claims_overview(replace(manifest, repository_config=config))


def test_claim_provenance_requires_explicit_producer_metadata(tmp_path):
    configure(tmp_path)
    claim = claims_overview(scan_repository(tmp_path)).claims[0]
    assert claim.provenance.extraction_method == "repository_config_explicit"
    assert claim.provenance.extractor_version == "claims-v1"
    with pytest.raises(TypeError):
        type(claim.provenance)(
            claim.provenance.source_id,
            claim.provenance.path,
            claim.provenance.revision,
            claim.provenance.locator,
        )


def test_show_scopes_diagnostics_and_retains_global_warnings(tmp_path, monkeypatch):
    entries = CLAIM.replace('"docs/architecture.md"', '"missing/a.md"') + CLAIM.replace(
        'id = "owns_policy"', 'id = "second"'
    ).replace('"docs/architecture.md"', '"missing/a.md"')
    configure(tmp_path, entries)
    manifest = scan_repository(tmp_path)
    manifest = replace(manifest, warnings=(ScanWarning("global_issue", None, "global"),))
    monkeypatch.setattr("context_integrity.cli.load_inventory", lambda path: (None, manifest))
    listed = runner.invoke(app, ["claims", "list", "--format", "json"])
    shown = runner.invoke(app, ["claims", "show", "owns_policy", "--format", "json"])
    shown_second = runner.invoke(app, ["claims", "show", "second", "--format", "json"])
    assert listed.exit_code == shown.exit_code == shown_second.exit_code == 0
    list_data, show_data = json.loads(listed.output), json.loads(shown.output)
    second_data = json.loads(shown_second.output)
    assert {d["claim_id"] for d in list_data["diagnostics"]} == {"owns_policy", "second"}
    assert len({(d["claim_id"], d["path"]) for d in list_data["diagnostics"]}) == 2
    assert {d["claim_id"] for d in show_data["diagnostics"]} == {"owns_policy"}
    assert {d["claim_id"] for d in second_data["diagnostics"]} == {"second"}
    assert show_data["warnings"] == [{"code": "global_issue", "path": None, "message": "global"}]


def test_ignored_config_is_declaration_but_ignored_dependency_is_unresolved(git_repo):
    configure(git_repo)
    (git_repo / ".gitignore").write_text(CONFIG_PATH + "\ndocs/architecture.md\n")
    overview = claims_overview(scan_repository(git_repo))
    claim = overview.claims[0]
    assert claim.provenance.path == CONFIG_PATH
    assert claim.provenance.revision.content_sha256 == overview.config_sha256
    assert claim.provenance.revision.git_status == "unknown"
    assert not claim.dependencies[0].resolved
    assert not claim.provenance_complete
    assert claim.validity == "unverified"


def test_deleted_dependency_is_not_replaced_from_git(git_repo, git):
    configure(git_repo)
    git(git_repo, "add", ".")
    git(git_repo, "commit", "-m", "fixture")
    (git_repo / "docs/architecture.md").unlink()
    claim = claims_overview(scan_repository(git_repo)).claims[0]
    assert not claim.dependencies[0].resolved
    assert claim.dependencies[0].revision is None
    assert claim.validity == "unverified"
