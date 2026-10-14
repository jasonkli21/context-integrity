"""Policy semantics, metadata, stable projections, and CLI on small local repositories."""

import json
import os
from dataclasses import dataclass, replace
from pathlib import Path

import pytest
from typer.testing import CliRunner

from context_integrity.authority import BUILTIN_POLICIES, effective_policies, resolve_authority
from context_integrity.cli import app
from context_integrity.configuration import CONFIG_PATH, ConfigurationError, parse_config
from context_integrity.inventory import scan_repository
from context_integrity.models import AuthorityClass as A
from context_integrity.models import (
    AuthorityPolicy,
    AuthorityTier,
    RepositoryAuthorityConfig,
    RepositoryRef,
    SourceAuthorityMetadata,
)
from context_integrity.rendering import (
    authority_dict,
    render_authority_json,
    render_authority_text,
    render_explanation,
    render_policy,
    render_policy_list,
)

EXPECTED = {
    "delivered_behavior": [
        ["executable_truth"],
        ["verification_evidence"],
        ["generated_derivative"],
    ],
    "architectural_intent": [["decision"], ["architecture_product"], ["plan"]],
    "operating_instructions": [["operating_instruction"], ["architecture_product"], ["plan"]],
    "implementation_status": [["verification_evidence"], ["generated_derivative"], ["plan"]],
    "future_work": [["plan"], ["architecture_product"], ["generated_derivative"]],
}


def write(root, path, body=b"Source body must never appear in authority JSON\n"):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body)


@pytest.fixture
def authority_repo(tmp_path):
    for path in [
        "AGENTS.md",
        "docs/architecture.md",
        "docs/prd.md",
        "docs/adr/0001.md",
        "docs/adr/0002.md",
        "docs/plans/phase-1.md",
        "docs/verification/check.md",
        "docs/current-state.md",
        "docs/history/old-architecture.md",
        "docs/misc.md",
    ]:
        write(tmp_path, path)
    return tmp_path


def policy(id):
    return next(p for p in BUILTIN_POLICIES if p.id == id)


def test_exact_builtin_set():
    actual = {p.id: [[c.value for c in t.classes] for t in p.tiers] for p in BUILTIN_POLICIES}
    assert actual == EXPECTED
    assert all(p.origin == "builtin" and p.policy_version == "builtin-v1" for p in BUILTIN_POLICIES)
    listed = effective_policies()
    assert [p.id for p in listed] == sorted(EXPECTED)
    assert render_policy_list(listed) == render_policy_list(effective_policies())
    assert A.EXECUTABLE_TRUTH == "executable_truth"


@pytest.mark.parametrize(
    "id,highest,paths",
    [
        ("architectural_intent", 0, ["docs/adr/0001.md", "docs/adr/0002.md"]),
        ("delivered_behavior", 1, ["docs/verification/check.md"]),
        ("operating_instructions", 0, ["AGENTS.md"]),
        ("implementation_status", 0, ["docs/verification/check.md"]),
        ("future_work", 0, ["docs/plans/phase-1.md"]),
    ],
)
def test_resolution_policies(authority_repo, id, highest, paths):
    result = resolve_authority(scan_repository(authority_repo), policy(id))
    assert result.status == "candidates_found"
    assert result.highest_observed_tier == highest
    assert [c.source.path for c in result.highest_candidates] == paths
    assert result.missing_stronger_tiers == tuple(range(highest))
    assert all(c.tier_index > highest for c in result.lower_candidates)
    assert any(e.reason == "historical_lifecycle" for e in result.excluded)
    assert any(e.reason == "not_in_policy" for e in result.excluded)
    assert len(result.highest_candidates + result.lower_candidates) + len(result.excluded) == 10


@pytest.mark.parametrize("classes", [(), (A.PLAN, A.PLAN), (A.UNKNOWN,), (A.HISTORICAL,)])
def test_invalid_tier(classes):
    with pytest.raises(ValueError):
        AuthorityTier(classes)


@pytest.mark.parametrize("id", ["Upper", "1bad", "has space", "é", "", "../escape"])
def test_invalid_policy_id(id):
    with pytest.raises(ValueError):
        AuthorityPolicy(id, "Description", (AuthorityTier((A.PLAN,)),))


