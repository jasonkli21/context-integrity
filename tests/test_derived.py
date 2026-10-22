"""Adversarial provenance tests over actual local files and Git metadata."""

import json
from dataclasses import replace
from hashlib import sha256

import pytest

from context_integrity.derived import (
    Checker,
    Observation,
    Reader,
    aggregate,
    capture_receipt,
    check_receipt,
    compare_pin,
    render_result,
)
from context_integrity.derived_models import (
    MAX_RECEIPT_BYTES,
    CompilationPin,
    Derivation,
    ProviderPin,
    ReceiptError,
    RepositorySnapshot,
    SourcePin,
    UpstreamPin,
    parse_receipt,
    receipt_dict,
    render_receipt,
)
from context_integrity.inventory import inventory_repository
from context_integrity.models import make_source_id
from context_integrity.repository import discover_repository


def capture(root, *, name="a", deps=("AGENTS.md",), parents=()):
    artifact = f"docs/{name}.md"
    if not (root / artifact).exists():
        (root / artifact).write_text(f"Generated {name}\n")
    context = discover_repository(root)
    return capture_receipt(
        context,
        inventory_repository(context),
        artifact,
        artifact_id=name,
        kind="handoff",
        derivation=Derivation("model", "agent"),
        depends_on=deps,
        upstream_receipts=parents,
        receipt_path=f"docs/{name}.receipt.json",
    )


def save(root, receipt):
    path = f"docs/{receipt.artifact.id}.receipt.json"
    (root / path).write_text(render_receipt(receipt))
    return path


def check(root, path="docs/a.receipt.json"):
    return check_receipt(discover_repository(root), path)[0]


def codes(result):
    return {r.code for r in result.reasons}


def test_roundtrip_sorted_actual_bytes(git_repo):
    receipt = capture(git_repo, deps=("docs/architecture.md", "AGENTS.md"))
    assert receipt.artifact.content_sha256 == sha256(b"Generated a\n").hexdigest()
    assert receipt.dependencies[0].content_sha256 == sha256(b"Instructions\n").hexdigest()
    assert parse_receipt(render_receipt(receipt).encode()) == receipt
    assert render_receipt(
        replace(receipt, dependencies=tuple(reversed(receipt.dependencies)))
    ) == render_receipt(receipt)
    save(git_repo, receipt)
    result = check(git_repo)
    assert result.status == "unchanged_observed_inputs"
    assert "semantic correctness" in render_result(result)
    assert str(git_repo) not in render_receipt(receipt) + render_result(result, True)
    assert "Generated a" not in render_receipt(receipt)


@pytest.mark.parametrize("version", [0, -1, 2, True, "1", None])
def test_schema_versions_rejected(git_repo, version):
    receipt = capture(git_repo)
    with pytest.raises(ValueError):
        replace(receipt, derived_receipt_schema_version=version)
    raw = receipt_dict(receipt)
    raw["derived_receipt_schema_version"] = version
    with pytest.raises(ReceiptError):
        parse_receipt(json.dumps(raw).encode())


@pytest.mark.parametrize(
    "path",
    [
        "",
        "/etc/passwd",
        "../x",
        "docs/../x",
        "docs//x",
        "./x",
        "x/",
        "x\\y",
        "C:x",
        "x\nx",
        "x\x00",
        "é.md",
        "x\ud800",
        ".git/config",
        "x/*",
        "x/./y",
        "a" * 513,
    ],
)
def test_strict_paths_in_constructor(git_repo, path):
    with pytest.raises(ValueError):
        replace(capture(git_repo).artifact, path=path)


@pytest.mark.parametrize(
    "field,value",
    [
        ("id", "contains secret text"),
        ("kind", "authoritative"),
        ("content_sha256", "A" * 64),
        ("content_sha256", None),
        ("derivation", {}),
    ],
)
def test_artifact_constructor(git_repo, field, value):
    with pytest.raises(ValueError):
        replace(capture(git_repo).artifact, **{field: value})


