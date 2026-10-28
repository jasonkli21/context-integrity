#!/usr/bin/env python3
"""Run a small, offline task-context evaluation against authored Git fixtures.

This is descriptive evaluation tooling. It does not execute fixture source, modify
the product, or claim task success from selected-file recall.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SENTINEL = "EVAL_BODY_SENTINEL_NEVER_EXPORT"


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    category: str
    task: str
    expected_paths: tuple[str, ...]
    budget_bytes: int


FILES: dict[str, str] = {
    "src/parser/token_rules.py": (
        "# " + SENTINEL + "\n"
        "def load_token_rules():\n"
        '    return {"quoted": True, "escaped": True}\n'
    ),
    "tests/test_token_rules.py": (
        "def test_token_rules_preserve_quoted_values():\n    assert True\n"
    ),
    "src/session/manager.py": (
        'def refresh_session(session_id):\n    return {"id": session_id, "refreshed": True}\n'
    ),
    "tests/test_manager.py": ("def test_refresh_session_keeps_identifier():\n    assert True\n"),
    "src/transport.rs": (
        "pub fn decode_frame_v2(input: &[u8]) -> Result<Vec<u8>, &'static str> {\n"
        '    if input.is_empty() { return Err("empty"); }\n'
        "    Ok(input.to_vec())\n"
        "}\n"
    ),
    "tests/transport.rs": ("#[test]\nfn decoding_a_frame_preserves_payload() { assert!(true); }\n"),
    "src/keys.py": (
        "def rotate_signing_key(key_id, key_store):\n    return key_store.replace(key_id)\n"
    ),
    "tests/test_keys.py": ("def test_rotate_signing_key_replaces_old_key():\n    assert True\n"),
    "docs/credential-rotation.md": (
        "# Credential rotation\n"
        "Old runbook: rotate signing key by editing the legacy key table.\n"
        "The current service implementation is documented elsewhere.\n"
    ),
    "src/policy/current.rs": (
        "pub fn validate_policy(input: &str) -> bool { !input.is_empty() }\n"
    ),
    "src/compat/old_policy.rs": (
        "pub fn validate_policy(input: &str) -> bool { input.trim().len() > 0 }\n"
    ),
    "src/worker.py": (
        "def drain_job_queue(queue):\n    return [job for job in queue if job.ready]\n"
    ),
    "tests/test_worker.py": ("def test_drain_job_queue_skips_unready_jobs():\n    assert True\n"),
    "docs/queue-troubleshooting.md": (
        "# Queue troubleshooting\n"
        "Drain job queue incidents by checking worker logs and retry settings.\n"
    ),
    "src/queue_metrics.py": ('def queue_metrics_snapshot():\n    return {"depth": 0}\n'),
    "src/index.rs": ("pub fn rebuild_compact_index(paths: &[String]) -> usize { paths.len() }\n"),
    "tests/index_test.rs": ("#[test]\nfn compact_index_keeps_unique_paths() { assert!(true); }\n"),
    "docs/index-operations.md": (
        "# Compact index operations\n"
        "This document describes the compact index rollout and rollback.\n"
    ),
    "src/index_debug.rs": ('pub fn compact_index_debug_label() -> &\'static str { "debug" }\n'),
    "src/unsupported/manifest.go": (
        "package manifest\nfunc extractManifest(input []byte) []byte { return input }\n"
    ),
    "docs/overview.md": "Local fixture project for bounded ranking evaluation.\n",
}


def _byte_len(path: str) -> int:
    return len(FILES[path].encode("utf-8"))


# Oracles and budgets are fixed before the runner observes a ctx result.
SCENARIOS = (
    Scenario(
        "path_only_python",
        "exact_path_only",
        "src/parser/token_rules.py",
        ("src/parser/token_rules.py",),
        _byte_len("src/parser/token_rules.py"),
    ),
    Scenario(
        "symbol_only_python",
        "symbol_only",
        "refresh_session",
        ("src/session/manager.py",),
        _byte_len("src/session/manager.py"),
    ),
    Scenario(
        "symbol_only_rust",
        "symbol_only",
        "decode_frame_v2",
        ("src/transport.rs",),
        _byte_len("src/transport.rs"),
    ),
    Scenario(
        "misleading_documentation",
        "misleading_docs",
        "rotate signing key",
        ("src/keys.py", "tests/test_keys.py"),
        _byte_len("src/keys.py") + _byte_len("tests/test_keys.py"),
    ),
    Scenario(
        "multiple_plausible_implementations",
        "multiple_plausible_files",
        "validate_policy",
        ("src/compat/old_policy.rs", "src/policy/current.rs"),
        _byte_len("src/compat/old_policy.rs") + _byte_len("src/policy/current.rs"),
    ),
    Scenario(
        "irrelevant_lexical_hits",
        "irrelevant_lexical_hits",
        "drain job queue",
        ("src/worker.py", "tests/test_worker.py"),
        _byte_len("src/worker.py") + _byte_len("tests/test_worker.py"),
    ),
    Scenario(
        "budget_pressure",
        "budget_pressure",
        "rebuild compact index",
        ("src/index.rs", "tests/index_test.rs"),
        _byte_len("src/index.rs") + _byte_len("tests/index_test.rs"),
    ),
    Scenario(
        "unsupported_language_coverage",
        "incomplete_or_unsupported_analysis",
        "src/unsupported/manifest.go",
        ("src/unsupported/manifest.go",),
        _byte_len("src/unsupported/manifest.go"),
    ),
)


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("ascii")).hexdigest()


def oracle_manifest() -> dict[str, Any]:
    """Commit the registered task text, fixture bytes, expected paths, and budgets."""
    return {
        "scenarios": [
            {
                "id": scenario.scenario_id,
                "category": scenario.category,
                "task_sha256": hashlib.sha256(scenario.task.encode("utf-8")).hexdigest(),
                "expected_paths": list(scenario.expected_paths),
                "budget_bytes": scenario.budget_bytes,
            }
            for scenario in SCENARIOS
        ],
        "fixture_files": {
            path: hashlib.sha256(content.encode("utf-8")).hexdigest()
            for path, content in sorted(FILES.items())
        },
    }


def _task_terms(task: str) -> tuple[str, ...]:
    phrase = " ".join(task.split()).lower()
    terms: set[str] = set()
    for token in re.split(r"[^\w./:-]+", phrase):
        for term in re.split(r"[_\-./:]", token):
            if term and (len(term) > 1 or len(phrase) == 1):
                terms.add(term)
    return tuple(sorted(terms))


def select_keyword_grep(task: str, budget_bytes: int) -> tuple[list[str], int]:
    """Primitive path-and-body grep baseline, with whole-file byte accounting."""
    terms = _task_terms(task)
    phrase = " ".join(task.split()).lower()
    ranked: list[tuple[int, str, int]] = []
    for path, content in FILES.items():
        haystack = f"{path.lower()}\n{content.lower()}"
        matched = sum(term in haystack for term in terms)
        if matched:
            if phrase in path.lower():
                matched += 1
            ranked.append((-matched, path, _byte_len(path)))
    ranked.sort()
    return _fit_budget(ranked, budget_bytes)


def select_path_order(budget_bytes: int) -> tuple[list[str], int]:
    """Lexical path-order baseline over the same authored files and byte budget."""
    ranked = [(0, path, _byte_len(path)) for path in sorted(FILES)]
    return _fit_budget(ranked, budget_bytes)


def _fit_budget(ranked: list[tuple[int, str, int]], budget_bytes: int) -> tuple[list[str], int]:
    selected: list[str] = []
    used = 0
    for _, path, size in ranked:
        if used + size <= budget_bytes:
            selected.append(path)
            used += size
    return selected, used


def normalize_candidates(document: dict[str, Any]) -> dict[str, Any]:
    """Remove invocation-scoped references while retaining stable candidate semantics."""
    if not isinstance(document, dict) or document.get("feed") != "candidates":
        raise ValueError("unexpected evidence feed")
    data = document.get("data")
    if not isinstance(data, dict) or not isinstance(data.get("candidates"), list):
        raise ValueError("malformed candidate feed")
    normalized = []
    for candidate in data["candidates"]:
        if not isinstance(candidate, dict):
            raise ValueError("malformed candidate")
        file = candidate.get("file")
        if not isinstance(file, dict):
            raise ValueError("malformed candidate file")
        matched_symbols = candidate.get("matched_symbols")
        if not isinstance(matched_symbols, list) or any(
            not isinstance(symbol, dict) for symbol in matched_symbols
        ):
            raise ValueError("malformed matched symbols")
        normalized.append(
            {
                "rank": candidate.get("rank"),
                "path": file.get("path"),
                "language": file.get("language"),
                "role": file.get("role"),
                "analysis_status": file.get("analysis_status"),
                "score": candidate.get("score"),
                "reasons": candidate.get("reasons"),
                "matched_symbols": [
                    {
                        "path": symbol.get("path"),
                        "kind": symbol.get("kind"),
                        "name": symbol.get("name"),
                        "qualified_name": symbol.get("qualified_name"),
                        "range": symbol.get("range"),
                    }
                    for symbol in matched_symbols
                ],
                "matched_symbols_omitted": candidate.get("matched_symbols_omitted"),
                "graph_distance": candidate.get("graph_distance"),
                "change_distance": candidate.get("change_distance"),
            }
        )
    return {
        "ranker_version": data.get("ranker_version"),
        "sort_order": data.get("sort_order"),
        "semantics": data.get("semantics"),
        "task_digest": data.get("task_digest"),
        "fallback": data.get("fallback"),
        "candidates": normalized,
        "coverage": document.get("coverage"),
    }


def _contains_key(value: Any, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, key) for item in value)
    return False


def _run(argv: list[str], env: dict[str, str], timeout_seconds: int = 120) -> tuple[int, str]:
    try:
        result = subprocess.run(
            argv,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return 124, "timeout"
    except OSError:
        return 127, "launch_failed"
    if result.returncode:
        return result.returncode, "command_failed"
    return 0, result.stdout


def _isolated_git_env(base_env: dict[str, str]) -> dict[str, str]:
    """Ignore ambient Git config and repository overrides for disposable fixtures."""
    env = {key: value for key, value in base_env.items() if not key.startswith("GIT_")}
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    return env


def _git(root: Path, *args: str, env: dict[str, str]) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )
    return result.stdout.strip()


def _write_fixture(root: Path, env: dict[str, str]) -> str:
    for relative, content in FILES.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
    _git(root, "init", "--initial-branch=main", "--object-format=sha1", env=env)
    _git(root, "add", "--all", env=env)
    _git(root, "commit", "-m", "fixture", env=env)
    return _git(root, "rev-parse", "HEAD", env=env)


def _context_result(
    binary: Path, root: Path, scenario: Scenario, env: dict[str, str]
) -> dict[str, Any]:
    code, stdout = _run(
        [
            str(binary),
            "context",
            str(root),
            "--task",
            scenario.task,
            "--budget",
            str(scenario.budget_bytes),
            "--format",
            "json",
        ],
        env,
    )
    if code:
        return {
            "status": "error",
            "error_code": stdout,
            "selected": [],
            "content_bytes": 0,
        }
    try:
        document = json.loads(stdout)
    except json.JSONDecodeError:
        return {
            "status": "error",
            "error_code": "invalid_json",
            "selected": [],
            "content_bytes": 0,
        }
    if (
        not isinstance(document, dict)
        or document.get("command") != "context"
        or document.get("schema_version") != 1
    ):
        return {
            "status": "error",
            "error_code": "unexpected_context_schema",
            "selected": [],
            "content_bytes": 0,
        }
    data = document.get("data")
    if not isinstance(data, dict) or not isinstance(data.get("selected"), list):
        return {
            "status": "error",
            "error_code": "malformed_context",
            "selected": [],
            "content_bytes": 0,
        }
    try:
        coverage = data["coverage"]
        budget_used = data["budget"]["used"]
        if not isinstance(coverage, dict):
            raise TypeError
        selected_metadata = [
            {
                "path": item["path"],
                "content_bytes": item["content_bytes"],
                "score": item["score"],
                "reasons": item["reasons"],
            }
            for item in data["selected"]
            if isinstance(item, dict)
        ]
        if len(selected_metadata) != len(data["selected"]):
            raise TypeError
        coverage_metadata = {
            key: coverage[key]
            for key in (
                "files_considered",
                "files_eligible",
                "content_load_failures",
                "budget_skips",
                "selection_candidates_omitted",
            )
        }
    except (KeyError, TypeError):
        return {
            "status": "error",
            "error_code": "malformed_context",
            "selected": [],
            "content_bytes": 0,
        }
    return {
        "status": "ok",
        "selected": selected_metadata,
        "content_bytes": budget_used,
        "coverage": coverage_metadata,
    }


def _candidate_pair(
    binary: Path, root: Path, scenario: Scenario, env: dict[str, str], commit: str
) -> dict[str, Any]:
    command = [
        str(binary),
        "evidence",
        "candidates",
        str(root),
        "--repository-id",
        "evaluation",
        "--task",
        scenario.task,
        "--limit",
        "200",
        "--format",
        "json",
    ]
    normal_forms = []
    observations = []
    for _ in range(2):
        code, stdout = _run(command, env)
        if code:
            return {"status": "error", "error_code": stdout}
        try:
            document = json.loads(stdout)
            normal_forms.append(normalize_candidates(document))
        except (json.JSONDecodeError, ValueError, KeyError, TypeError, AttributeError):
            return {"status": "error", "error_code": "invalid_evidence_feed"}
        if not isinstance(document, dict):
            return {"status": "error", "error_code": "invalid_evidence_feed"}
        observation = document.get("observation", {})
        coverage = document.get("coverage", {})
        if not isinstance(observation, dict) or not isinstance(coverage, dict):
            return {"status": "error", "error_code": "invalid_evidence_feed"}
        if (
            document.get("evidence_schema_version") != 1
            or observation.get("basis") != "best_effort_worktree"
            or observation.get("atomic") is not False
            or observation.get("git_head") != commit
            or observation.get("git_dirty") is not False
            or coverage.get("complete") is not False
            or _contains_key(document, "content")
            or SENTINEL in stdout
            or str(root) in stdout
        ):
            return {"status": "error", "error_code": "evidence_boundary_violation"}
        observations.append(observation)
    first, second = normal_forms
    scopes_differ = observations[0]["scope"] != observations[1]["scope"]
    counters = first.get("coverage", {}).get("counts", {})
    return {
        "status": "ok",
        "normalized_semantics_equal": first == second,
        "worktree_scope_nonce_changed": scopes_differ,
        "basis": "best_effort_worktree",
        "committed_head_matches_fixture": True,
        "coverage_complete": False,
        "unsupported_language_files": counters.get("analysis_unsupported_language", 0),
        "candidate_count": len(first["candidates"]),
    }


def evaluate(binary: Path, engine: Path) -> dict[str, Any]:
    binary = binary.resolve(strict=True)
    engine = engine.resolve(strict=True)
    git_env = _isolated_git_env(dict(os.environ))
    engine_sha = subprocess.run(
        ["git", "-C", str(engine), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        env=git_env,
    ).stdout.strip()
    engine_status = subprocess.run(
        ["git", "-C", str(engine), "status", "--porcelain=v1"],
        check=True,
        capture_output=True,
        text=True,
        env=git_env,
    ).stdout.splitlines()
    version_code, version = _run([str(binary), "--version"], dict(os.environ))
    if version_code:
        raise RuntimeError("ctx_version_failed")
    binary_sha = hashlib.sha256(binary.read_bytes()).hexdigest()
    integrity_sha = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        env=git_env,
    ).stdout.strip()
    integrity_status = subprocess.run(
        ["git", "-C", str(ROOT), "status", "--porcelain=v1"],
        check=True,
        capture_output=True,
        text=True,
        env=git_env,
    ).stdout.splitlines()

    registration = oracle_manifest()
    with tempfile.TemporaryDirectory(prefix="context-integrity-post-phase11-") as temp_name:
        temp = Path(temp_name)
        fixture_root = temp / "fixture"
        fixture_root.mkdir()
        cache = temp / "engine-cache"
        cache.mkdir()
        fixture_env = {
            **_isolated_git_env(dict(os.environ)),
            "GIT_AUTHOR_NAME": "Evaluation Fixture",
            "GIT_AUTHOR_EMAIL": "evaluation@example.invalid",
            "GIT_COMMITTER_NAME": "Evaluation Fixture",
            "GIT_COMMITTER_EMAIL": "evaluation@example.invalid",
            "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z",
            "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z",
        }
        fixture_commit = _write_fixture(fixture_root, fixture_env)
        command_env = _isolated_git_env(dict(os.environ))
        command_env["CONTEXT_ENGINE_CACHE_DIR"] = str(cache)

        results: list[dict[str, Any]] = []
        for scenario in SCENARIOS:
            first = _context_result(binary, fixture_root, scenario, command_env)
            second = _context_result(binary, fixture_root, scenario, command_env)
            if first.get("status") == "ok" and second.get("status") == "ok":
                stable = first == second
                selected_paths = sorted(item["path"] for item in first["selected"])
                selected_bytes = first["content_bytes"]
            else:
                stable = False
                selected_paths = []
                selected_bytes = 0

            grep_paths, grep_bytes = select_keyword_grep(scenario.task, scenario.budget_bytes)
            path_paths, path_bytes = select_path_order(scenario.budget_bytes)
            expected = set(scenario.expected_paths)
            strategies = {
                "ctx": (selected_paths, selected_bytes),
                "keyword_grep": (grep_paths, grep_bytes),
                "path_order": (path_paths, path_bytes),
            }
            metrics = {}
            for name, (paths, used_bytes) in strategies.items():
                selected = set(paths)
                metrics[name] = {
                    "recalled": len(expected & selected),
                    "expected": len(expected),
                    "recall": round(len(expected & selected) / len(expected), 4)
                    if expected
                    else None,
                    "extraneous": len(selected - expected),
                    "selected_file_count": len(paths),
                    "content_bytes": used_bytes,
                }
            evidence = _candidate_pair(binary, fixture_root, scenario, command_env, fixture_commit)
            results.append(
                {
                    "scenario_id": scenario.scenario_id,
                    "category": scenario.category,
                    "expected_paths": list(scenario.expected_paths),
                    "ctx_status": first.get("status"),
                    "ctx_error_code": first.get("error_code"),
                    "normalized_context_stable": stable,
                    "ctx_selected_paths": selected_paths,
                    "ctx_coverage": first.get("coverage"),
                    "strategies": metrics,
                    "evidence_v1": evidence,
                }
            )

    totals = {}
    for name in ("ctx", "keyword_grep", "path_order"):
        totals[name] = {
            key: sum(s["strategies"][name][key] for s in results)
            for key in (
                "recalled",
                "expected",
                "extraneous",
                "selected_file_count",
                "content_bytes",
            )
        }
        totals[name]["recall"] = round(totals[name]["recalled"] / totals[name]["expected"], 4)
    comparisons = {}
    for baseline in ("keyword_grep", "path_order"):
        comparisons[baseline] = {
            "recall_wins": 0,
            "recall_ties": 0,
            "recall_losses": 0,
            "extraneous_wins": 0,
            "extraneous_ties": 0,
            "extraneous_losses": 0,
            "ctx_bytes_lower": 0,
            "ctx_bytes_ties": 0,
            "ctx_bytes_higher": 0,
        }
        for result in results:
            current = result["strategies"]["ctx"]
            other = result["strategies"][baseline]
            for metric, direction in (
                ("recall", "higher"),
                ("extraneous", "lower"),
                ("content_bytes", "lower"),
            ):
                key = f"{metric}_wins" if metric != "content_bytes" else "ctx_bytes_lower"
                tie = f"{metric}_ties" if metric != "content_bytes" else "ctx_bytes_ties"
                loss = f"{metric}_losses" if metric != "content_bytes" else "ctx_bytes_higher"
                current_value = current[metric]
                other_value = other[metric]
                if current_value == other_value:
                    comparisons[baseline][tie] += 1
                elif (current_value > other_value) == (direction == "higher"):
                    comparisons[baseline][key] += 1
                else:
                    comparisons[baseline][loss] += 1

    semantic = [
        {
            "scenario_id": result["scenario_id"],
            "category": result["category"],
            "expected_paths": result["expected_paths"],
            "ctx_status": result["ctx_status"],
            "ctx_error_code": result["ctx_error_code"],
            "normalized_context_stable": result["normalized_context_stable"],
            "ctx_selected_paths": result["ctx_selected_paths"],
            "ctx_coverage": result["ctx_coverage"],
            "strategies": result["strategies"],
            "evidence_v1": result["evidence_v1"],
        }
        for result in results
    ]
    return {
        "post_phase11_evaluation_schema_version": 1,
        "evaluation": {
            "integrity_source_sha": integrity_sha,
            "engine_source_sha": engine_sha,
            "engine_worktree_clean": not engine_status,
            "engine_untracked_or_modified_paths": sorted(
                line[3:] for line in engine_status if len(line) > 3
            ),
            "ctx_version": version.strip(),
            "ctx_binary_sha256": binary_sha,
            "evaluation_runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "ctx_binary_build_provenance": (
                "operator recorded offline build from engine_source_sha; executable hash is "
                "verified, but build provenance is not encoded in the binary"
            ),
            "fixture_git_configuration": (
                "system and global Git config disabled; ambient GIT_* overrides removed"
            ),
            "resource_limits": {
                "ctx_command_timeout_seconds": 120,
                "candidate_limit": 200,
                "fixture_file_count": len(FILES),
                "fixture_content_bytes": sum(_byte_len(path) for path in FILES),
            },
            "fixture_commit": fixture_commit,
            "fixture_task_count": len(SCENARIOS),
            "fixture_oracle_sha256": _canonical_sha256(registration),
            "execution_status": "complete"
            if all(
                r["ctx_status"] == "ok"
                and r["normalized_context_stable"]
                and r["evidence_v1"].get("status") == "ok"
                and r["evidence_v1"].get("normalized_semantics_equal") is True
                and r["evidence_v1"].get("worktree_scope_nonce_changed") is True
                and (
                    r["category"] != "incomplete_or_unsupported_analysis"
                    or r["evidence_v1"].get("unsupported_language_files", 0) > 0
                )
                for r in results
            )
            else "incomplete",
            "full_recall_scenarios": sum(
                result["strategies"]["ctx"]["recalled"] == result["strategies"]["ctx"]["expected"]
                for result in results
            ),
            "integrity_worktree_clean": not integrity_status,
            "integrity_untracked_or_modified_paths": sorted(
                line[3:] for line in integrity_status if len(line) > 3
            ),
            "scenarios": results,
            "totals": totals,
            "comparison_to_baselines": comparisons,
            "semantic_sha256": _canonical_sha256(semantic),
            "limits": [
                "authored_fixtures_only",
                "selected_file_recall_is_not_task_success",
                "keyword_grep_baseline_is_simple_and_not_tuned",
                "path_order_baseline_is_a_budgeted_control_not_a_search_product",
                "coverage_is_never_complete_evidence",
                "evidence_v1_worktree_references_are_invocation_scoped",
                "no_production_evidence_v1_consumer_is_exercised",
                "fixture_source_is_analyzed_but_never_executed",
            ],
        },
    }


def _write_json(path: Path, report: dict[str, Any]) -> None:
    rendered = json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    if len(rendered.encode("utf-8")) > 2 * 1024 * 1024:
        raise RuntimeError("evaluation_report_exceeds_limit")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ctx", type=Path, required=True, help="Locally built ctx executable")
    parser.add_argument("--engine", type=Path, required=True, help="Engine source checkout")
    parser.add_argument("--output", type=Path, required=True, help="Machine-readable JSON report")
    args = parser.parse_args(argv)
    report = evaluate(args.ctx, args.engine)
    _write_json(args.output, report)
    print(
        json.dumps(
            {
                "execution_status": report["evaluation"]["execution_status"],
                "task_count": report["evaluation"]["fixture_task_count"],
                "totals": report["evaluation"]["totals"],
                "semantic_sha256": report["evaluation"]["semantic_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0 if report["evaluation"]["execution_status"] == "complete" else 1


if __name__ == "__main__":
    sys.exit(main())
