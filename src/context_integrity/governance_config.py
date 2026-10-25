"""Strict explicit governance TOML v1; no implicit policy discovery."""

import re
import tomllib
from datetime import date
from hashlib import sha256
from pathlib import Path

from context_integrity.acquisition import read_source_bytes
from context_integrity.derived_models import digest, path_value, repo_value, require, token
from context_integrity.governance_models import (
    MAX_POLICY_BYTES,
    SEVERITIES,
    GovernanceError,
    Policy,
    RulePolicy,
    Target,
    Waiver,
)
from context_integrity.repository import RepositoryContext
from context_integrity.workspace_config import array, keys, safe_directory


def owner(value):
    require(isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.:+-]{0,99}", value))


def reason(value):
    require(isinstance(value, str) and 1 <= len(value) <= 512 and bool(value.strip()))
    require(all(32 <= ord(c) < 127 for c in value))


def review(value):
    require(isinstance(value, str) and 1 <= len(value) <= 256)
    require(re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.:+/-]*", value))
    require(not value.startswith("/") and ".." not in value)
    require(":" not in value or value.startswith("https://"))


def iso_date(value):
    require(type(value) is str and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value))
    return date.fromisoformat(value)


def relative(value, *, root=False):
    if root and value == ".":
        return
    path_value(value)


def read_input(path: Path, limit: int) -> bytes:
    """Bound and verify stable regular-file bytes through no-follow ancestors."""
    try:
        parent = safe_directory(path.absolute().parent)
        path_value(path.name)
        context = RepositoryContext(parent, None, {}, False, [])
        data = read_source_bytes(context, path.name, max_bytes=limit, require_stable=True)
        require(data is not None)
        return data
    except (OSError, ValueError) as exc:
        raise GovernanceError("governance_input_unavailable") from exc


def parse_policy(data: bytes) -> Policy:
    try:
        require(type(data) is bytes and len(data) <= MAX_POLICY_BYTES)
        raw = tomllib.loads(data.decode("utf-8"))
        keys(
            raw,
            (
                "governance_schema_version",
                "policy_id",
                "owner",
                "fail_on",
                "on_inconclusive",
                "targets",
            ),
            ("rule_policies", "waivers"),
        )
        require(
            type(raw["governance_schema_version"]) is int and raw["governance_schema_version"] == 1
        )
        token(raw["policy_id"])
        owner(raw["owner"])
        require(type(raw["fail_on"]) is str and raw["fail_on"] in SEVERITIES)
        require(type(raw["on_inconclusive"]) is str and raw["on_inconclusive"] in {"fail", "warn"})
        targets = []
        for item in array(raw["targets"], 16):
            require(type(item) is dict and type(item.get("kind")) is str)
            kind = item["kind"]
            require(kind in {"repository", "workspace", "derived"})
            if kind == "workspace":
                keys(item, ("id", "kind", "manifest", "review_severity"))
                relative(item["manifest"])
            else:
                required = ("id", "kind", "root")
                if kind == "derived":
                    required += ("receipt", "review_severity")
                keys(
                    item,
                    required,
                    ("repository_id",)
                    + (("require_architecture",) if kind == "repository" else ()),
                )
                relative(item["root"], root=True)
                if kind == "derived":
                    relative(item["receipt"])
                if "repository_id" in item:
                    repo_value(item["repository_id"])
            token(item["id"])
            if "review_severity" in item:
                require(
                    type(item["review_severity"]) is str and item["review_severity"] in SEVERITIES
                )
            require(type(item.get("require_architecture", False)) is bool)
            targets.append(Target(**item))
        ids = {t.id for t in targets}
        require(1 <= len(ids) == len(targets))
        scopes = [(t.kind, t.root, t.manifest, t.receipt) for t in targets]
        require(len(set(scopes)) == len(scopes))
        rules = []
        for item in array(raw.get("rule_policies", []), 128):
            keys(item, ("target", "rule_id", "severity", "owner", "reason", "review_ref"))
            require(type(item["target"]) is str and item["target"] in ids)
            token(item["rule_id"])
            require(type(item["severity"]) is str and item["severity"] in SEVERITIES)
            owner(item["owner"])
            reason(item["reason"])
            review(item["review_ref"])
            rules.append(RulePolicy(**item))
        require(len({(r.target, r.rule_id) for r in rules}) == len(rules))
        waivers = []
        for item in array(raw.get("waivers", []), 256):
            keys(
                item,
                (
                    "id",
                    "target",
                    "finding_fingerprint",
                    "owner",
                    "reason",
                    "review_ref",
                    "expires_on",
                ),
            )
            token(item["id"])
            require(type(item["target"]) is str and item["target"] in ids)
            digest(item["finding_fingerprint"])
            owner(item["owner"])
            reason(item["reason"])
            review(item["review_ref"])
            waivers.append(Waiver(**(item | {"expires_on": iso_date(item["expires_on"])})))
        require(len({w.id for w in waivers}) == len(waivers))
        require(len({(w.target, w.finding_fingerprint) for w in waivers}) == len(waivers))
        return Policy(
            raw["policy_id"],
            raw["owner"],
            sha256(data).hexdigest(),
            raw["fail_on"],
            raw["on_inconclusive"],
            tuple(sorted(targets, key=lambda t: t.id)),
            tuple(sorted(rules, key=lambda r: (r.target, r.rule_id))),
            tuple(sorted(waivers, key=lambda w: w.id)),
        )
    except (ValueError, TypeError, KeyError, RecursionError, OverflowError) as exc:
        raise GovernanceError("invalid_governance_policy") from exc


def load_policy(path: Path) -> tuple[Policy, Path]:
    data = read_input(path, MAX_POLICY_BYTES)
    return parse_policy(data), safe_directory(path.absolute().parent)
