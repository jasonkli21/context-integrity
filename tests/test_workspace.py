"""Synthetic independent repositories prove workspace identity, policy and safety."""

import json
import subprocess
from hashlib import sha256

import pytest

from context_integrity.derived_models import canonical_json
from context_integrity.repository import RepositoryError, discover_repository
from context_integrity.workspace import resolve_workspace
from context_integrity.workspace_config import WorkspaceInputError, parse_lock, parse_workspace
from context_integrity.workspace_models import ContractLock, QualifiedClaimRef, QualifiedSourceRef
from context_integrity.workspace_output import check_dict, context_dict

BODY = b"PRIVATE_SOURCE_BODY\r\n\xff"
CLAIMS = """schema_version = 6
[[source_metadata]]
path = "docs/architecture.md"
lifecycle = "active"
reason = "current"
[[claims]]
id = "region"
claim_type = "policy"
subject = "product"
predicate = "stores_in"
scope = "data"
value = "us"
depends_on = ["docs/architecture.md"]
[[context_contracts]]
id = "work"
task_class = "implementation"
description = "Required architecture"
[[context_contracts.rules]]
mode = "required"
id = "architecture"
paths = ["docs/architecture.md"]
"""


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def write(root, path, data):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data.encode() if isinstance(data, str) else data)
    return target


def commit(root):
    git(root, "add", ".")
    git(
        root,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.org",
        "commit",
        "-qm",
        "fixture",
    )


@pytest.fixture
def workspace(tmp_path):
    # Canonical host ancestors avoid intentionally unsupported /tmp symlink aliases.
    tmp_path = tmp_path.resolve()
    repos = [tmp_path / "api", tmp_path / "web"]
    for i, root in enumerate(repos):
        root.mkdir()
        git(root, "init", "-q")
        git(root, "remote", "add", "origin", f"https://example.org/workspace-{i}.git")
        write(root, "docs/architecture.md", BODY)
        write(root, "spec/api.json", b"{}\n")
        write(root, ".context-integrity.toml", CLAIMS)
        commit(root)
    ids = [discover_repository(r).repository.id for r in repos]
    lock = {
        "contract_lock_schema_version": 1,
        "producer_repository_id": ids[0],
        "producer_path": "spec/api.json",
        "accepted_sha256": sha256(b"{}\n").hexdigest(),
    }
    write(repos[1], "contracts/api.lock.json", canonical_json(lock))
    commit(repos[1])
    manifest = write(
        tmp_path,
        "workspace.context-integrity.toml",
        f'''workspace_schema_version = 1
[[repositories]]
alias = "api"
root = "api"
repository_id = "{ids[0]}"
[[repositories]]
alias = "web"
root = "web"
repository_id = "{ids[1]}"
[[checks]]
id = "pin"
kind = "contract_pin"
producer_repo = "api"
producer_path = "spec/api.json"
consumer_repo = "web"
consumer_path = "contracts/api.lock.json"
[[checks]]
id = "mirror"
kind = "mirror_bytes"
left_repo = "api"
left_path = "docs/architecture.md"
right_repo = "web"
right_path = "docs/architecture.md"
[[checks]]
id = "claims"
kind = "claim_match"
left_repo = "api"
left_claim_id = "region"
right_repo = "web"
right_claim_id = "region"
[[context_targets]]
repo = "api"
contract_id = "work"
budget_bytes = 10000
[[context_targets]]
repo = "web"
contract_id = "work"
budget_bytes = 10000
''',
    )
    return manifest, *repos


def report(manifest):
    workspace = resolve_workspace(manifest)
    return check_dict(workspace, workspace.check())


def by_id(value, id):
    return next(f for f in value["findings"] if f["id"] == id)


def codes(finding):
    return {r["code"] for r in finding["reasons"]}


def test_three_checks_qualified_provenance_and_determinism(workspace):
    manifest, api, _web = workspace
    value = report(manifest)
    assert value["status"] == "aligned_observed"
    assert report(manifest) == value
    mirror = by_id(value, "mirror")
    assert len({s["source_id"] for s in mirror["sources"]}) == 2
    assert {s["source"]["path"] for s in mirror["sources"]} == {"docs/architecture.md"}
    claims = by_id(value, "claims")["claims"]
    assert len({c["claim"]["repository_id"] for c in claims}) == 2
    assert all(c["validity"] == "unverified" for c in claims)
    rendered = canonical_json(value)
    assert str(api.parent) not in rendered and "PRIVATE_SOURCE_BODY" not in rendered
    assert "https://" not in rendered
    assert "consumer_implementation_not_verified" in codes(by_id(value, "pin"))


