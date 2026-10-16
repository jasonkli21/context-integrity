"""External schema fixtures are generated here; no real ctx or network required."""

import json
import sys
from dataclasses import asdict, replace
from hashlib import sha256

import pytest
from typer.testing import CliRunner

from context_integrity.cli import app
from context_integrity.context_engine import (
    CHANGE_COUNTS,
    COVERAGE_BOOLS,
    COVERAGE_COUNTS,
    ContextEngineProvider,
    normalize_context,
)
from context_integrity.evidence import (
    EvidenceContextRequest,
    EvidenceProviderDescriptor,
    EvidenceProviderError,
)
from context_integrity.inventory import scan_repository

DESCRIPTOR = EvidenceProviderDescriptor(
    "context-engine",
    "0.1.0",
    capabilities=("context_candidates", "change_context"),
    derivation="context-engine-cli-json-v1",
)
BODY = "def sample():\n    return 'private body é'\n"


def selected_file(path="src/sample.py", rank=1, role="source", body=BODY):
    return dict(
        rank=rank,
        file_id=900,
        path=path,
        path_lossy=False,
        language="python",
        role=role,
        content_bytes=len(body.encode()),
        content=body,
        score=dict(
            total=10, lexical_path=10, lexical_symbol=0, graph=0, role=0, change=0, centrality=0
        ),
        reasons=["path_component_exact"],
        matched_symbols=[
            dict(
                qualified_name="sample",
                kind="function",
                path=path,
                range=dict(start=dict(byte=0), end=dict(byte=12)),
            )
        ],
        matched_symbols_omitted=0,
        graph_distance=None,
        change_distance=None,
    )


def response(request, files=None):
    files = [selected_file()] if files is None else files
    used = sum(f["content_bytes"] for f in files)
    return dict(
        schema_version=1,
        command="context",
        data=dict(
            repository=dict(
                root=str(request.repository_root),
                coverage=dict(
                    analysis_incomplete=False,
                    paths_may_be_lossy=False,
                    diagnostics_count=0,
                    scan_warning_count=0,
                ),
            ),
            git_head=request.repository.git_head,
            git_dirty=request.repository.git_dirty,
            task=request.task,
            ranker_version="file-ranker-v1",
            fallback_mode=None,
            budget=dict(
                unit="utf8_content_bytes",
                max=request.acquisition_budget_bytes,
                used=used,
                remaining=request.acquisition_budget_bytes - used,
            ),
            change=None,
            coverage={**dict.fromkeys(COVERAGE_BOOLS, False), **dict.fromkeys(COVERAGE_COUNTS, 0)},
            selected=files,
            skipped=[],
        ),
    )


def normalize(value, request):
    return normalize_context(json.dumps(value).encode(), request, DESCRIPTOR)


@pytest.fixture
def request_context(tmp_path):
    return EvidenceContextRequest(tmp_path, scan_repository(tmp_path).repository, "sample", 4096)


def fake_executable(tmp_path, value=None, script=None):
    path = tmp_path / "fake ctx"
    program = script or (
        "import json,sys\n"
        "if sys.argv[1:] == ['--version']:\n print('ctx 0.1.0')\n"
        f"else:\n print({json.dumps(value)!r})\n"
    )
    path.write_text(f"#!{sys.executable}\n" + program)
    path.chmod(0o755)
    return str(path)


def test_valid_hash_discard_and_relevance(request_context):
    batch = normalize(response(request_context), request_context)
    candidate = batch.candidates[0]
    assert candidate.revision.content_sha256 == sha256(BODY.encode()).hexdigest()
    assert candidate.size_bytes == len(BODY.encode())
    assert candidate.kind == "source_code" and candidate.authority_class == "executable_truth"
    assert candidate.lifecycle == "unknown" and candidate.revision.git_status == "unknown"
    assert candidate.relevance.rank == 1 and candidate.relevance.score == 10
    assert candidate.relevance.matched_entities == (("sample", "function", 0, 12),)
    assert BODY not in repr(asdict(batch)) and "content_bytes" not in repr(asdict(batch))
    assert str(request_context.repository_root) not in repr(asdict(batch))


@pytest.mark.parametrize(
    "location,value,code",
    [
        (("schema_version",), 2, "unsupported_contract"),
        (("schema_version",), True, "unsupported_contract"),
        (("command",), "scan", "unsupported_contract"),
        (("data", "repository", "root"), "/different-private-root", "repository_mismatch"),
        (("data", "task"), "other", "query_mismatch"),
        (("data", "selected", 0, "content_bytes"), 3, "content_size_mismatch"),
        (("data", "selected", 0, "content"), 2, "invalid_response"),
        (("data", "selected", 0, "rank"), 0, "invalid_response"),
        (("data", "selected", 0, "rank"), True, "invalid_response"),
        (("data", "selected", 0, "score", "total"), 99, "invalid_response"),
        (("data", "selected", 0, "reasons"), ["/secret/body"], "invalid_response"),
        (("data", "coverage", "graph_truncated"), "true", "invalid_response"),
        (("data", "budget", "used"), 0, "invalid_response"),
        (("data", "git_head"), "secret", "invalid_response"),
        (("data", "git_dirty"), 1, "invalid_response"),
        (("data", "ranker_version"), "/private/path", "invalid_response"),
    ],
)
def test_malformed_fields(request_context, location, value, code):
    fixture = response(request_context)
    target = fixture
    for key in location[:-1]:
        target = target[key]
    target[location[-1]] = value
    with pytest.raises(EvidenceProviderError) as error:
        normalize(fixture, request_context)
    assert error.value.code == code
    assert "secret" not in str(error.value) and "/private" not in str(error.value)


