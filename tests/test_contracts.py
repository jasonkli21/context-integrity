"""Bounded metadata contracts, strict constructors/config, and public CLI contracts."""

import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest
from typer.testing import CliRunner

from context_integrity.cli import app
from context_integrity.configuration import ConfigurationError, parse_config
from context_integrity.contracts import (
    _finding,
    effective_contracts,
    matches_rule,
    resolve_contract,
    validate_contract,
)
from context_integrity.inventory import scan_repository
from context_integrity.models import (
    AuthorityClass,
    ContextContract,
    ContextContractRule,
    ContextRuleMode,
    LifecycleState,
    RepositoryConfig,
    SourceKind,
)
from context_integrity.rendering import (
    contract_validation_dict,
    render_contract_validation_json,
    render_contract_validation_text,
    render_contracts,
)

REQUIRED = ContextRuleMode.REQUIRED
OPTIONAL = ContextRuleMode.OPTIONAL
EXCLUDED = ContextRuleMode.EXCLUDED
CONFIG = """schema_version = 5
[[context_contracts]]
id = "implementation"
task_class = "implementation"
description = "Explicit implementation package"
[[context_contracts.rules]]
id = "instructions"
mode = "required"
paths = ["AGENTS.md"]
max_count = 1
[[context_contracts.rules]]
id = "architecture"
mode = "optional"
kinds = ["architecture"]
authority_classes = ["architecture_product"]
lifecycles = ["unknown", "active"]
max_count = 1
[[context_contracts.rules]]
id = "history"
mode = "excluded"
lifecycles = ["historical", "superseded", "expired", "invalid"]
"""


def rule(**changes):
    return ContextContractRule(
        **{"id": "rule", "mode": REQUIRED, "paths": ("AGENTS.md",), **changes}
    )


def contract(*rules):
    return ContextContract("test", "implementation", "Fixture contract", rules or (rule(),))


def bind_contract(manifest, value):
    """Build a manifest configuration containing this contract for domain tests."""
    config = RepositoryConfig(
        schema_version=5,
        content_sha256=value.config_revision,
        context_contracts=(value,),
    )
    return replace(manifest, repository_config=config)


@pytest.fixture
def contract_repo(git_repo):
    (git_repo / ".context-integrity.toml").write_text(CONFIG)
    (git_repo / "docs/history").mkdir()
    (git_repo / "docs/history/old.md").write_text("PRIVATE BODY SENTINEL")
    (git_repo / "code.py").write_text("print('not an inventory source')")
    return git_repo


@pytest.mark.parametrize(
    "changes",
    [
        {"id": "Invalid ID"},
        {"id": None},
        {"mode": "required"},
        {"paths": ()},
        {"paths": ["AGENTS.md"]},
        {"paths": (None,)},
        {"paths": ("AGENTS.md", "AGENTS.md")},
        {"paths": ("../secret",)},
        {"paths": ("/absolute",)},
        {"paths": ("./AGENTS.md",)},
        {"paths": ("a//b",)},
        {"paths": ("a\\b",)},
        {"paths": ("C:drive",)},
        {"paths": ("a/",)},
        {"paths": ("a\0b",)},
        {"paths": (".",)},
        {"kinds": ("readme",)},
        {"authority_classes": ("plan",)},
        {"lifecycles": ("active",)},
        {"kinds": (SourceKind.README, SourceKind.README)},
        {"authority_classes": (AuthorityClass.PLAN, AuthorityClass.PLAN)},
        {"lifecycles": (LifecycleState.ACTIVE, LifecycleState.ACTIVE)},
        {"min_count": True},
        {"max_count": False},
        {"min_count": "1"},
        {"max_count": 1.0},
        {"min_count": -1},
        {"max_count": -1},
        {"min_count": 0},
        {"min_count": 2, "max_count": 1},
        {"mode": OPTIONAL, "min_count": 1},
        {"mode": EXCLUDED, "max_count": 1},
        {"mode": EXCLUDED, "min_count": 1},
    ],
)
def test_rule_model_rejects_invalid_direct_construction(changes):
    with pytest.raises(ValueError):
        rule(**changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"id": "Bad"},
        {"task_class": "Bad class"},
        {"description": " "},
        {"rules": ()},
        {"rules": [rule()]},
        {"rules": ("rule",)},
        {"rules": (rule(), rule())},
    ],
)
def test_contract_model_invariants(changes):
    with pytest.raises(ValueError):
        replace(contract(), **changes)