@pytest.mark.parametrize("staged", [False, True])
def test_dirty_contract_content_unchanged_head(workspace, staged):
    manifest, api, _ = workspace
    head = discover_repository(api).repository.git_head
    write(api, "spec/api.json", b'{"changed":true}\n')
    if staged:
        git(api, "add", "spec/api.json")
    value = report(manifest)
    assert value["status"] == "review_required"
    pin = by_id(value, "pin")
    assert "producer_contract_revision_changed" in codes(pin)
    assert pin["sources"][0]["content_sha256"] != pin["accepted_sha256"]
    assert discover_repository(api).repository.git_head == head
    write(api, "spec/api.json", b"{}\n")
    assert by_id(report(manifest), "pin")["signal"] == "aligned"


def test_mismatch_and_independent_uncertainty_retained(workspace):
    manifest, api, web = workspace
    write(api, "spec/api.json", b"changed")
    (web / "docs/architecture.md").unlink()
    (web / "docs/architecture.md").symlink_to(api / "docs/architecture.md")
    value = report(manifest)
    assert value["status"] == "review_required"
    assert by_id(value, "mirror")["signal"] == "not_established"
    assert by_id(value, "claims")["signal"] == "not_established"


@pytest.mark.parametrize(
    "mode,signal,reason",
    [
        ("different_value", "declared_disagreement", "declared_claim_disagreement"),
        ("different_subject", "not_established", "not_comparable"),
        ("different_scope", "not_established", "not_comparable"),
        ("historical", "not_established", "claim_provenance_not_active"),
        ("missing_claim", "not_established", "claim_missing"),
        ("missing_config", "not_established", "claim_missing"),
        ("missing_dependency", "not_established", "claim_evidence_incomplete"),
        ("changed_dependency", "not_established", "claim_dependency_changed_or_unknown"),
    ],
)
def test_claim_comparability_and_coverage(workspace, mode, signal, reason):
    manifest, _, web = workspace
    config = web / ".context-integrity.toml"
    replacements = {
        "different_value": ('value = "us"', 'value = "eu"'),
        "different_subject": ('subject = "product"', 'subject = "other"'),
        "different_scope": ('scope = "data"', 'scope = "other"'),
        "historical": ('lifecycle = "active"', 'lifecycle = "historical"'),
        "missing_claim": ('id = "region"', 'id = "other"'),
    }
    if mode in replacements:
        config.write_text(config.read_text().replace(*replacements[mode]))
    elif mode == "missing_config":
        config.unlink()
    elif mode == "missing_dependency":
        (web / "docs/architecture.md").unlink()
    else:
        write(web, "docs/architecture.md", b"changed")
    finding = by_id(report(manifest), "claims")
    assert finding["signal"] == signal
    assert reason in codes(finding)
    assert "claims_unverified" in codes(finding)


@pytest.mark.parametrize(
    "mode,state",
    [
        ("missing", "missing"),
        ("directory", "unobservable"),
        ("symlink", "unobservable"),
        ("parent_symlink", "unobservable"),
        ("large", "too_large"),
    ],
)
def test_file_acquisition_failures(workspace, mode, state):
    manifest, api, web = workspace
    target = api / "spec/api.json"
    target.unlink()
    if mode == "directory":
        target.mkdir()
    elif mode == "symlink":
        target.symlink_to(web / "spec/api.json")
    elif mode == "parent_symlink":
        target.parent.rmdir()
        target.parent.symlink_to(web / "spec", target_is_directory=True)
    elif mode == "large":
        target.write_bytes(b"x" * (5 * 1024 * 1024 + 1))
    value = by_id(report(manifest), "pin")
    assert value["sources"][0]["state"] == state
    assert value["signal"] == ("review_required" if mode == "missing" else "not_established")