def test_duplicate_class_across_tiers():
    with pytest.raises(ValueError):
        AuthorityPolicy("duplicate", "Description", (AuthorityTier((A.PLAN,)),) * 2)
    with pytest.raises(ValueError):
        AuthorityPolicy("empty", "Description", ())


def test_equal_tier_and_no_recency(authority_repo):
    manifest = scan_repository(authority_repo)
    equal = AuthorityPolicy("equal", "Equal roles", (AuthorityTier((A.PLAN, A.DECISION)),))
    before = resolve_authority(manifest, equal)
    assert [c.source.path for c in before.highest_candidates] == [
        "docs/adr/0001.md",
        "docs/adr/0002.md",
        "docs/plans/phase-1.md",
    ]
    os.utime(authority_repo / "docs/adr/0002.md", (1, 1))
    after = resolve_authority(scan_repository(authority_repo), equal)
    assert render_authority_json(before) == render_authority_json(after)
    shuffled = replace(manifest, sources=tuple(reversed(manifest.sources)))
    assert resolve_authority(shuffled, equal) == before


def test_no_candidates(tmp_path):
    result = resolve_authority(scan_repository(tmp_path), policy("delivered_behavior"))
    assert result.status == "no_eligible_candidates"
    assert result.highest_observed_tier is None
    assert result.highest_candidates == result.lower_candidates == ()
    assert result.missing_stronger_tiers == (0, 1, 2)


CONFIG = b"""schema_version=1
[[authority.policies]]
id="architectural_intent"
description="Prefer curated verification"
tiers=[["verification_evidence"], ["decision", "architecture_product"]]
[[authority.policies]]
id="custom"
description="Custom order"
tiers=[["plan"]]
[[source_metadata]]
path="docs/adr/0001.md"
authority_eligible=false
reason="Template"
[[source_metadata]]
path="docs/misc.md"
authority_class="verification_evidence"
reason="Curated verification"
[[source_metadata]]
path="docs/history/old-architecture.md"
authority_class="decision"
authority_eligible=true
reason="Class override cannot undo historical lifecycle"
[[source_metadata]]
path="docs/absent.md"
authority_eligible=false
reason="Stale entry"
"""


def test_metadata_and_policy_merge(authority_repo):
    write(authority_repo, CONFIG_PATH, CONFIG)
    manifest = scan_repository(authority_repo)
    policies = effective_policies(manifest.authority_config)
    assert [p.id for p in policies] == sorted([*EXPECTED, "custom"])
    selected = next(p for p in policies if p.id == "architectural_intent")
    assert selected.origin == "repository_config"
    assert selected.tiers == (
        AuthorityTier((A.VERIFICATION_EVIDENCE,)),
        AuthorityTier((A.DECISION, A.ARCHITECTURE_PRODUCT)),
    )
    assert selected.description == "Prefer curated verification"
    assert selected.policy_version == "config-v1"
    assert len(selected.tiers) == 2
    assert all(
        p == policy(p.id) for p in policies if p.id not in {"architectural_intent", "custom"}
    )
    result = resolve_authority(manifest, selected)
    assert [c.source.path for c in result.highest_candidates] == [
        "docs/misc.md",
        "docs/verification/check.md",
    ]
    excluded = {e.source.path: e for e in result.excluded}
    assert excluded["docs/adr/0001.md"].reason == "explicitly_ineligible"
    assert excluded["docs/history/old-architecture.md"].reason == "historical_lifecycle"
    assert excluded["docs/history/old-architecture.md"].source.authority_class == "decision"
    assert excluded["docs/history/old-architecture.md"].source.lifecycle == "historical"
    assert [w.code for w in result.warnings] == ["authority_metadata_source_missing"]
    misc = next(s for s in manifest.sources if s.path == "docs/misc.md")
    assert misc.kind == "other_document"
    assert misc.classification.confidence == "unknown"
    assert misc.classification.basis[-1].confidence == "explicit"
    assert misc.classification.basis[-1].rule_id == "authority.metadata.repository_override"
    assert misc.authority_class == misc.classification.authority_class == "verification_evidence"
    explanation = render_explanation(excluded["docs/adr/0001.md"].source)
    assert "authority_eligible: false" in explanation and "Template" in explanation


def test_eligibility_omission_defaults_true(authority_repo):
    manifest = scan_repository(authority_repo)
    metadata = (SourceAuthorityMetadata("docs/adr/0001.md", "Eligible", authority_eligible=True),)
    result = resolve_authority(manifest, policy("architectural_intent"), metadata)
    assert len(result.highest_candidates) == 2


