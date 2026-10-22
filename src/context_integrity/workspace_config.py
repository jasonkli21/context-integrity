"""Strict bounded workspace TOML and consumer-owned contract lock JSON v1."""

import json
import os
import tomllib
from hashlib import sha256
from pathlib import Path

from context_integrity.acquisition import open_directory_no_follow, read_source_bytes
from context_integrity.derived_models import path_value, repo_value, require, token
from context_integrity.repository import RepositoryContext
from context_integrity.workspace_models import (
    CheckSpec,
    ContextTarget,
    ContractLock,
    RepositorySpec,
    RuleKind,
    WorkspaceSpec,
    root_value,
)

MANIFEST_LIMIT = 256 * 1024
LOCK_LIMIT = 16 * 1024
MAX_TOTAL_BUDGET = 64 * 1024 * 1024


class WorkspaceInputError(ValueError):
    """Sanitized invalid workspace declaration."""


def safe_directory(path: Path) -> Path:
    """Verify every ancestor with no-follow, including before processing '..'."""
    absolute = path.absolute()
    fd = open_directory_no_follow(absolute)
    os.close(fd)
    return Path(os.path.abspath(absolute))


def keys(value, required, optional=()):
    require(type(value) is dict and set(required) <= value.keys() <= set(required) | set(optional))


def array(value, maximum):
    require(type(value) is list and len(value) <= maximum)
    return value


def parse_workspace(data: bytes) -> WorkspaceSpec:
    try:
        require(len(data) <= MANIFEST_LIMIT)
        raw = tomllib.loads(data.decode("utf-8"))
        keys(raw, ("workspace_schema_version", "repositories"), ("checks", "context_targets"))
        require(
            type(raw["workspace_schema_version"]) is int and raw["workspace_schema_version"] == 1
        )
        repositories = []
        for entry in array(raw["repositories"], 8):
            keys(entry, ("alias", "root", "repository_id"))
            token(entry["alias"])
            repo_value(entry["repository_id"])
            root_value(entry["root"])
            repositories.append(RepositorySpec(**entry))
        aliases = {r.alias for r in repositories}
        require(2 <= len(repositories) == len(aliases))
        require(len({r.repository_id for r in repositories}) == len(repositories))
        checks = []
        for entry in array(raw.get("checks", []), 128):
            require(type(entry) is dict)
            kind = RuleKind(entry.get("kind"))
            if kind == RuleKind.CONTRACT_PIN:
                fields = ("producer_repo", "producer_path", "consumer_repo", "consumer_path")
            else:
                suffix = "claim_id" if kind == RuleKind.CLAIM_MATCH else "path"
                fields = ("left_repo", f"left_{suffix}", "right_repo", f"right_{suffix}")
            keys(entry, ("id", "kind", *fields))
            token(entry["id"])
            left_repo, left, right_repo, right = (entry[f] for f in fields)
            require(type(left_repo) is str and type(right_repo) is str)
            require(left_repo in aliases and right_repo in aliases and left_repo != right_repo)
            validate = token if kind == RuleKind.CLAIM_MATCH else path_value
            validate(left)
            validate(right)
            checks.append(CheckSpec(entry["id"], kind, left_repo, left, right_repo, right))
        require(len({c.id for c in checks}) == len(checks))
        refs = {(c.left_repo, c.left) for c in checks} | {(c.right_repo, c.right) for c in checks}
        require(len(refs) <= 256)
        targets = []
        for entry in array(raw.get("context_targets", []), 16):
            keys(entry, ("repo", "contract_id", "budget_bytes"))
            token(entry["repo"])
            require(entry["repo"] in aliases)
            token(entry["contract_id"])
            budget = entry["budget_bytes"]
            require(type(budget) is int and 1 <= budget <= MAX_TOTAL_BUDGET)
            targets.append(ContextTarget(**entry))
        require(len({(t.repo, t.contract_id) for t in targets}) == len(targets))
        require(sum(t.budget_bytes for t in targets) <= MAX_TOTAL_BUDGET)
        return WorkspaceSpec(
            sha256(data).hexdigest(),
            tuple(sorted(repositories, key=lambda r: r.alias)),
            tuple(sorted(checks, key=lambda c: c.id)),
            tuple(sorted(targets, key=lambda t: (t.repo, t.contract_id))),
        )
    except (ValueError, TypeError, KeyError, RecursionError) as exc:
        raise WorkspaceInputError("invalid_workspace_manifest") from exc


def load_workspace(path: Path) -> tuple[WorkspaceSpec, Path]:
    try:
        parent = safe_directory(path.absolute().parent)
        path_value(path.name)
        context = RepositoryContext(parent, None, {}, False, [])
        data = read_source_bytes(context, path.name, max_bytes=MANIFEST_LIMIT, require_stable=True)
        require(data is not None)
        return parse_workspace(data), parent
    except (OSError, ValueError) as exc:
        raise WorkspaceInputError("invalid_workspace_manifest") from exc


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result)
        result[key] = value
    return result


def parse_lock(data: bytes) -> ContractLock:
    try:
        require(len(data) <= LOCK_LIMIT)
        raw = json.loads(data, object_pairs_hook=_pairs)
        keys(
            raw,
            (
                "contract_lock_schema_version",
                "producer_repository_id",
                "producer_path",
                "accepted_sha256",
            ),
        )
        require(type(raw["contract_lock_schema_version"]) is int)
        require(raw["contract_lock_schema_version"] == 1)
        return ContractLock(
            raw["producer_repository_id"], raw["producer_path"], raw["accepted_sha256"]
        )
    except (ValueError, TypeError, KeyError, RecursionError) as exc:
        raise WorkspaceInputError("invalid_contract_lock") from exc
