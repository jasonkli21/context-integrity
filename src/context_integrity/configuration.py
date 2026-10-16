"""Strict versioned repository configuration parsing and descriptor-safe loading."""

import os
import re
import tomllib
from hashlib import sha256

from context_integrity.acquisition import normalize_path, read_source_bytes
from context_integrity.lifecycle import validate_supersession
from context_integrity.models import (
    AuthorityClass,
    AuthorityPolicy,
    AuthorityTier,
    ClaimId,
    ClaimSpec,
    DriftDependencySpec,
    InstructionPolicySpec,
    LifecycleState,
    RepositoryConfig,
    SourceMetadata,
    SupersessionSpec,
    validate_unique_claim_ids,
)
from context_integrity.repository import RepositoryContext

CONFIG_PATH = ".context-integrity.toml"

# Document metadata cannot synthesize executable evidence or bypass lifecycle filtering.
SOURCE_METADATA_AUTHORITY_CLASSES = frozenset(
    {
        AuthorityClass.VERIFICATION_EVIDENCE,
        AuthorityClass.DECISION,
        AuthorityClass.ARCHITECTURE_PRODUCT,
        AuthorityClass.OPERATING_INSTRUCTION,
        AuthorityClass.PLAN,
        AuthorityClass.GENERATED_DERIVATIVE,
        AuthorityClass.UNKNOWN,
    }
)


class ConfigurationError(Exception):
    """Repository interpretation cannot proceed safely."""


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


def _path(value: object) -> str:
    raw = _text(value)
    # POSIX repository paths only, reject Windows drive/UNC ambiguity too.
    if "\\" in raw or ":" in raw or raw.endswith("/"):
        raise ValueError("Unsafe configuration path.")
    return normalize_path(raw)