def test_unknown_override_allowed(authority_repo):
    write(
        authority_repo,
        CONFIG_PATH,
        b"""schema_version=1
[[source_metadata]]
path="docs/adr/0001.md"
authority_class="unknown"
reason="Not accepted"
""",
    )
    manifest = scan_repository(authority_repo)
    result = resolve_authority(manifest, policy("architectural_intent"))
    assert [c.source.path for c in result.highest_candidates] == ["docs/adr/0002.md"]


def test_rendering_terminal_controls(authority_repo):
    config = parse_config(
        CONFIG.replace(b'Curated verification"', b'Curated\\u001b[31m\\nverification"')
    )
    write(
        authority_repo,
        CONFIG_PATH,
        CONFIG.replace(b'Curated verification"', b'Curated\\u001b[31m\\nverification"'),
    )
    manifest = scan_repository(authority_repo)
    selected = effective_policies(config)[0]
    hostile = replace(selected, description="Description\x1b[31m\nInjected row")
    output = render_policy(hostile) + render_policy_list((hostile,))
    output += render_authority_text(resolve_authority(manifest, selected))
    output += "".join(render_explanation(s) for s in manifest.sources)
    assert "\x1b" not in output
    assert r"\u001b" in output
    assert "claim correctness or agreement" in output


def test_authority_projection_explicit(authority_repo):
    @dataclass(frozen=True)
    class ExtendedPolicy(AuthorityPolicy):
        private_body: str = "Never serialize"

    result = resolve_authority(scan_repository(authority_repo), policy("architectural_intent"))
    base = result.policy
    extended = ExtendedPolicy(base.id, base.description, base.tiers)
    data = authority_dict(replace(result, policy=extended))
    assert set(data) == {
        "schema_version",
        "repository",
        "policy",
        "config_sha256",
        "status",
        "highest_observed_tier",
        "missing_stronger_tiers",
        "highest_candidates",
        "lower_candidates",
        "excluded",
        "warnings",
    }
    assert set(data["policy"]) == {
        "id",
        "description",
        "origin",
        "policy_version",
        "config_sha256",
        "tiers",
    }
    assert set(data["highest_candidates"][0]) == {
        "source_id",
        "path",
        "kind",
        "authority_class",
        "lifecycle",
        "revision",
        "tier_index",
    }
    text = render_authority_json(result)
    assert str(authority_repo) not in text
    assert "Source body must never" not in text and "Never serialize" not in json.dumps(data)
    assert "observed_at" not in text and text.endswith("\n")


@pytest.mark.parametrize("scenario", ["architecture", "missing-executable", "config"])
def test_authority_golden(authority_repo, scenario):
    if scenario == "config":
        write(authority_repo, CONFIG_PATH, CONFIG)
    manifest = scan_repository(authority_repo)
    # Fixed identity isolates the public projection from temporary directory names.
    manifest = replace(
        manifest,
        repository=RepositoryRef("repo_fixture", "authority-fixture", "fixture", False, None, None),
        sources=tuple(replace(s, id="src_" + s.path) for s in manifest.sources),
    )
    id = "delivered_behavior" if scenario == "missing-executable" else "architectural_intent"
    selected = next(p for p in effective_policies(manifest.authority_config) if p.id == id)
    rendered = render_authority_json(resolve_authority(manifest, selected))
    golden = Path(__file__).parent / "fixtures" / f"authority-v1-{scenario}.json"
    assert rendered == golden.read_text()


runner = CliRunner()


@pytest.mark.parametrize(
    "command",
    [
        ["authority", "list"],
        ["authority", "show", "architectural_intent"],
        ["authority", "resolve", "delivered_behavior"],
    ],
)
@pytest.mark.parametrize("format", ["text", "json"])
def test_cli_commands(authority_repo, command, format):
    result = runner.invoke(app, [*command, str(authority_repo), "--format", format])
    assert result.exit_code == 0, result.output
    if format == "json":
        assert json.loads(result.stdout)
    if "resolve" in command and format == "text":
        assert "claim correctness or agreement" in result.output
        assert "Highest observed tier: 1" in result.output
        assert "0: executable_truth" in result.output