def test_repository_contract_invariants_and_discovery():
    with pytest.raises(ValueError):
        RepositoryConfig(context_contracts=(contract(), contract()))
    with pytest.raises(ValueError):
        RepositoryConfig(context_contracts=[contract()])
    assert effective_contracts(None) == ()
    with pytest.raises(ValueError, match="Unknown"):
        resolve_contract(None, "missing")
    c = contract()
    assert resolve_contract(RepositoryConfig(schema_version=5, context_contracts=(c,)), "test") == c


@pytest.mark.parametrize("version", [1, 2, 3, 4])
def test_repository_config_rejects_contracts_before_schema_v5(version):
    with pytest.raises(ValueError, match="schema v5"):
        RepositoryConfig(schema_version=version, context_contracts=(contract(),))


def test_repository_config_accepts_contracts_in_schema_v5():
    c = contract()
    assert RepositoryConfig(schema_version=5, context_contracts=(c,)).context_contracts == (c,)


@pytest.mark.parametrize(
    ("mode", "minimum", "maximum"),
    [
        (REQUIRED, 1, None),
        (OPTIONAL, 0, None),
        (EXCLUDED, 0, 0),
    ],
)
def test_default_counts(mode, minimum, maximum):
    r = rule(mode=mode)
    assert (r.min_count, r.max_count) == (minimum, maximum)


@pytest.mark.parametrize("version", [1, 2, 3, 4])
def test_old_config_versions_reject_contracts(version):
    with pytest.raises(ConfigurationError):
        parse_config(CONFIG.replace("schema_version = 5", f"schema_version = {version}").encode())


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ('task_class = "implementation"', 'task_class = "bad class"'),
        ('description = "Explicit implementation package"', 'description = " "'),
        ("max_count = 1", "max_count = true"),
        ("max_count = 1", "max_count = 0"),
        ("max_count = 1", "min_count = -1"),
        ('mode = "required"', 'mode = "maybe"'),
        ('paths = ["AGENTS.md"]', 'paths = ["../secret"]'),
        ('paths = ["AGENTS.md"]', 'paths = ["AGENTS.md", "./AGENTS.md"]'),
        ('paths = ["AGENTS.md"]', 'paths = "AGENTS.md"'),
        ('paths = ["AGENTS.md"]', "paths = []"),
        ('kinds = ["architecture"]', 'kinds = ["code_symbol"]'),
        ('authority_classes = ["architecture_product"]', 'authority_classes = ["best"]'),
        ('lifecycles = ["unknown", "active"]', 'lifecycles = ["stale"]'),
        ('id = "history"', 'id = "instructions"'),
        ("max_count = 1", 'authority_policy = "architectural_intent"'),
        ('description = "Explicit implementation package"', 'inherit = "secret-body"'),
    ],
)
def test_config_contract_errors_are_sanitized(old, new):
    with pytest.raises(ConfigurationError) as error:
        parse_config(CONFIG.replace(old, new, 1).encode())
    assert str(error.value) == "Invalid .context-integrity.toml configuration."