@pytest.mark.parametrize(
    "payload", [b"{", b"null", b"[]", b"{}", b'{"schema_version":1,"schema_version":1}', b"\xff"]
)
def test_invalid_json(payload, request_context):
    with pytest.raises(EvidenceProviderError):
        normalize_context(payload, request_context, DESCRIPTOR)


@pytest.mark.parametrize(
    "key",
    ["selected", "coverage", "git_head", "git_dirty", "change", "budget", "task", "ranker_version"],
)
def test_missing_fields(request_context, key):
    value = response(request_context)
    del value["data"][key]
    with pytest.raises(EvidenceProviderError):
        normalize(value, request_context)


@pytest.mark.parametrize(
    "path",
    [
        "/etc/secret",
        "../a",
        "a/../b",
        "C:/secret",
        "a\\b",
        "a\0b",
        "a//b",
        "./a",
        "a/",
        "a\nbody",
        "a\ufffdb",
    ],
)
def test_unsafe_paths(request_context, path):
    with pytest.raises(EvidenceProviderError, match="unsafe_path"):
        normalize(response(request_context, [selected_file(path)]), request_context)


def test_lossy_and_skipped_roles(request_context):
    value = response(
        request_context, [selected_file("a", 1), selected_file("README.md", 2, "docs")]
    )
    value["data"]["selected"][0]["path_lossy"] = True
    batch = normalize(value, request_context)
    assert not batch.candidates and batch.state.coverage.incomplete
    assert dict(batch.state.coverage.signals)["lossy_candidates_omitted"] == 1


@pytest.mark.parametrize(
    "role,kind",
    [("source", "source_code"), ("test", "test"), ("schema", "schema"), ("migration", "migration")],
)
def test_roles(request_context, role, kind):
    assert (
        normalize(response(request_context, [selected_file(role=role)]), request_context)
        .candidates[0]
        .kind
        == kind
    )


def test_duplicate_path_and_rank(request_context):
    for files in (
        [selected_file(), selected_file(rank=2, body="different")],
        [selected_file("a"), selected_file("b")],
    ):
        with pytest.raises(EvidenceProviderError):
            normalize(response(request_context, files), request_context)


@pytest.mark.parametrize("field,value", [("git_head", "b" * 40), ("git_dirty", True)])
def test_snapshot_mismatch(request_context, field, value):
    request = replace(
        request_context,
        repository=replace(request_context.repository, git_head="a" * 40, git_dirty=False),
    )
    fixture = response(request)
    fixture["data"][field] = value
    with pytest.raises(EvidenceProviderError, match="snapshot_mismatch"):
        normalize(fixture, request)


def test_change_and_coverage(request_context):
    request = replace(
        request_context,
        repository=replace(request_context.repository, git_head="a" * 40, git_dirty=False),
        change_range="base..HEAD",
    )
    fixture = response(request)
    fixture["data"]["change"] = {
        "range": "base..HEAD",
        "base": "b" * 40,
        "head": "a" * 40,
        **dict.fromkeys(CHANGE_COUNTS, 0),
    }
    fixture["data"]["change"]["unmapped_symbols"] = 1
    fixture["data"]["coverage"]["graph_truncated"] = True
    batch = normalize(fixture, request)
    assert batch.state.coverage.incomplete and batch.state.warnings
    assert dict(batch.state.change)["range"] == "base..HEAD"
    assert batch.candidates[0].revision.git_status == "tracked_clean"


@pytest.mark.parametrize(
    "signal",
    sorted(
        COVERAGE_BOOLS
        | {
            "content_load_failures",
            "ranking_roots_omitted",
            "selection_candidates_omitted",
            "budget_skips",
        }
    ),
)
def test_material_coverage(request_context, signal):
    value = response(request_context)
    value["data"]["coverage"][signal] = True if signal in COVERAGE_BOOLS else 1
    assert normalize(value, request_context).state.coverage.incomplete


def test_process_and_argv(tmp_path, request_context):
    script = (
        "import sys,json\nif sys.argv[1:] == ['--version']:\n print('ctx 0.1.0')\n"
        "else:\n assert sys.argv[1:] == "
        + repr(
            ["context", str(tmp_path), "--task", "sample", "--budget", "4096", "--format", "json"]
        )
        + "\n print("
        + repr(json.dumps(response(request_context)))
        + ")\n"
    )
    batch = ContextEngineProvider(fake_executable(tmp_path, script=script)).context_candidates(
        request_context
    )
    assert batch.candidates


