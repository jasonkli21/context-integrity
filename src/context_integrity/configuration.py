"""Strict local authority configuration parsing and descriptor-safe loading."""

import os
import tomllib
from hashlib import sha256

from context_integrity.acquisition import normalize_path, read_source_bytes
from context_integrity.models import (
    AuthorityClass,
    AuthorityPolicy,
    AuthorityTier,
    RepositoryAuthorityConfig,
    SourceAuthorityMetadata,
)
from context_integrity.repository import RepositoryContext

CONFIG_PATH = ".context-integrity.toml"


class ConfigurationError(Exception):
    """Authority interpretation cannot proceed safely."""


def _table(value: object, allowed: set[str]) -> dict:
    if not isinstance(value, dict) or value.keys() - allowed:
        raise ValueError("Invalid configuration table or unknown key.")
    return value


def _array(value: object) -> list:
    if not isinstance(value, list):
        raise ValueError("Expected a configuration array.")
    return value


def _text(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Expected a nonblank string.")
    return value


def parse_config(data: bytes) -> RepositoryAuthorityConfig:
    """Parse only the Phase 1 schema; unknown keys fail closed."""
    try:
        root = _table(
            tomllib.loads(data.decode("utf-8")), {"schema_version", "authority", "source_metadata"}
        )
        if type(root.get("schema_version")) is not int or root["schema_version"] != 1:
            raise ValueError("Unsupported configuration schema version.")
        digest = sha256(data).hexdigest()
        authority = _table(root.get("authority", {}), {"policies"})
        policies = []
        for raw in _array(authority.get("policies", [])):
            entry = _table(raw, {"id", "description", "tiers"})
            tiers = tuple(
                AuthorityTier(tuple(AuthorityClass(_text(c)) for c in _array(tier)))
                for tier in _array(entry.get("tiers"))
            )
            policies.append(
                AuthorityPolicy(
                    _text(entry.get("id")),
                    _text(entry.get("description")),
                    tiers,
                    "repository_config",
                    "config-v1",
                    digest,
                )
            )
        if len({p.id for p in policies}) != len(policies):
            raise ValueError("Duplicate policy ID.")
        metadata = []
        for raw in _array(root.get("source_metadata", [])):
            entry = _table(raw, {"path", "authority_class", "authority_eligible", "reason"})
            raw_path = _text(entry.get("path"))
            # POSIX repository paths only, also reject Windows drive/UNC ambiguity.
            if "\\" in raw_path or ":" in raw_path or raw_path.endswith("/"):
                raise ValueError("Unsafe metadata path.")
            path = normalize_path(raw_path)
            eligible = entry.get("authority_eligible")
            if "authority_eligible" in entry and type(eligible) is not bool:
                raise ValueError("authority_eligible must be boolean.")
            override = (
                AuthorityClass(_text(entry["authority_class"]))
                if "authority_class" in entry
                else None
            )
            if override is None and eligible is None:
                raise ValueError(
                    "Source metadata must specify an authority override or eligibility."
                )
            metadata.append(
                SourceAuthorityMetadata(
                    path,
                    _text(entry.get("reason")),
                    override,
                    eligible,
                )
            )
        if len({m.path for m in metadata}) != len(metadata):
            raise ValueError("Duplicate source metadata path.")
        return RepositoryAuthorityConfig(tuple(policies), tuple(metadata), digest)
    except (ValueError, TypeError, KeyError, RecursionError) as exc:
        # Parser exceptions can contain arbitrary repository text; keep errors path/body-free.
        raise ConfigurationError("Invalid .context-integrity.toml configuration.") from exc


def load_config(context: RepositoryContext) -> RepositoryAuthorityConfig:
    try:
        os.lstat(context.root / CONFIG_PATH)
    except FileNotFoundError:
        return RepositoryAuthorityConfig()
    except OSError as exc:
        raise ConfigurationError("Authority configuration could not be inspected safely.") from exc
    data = read_source_bytes(context, CONFIG_PATH)
    if data is None:
        raise ConfigurationError("Authority configuration could not be read safely.")
    return parse_config(data)


def verify_config_revision(
    context: RepositoryContext, config: RepositoryAuthorityConfig, observed_hash: str | None
) -> None:
    current = load_config(context)
    if current.content_sha256 != config.content_sha256 or observed_hash != config.content_sha256:
        raise ConfigurationError("Authority configuration changed during inventory observation.")
