"""Public graph DTO contract fixtures and executable transport tests, entirely offline."""

import copy
import json
from dataclasses import asdict, replace
from hashlib import sha256

import pytest
from typer.testing import CliRunner

from context_integrity.cli import app
from context_integrity.context_engine import ContextEngineProvider
from context_integrity.evidence import EvidenceProviderDescriptor, EvidenceProviderError
from context_integrity.graph_adapter import normalize_graph
from context_integrity.inventory import scan_repository
from context_integrity.relations import EvidenceRelationRequest

CONFIG = """schema_version = 8
[[claims]]
id = "boundary"
claim_type = "architecture_invariant"
subject = "application"
predicate = "must_not_depend_on"
value = "storage"
[[architecture_invariants]]
id = "boundary"
claim_id = "boundary"
rule = "forbid_relation"
relation_kinds = ["imports", "references"]
source_path_prefixes = ["src/application/"]
target_names = ["Storage"]
"""
DESCRIPTOR = EvidenceProviderDescriptor("context-engine", "0.1.0", capabilities=("relations",))


def span(start=0, end=10):
    return dict(start=dict(byte=start, row=0, column=start), end=dict(byte=end, row=0, column=end))


def graph(graph_request):
    path = "src/application/main.py"
    return dict(
        schema_version=1,
        command="graph",
        data=dict(
            root=str(graph_request.repository_root),
            git=dict(
                repository_root=str(graph_request.repository_root),
                head_commit=graph_request.repository.git_head,
                is_dirty=graph_request.repository.git_dirty,
                branch="unused",
            ),
            id_semantics="index-local",
            entities=[
                dict(id=800, kind="repository", path=None, symbol=None),
                dict(id=801, kind="file", path=path, symbol=None),
                dict(
                    id=802,
                    kind="symbol",
                    path=path,
                    symbol=dict(
                        name="run",
                        qualified_name="App.run",
                        kind="method",
                        language="python",
                        path=path,
                        range=span(0, 50),
                        name_range=span(0, 3),
                    ),
                ),
            ],
            relations=[
                dict(
                    id=700,
                    kind="contains",
                    source_id=800,
                    target=dict(state="resolved", entity_id=801),
                    resolution="direct_structural",
                    evidence=dict(
                        path=path, range=None, language=None, derivation="repository_contains_file"
                    ),
                ),
                dict(
                    id=701,
                    kind="imports",
                    source_id=801,
                    target=dict(state="unresolved", name="Storage"),
                    resolution="unresolved",
                    evidence=dict(
                        path=path,
                        range=span(),
                        language="python",
                        derivation="python_import_syntax",
                    ),
                ),
                dict(
                    id=702,
                    kind="references",
                    source_id=801,
                    target=dict(state="resolved", entity_id=802),
                    resolution="exact_same_file_qualified_name",
                    evidence=dict(
                        path=path,
                        range=span(20, 25),
                        language="python",
                        derivation="python_call_syntax",
                    ),
                ),
            ],
            files=[
                dict(
                    path=path,
                    language="python",
                    symbol_status="analyzed",
                    symbol_count=1,
                    syntax_error_count=0,
                )
            ],
            relation_files=[
                dict(
                    path=path,
                    status="analyzed",
                    import_count=1,
                    reference_count=1,
                    unresolved_count=1,
                    unsupported_candidate_count=0,
                )
            ],
            summary=dict(
                entities=3,
                relations=3,
                resolved=2,
                unresolved=1,
                relation_statuses=dict(analyzed=1),
                symbol_analysis_unavailable=0,
                unsupported_candidates=0,
            ),
            diagnostics=[],
            scan_warnings=[],
        ),
    )


@pytest.fixture
def graph_request(tmp_path):
    repository = replace(scan_repository(tmp_path).repository, git_head="a" * 40, git_dirty=False)
    return EvidenceRelationRequest(tmp_path, repository)


