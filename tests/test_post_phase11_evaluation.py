"""Guards for the frozen, metadata-only post-Phase-11 evaluation harness."""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import replace
from pathlib import Path

module_path = Path(__file__).resolve().parents[1] / "scripts" / "post_phase11_evaluate.py"
module_spec = importlib.util.spec_from_file_location("post_phase11_evaluate", module_path)
assert module_spec is not None and module_spec.loader is not None
evaluation = importlib.util.module_from_spec(module_spec)
sys.modules[module_spec.name] = evaluation
module_spec.loader.exec_module(evaluation)


def test_task_oracles_are_pre_registered_and_span_requested_cases(monkeypatch):
    assert len(evaluation.SCENARIOS) == 8
    assert {scenario.category for scenario in evaluation.SCENARIOS} == {
        "exact_path_only",
        "symbol_only",
        "misleading_docs",
        "multiple_plausible_files",
        "irrelevant_lexical_hits",
        "budget_pressure",
        "incomplete_or_unsupported_analysis",
    }
    assert all(scenario.expected_paths for scenario in evaluation.SCENARIOS)
    assert all(
        path in evaluation.FILES
        for scenario in evaluation.SCENARIOS
        for path in scenario.expected_paths
    )
    assert all(
        scenario.budget_bytes == sum(evaluation._byte_len(path) for path in scenario.expected_paths)
        for scenario in evaluation.SCENARIOS
    )
    original_digest = evaluation._canonical_sha256(evaluation.oracle_manifest())
    changed = replace(evaluation.SCENARIOS[0], task="different task")
    monkeypatch.setattr(evaluation, "SCENARIOS", (changed, *evaluation.SCENARIOS[1:]))
    assert evaluation._canonical_sha256(evaluation.oracle_manifest()) != original_digest


def test_keyword_grep_and_path_order_honor_whole_file_byte_budgets(monkeypatch):
    monkeypatch.setattr(
        evaluation,
        "FILES",
        {
            "src/a.py": "alpha marker\n",
            "src/b.py": "beta marker\n",
            "docs/c.md": "no terms\n",
        },
    )
    grep_paths, grep_bytes = evaluation.select_keyword_grep("alpha", 13)
    path_paths, path_bytes = evaluation.select_path_order(13)

    assert grep_paths == ["src/a.py"]
    assert grep_bytes == len(b"alpha marker\n")
    assert path_paths == ["docs/c.md"]
    assert path_bytes == len(b"no terms\n")


def test_fixture_git_commands_ignore_ambient_git_environment():
    isolated = evaluation._isolated_git_env(
        {
            "PATH": "/usr/bin",
            "GIT_DIR": "/tmp/unrelated.git",
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "filter.probe.clean",
            "GIT_AUTHOR_NAME": "ambient",
        }
    )

    assert isolated["PATH"] == "/usr/bin"
    assert isolated["GIT_CONFIG_NOSYSTEM"] == "1"
    assert isolated["GIT_CONFIG_GLOBAL"] == evaluation.os.devnull
    assert "GIT_DIR" not in isolated
    assert "GIT_CONFIG_COUNT" not in isolated
    assert "GIT_AUTHOR_NAME" not in isolated


def test_normalized_evidence_discards_nonce_bound_references():
    def document(scope: str, file_id: str) -> dict:
        return {
            "feed": "candidates",
            "coverage": {"complete": False, "counts": {"eligible_files": 1}},
            "data": {
                "ranker_version": "file-ranker-v1",
                "sort_order": "total_desc,native_path_asc",
                "semantics": "ranked_metadata_not_content_selection",
                "task_digest": "a" * 64,
                "fallback": False,
                "candidates": [
                    {
                        "rank": 1,
                        "file": {
                            "id": file_id,
                            "path": "src/a.py",
                            "language": "Python",
                            "role": "Source",
                            "analysis_status": "analyzed",
                        },
                        "score": {"total": 10, "lexical_symbol": 10},
                        "reasons": ["symbol_local_exact"],
                        "matched_symbols": [],
                        "matched_symbols_omitted": 0,
                        "graph_distance": None,
                        "change_distance": None,
                    }
                ],
            },
            "observation": {"scope": scope},
        }

    first = evaluation.normalize_candidates(document("nonce-a", "file-a"))
    second = evaluation.normalize_candidates(document("nonce-b", "file-b"))
    assert first == second
    assert first["candidates"][0]["path"] == "src/a.py"


def test_process_failures_are_recorded_with_bounded_status(monkeypatch):
    def timeout(*_args, **_kwargs):
        raise evaluation.subprocess.TimeoutExpired("ctx", 1)

    monkeypatch.setattr(evaluation.subprocess, "run", timeout)
    assert evaluation._run(["ctx"], {}, timeout_seconds=1) == (124, "timeout")

    def launch_failure(*_args, **_kwargs):
        raise OSError("not exposed")

    monkeypatch.setattr(evaluation.subprocess, "run", launch_failure)
    assert evaluation._run(["ctx"], {}) == (127, "launch_failed")