def test_strict_keys_json_limits_and_shapes(git_repo):
    data = render_receipt(capture(git_repo)).encode()
    for invalid in (
        b'{"x":1,"x":2}',
        data.replace(
            b'"known_incomplete": false', b'"known_incomplete": false, "known_incomplete": true'
        ),
        b"[" * 10000,
        b" " * (MAX_RECEIPT_BYTES + 1),
        b"NaN",
        b"null",
        b"\xff",
    ):
        with pytest.raises(ReceiptError):
            parse_receipt(invalid)
    raw = json.loads(data)
    for variant in (
        raw | {"body": "private"},
        {k: v for k, v in raw.items() if k != "compilation"},
        raw | {"dependencies": {}},
        raw | {"dependencies": raw["dependencies"] * 257},
        raw | {"repository": raw["repository"] | {"root": "/private"}},
    ):
        with pytest.raises(ReceiptError):
            parse_receipt(json.dumps(variant).encode())


def test_conflicts_and_ids(git_repo):
    r = capture(git_repo)
    for deps in (
        (r.dependencies[0],) * 2,
        (replace(r.dependencies[0], path=r.artifact.path),),
        (replace(r.dependencies[0], source_id="src_" + "0" * 32),),
    ):
        with pytest.raises(ReceiptError):
            replace(r, dependencies=deps)
    with pytest.raises(ReceiptError):
        replace(r.dependencies[0], observation_basis="unknown")
    with pytest.raises(ReceiptError):
        replace(r, repository=RepositorySnapshot("repo_" + "0" * 32, None, None))
    with pytest.raises(ReceiptError):
        replace(r, provenance_scope="compiler_selection")
    with pytest.raises(ReceiptError):
        replace(r, known_incomplete=1)


def test_dirty_staged_reverted_unrelated_head(git_repo, git):
    git(git_repo, "add", ".")
    git(git_repo, "commit", "-m", "base")
    save(git_repo, capture(git_repo))
    head = git(git_repo, "rev-parse", "HEAD")
    (git_repo / "AGENTS.md").write_text("dirty staged change")
    assert check(git_repo).status == "review_required"
    git(git_repo, "add", "AGENTS.md")
    assert git(git_repo, "rev-parse", "HEAD") == head
    assert "source_changed" in codes(check(git_repo))
    (git_repo / "AGENTS.md").write_bytes(b"Instructions\n")
    assert check(git_repo).status == "unchanged_observed_inputs"
    git(git_repo, "add", "AGENTS.md")
    (git_repo / "unrelated").write_text("unrelated")
    git(git_repo, "add", "unrelated")
    git(git_repo, "commit", "-m", "unrelated")
    assert git(git_repo, "rev-parse", "HEAD") != head
    assert check(git_repo).status == "unchanged_observed_inputs"


@pytest.mark.parametrize(
    "operation,reason,status",
    [
        ("delete", "source_missing", "review_required"),
        ("rename", "source_missing", "review_required"),
        ("symlink", "source_unobservable", "inconclusive"),
        ("oversize", "source_too_large", "inconclusive"),
        ("artifact", "artifact_changed", "review_required"),
    ],
)
def test_non_safe_observations(git_repo, operation, reason, status):
    save(git_repo, capture(git_repo))
    source = git_repo / "AGENTS.md"
    if operation == "delete":
        source.unlink()
    elif operation == "rename":
        source.rename(git_repo / "RENAMED.md")
    elif operation == "symlink":
        source.unlink()
        source.symlink_to("/etc/passwd")
    elif operation == "oversize":
        source.write_bytes(b"x" * (5 * 1024 * 1024 + 1))
    else:
        (git_repo / "docs/a.md").write_text("new bytes")
    result = check(git_repo)
    assert result.status == status
    assert reason in codes(result)


def test_unreadable_and_simultaneous_change(git_repo):
    save(git_repo, capture(git_repo))
    (git_repo / "AGENTS.md").chmod(0)
    try:
        result = check(git_repo)
        assert result.status == "inconclusive"
        (git_repo / "docs/a.md").write_text("changed")
        result = check(git_repo)
        assert result.status == "review_required"
        assert {"source_unobservable", "artifact_changed"} <= codes(result)
    finally:
        (git_repo / "AGENTS.md").chmod(0o644)


def test_explicit_non_inventory_and_no_dependencies(git_repo):
    (git_repo / "main.py").write_text("code")
    r = capture(git_repo, deps=("main.py",))
    assert r.dependencies[0].observation_basis == "explicit_file"
    save(git_repo, r)
    assert check(git_repo).status == "unchanged_observed_inputs"
    (git_repo / "main.py").write_text("new code")
    assert check(git_repo).status == "review_required"
    save(git_repo, capture(git_repo, name="empty", deps=()))
    assert check(git_repo, "docs/empty.receipt.json").status == "inconclusive"