@pytest.mark.parametrize(
    "script,options,code",
    [
        ("import sys; print('private body',file=sys.stderr); sys.exit(1)", {}, "process_failed"),
        ("import time; time.sleep(5)", {"timeout": 0.05}, "timeout"),
        ("print('x'*10000)", {"stdout_limit": 100}, "output_limit"),
        ("import sys; print('x'*10000,file=sys.stderr)", {"stderr_limit": 100}, "output_limit"),
        ("print('secret-version /root')", {}, "invalid_version"),
    ],
)
def test_process_failures(tmp_path, request_context, script, options, code):
    with pytest.raises(EvidenceProviderError) as error:
        ContextEngineProvider(
            fake_executable(tmp_path, script=script), **options
        ).context_candidates(request_context)
    assert error.value.code == code and "private" not in str(error.value)


def test_missing_executable(request_context):
    with pytest.raises(EvidenceProviderError, match="executable_unavailable"):
        ContextEngineProvider("/nonexistent/ctx").context_candidates(request_context)


CONFIG = """schema_version = 7
[[context_contracts]]
id = "work"
task_class = "implementation"
description = "Mixed context"
[[context_contracts.rules]]
id = "docs"
mode = "required"
paths = ["AGENTS.md"]
[[context_contracts.rules]]
id = "code"
mode = "required"
kinds = ["source_code"]
max_count = 1
"""


def test_cli_provider_output_and_errors(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "AGENTS.md").write_text("Instructions")
    (root / ".context-integrity.toml").write_text(CONFIG)
    request = EvidenceContextRequest(root, scan_repository(root).repository, "sample", 4096)
    executable = fake_executable(tmp_path, response(request))
    args = [
        "compile",
        "work",
        str(root),
        "--task",
        "sample",
        "--evidence-provider",
        "context-engine",
        "--context-engine-bin",
        executable,
        "--evidence-budget-bytes",
        "4096",
    ]
    result = CliRunner().invoke(app, [*args, "--format", "json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["status"] == "complete" and data["schema_version"] == 3
    assert BODY not in result.output and str(root) not in result.output
    output = tmp_path / "compiled.json"
    written = CliRunner().invoke(app, [*args, "--format", "json", "--output", str(output)])
    assert written.exit_code == 0 and json.loads(output.read_text()) == data
    assert "Provider: context-engine" in CliRunner().invoke(app, args).output
    missing = args.copy()
    missing[missing.index(executable)] = "/missing/ctx"
    failed = CliRunner().invoke(app, [*missing, "--format", "json"])
    assert failed.exit_code == 7 and "executable_unavailable" in failed.output


@pytest.mark.parametrize(
    "options",
    [
        ["--evidence-provider", "context-engine"],
        ["--evidence-provider", "unknown"],
        ["--context-engine-bin", "ctx"],
        ["--evidence-change", "x..y"],
        ["--evidence-provider", "context-engine", "--task", " "],
    ],
)
def test_cli_usage(options):
    assert CliRunner().invoke(app, ["compile", "work", *options]).exit_code == 2


def test_change_argv_literal_task_and_stderr_discard(tmp_path, request_context):
    request = replace(
        request_context,
        repository=replace(request_context.repository, git_head="a" * 40, git_dirty=False),
        task="sample; $(touch should-never-exist)",
        change_range="base..HEAD",
    )
    fixture = response(request)
    fixture["data"]["change"] = {
        "range": request.change_range,
        "base": "b" * 40,
        "head": "a" * 40,
        **dict.fromkeys(CHANGE_COUNTS, 0),
    }
    args = [
        "context",
        str(tmp_path),
        "--task",
        request.task,
        "--budget",
        "4096",
        "--format",
        "json",
        "--change",
        "base..HEAD",
    ]
    script = (
        "import sys\nif sys.argv[1:] == ['--version']:\n print('ctx 0.1.0')\n"
        f"else:\n assert sys.argv[1:] == {args!r}\n"
        " print('private stderr sentinel',file=sys.stderr)\n"
        f" print({json.dumps(fixture)!r})\n"
    )
    batch = ContextEngineProvider(fake_executable(tmp_path, script=script)).context_candidates(
        request
    )
    assert batch.state.task == request.task
    assert dict(batch.state.change)["head"] == "a" * 40
    assert "private stderr sentinel" not in repr(batch)


@pytest.mark.parametrize("value", [None, [], "1", -1])
def test_malformed_top_level_schema_types(request_context, value):
    fixture = response(request_context)
    fixture["schema_version"] = value
    with pytest.raises(EvidenceProviderError):
        normalize(fixture, request_context)


def test_reversed_provider_emission_order(request_context):
    fixture = response(request_context, [selected_file("a.py", 2), selected_file("z.py", 1)])
    forward = normalize(fixture, request_context)
    fixture["data"]["selected"].reverse()
    assert forward == normalize(fixture, request_context)