def test_config_v5_retains_prior_features_and_revision():
    data = (
        CONFIG
        + """
[[authority.policies]]
id = "custom"
description = "Policy"
tiers = [["plan"]]
[[source_metadata]]
path = "AGENTS.md"
lifecycle = "active"
reason = "Current"
[[supersession]]
source = "old.md"
superseded_by = "new.md"
reason = "Replaced"
[[claims]]
id = "claim"
claim_type = "intent"
subject = "task"
predicate = "requires"
value = "context"
[instruction_policy]
canonical = "AGENTS.md"
compatibility = ["CLAUDE.md"]
[[drift_dependencies]]
id = "docs"
dependent = "README.md"
upstream = ["docs/architecture.md"]
reason = "Review"
"""
    )
    config = parse_config(data.encode())
    assert config.schema_version == 5
    assert config.policies and config.source_metadata and config.supersession and config.claims
    assert config.instruction_policy and config.drift_dependencies
    assert config.context_contracts[0].config_revision == sha256(data.encode()).hexdigest()
    assert parse_config(
        CONFIG.replace('paths = ["AGENTS.md"]', 'paths = ["./AGENTS.md"]').encode()
    ).context_contracts
    duplicate = CONFIG + CONFIG[CONFIG.index("[[context_contracts]]") :]
    with pytest.raises(ConfigurationError):
        parse_config(duplicate.encode())


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({}, True),
        ({"paths": ("other.md", "docs/architecture.md")}, True),
        ({"paths": ("docs",)}, False),
        ({"kinds": (SourceKind.README, SourceKind.ARCHITECTURE)}, True),
        ({"kinds": (SourceKind.README,)}, False),
        (
            {"authority_classes": (AuthorityClass.DECISION, AuthorityClass.ARCHITECTURE_PRODUCT)},
            True,
        ),
        ({"authority_classes": (AuthorityClass.PLAN,)}, False),
        ({"lifecycles": (LifecycleState.ACTIVE, LifecycleState.UNKNOWN)}, True),
        ({"lifecycles": (LifecycleState.ACTIVE,)}, False),
        ({"kinds": (SourceKind.ARCHITECTURE,), "lifecycles": (LifecycleState.HISTORICAL,)}, False),
    ],
)
def test_selector_and_or_exact_semantics(git_repo, changes, expected):
    source = next(s for s in scan_repository(git_repo).sources if s.path == "docs/architecture.md")
    assert matches_rule(source, rule(**{"paths": (source.path,), **changes})) is expected


@pytest.mark.parametrize(
    ("mode", "minimum", "maximum", "paths", "code"),
    [
        (REQUIRED, None, None, (), "required_context_missing"),
        (REQUIRED, 2, None, ("AGENTS.md",), "required_context_missing"),
        (REQUIRED, None, 1, ("AGENTS.md", "docs/architecture.md"), "context_rule_overfilled"),
        (OPTIONAL, None, 0, ("AGENTS.md",), "context_rule_overfilled"),
        (OPTIONAL, None, None, (), None),
        (EXCLUDED, None, None, (), None),
        (EXCLUDED, None, None, ("AGENTS.md",), "excluded_context_present"),
        (REQUIRED, None, 1, ("AGENTS.md",), None),
    ],
)
def test_rule_cardinality(git_repo, mode, minimum, maximum, paths, code):
    r = rule(
        paths=("AGENTS.md", "docs/architecture.md"), mode=mode, min_count=minimum, max_count=maximum
    )
    manifest = bind_contract(scan_repository(git_repo), contract(r))
    result = validate_contract(manifest, contract(r), paths)
    assert [f.code for f in result.findings] == ([code] if code else [])
    assert result.rule_results[0].satisfied is (code is None)


def test_package_resolution_and_determinism(contract_repo):
    manifest = scan_repository(contract_repo)
    c = resolve_contract(manifest.repository_config, "implementation")
    paths = ("./AGENTS.md", "AGENTS.md", "missing.md", "code.py", "docs/history/old.md")
    result = validate_contract(manifest, c, paths)
    assert [r.rule_id for r in result.rule_results] == ["architecture", "history", "instructions"]
    assert result.package.duplicate_paths == ("AGENTS.md",)
    assert result.package.unresolved_paths == ("code.py", "missing.md")
    assert result.rule_results[-1].match_count == 1
    assert [f.code for f in result.findings] == [
        "package_source_unavailable",
        "package_source_unavailable",
        "excluded_context_present",
    ]
    assert [w.code for w in result.warnings] == ["duplicate_package_source"]
    repeated = validate_contract(scan_repository(contract_repo), c, tuple(reversed(paths)))
    assert render_contract_validation_json(result) == render_contract_validation_json(repeated)
    assert (
        _finding("c", "r", "code", ("AGENTS.md",), "one").id
        == _finding("c", "r", "code", ("AGENTS.md",), "two").id
    )
    assert (
        validate_contract(
            bind_contract(manifest, contract(rule(paths=("docs/history/old.md",)))),
            contract(rule(paths=("docs/history/old.md",))),
            ("docs/history/old.md",),
        ).findings
        == ()
    )
    assert "FAIL history" in render_contract_validation_text(result)