def test_known_generated_dependencies_require_their_receipt(git_repo):
    from context_integrity.derived import capture_receipt

    upstream_path = "docs/source-summary.md"
    (git_repo / upstream_path).write_text("Generated source summary\n")
    context = discover_repository(git_repo)
    manifest = inventory_repository(context)
    parent = capture_receipt(
        context,
        manifest,
        upstream_path,
        artifact_id="source-summary",
        kind="summary",
        derivation=Derivation("model", "agent"),
        depends_on=("AGENTS.md",),
        receipt_path="docs/source-summary.receipt.json",
    )
    save(git_repo, parent)

    unlinked = capture(git_repo, name="unlinked", deps=(upstream_path,))
    save(git_repo, unlinked)
    result = check(git_repo, "docs/unlinked.receipt.json")
    assert result.status == "inconclusive"
    assert "unlinked_derived_dependency" in codes(result)

    linked = capture(
        git_repo, name="linked", deps=(), parents=("docs/source-summary.receipt.json",)
    )
    save(git_repo, linked)
    result = check(git_repo, "docs/linked.receipt.json")
    assert result.status == "unchanged_observed_inputs"

    (git_repo / "docs/manual-compiled.json").write_text("{}\n")
    context = discover_repository(git_repo)
    manual_compiled = capture_receipt(
        context,
        inventory_repository(context),
        "docs/manual-compiled.json",
        artifact_id="manual-compiled",
        kind="compiled_context",
        derivation=Derivation("manual", "user"),
        depends_on=("AGENTS.md",),
        receipt_path="docs/manual-compiled.receipt.json",
    )
    save(git_repo, manual_compiled)
    result = check(git_repo, "docs/manual-compiled.receipt.json")
    assert result.status == "inconclusive"
    assert "provenance_incomplete" in codes(result)

    (git_repo / "docs/current-state.md").write_text("Current state\n")
    (git_repo / "docs/state.md").write_text("State handoff\n")
    context = discover_repository(git_repo)
    current_state = capture_receipt(
        context,
        inventory_repository(context),
        "docs/state.md",
        artifact_id="state",
        kind="handoff",
        derivation=Derivation("manual", "user"),
        depends_on=("docs/current-state.md",),
        receipt_path="docs/state.receipt.json",
    )
    save(git_repo, current_state)
    assert "unlinked_derived_dependency" not in codes(check(git_repo, "docs/state.receipt.json"))


def test_reader_distinguishes_graph_budget_from_file_ceiling(git_repo, monkeypatch):
    import context_integrity.derived as module
    from context_integrity.derived import Reason

    monkeypatch.setattr(module, "MAX_GRAPH_BYTES", 10)
    reader = Reader(discover_repository(git_repo))
    reader.bytes = 9
    observation, _ = reader.read("AGENTS.md")
    assert observation.state == "budget_exceeded"
    assert {r.code for r in compare_pin("a", "source", "a" * 64, observation)} == {
        "source_budget_exceeded"
    }

    receipt_reader = Reader(discover_repository(git_repo))
    receipt_reader.bytes = 9
    receipt_observation, _ = receipt_reader.read("AGENTS.md", MAX_RECEIPT_BYTES)
    assert receipt_observation.state == "budget_exceeded"

    reader = Reader(discover_repository(git_repo))
    reader.bytes = 10
    zero_budget, _ = reader.read("AGENTS.md")
    assert zero_budget.state == "budget_exceeded"
    reasons = [
        *compare_pin("a", "source", "a" * 64, zero_budget),
        Reason("artifact_changed", "docs/a.md", "a", "review"),
    ]
    assert aggregate(reasons) == "review_required"

    reader = Reader(discover_repository(git_repo))
    observation, _ = reader.read("AGENTS.md", limit=4)
    assert observation.state == "too_large"


@pytest.mark.parametrize("mode", ["create", "delete", "change", "invalid"])
def test_config_absence_presence_and_metadata(git_repo, mode):
    config = git_repo / ".context-integrity.toml"
    if mode != "create":
        config.write_text("schema_version = 8\n")
    save(git_repo, capture(git_repo))
    if mode == "delete":
        config.unlink()
    elif mode == "invalid":
        config.write_text("invalid secret config prose")
    else:
        config.write_text(
            'schema_version = 8\n[[source_metadata]]\npath = "AGENTS.md"\n'
            'authority_class = "plan"\nlifecycle = "historical"\nreason = "fixture"\n'
        )
    result = check(git_repo)
    assert result.status == "review_required"
    assert ("config_missing" if mode == "delete" else "config_changed") in codes(result)
    if mode == "change":
        assert "source_metadata_changed" in codes(result)
    if mode == "invalid":
        assert "source_metadata_unobservable" in codes(result)