@pytest.mark.parametrize(
    "mutation",
    [
        lambda s: s.replace("workspace_schema_version = 1", "workspace_schema_version = true"),
        lambda s: s.replace("workspace_schema_version = 1", "workspace_schema_version = 2"),
        lambda s: "unknown = 1\n" + s,
        lambda s: s.replace('alias = "web"', 'alias = "api"'),
        lambda s: s.replace('root = "api"', 'root = "/absolute"'),
        lambda s: s.replace('root = "api"', 'root = "https://host/repo"'),
        lambda s: s.replace('left_path = "docs/architecture.md"', 'left_path = "../secret"'),
        lambda s: s.replace('left_path = "docs/architecture.md"', 'left_path = ".git/config"'),
        lambda s: s.replace('left_path = "docs/architecture.md"', 'left_path = "docs/./file"'),
        lambda s: s.replace('left_path = "docs/architecture.md"', 'left_path = "döcs/file"'),
        lambda s: s.replace('left_repo = "api"', 'left_repo = "missing"'),
        lambda s: s.replace('id = "mirror"', 'id = "pin"'),
        lambda s: s.replace("budget_bytes = 10000", "budget_bytes = true"),
        lambda s: s.replace("budget_bytes = 10000", "budget_bytes = 0"),
        lambda s: s.replace("budget_bytes = 10000", "budget_bytes = 67108864"),
        lambda s: s.replace("repository_id = ", "missing_id = ", 1),
    ],
)
def test_strict_manifest(workspace, mutation):
    manifest, *_ = workspace
    with pytest.raises(WorkspaceInputError, match="invalid_workspace_manifest"):
        parse_workspace(mutation(manifest.read_text()).encode())


@pytest.mark.parametrize(
    "data",
    [
        b"{",
        b"[]",
        b"null",
        b"\xff",
        b"{" * 2000,
        b"x" * 16385,
        b'{"contract_lock_schema_version":1,"contract_lock_schema_version":1}',
    ],
)
def test_invalid_lock_bytes(data):
    with pytest.raises(WorkspaceInputError, match="invalid_contract_lock"):
        parse_lock(data)


@pytest.mark.parametrize(
    "field,bad",
    [
        ("contract_lock_schema_version", True),
        ("contract_lock_schema_version", 2),
        ("accepted_sha256", "A" * 64),
        ("producer_path", "../secret"),
        ("producer_repository_id", "bogus"),
        ("unknown", 1),
    ],
)
def test_strict_lock_shape(workspace, field, bad):
    _, _, web = workspace
    data = json.loads((web / "contracts/api.lock.json").read_bytes())
    data[field] = bad
    with pytest.raises(WorkspaceInputError):
        parse_lock(json.dumps(data).encode())


def test_wrong_lock_binding_is_input_failure(workspace):
    manifest, _, web = workspace
    path = web / "contracts/api.lock.json"
    path.write_text(path.read_text().replace('"spec/api.json"', '"spec/other.json"'))
    with pytest.raises(WorkspaceInputError, match="contract_lock_producer_mismatch"):
        report(manifest)


@pytest.mark.parametrize(
    "mode", ["wrong_id", "same_origin", "subdirectory", "duplicate_root", "nested", "root_link"]
)
def test_repository_binding_and_boundaries(workspace, mode):
    manifest, api, web = workspace
    data = manifest.read_text()
    if mode == "wrong_id":
        data = data.replace(discover_repository(api).repository.id, "repo_" + "0" * 32)
    elif mode == "same_origin":
        git(web, "remote", "set-url", "origin", "https://example.org/workspace-0.git")
    elif mode == "subdirectory":
        data = data.replace('root = "api"', 'root = "api/docs"')
    elif mode == "duplicate_root":
        data = data.replace('root = "web"', 'root = "api"')
    elif mode == "nested":
        nested = api / "nested"
        web.rename(nested)
        data = data.replace('root = "web"', 'root = "api/nested"')
    else:
        alias = api.parent / "alias"
        alias.symlink_to(api, target_is_directory=True)
        data = data.replace('root = "api"', 'root = "alias"')
    manifest.write_text(data)
    with pytest.raises(RepositoryError):
        resolve_workspace(manifest)