def test_validation_binds_contract_and_provenance_to_manifest_config(contract_repo):
    manifest = scan_repository(contract_repo)
    configured = resolve_contract(manifest.repository_config, "implementation")
    result = validate_contract(manifest, configured, ("AGENTS.md",))
    assert result.config_sha256 == manifest.repository_config.content_sha256
    assert result.contract.config_revision == manifest.repository_config.content_sha256

    foreign = replace(configured, id="foreign")
    modified = replace(configured, description="Modified after observation")
    stale_revision = replace(configured, config_revision="0" * 64)
    for candidate in (foreign, modified, stale_revision):
        with pytest.raises(ValueError, match="not bound"):
            validate_contract(manifest, candidate, ("AGENTS.md",))


@pytest.mark.parametrize("path", ["../secret", "/absolute", "C:drive", "a\\b", "a\0b", ".", "a/"])
def test_package_path_rejection(git_repo, path):
    with pytest.raises(ValueError):
        validate_contract(bind_contract(scan_repository(git_repo), contract()), contract(), (path,))


def test_json_golden_and_privacy(git_repo):
    c = contract()
    result = validate_contract(
        bind_contract(scan_repository(git_repo), c), c, ("AGENTS.md", "missing.md")
    )
    rendered = render_contract_validation_json(result)
    assert rendered == (Path(__file__).parent / "fixtures/contracts-v1.json").read_text()
    assert str(git_repo) not in rendered and "Instructions" not in rendered
    assert "observed_at" not in rendered and rendered.endswith("\n")
    assert set(contract_validation_dict(result)) == {
        "schema_version",
        "repository",
        "config_sha256",
        "contract",
        "package",
        "rules",
        "findings",
        "warnings",
    }
    with pytest.raises(ValueError):
        render_contract_validation_json(replace(result, schema_version=2))
    unsafe = replace(contract(), description="line\n\x1b[31m")
    assert "line\\n" in render_contracts((unsafe,), detail=True)
    assert "\x1b" not in render_contracts((unsafe,), detail=True)


def test_cli_contract_flow_and_exits(contract_repo, tmp_path):
    runner = CliRunner()
    root = str(contract_repo)
    for args in (
        ["list", root],
        ["show", "implementation", root],
        ["validate", "implementation", root, "--source", "AGENTS.md"],
        ["validate", "implementation", root],
    ):
        text = runner.invoke(app, ["contracts", *args])
        assert text.exit_code == 0, text.output
        result = runner.invoke(app, ["contracts", *args, "--format", "json"])
        assert result.exit_code == 0, result.output
        assert json.loads(result.stdout)["schema_version"] == 1
        output = tmp_path / "result.json"
        saved = runner.invoke(
            app, ["contracts", *args, "--format", "json", "--output", str(output)]
        )
        assert saved.exit_code == 0 and saved.stdout == ""
        assert output.read_text() == result.stdout
        assert runner.invoke(app, ["contracts", *args, "--output", str(tmp_path)]).exit_code == 4
    empty = runner.invoke(
        app, ["contracts", "validate", "implementation", root, "--format", "json"]
    )
    assert json.loads(empty.stdout)["findings"][0]["code"] == "required_context_missing"
    assert runner.invoke(app, ["contracts", "show", "missing", root]).exit_code == 2
    assert runner.invoke(app, ["contracts", "validate", "missing", root]).exit_code == 2
    invalid = runner.invoke(
        app, ["contracts", "validate", "implementation", root, "--source", "/secret/sentinel"]
    )
    assert invalid.exit_code == 2 and "/secret/sentinel" not in invalid.output
    assert runner.invoke(app, ["contracts", "list", str(tmp_path / "missing")]).exit_code == 3
    (contract_repo / ".context-integrity.toml").write_text("schema_version = 8")
    assert runner.invoke(app, ["contracts", "list", root]).exit_code == 6


def test_cli_no_contracts(git_repo):
    result = CliRunner().invoke(app, ["contracts", "list", str(git_repo), "--format", "json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout) == {"schema_version": 1, "contracts": []}