def normalize(value, graph_request):
    return normalize_graph(json.dumps(value).encode(), graph_request, DESCRIPTOR)


def test_valid_normalization_unresolved_and_no_provider_ids(graph_request):
    batch = normalize(graph(graph_request), graph_request)
    assert len(batch.relations) == 2
    assert batch.relations[0].target.name == "Storage"
    assert batch.relations[1].target.entity.qualified_name == "App.run"
    assert batch.state.coverage.summary.incomplete  # unresolved count is not proof of coverage
    encoded = json.dumps(asdict(batch))
    for key in ('"entity_id"', '"source_id"', '"relation_id"', '"root"', '"id": 801'):
        assert key not in encoded
    assert str(graph_request.repository_root) not in encoded


@pytest.mark.parametrize(
    "change",
    [
        {"schema_version": 2},
        {"schema_version": True},
        {"command": "deps"},
    ],
)
def test_wrong_envelope(graph_request, change):
    data = graph(graph_request)
    data.update(change)
    with pytest.raises(EvidenceProviderError, match="unsupported_contract"):
        normalize(data, graph_request)


@pytest.mark.parametrize(
    "payload", [b"{", b"\xff", b"null", b'{"data":NaN}', b'{"schema_version":1,"schema_version":1}']
)
def test_malformed_json(graph_request, payload):
    with pytest.raises(EvidenceProviderError):
        normalize_graph(payload, graph_request, DESCRIPTOR)


@pytest.mark.parametrize(
    "field",
    ["entities", "relations", "files", "relation_files", "summary", "diagnostics", "scan_warnings"],
)
def test_missing_or_wrong_array(graph_request, field):
    value = graph(graph_request)
    del value["data"][field]
    with pytest.raises(EvidenceProviderError):
        normalize(value, graph_request)
    value = graph(graph_request)
    value["data"][field] = "SECRET"
    with pytest.raises(EvidenceProviderError):
        normalize(value, graph_request)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d["entities"].append(copy.deepcopy(d["entities"][1])),
        lambda d: d["relations"].append(copy.deepcopy(d["relations"][1])),
        lambda d: d["relations"][1].update(source_id=99999),
        lambda d: d["relations"][2]["target"].update(entity_id=99999),
        lambda d: d["relations"][1].update(kind="calls"),
        lambda d: d["relations"][1].update(resolution="guess"),
        lambda d: d["relations"][1]["evidence"].update(derivation="LLM_SECRET"),
        lambda d: d["relations"][1]["evidence"].update(derivation="rust_use_syntax"),
        lambda d: d["relations"][1]["evidence"].update(path="../SECRET"),
        lambda d: d["relations"][1]["evidence"]["range"]["end"].update(byte=-1),
        lambda d: d["entities"][1].update(path="/SECRET"),
        lambda d: d["entities"][1].update(id=True),
        lambda d: d["entities"][2]["symbol"]["range"]["start"].update(row=30),
        lambda d: d["entities"][2]["symbol"].update(path="other.py"),
        lambda d: d["files"][0].update(symbol_status="unknown"),
        lambda d: d["files"].append(copy.deepcopy(d["files"][0])),
        lambda d: d["relation_files"][0].update(unresolved_count=100),
        lambda d: d["relation_files"][0].update(status="unknown"),
        lambda d: d["summary"].update(unresolved=100),
        lambda d: d["summary"].update(entities=100),
        lambda d: d["summary"].update(relation_statuses={"SECRET": 1}),
    ],
)
def test_invalid_graph_fails_sanitized(graph_request, mutation):
    value = graph(graph_request)
    mutation(value["data"])
    with pytest.raises(EvidenceProviderError) as exc:
        normalize(value, graph_request)
    assert "SECRET" not in str(exc.value)
    assert str(graph_request.repository_root) not in str(exc.value)