def test_zero_checks_no_global_compliance(workspace):
    manifest, *_ = workspace
    data = manifest.read_text()
    manifest.write_text(data[: data.index("[[checks]]")])
    value = report(manifest)
    assert value["status"] == "inconclusive"
    assert "no_checks_declared" in value["coverage"]["limitations"]


def test_sibling_roots_and_local_identity(workspace):
    manifest, api, web = workspace
    for root in (api, web):
        old = discover_repository(root).repository.id
        git(root, "remote", "remove", "origin")
        manifest.write_text(
            manifest.read_text().replace(old, discover_repository(root).repository.id)
        )
    lock_path = web / "contracts/api.lock.json"
    lock = json.loads(lock_path.read_bytes())
    lock["producer_repository_id"] = discover_repository(api).repository.id
    lock_path.write_text(canonical_json(lock))
    destination = manifest.parent / "workspace"
    destination.mkdir()
    data = (
        manifest.read_text()
        .replace('root = "api"', 'root = "../api"')
        .replace('root = "web"', 'root = "../web"')
    )
    manifest = write(destination, manifest.name, data)
    value = report(manifest)
    assert all(r["limitations"] == ["local_identity_nonportable"] for r in value["repositories"])


def test_composite_independent_budgets_body_free(workspace):
    manifest, api, _web = workspace
    manifest.write_text(
        manifest.read_text().replace(
            'repo = "web"\ncontract_id = "work"\nbudget_bytes = 10000',
            'repo = "web"\ncontract_id = "work"\nbudget_bytes = 1',
        )
    )
    task = "PRIVATE_TASK_TEXT"
    resolved = resolve_workspace(manifest)
    findings = resolved.check()
    compiled = resolved.compile(task)
    value = context_dict(resolved, findings, compiled, task)
    assert not value["selection_complete"]
    assert value["checks_status"] == "aligned_observed"
    assert [t["status"] for t in value["targets"]] == ["complete", "incomplete"]
    assert value["targets"][0]["selected_sources"][0]["source"]["repo_alias"] == "api"
    assert task not in canonical_json(value)
    assert "PRIVATE_SOURCE_BODY" not in canonical_json(value)
    assert value["task_sha256"] == sha256(task.encode()).hexdigest()
    assert str(api.parent) not in canonical_json(value)
    assert value == context_dict(resolved, findings, compiled, task)


def test_typed_qualified_refs_validate():
    for cls, args in [
        (QualifiedSourceRef, ("api", "bogus", "file")),
        (QualifiedSourceRef, ("api", "repo_" + "0" * 32, "../file")),
        (QualifiedClaimRef, ("api", "repo_" + "0" * 32, "bad id")),
        (ContractLock, ("repo_" + "0" * 32, "file", "bad")),
    ]:
        with pytest.raises(ValueError):
            cls(*args)


def test_observation_budget_and_repo_qualified_cache(workspace, monkeypatch):
    manifest, api, _ = workspace
    resolved = resolve_workspace(manifest)
    a, _ = resolved.observe("api", "docs/architecture.md")
    b, _ = resolved.observe("web", "docs/architecture.md")
    assert a.ref != b.ref and a.content_sha256 == b.content_sha256
    write(api, "docs/architecture.md", b"later")
    assert resolved.observe("api", "docs/architecture.md")[0] == a
    monkeypatch.setattr("context_integrity.workspace.OBSERVATION_BYTES", resolved.bytes)
    assert resolved.observe("api", "spec/api.json")[0].state == "budget_exceeded"


def test_inventory_budget_incomplete_target(workspace, monkeypatch):
    manifest, *_ = workspace
    resolved = resolve_workspace(manifest)
    monkeypatch.setattr("context_integrity.workspace.OBSERVATION_ATTEMPTS", 1)
    findings = resolved.check()
    assert by_id(check_dict(resolved, findings), "claims")["signal"] == "not_established"
    value = context_dict(resolved, findings, resolved.compile("task"), "task")
    assert not value["selection_complete"]
    assert all(t["coverage"] == "inventory_unavailable" for t in value["targets"])