def test_cli_output_and_errors(tmp_path):
    output = tmp_path / "result.json"
    result = runner.invoke(
        app,
        [
            "authority",
            "resolve",
            "future_work",
            str(tmp_path),
            "--format",
            "json",
            "--output",
            str(output),
        ],
    )
    assert result.exit_code == 0
    assert json.loads(output.read_text())["status"] == "no_eligible_candidates"
    result = runner.invoke(app, ["authority", "resolve", "bad", str(tmp_path)])
    assert result.exit_code == 2
    result = runner.invoke(app, ["authority", "show", "bad", str(tmp_path)])
    assert result.exit_code == 2
    result = runner.invoke(
        app, ["authority", "resolve", "future_work", str(tmp_path), "--output", str(tmp_path)]
    )
    assert result.exit_code == 4
    assert runner.invoke(app, ["authority", "--help"]).exit_code == 0


@pytest.mark.parametrize(
    "command",
    [
        ["scan"],
        ["authority", "list"],
        ["authority", "show", "future_work"],
        ["authority", "resolve", "future_work"],
        ["explain", "AGENTS.md", "--root"],
    ],
)
def test_cli_config_error_exit_6(tmp_path, command):
    write(tmp_path, CONFIG_PATH, b"invalid TOML")
    result = runner.invoke(app, [*command, str(tmp_path)])
    assert result.exit_code == 6
    assert "configuration" in result.output


def test_cli_scan_and_explain_metadata(authority_repo):
    write(authority_repo, CONFIG_PATH, CONFIG)
    result = runner.invoke(app, ["scan", str(authority_repo), "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert "authority_config" not in data
    sources = {s["path"]: s for s in data["sources"]}
    assert sources["docs/misc.md"]["authority_class"] == "verification_evidence"
    assert "authority_metadata" not in sources["docs/misc.md"]
    result = runner.invoke(app, ["explain", "docs/adr/0001.md", "--root", str(authority_repo)])
    assert result.exit_code == 0
    assert "authority_eligible: false" in result.output
    assert "Template" in result.output


def test_custom_policy_addition():
    custom = AuthorityPolicy("custom", "Custom", (AuthorityTier((A.PLAN,)),))
    merged = effective_policies(RepositoryAuthorityConfig(policies=(custom,)))
    assert len(merged) == 6
    assert next(p for p in merged if p.id == "custom") == custom
    assert next(p for p in merged if p.id == "future_work") == policy("future_work")


def test_source_metadata_cannot_synthesize_reserved_authority_classes(authority_repo):
    delivered = resolve_authority(scan_repository(authority_repo), policy("delivered_behavior"))
    assert delivered.highest_observed_tier == 1
    assert delivered.missing_stronger_tiers == (0,)
    assert delivered.highest_candidates[0].source.authority_class == A.VERIFICATION_EVIDENCE

    for authority_class in ("executable_truth", "historical"):
        write(
            authority_repo,
            CONFIG_PATH,
            f"""schema_version=1
[[source_metadata]]
path="docs/verification/check.md"
authority_class="{authority_class}"
reason="Must be rejected"
""".encode(),
        )
        with pytest.raises(ConfigurationError, match=r"Invalid \.context-integrity\.toml"):
            scan_repository(authority_repo)


@pytest.mark.parametrize("authority_class", ["executable_truth", "historical"])
def test_cli_reserved_source_metadata_class_exits_6(tmp_path, authority_class):
    write(
        tmp_path,
        CONFIG_PATH,
        f"""schema_version=1
[[source_metadata]]
path="docs/verification/check.md"
authority_class="{authority_class}"
reason="Must be rejected"
""".encode(),
    )
    result = runner.invoke(app, ["authority", "resolve", "delivered_behavior", str(tmp_path)])
    assert result.exit_code == 6
    assert "configuration" in result.output


def test_explain_limits_authority_wording_to_this_command(authority_repo):
    explanation = render_explanation(scan_repository(authority_repo).sources[0])
    assert (
        "authority policy resolution in this explanation (see `authority resolve`)" in explanation
    )
    assert "authority precedence" not in explanation


def test_cli_config_symlink_exit_6(tmp_path):
    (tmp_path / CONFIG_PATH).symlink_to(tmp_path / "missing")
    result = runner.invoke(app, ["authority", "list", str(tmp_path)])
    assert result.exit_code == 6
    assert str(tmp_path) not in result.output