def parse_config(data: bytes) -> RepositoryConfig:
    """Parse v1 authority, v2 lifecycle, v3 claims, or v4 drift policy; unknown keys fail closed."""
    try:
        raw_root = tomllib.loads(data.decode("utf-8"))
        version = raw_root.get("schema_version")
        if type(version) is not int or version not in {1, 2, 3, 4}:
            raise ValueError("Unsupported configuration schema version.")
        root = _table(
            raw_root,
            {"schema_version", "authority", "source_metadata"}
            | ({"supersession"} if version >= 2 else set())
            | ({"claims"} if version >= 3 else set())
            | ({"instruction_policy", "drift_dependencies"} if version >= 4 else set()),
        )
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
                    f"config-v{version}",
                    digest,
                )
            )
        if len({p.id for p in policies}) != len(policies):
            raise ValueError("Duplicate policy ID.")
        metadata = []
        for raw in _array(root.get("source_metadata", [])):
            entry = _table(
                raw,
                {"path", "authority_class", "authority_eligible", "reason"}
                | ({"lifecycle"} if version >= 2 else set()),
            )
            path = _path(entry.get("path"))
            lifecycle = LifecycleState(_text(entry["lifecycle"])) if "lifecycle" in entry else None
            if lifecycle == LifecycleState.UNKNOWN:
                raise ValueError("Unknown lifecycle is fallback only.")
            if lifecycle is not None and path == CONFIG_PATH:
                raise ValueError("Configuration cannot manage its own lifecycle.")
            eligible = entry.get("authority_eligible")
            if "authority_eligible" in entry and type(eligible) is not bool:
                raise ValueError("authority_eligible must be boolean.")
            override = (
                AuthorityClass(_text(entry["authority_class"]))
                if "authority_class" in entry
                else None
            )
            if override is not None and override not in SOURCE_METADATA_AUTHORITY_CLASSES:
                raise ValueError("Authority class is reserved from Phase 1 source metadata.")
            if override is None and eligible is None and lifecycle is None:
                raise ValueError("Source metadata must specify an override or eligibility.")
            metadata.append(
                SourceMetadata(
                    path,
                    _text(entry.get("reason")),
                    override,
                    eligible,
                    lifecycle,
                )
            )
        if len({m.path for m in metadata}) != len(metadata):
            raise ValueError("Duplicate source metadata path.")
        supersession = []
        for raw in _array(root.get("supersession", [])):
            entry = _table(raw, {"source", "superseded_by", "reason"})
            source, target = _path(entry.get("source")), _path(entry.get("superseded_by"))
            if CONFIG_PATH in {source, target}:
                raise ValueError("Configuration cannot be a supersession endpoint.")
            supersession.append(SupersessionSpec(source, target, _text(entry.get("reason"))))
        validate_supersession(tuple(supersession), tuple(metadata))
        claims = []
        for raw in _array(root.get("claims", [])):
            entry = _table(
                raw, {"id", "claim_type", "subject", "predicate", "value", "scope", "depends_on"}
            )
            claim_id, claim_type = _text(entry.get("id")), _text(entry.get("claim_type"))
            dependencies = tuple(_path(p) for p in _array(entry.get("depends_on", [])))
            if CONFIG_PATH in dependencies or len(set(dependencies)) != len(dependencies):
                raise ValueError("Self dependency or duplicate claim dependency.")
            claims.append(
                ClaimSpec(
                    ClaimId(claim_id),
                    claim_type,
                    _text(entry.get("subject")),
                    _text(entry.get("predicate")),
                    _text(entry.get("value")),
                    _text(entry["scope"]) if "scope" in entry else None,
                    tuple(sorted(dependencies)),
                )
            )
        validate_unique_claim_ids(tuple(claims))
        instruction_policy = None
        if "instruction_policy" in root:
            entry = _table(root["instruction_policy"], {"canonical", "compatibility"})
            canonical = _path(entry.get("canonical"))
            compatibility = tuple(_path(p) for p in _array(entry.get("compatibility")))
            paths = (canonical, *compatibility)
            if CONFIG_PATH in paths or len(set(paths)) != len(paths):
                raise ValueError("Instruction path collision or self reference.")
            instruction_policy = InstructionPolicySpec(canonical, tuple(sorted(compatibility)))
        dependencies = []
        for raw in _array(root.get("drift_dependencies", [])):
            entry = _table(raw, {"id", "dependent", "upstream", "reason"})
            identifier = _text(entry.get("id"))
            if not re.fullmatch(r"[a-z][a-z0-9_-]*", identifier):
                raise ValueError("Invalid drift dependency ID.")
            dependent = _path(entry.get("dependent"))
            upstream = tuple(_path(p) for p in _array(entry.get("upstream")))
            if (
                not upstream
                or len(set(upstream)) != len(upstream)
                or dependent in upstream
                or dependent == CONFIG_PATH
            ):
                raise ValueError("Invalid drift dependency paths.")
            dependencies.append(
                DriftDependencySpec(
                    identifier, dependent, tuple(sorted(upstream)), _text(entry.get("reason"))
                )
            )
        if len({d.id for d in dependencies}) != len(dependencies):
            raise ValueError("Duplicate drift dependency ID.")
        return RepositoryConfig(
            tuple(policies),
            tuple(metadata),
            digest,
            version,
            tuple(supersession),
            tuple(claims),
            instruction_policy,
            tuple(sorted(dependencies, key=lambda d: d.id)),
        )
    except (ValueError, TypeError, KeyError, RecursionError) as exc:
        # Parser exceptions can contain arbitrary repository text; keep errors path/body-free.
        raise ConfigurationError("Invalid .context-integrity.toml configuration.") from exc


def load_config(context: RepositoryContext) -> RepositoryConfig:
    try:
        os.lstat(context.root / CONFIG_PATH)
    except FileNotFoundError:
        return RepositoryConfig()
    except OSError as exc:
        raise ConfigurationError("Repository configuration could not be inspected safely.") from exc
    data = read_source_bytes(context, CONFIG_PATH)
    if data is None:
        raise ConfigurationError("Repository configuration could not be read safely.")
    return parse_config(data)


def verify_config_revision(
    context: RepositoryContext, config: RepositoryConfig, observed_hash: str | None
) -> None:
    current = load_config(context)
    if current.content_sha256 != config.content_sha256 or observed_hash != config.content_sha256:
        raise ConfigurationError("Repository configuration changed during inventory observation.")