def test_transitive_diamond_memoization(git_repo):
    save(git_repo, capture(git_repo))
    save(git_repo, capture(git_repo, name="b", deps=(), parents=("docs/a.receipt.json",)))
    save(git_repo, capture(git_repo, name="c", deps=(), parents=("docs/a.receipt.json",)))
    save(
        git_repo,
        capture(
            git_repo, name="d", deps=(), parents=("docs/c.receipt.json", "docs/b.receipt.json")
        ),
    )
    result = check(git_repo, "docs/d.receipt.json")
    assert result.status == "unchanged_observed_inputs"
    assert result.receipts_observed == 4
    checker = Checker(discover_repository(git_repo))
    checker.manifest = inventory_repository(checker.context)
    checker.evaluate("docs/d.receipt.json")
    assert len(checker.results) == 4
    (git_repo / "AGENTS.md").write_text("changed original")
    result = check(git_repo, "docs/d.receipt.json")
    assert result.status == "review_required"
    assert {"source_changed", "upstream_review_required"} <= codes(result)
    assert any(r.artifact_id == "a" and r.path == "AGENTS.md" for r in result.reasons)


@pytest.mark.parametrize("operation", ["missing", "tampered", "invalid", "cross_repo", "identity"])
def test_untrusted_upstream(git_repo, operation):
    parent = capture(git_repo)
    save(git_repo, parent)
    child = capture(git_repo, name="b", deps=(), parents=("docs/a.receipt.json",))
    parent_path = git_repo / "docs/a.receipt.json"
    if operation == "missing":
        parent_path.unlink()
    else:
        raw = receipt_dict(parent)
        if operation == "tampered":
            raw["artifact"]["content_sha256"] = "0" * 64
        elif operation == "invalid":
            raw["derived_receipt_schema_version"] = 99
        elif operation == "cross_repo":
            raw["repository"]["id"] = "repo_" + "0" * 32
            raw["dependencies"][0]["source_id"] = make_source_id(
                raw["repository"]["id"], "AGENTS.md"
            )
        else:
            raw["artifact"]["id"] = "another"
        parent_path.write_text(json.dumps(raw))
        if operation in ("invalid", "cross_repo", "identity"):
            child = replace(
                child,
                upstream_receipts=(
                    replace(
                        child.upstream_receipts[0],
                        receipt_sha256=sha256(parent_path.read_bytes()).hexdigest(),
                    ),
                ),
            )
    save(git_repo, child)
    result = check(git_repo, "docs/b.receipt.json")
    assert result.status == (
        "review_required" if operation in ("missing", "tampered") else "inconclusive"
    )


def test_capture_rejects_self_broken_and_stale(git_repo):
    with pytest.raises(ReceiptError):
        capture(git_repo, deps=("docs/a.md",))
    with pytest.raises(ReceiptError):
        capture(git_repo, deps=("AGENTS.md", "AGENTS.md"))
    with pytest.raises(ReceiptError):
        capture(git_repo, parents=("docs/missing.json",))
    save(git_repo, capture(git_repo))
    with pytest.raises(ReceiptError):
        capture(git_repo, parents=("docs/a.receipt.json",))
    (git_repo / "AGENTS.md").write_text("stale")
    with pytest.raises(ReceiptError):
        capture(git_repo, name="b", deps=(), parents=("docs/a.receipt.json",))


def test_graph_limits_and_cycle_guard(git_repo, monkeypatch):
    save(git_repo, capture(git_repo))
    save(git_repo, capture(git_repo, name="b", deps=(), parents=("docs/a.receipt.json",)))
    import context_integrity.derived as module

    monkeypatch.setattr(module, "MAX_DEPTH", 1)
    assert check(git_repo, "docs/b.receipt.json").status == "inconclusive"
    monkeypatch.setattr(module, "MAX_DEPTH", 16)
    monkeypatch.setattr(module, "MAX_RECEIPTS", 1)
    assert check(git_repo, "docs/b.receipt.json").status == "inconclusive"
    checker = Checker(discover_repository(git_repo))
    with pytest.raises(ReceiptError):
        checker.evaluate("docs/a.receipt.json", ("docs/a.receipt.json",))
    monkeypatch.setattr(module, "MAX_GRAPH_BYTES", 1)
    reader = Reader(discover_repository(git_repo))
    reader.read("AGENTS.md")
    assert reader.read("docs/architecture.md")[0].state == "budget_exceeded"