def test_declaration_order_only_changes_manifest_digest(workspace):
    manifest, *_ = workspace
    before = report(manifest)
    chunks = manifest.read_text().split("\n[[")
    manifest.write_text(chunks[0] + "\n[[" + "\n[[".join(reversed(chunks[1:])))
    after = report(manifest)
    assert before.pop("manifest_sha256") != after.pop("manifest_sha256")
    assert before == after


def test_missing_plus_unobservable_preserves_both_reasons(workspace):
    manifest, api, web = workspace
    (api / "docs/architecture.md").unlink()
    target = web / "docs/architecture.md"
    target.unlink()
    target.symlink_to(web / "spec/api.json")
    finding = by_id(report(manifest), "mirror")
    assert finding["signal"] == "review_required"
    assert codes(finding) >= {"api:source_missing", "web:source_unobservable"}


def test_unreadable_source_is_not_alignment(workspace):
    manifest, api, _ = workspace
    path = api / "spec/api.json"
    path.chmod(0)
    try:
        finding = by_id(report(manifest), "pin")
        assert finding["sources"][0]["state"] == "unobservable"
        assert finding["signal"] == "not_established"
    finally:
        path.chmod(0o600)


def test_unstable_file_read_is_not_alignment(workspace, monkeypatch):
    import os

    from context_integrity.acquisition import read_source

    _, api, _ = workspace
    context = discover_repository(api)
    original = os.read
    changed = False

    def changing_read(fd, count):
        nonlocal changed
        data = original(fd, count)
        if data and not changed:
            changed = True
            write(api, "spec/api.json", b"changed while reading")
        return data

    monkeypatch.setattr("context_integrity.acquisition.os.read", changing_read)
    assert read_source(context, "spec/api.json", require_stable=True)[1] is None
    assert any(w.code == "source_changed_during_read" for w in context.warnings)


def test_inventory_ancestor_symlink_is_refused(workspace):
    from context_integrity.acquisition import read_source

    _, api, _ = workspace
    context = discover_repository(api)
    saved = api.with_name("saved")
    api.rename(saved)
    api.symlink_to(saved, target_is_directory=True)
    assert read_source(context, "spec/api.json")[1] is None


def test_invalid_lock_never_masked_by_missing_producer(workspace):
    manifest, api, web = workspace
    (api / "spec/api.json").unlink()
    write(web, "contracts/api.lock.json", '{"secret": "PRIVATE"}')
    with pytest.raises(WorkspaceInputError):
        report(manifest)


def test_no_checks_compile_requires_targets(workspace):
    manifest, *_ = workspace
    data = manifest.read_text()
    manifest.write_text(data[: data.index("[[checks]]")])
    resolved = resolve_workspace(manifest)
    with pytest.raises(WorkspaceInputError, match="context_targets_required"):
        resolved.compile("task")


def test_observation_attempt_budget(workspace, monkeypatch):
    manifest, *_ = workspace
    resolved = resolve_workspace(manifest)
    monkeypatch.setattr("context_integrity.workspace.OBSERVATION_ATTEMPTS", 0)
    assert resolved.observe("api", "spec/api.json")[0].state == "budget_exceeded"


def test_config_versions_remain_local_and_supported(workspace):
    manifest, api, web = workspace
    for version in range(1, 9):
        write(api, ".context-integrity.toml", f"schema_version = {version}\n")
        write(web, ".context-integrity.toml", f"schema_version = {9 - version}\n")
        value = report(manifest)
        assert by_id(value, "pin")["signal"] == "aligned"
        assert by_id(value, "claims")["signal"] == "not_established"


def normalize_heads(value):
    """Goldens mask only Git commit IDs; actual bytes/qualified IDs stay pinned."""
    if isinstance(value, dict):
        return {
            k: "1" * 40 if k == "git_head" and v else normalize_heads(v) for k, v in value.items()
        }
    if isinstance(value, list):
        return [normalize_heads(v) for v in value]
    return value