@pytest.mark.parametrize(
    "field,value,code",
    [
        ("root", "/other/SECRET", "repository_mismatch"),
        ("head_commit", "b" * 40, "snapshot_mismatch"),
        ("is_dirty", True, "snapshot_mismatch"),
    ],
)
def test_snapshot_mismatch(graph_request, field, value, code):
    data = graph(graph_request)
    if field == "root":
        data["data"][field] = value
    else:
        data["data"]["git"][field] = value
    with pytest.raises(EvidenceProviderError, match=code):
        normalize(data, graph_request)


def test_coverage_statuses_and_sanitized_categories(graph_request):
    data = graph(graph_request)
    data["data"]["relation_files"][0].update(
        status="extraction_failed", unsupported_candidate_count=3
    )
    data["data"]["summary"].update(
        relation_statuses={"extraction_failed": 1}, unsupported_candidates=3
    )
    data["data"]["diagnostics"] = [dict(message="PRIVATE BODY", path="/SECRET")]
    data["data"]["scan_warnings"] = [dict(message="RAW STDERR", path="/SECRET")]
    batch = normalize(data, graph_request)
    coverage = batch.state.coverage
    assert coverage.summary.incomplete
    assert coverage.files[0].relation_status == "extraction_failed"
    assert coverage.files[0].unsupported == 3
    assert coverage.warning_categories == ("diagnostics", "scan_warnings")
    assert "PRIVATE" not in repr(batch) and "SECRET" not in repr(batch)


def test_no_relations_complete_and_unknown_snapshot(graph_request):
    data = graph(graph_request)
    data["data"]["relations"] = data["data"]["relations"][:1]
    data["data"]["relation_files"][0].update(import_count=0, reference_count=0, unresolved_count=0)
    data["data"]["summary"].update(relations=1, resolved=1, unresolved=0)
    assert not normalize(data, graph_request).state.coverage.summary.incomplete
    data["data"]["git"] = None
    assert normalize(data, graph_request).state.coverage.summary.incomplete
    data["data"]["relation_files"] = []
    data["data"]["summary"]["relation_statuses"] = {}
    coverage = normalize(data, graph_request).state.coverage
    assert coverage.files[0].relation_status == "not_analyzed"
    assert coverage.summary.incomplete


def test_reordering_numeric_id_changes_do_not_change_normalized_state(graph_request):
    first = graph(graph_request)
    second = copy.deepcopy(first)
    for entity in second["data"]["entities"]:
        entity["id"] += 999
    for relation in second["data"]["relations"]:
        relation["id"] += 555
        relation["source_id"] += 999
        if "entity_id" in relation["target"]:
            relation["target"]["entity_id"] += 999
    second["data"]["entities"].reverse()
    second["data"]["relations"].reverse()
    assert normalize(first, graph_request) == normalize(second, graph_request)


def executable(tmp_path, graph_request, body=None):
    binary = tmp_path / "fake ctx; literal"
    payload = json.dumps(graph(graph_request))
    source = (
        body
        or f"""import sys
if sys.argv[1:] == ["--version"]:
    print("ctx 0.1.0")
else:
    assert sys.argv[1:] == ["graph", {str(graph_request.repository_root)!r}, "--format", "json"]
    print({payload!r})
"""
    )
    # Use the active test interpreter; no external executable is required.
    import sys

    binary.write_text(f"#!{sys.executable}\n" + source)
    binary.chmod(0o755)
    return str(binary)