def test_pure_comparison_matrix():
    for state, pinned, current, expected in (
        ("observed", "a" * 64, "a" * 64, "unchanged_observed_inputs"),
        ("observed", "a" * 64, "b" * 64, "review_required"),
        ("missing", None, None, "unchanged_observed_inputs"),
        ("missing", "a" * 64, None, "review_required"),
        ("unobservable", None, None, "inconclusive"),
        ("budget_exceeded", "a" * 64, None, "inconclusive"),
    ):
        assert (
            aggregate(compare_pin("artifact", "config", pinned, Observation("x", current, state)))
            == expected
        )


def test_equivalent_roots_with_remote_identity(git_repo, git, tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    git(other, "init")
    git(other, "config", "remote.origin.url", "git@example.invalid:team/basic-context.git")
    (other / "docs").mkdir()
    (other / "AGENTS.md").write_bytes((git_repo / "AGENTS.md").read_bytes())
    assert render_receipt(capture(other)) == render_receipt(capture(git_repo))


def test_all_pin_constructors(git_repo):
    r = capture(git_repo)
    with pytest.raises(ReceiptError):
        Derivation("untrusted", "agent")
    with pytest.raises(ReceiptError):
        RepositorySnapshot(r.repository.id, "unknown-head", False)
    with pytest.raises(ReceiptError):
        RepositorySnapshot(r.repository.id, None, 1)
    with pytest.raises(ReceiptError):
        SourcePin("x", r.dependencies[0].source_id, "x", None, None, None, "explicit_file")
    with pytest.raises(ReceiptError):
        UpstreamPin("x", "a" * 64, "parent", "x", "b" * 64)
    with pytest.raises(ReceiptError):
        ProviderPin("provider", "1", "adapter", True, 1, None, None, "a" * 64, "b" * 64, False)
    with pytest.raises(ReceiptError):
        CompilationPin(
            "work", "a" * 64, "a" * 64, "a" * 64, None, True, "complete", "not_evaluated", (), "1"
        )


def test_metadata_supersession_ignores_unrelated_head(git_repo, git):
    config = """schema_version = 8
[[source_metadata]]
path = "AGENTS.md"
lifecycle = "active"
reason = "fixture"
[[supersession]]
source = "docs/architecture.md"
superseded_by = "docs/new-architecture.md"
reason = "explicit decision"
"""
    (git_repo / ".context-integrity.toml").write_text(config)
    (git_repo / "docs/new-architecture.md").write_text("New architecture")
    git(git_repo, "add", ".")
    git(git_repo, "commit", "-m", "base")
    save(git_repo, capture(git_repo, deps=("docs/architecture.md",)))
    assert check(git_repo).status == "unchanged_observed_inputs"
    (git_repo / "irrelevant").write_text("new commit")
    git(git_repo, "add", "irrelevant")
    git(git_repo, "commit", "-m", "unrelated")
    assert check(git_repo).status == "unchanged_observed_inputs"
    (git_repo / ".context-integrity.toml").write_text("schema_version = 8\n")
    result = check(git_repo)
    assert result.status == "review_required"
    assert "source_metadata_changed" in codes(result)


def test_no_git_capture(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "AGENTS.md").write_text("instructions")
    r = capture(tmp_path)
    assert r.repository.git_head is None and r.repository.git_dirty is None
    save(tmp_path, r)
    assert check(tmp_path).status == "unchanged_observed_inputs"


def test_resource_constructor_limits(git_repo):
    r = capture(git_repo)
    with pytest.raises(ReceiptError):
        replace(r, dependencies=r.dependencies * 257)
    parent = UpstreamPin("docs/p.json", "a" * 64, "parent", "docs/parent.md", "b" * 64)
    with pytest.raises(ReceiptError):
        replace(r, upstream_receipts=(parent,) * 17)
    with pytest.raises(ReceiptError):
        replace(r, dependencies=list(r.dependencies))
    with pytest.raises(ReceiptError):
        replace(r.dependencies[0], observation_basis="explicit_file")
    with pytest.raises(ReceiptError):
        replace(r, upstream_receipts=(replace(parent, artifact_id=r.artifact.id),))
    with pytest.raises(ReceiptError):
        replace(r, upstream_receipts=(replace(parent, artifact_path="AGENTS.md"),))


def test_corrupt_top_self_pointer(git_repo):
    r = capture(git_repo)
    pin = UpstreamPin("docs/a.receipt.json", "a" * 64, "parent", "docs/parent.md", "b" * 64)
    save(git_repo, replace(r, upstream_receipts=(pin,)))
    with pytest.raises(ReceiptError):
        check(git_repo)


def test_transitive_observation_gap(git_repo):
    save(git_repo, capture(git_repo))
    save(git_repo, capture(git_repo, name="b", deps=(), parents=("docs/a.receipt.json",)))
    (git_repo / "AGENTS.md").unlink()
    (git_repo / "AGENTS.md").symlink_to("/etc/passwd")
    result = check(git_repo, "docs/b.receipt.json")
    assert result.status == "inconclusive"
    assert {"source_unobservable", "upstream_inconclusive"} <= codes(result)


def test_direct_comparison_input_permutations(git_repo):
    r = capture(git_repo, deps=("docs/architecture.md", "AGENTS.md"))
    save(git_repo, r)
    (git_repo / "AGENTS.md").write_text("changed")
    (git_repo / "docs/architecture.md").unlink()
    first = render_result(check(git_repo), True)
    save(git_repo, replace(r, dependencies=tuple(reversed(r.dependencies))))
    assert render_result(check(git_repo), True) == first


def test_inventory_budget_gap_is_not_unchanged(git_repo, monkeypatch):
    save(git_repo, capture(git_repo))
    import context_integrity.derived as module

    original = module.inventory_repository

    def bounded(context, **kw):
        return original(context, max_sources=1)

    monkeypatch.setattr(module, "inventory_repository", bounded)
    assert check(git_repo).status == "inconclusive"


def test_diamond_conflicting_receipt_identity(git_repo):
    a = capture(git_repo)
    save(git_repo, a)
    (git_repo / "docs/alternate.json").write_text(render_receipt(a))
    b = capture(git_repo, name="b", deps=(), parents=("docs/a.receipt.json",))
    save(git_repo, b)
    c = capture(git_repo, name="c", deps=(), parents=("docs/alternate.json",))
    save(git_repo, c)
    d = capture(git_repo, name="d", deps=())

    def link(r, path):
        return UpstreamPin(
            path,
            sha256((git_repo / path).read_bytes()).hexdigest(),
            r.artifact.id,
            r.artifact.path,
            r.artifact.content_sha256,
        )

    d = replace(
        d,
        upstream_receipts=(link(b, "docs/b.receipt.json"), link(c, "docs/c.receipt.json")),
        known_incomplete=False,
    )
    save(git_repo, d)
    assert check(git_repo, "docs/d.receipt.json").status == "inconclusive"


def test_golden_receipt_and_result(git_repo):
    from pathlib import Path

    receipt = capture(git_repo, deps=("docs/architecture.md", "AGENTS.md"))
    fixtures = Path(__file__).parent / "fixtures"
    assert render_receipt(receipt) == (fixtures / "derived-receipt-v1.json").read_text()
    save(git_repo, receipt)
    assert render_result(check(git_repo), True) == (fixtures / "derived-result-v1.json").read_text()


def test_explicit_metadata_fields_are_compared(git_repo):
    r = capture(git_repo)
    pin = replace(r.dependencies[0], observed_lifecycle="active", observed_authority="plan")
    save(git_repo, replace(r, dependencies=(pin,)))
    result = check(git_repo)
    assert result.status == "review_required"
    assert "source_metadata_changed" in codes(result)


@pytest.mark.parametrize("schema", range(1, 9))
def test_capture_with_each_shipped_config_schema(git_repo, schema):
    (git_repo / ".context-integrity.toml").write_text(f"schema_version = {schema}\n")
    save(git_repo, capture(git_repo))
    assert check(git_repo).status == "unchanged_observed_inputs"


def test_receipt_text_projection(git_repo):
    from context_integrity.derived_models import render_receipt_text

    text = render_receipt_text(capture(git_repo))
    assert "a: handoff (docs/a.md)" in text
    assert "source: AGENTS.md [inventory]" in text
    assert "Generated a" not in text and str(git_repo) not in text