def test_workspace_schema_goldens(workspace):
    from pathlib import Path

    manifest, *_ = workspace
    resolved = resolve_workspace(manifest)
    findings = resolved.check()
    check = normalize_heads(check_dict(resolved, findings))
    context = normalize_heads(context_dict(resolved, findings, resolved.compile("task"), "task"))
    fixtures = Path(__file__).parent / "fixtures"
    assert manifest.read_bytes() == (fixtures / "workspace-v1.toml").read_bytes()
    assert check == json.loads((fixtures / "workspace-check-v1.json").read_bytes())
    assert context == json.loads((fixtures / "workspace-context-v1.json").read_bytes())
    lock = (workspace[2] / "contracts/api.lock.json").read_bytes()
    assert json.loads(lock) == json.loads((fixtures / "contract-lock-v1.json").read_bytes())


def test_independent_configured_authority_policies(workspace):
    manifest, api, web = workspace
    for root, policy in [(api, "api-policy"), (web, "web-policy")]:
        config = (root / ".context-integrity.toml").read_text()
        config = config.replace(
            'mode = "required"', f'mode = "required"\nauthority_policy = "{policy}"'
        )
        config += f'''\n[[authority.policies]]
id = "{policy}"
description = "Local authority"
tiers = [["architecture_product"]]
'''
        write(root, ".context-integrity.toml", config)
    resolved = resolve_workspace(manifest)
    value = context_dict(resolved, resolved.check(), resolved.compile("task"), "task")
    assert value["selection_complete"]
    assert [t["authority_policies"][0]["id"] for t in value["targets"]] == [
        "api-policy",
        "web-policy",
    ]
    for target in value["targets"]:
        source = target["selected_sources"][0]["source"]
        decision = next(d for d in target["decisions"] if d["source"] == source)
        assert (
            decision["rule_decisions"][0]["authority_policy"]
            == target["authority_policies"][0]["id"]
        )


def test_shared_inventory_accounts_skipped_reads(workspace):
    from context_integrity.inventory import InventoryObservationBudget, inventory_repository

    _, api, web = workspace
    write(api, "docs/unsafe.md", b"x")
    (api / "docs/unsafe.md").unlink()
    (api / "docs/unsafe.md").symlink_to(web / "docs/architecture.md")
    budget = InventoryObservationBudget(6 * 1024 * 1024, 20)
    first = inventory_repository(
        discover_repository(api), observation_budget=budget, require_stable=True
    )
    assert not any(s.path == "docs/unsafe.md" for s in first.sources)
    assert budget.remaining_bytes < 1024 * 1024
    assert budget.remaining_attempts == 17  # config, architecture, refused symlink
    before = budget.remaining_bytes
    inventory_repository(discover_repository(web), observation_budget=budget, require_stable=True)
    assert budget.remaining_bytes < before


def test_provider_requirements_remain_incomplete_offline(workspace):
    manifest, api, _ = workspace
    config = (
        (api / ".context-integrity.toml")
        .read_text()
        .replace("schema_version = 6", "schema_version = 7")
    )
    config = config.replace('paths = ["docs/architecture.md"]', 'kinds = ["source_code"]')
    write(api, ".context-integrity.toml", config)
    resolved = resolve_workspace(manifest)
    value = context_dict(resolved, resolved.check(), resolved.compile("task"), "task")
    assert not value["selection_complete"]
    assert [t["status"] for t in value["targets"]] == ["incomplete", "complete"]
    assert "providers_disabled" in value["limitations"]


def test_manifest_model_bounds_and_bad_primitives(workspace):
    from dataclasses import replace

    from context_integrity.workspace_models import (
        CheckSpec,
        ContextTarget,
        RepositorySpec,
        RuleKind,
    )

    manifest, *_ = workspace
    spec = parse_workspace(manifest.read_bytes())
    for update in [
        {"repositories": spec.repositories[:1]},
        {"repositories": spec.repositories * 2},
        {"checks": spec.checks * 50},
        {"context_targets": spec.context_targets * 9},
    ]:
        with pytest.raises(ValueError):
            replace(spec, **update)
    for cls, args in [
        (RepositorySpec, ("api", "http://host", spec.repositories[0].repository_id)),
        (ContextTarget, ("api", "work", True)),
        (CheckSpec, ("check", RuleKind.MIRROR_BYTES, "api", "x", "api", "x")),
    ]:
        with pytest.raises(ValueError):
            cls(*args)
    for data in [b"[", b"\xff", b"x" * (256 * 1024 + 1)]:
        with pytest.raises(WorkspaceInputError):
            parse_workspace(data)