def test_transport_argv_hashes_and_cli_output_file(tmp_path):
    (tmp_path / ".context-integrity.toml").write_text(CONFIG)
    path = tmp_path / "src/application/main.py"
    path.parent.mkdir(parents=True)
    path.write_text("from storage import Storage\n")
    graph_request = EvidenceRelationRequest(tmp_path, scan_repository(tmp_path).repository)
    binary = executable(tmp_path, graph_request)
    provider = ContextEngineProvider(binary)
    result = provider.relations(graph_request)
    assert result.state.observed_content == (
        ("src/application/main.py", sha256(path.read_bytes()).hexdigest()),
    )
    runner = CliRunner()
    args = [
        "check",
        str(tmp_path),
        "--evidence-provider",
        "context-engine",
        "--context-engine-bin",
        binary,
    ]
    response = runner.invoke(app, [*args, "--format", "json"])
    assert response.exit_code == 0, response.output
    payload = json.loads(response.output)
    assert payload["findings"][0]["severity"] == "high"
    assert payload["architecture"]["provider"]["version"] == "0.1.0"
    assert payload["architecture"]["invariants"][0]["status"] == "violated"
    assert str(tmp_path) not in response.output
    assert "from storage import" not in response.output
    output = tmp_path / "output.json"
    saved = runner.invoke(app, [*args, "--format", "json", "--output", str(output)])
    assert saved.exit_code == 0 and not saved.output
    assert json.loads(output.read_text())["architecture"] == payload["architecture"]
    text = runner.invoke(app, args)
    assert text.exit_code == 0 and "violated" in text.output
    assert "python_import_syntax" in text.output


@pytest.mark.parametrize(
    "mode,code",
    [
        ("missing", "executable_unavailable"),
        ("malformed", "invalid_graph_response"),
        ("process", "process_failed"),
        ("timeout", "timeout"),
        ("stdout", "output_limit"),
        ("stderr", "output_limit"),
    ],
)
def test_transport_failures_sanitized(tmp_path, graph_request, mode, code):
    script = {
        "malformed": (
            'import sys; print("ctx 0.1.0" if sys.argv[1] == "--version" else "PRIVATE BODY")'
        ),
        "process": 'import sys; print("PRIVATE BODY", file=sys.stderr); sys.exit(2)',
        "timeout": "import time; time.sleep(2)",
        "stdout": 'print("PRIVATE BODY" * 10000)',
        "stderr": 'import sys; print("PRIVATE BODY" * 10000, file=sys.stderr)',
    }.get(mode)
    binary = (
        str(tmp_path / "missing")
        if mode == "missing"
        else executable(tmp_path, graph_request, script)
    )
    provider = ContextEngineProvider(
        binary, timeout=0.1 if mode == "timeout" else 5, stdout_limit=1024, stderr_limit=1024
    )
    with pytest.raises(EvidenceProviderError, match=code) as error:
        provider.relations(graph_request)
    assert "PRIVATE" not in str(error.value)
    assert str(tmp_path) not in str(error.value)


@pytest.mark.parametrize("mode", ["missing", "malformed"])
def test_cli_provider_exit7(tmp_path, mode):
    graph_request = EvidenceRelationRequest(tmp_path, scan_repository(tmp_path).repository)
    binary = (
        str(tmp_path / "missing")
        if mode == "missing"
        else executable(
            tmp_path,
            graph_request,
            'import sys; print("ctx 0.1.0" if sys.argv[1] == "--version" else "SECRET")',
        )
    )
    result = CliRunner().invoke(
        app,
        [
            "check",
            str(tmp_path),
            "--evidence-provider",
            "context-engine",
            "--context-engine-bin",
            binary,
        ],
    )
    assert result.exit_code == 7
    assert "SECRET" not in result.output


def test_cli_invalid_provider_options(tmp_path):
    runner = CliRunner()
    assert (
        runner.invoke(app, ["check", str(tmp_path), "--evidence-provider", "unknown"]).exit_code
        == 2
    )
    assert (
        runner.invoke(app, ["check", str(tmp_path), "--context-engine-bin", "ctx"]).exit_code == 2
    )


@pytest.mark.parametrize("timeout", [float("inf"), float("nan"), 0, -1, True])
def test_process_deadline_must_be_finite(timeout):
    with pytest.raises(ValueError):
        ContextEngineProvider(timeout=timeout)
