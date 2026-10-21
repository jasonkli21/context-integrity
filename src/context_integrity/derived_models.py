"""Strict standalone derived receipt v1. Declarations are not attestations."""

import json
import re
from dataclasses import dataclass, fields

from context_integrity.models import AuthorityClass, LifecycleState, make_source_id

MAX_RECEIPT_BYTES = 1024 * 1024
MAX_DEPENDENCIES = 256
MAX_PARENTS = 16
MAX_RECEIPTS = 128
MAX_DEPTH = 16
MAX_GRAPH_BYTES = 64 * 1024 * 1024


class ReceiptError(ValueError):
    """Invalid or unobservable receipt/capture input; diagnostics contain no input prose."""


def require(condition: bool) -> None:
    if not condition:
        raise ReceiptError("Invalid derived receipt or capture input.")


def token(value: str) -> None:
    require(
        isinstance(value, str)
        and re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.+-]{0,99}", value) is not None
    )


def path_value(value: str) -> None:
    require(
        isinstance(value, str)
        and 0 < len(value) <= 512
        and not value.startswith("/")
        and not any(c in value for c in "\\:*?[]")
        and all(p not in {"", ".", ".."} and p.lower() != ".git" for p in value.split("/"))
        and all(32 <= ord(c) < 127 for c in value)
    )


def digest(value: str | None, *, nullable: bool = False) -> None:
    require(
        (nullable and value is None)
        or (isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None)
    )


def head_value(value: str | None) -> None:
    require(
        value is None
        or (
            isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", value) is not None
        )
    )


def repo_value(value: str) -> None:
    require(isinstance(value, str) and re.fullmatch(r"repo_[0-9a-f]{32}", value) is not None)


@dataclass(frozen=True)
class Derivation:
    kind: str
    producer: str
    version: str | None = None

    def __post_init__(self):
        require(self.kind in ("manual", "model", "tool"))
        token(self.producer)
        if self.version is not None:
            token(self.version)


@dataclass(frozen=True)
class Artifact:
    id: str
    kind: str
    path: str
    content_sha256: str
    derivation: Derivation

    def __post_init__(self):
        token(self.id)
        require(self.kind in ("summary", "handoff", "compiled_context"))
        path_value(self.path)
        digest(self.content_sha256)
        require(type(self.derivation) is Derivation)


@dataclass(frozen=True)
class RepositorySnapshot:
    id: str
    git_head: str | None
    git_dirty: bool | None

    def __post_init__(self):
        repo_value(self.id)
        head_value(self.git_head)
        require(self.git_dirty is None or type(self.git_dirty) is bool)


@dataclass(frozen=True)
class SourcePin:
    path: str
    source_id: str
    content_sha256: str
    observed_lifecycle: str | None
    observed_authority: str | None
    metadata_sha256: str | None
    observation_basis: str
    provider_id: str | None = None
    provider_version: str | None = None
    derivation: str | None = None

    def __post_init__(self):
        path_value(self.path)
        require(
            isinstance(self.source_id, str)
            and re.fullmatch(r"src_[0-9a-f]{32}", self.source_id) is not None
        )
        digest(self.content_sha256)
        require(
            self.observed_lifecycle is None
            or self.observed_lifecycle in tuple(s.value for s in LifecycleState)
        )
        require(
            self.observed_authority is None
            or self.observed_authority in tuple(s.value for s in AuthorityClass)
        )
        digest(self.metadata_sha256, nullable=True)
        require(self.observation_basis in ("inventory", "explicit_file", "provider"))
        if self.observation_basis == "provider":
            token(self.provider_id)
            token(self.provider_version)
            require(
                isinstance(self.derivation, str)
                and re.fullmatch(r"[A-Za-z0-9_.:+-]{1,200}", self.derivation) is not None
            )
            require(self.metadata_sha256 is None)
            require(self.observed_lifecycle is not None and self.observed_authority is not None)
        else:
            require(self.provider_id is self.provider_version is self.derivation is None)
            if self.observation_basis == "inventory":
                require(
                    self.metadata_sha256 is not None
                    and self.observed_lifecycle is not None
                    and self.observed_authority is not None
                )
            else:
                require(
                    self.metadata_sha256
                    is self.observed_lifecycle
                    is self.observed_authority
                    is None
                )


@dataclass(frozen=True)
class UpstreamPin:
    path: str
    receipt_sha256: str
    artifact_id: str
    artifact_path: str
    artifact_sha256: str

    def __post_init__(self):
        path_value(self.path)
        path_value(self.artifact_path)
        require(self.path != self.artifact_path)
        token(self.artifact_id)
        digest(self.receipt_sha256)
        digest(self.artifact_sha256)


@dataclass(frozen=True)
class ProviderPin:
    id: str
    version: str
    derivation: str
    contract_version: int
    provider_schema_version: int
    git_head: str | None
    git_dirty: bool | None
    coverage_sha256: str
    context_sha256: str
    incomplete: bool

    def __post_init__(self):
        token(self.id)
        token(self.version)
        token(self.derivation)
        require(type(self.contract_version) is int and self.contract_version == 1)
        require(type(self.provider_schema_version) is int and self.provider_schema_version == 1)
        head_value(self.git_head)
        require(self.git_dirty is None or type(self.git_dirty) is bool)
        digest(self.coverage_sha256)
        digest(self.context_sha256)
        require(type(self.incomplete) is bool)


@dataclass(frozen=True)
class CompilationPin:
    contract_id: str
    contract_sha256: str
    policies_sha256: str
    selection_sha256: str
    task_sha256: str | None
    budget_bytes: int | None
    status: str
    integrity_status: str
    warnings: tuple[str, ...]
    compiler_version: str

    def __post_init__(self):
        token(self.contract_id)
        for value in (self.contract_sha256, self.policies_sha256, self.selection_sha256):
            digest(value)
        digest(self.task_sha256, nullable=True)
        require(
            self.budget_bytes is None
            or (type(self.budget_bytes) is int and 0 < self.budget_bytes <= 2**63 - 1)
        )
        require(self.status in ("complete", "incomplete"))
        require(self.integrity_status in ("not_evaluated", "evaluated"))
        require(
            type(self.warnings) is tuple
            and len(self.warnings) <= 256
            and all(isinstance(w, str) for w in self.warnings)
            and len(set(self.warnings)) == len(self.warnings)
        )
        for value in self.warnings:
            token(value)
        token(self.compiler_version)


@dataclass(frozen=True)
class DerivedReceipt:
    artifact: Artifact
    repository: RepositorySnapshot
    provenance_scope: str
    config_sha256: str | None
    dependencies: tuple[SourcePin, ...]
    upstream_receipts: tuple[UpstreamPin, ...] = ()
    provider_context: tuple[ProviderPin, ...] = ()
    compilation: CompilationPin | None = None
    known_incomplete: bool = False
    derived_receipt_schema_version: int = 1

    def __post_init__(self):
        require(
            type(self.derived_receipt_schema_version) is int
            and self.derived_receipt_schema_version == 1
        )
        require(type(self.artifact) is Artifact and type(self.repository) is RepositorySnapshot)
        require(self.provenance_scope in ("declared", "compiler_selection"))
        digest(self.config_sha256, nullable=True)
        require(type(self.known_incomplete) is bool)
        for values, kind, limit in (
            (self.dependencies, SourcePin, MAX_DEPENDENCIES),
            (self.upstream_receipts, UpstreamPin, MAX_PARENTS),
            (self.provider_context, ProviderPin, 4),
        ):
            require(
                type(values) is tuple
                and len(values) <= limit
                and all(type(v) is kind for v in values)
            )
        paths = [s.path for s in self.dependencies]
        require(len(set(paths)) == len(paths) and self.artifact.path not in paths)
        require(
            all(
                s.source_id == make_source_id(self.repository.id, s.path) for s in self.dependencies
            )
        )
        parents = [s.path for s in self.upstream_receipts]
        require(
            len(set(parents)) == len(parents)
            and not set(parents) & set(paths)
            and self.artifact.path not in parents
        )
        require(len({p.artifact_id for p in self.upstream_receipts}) == len(parents))
        require(len({p.artifact_path for p in self.upstream_receipts}) == len(parents))
        require(
            all(
                p.artifact_id != self.artifact.id and p.artifact_path != self.artifact.path
                for p in self.upstream_receipts
            )
        )
        require(len({p.id for p in self.provider_context}) == len(self.provider_context))
        require(
            all(
                (s.provider_id, s.provider_version)
                in {(p.id, p.version) for p in self.provider_context}
                for s in self.dependencies
                if s.observation_basis == "provider"
            )
        )
        require(
            (self.provenance_scope == "compiler_selection")
            == (type(self.compilation) is CompilationPin)
        )
        if self.provenance_scope == "declared":
            require(self.compilation is None and not self.provider_context)
        else:
            require(
                self.artifact.kind == "compiled_context" and self.artifact.derivation.kind == "tool"
            )
            require(self.compilation.status != "incomplete" or self.known_incomplete)
            require(not any(p.incomplete for p in self.provider_context) or self.known_incomplete)
        for parent in self.upstream_receipts:
            for source in self.dependencies:
                if source.path == parent.artifact_path:
                    require(source.content_sha256 == parent.artifact_sha256)


def record(value, names):
    """Whitelisted projection: new dataclass fields never implicitly enter public output."""
    return {name: getattr(value, name) for name in names.split()}


def receipt_dict(receipt: DerivedReceipt) -> dict:
    artifact = record(receipt.artifact, "id kind path content_sha256")
    artifact["derivation"] = record(receipt.artifact.derivation, "kind producer version")
    return {
        "derived_receipt_schema_version": receipt.derived_receipt_schema_version,
        "artifact": artifact,
        "repository": record(receipt.repository, "id git_head git_dirty"),
        "provenance_scope": receipt.provenance_scope,
        "config_sha256": receipt.config_sha256,
        "dependencies": [
            record(
                s,
                "path source_id content_sha256 observed_lifecycle observed_authority "
                "metadata_sha256 observation_basis provider_id provider_version derivation",
            )
            for s in sorted(receipt.dependencies, key=lambda s: s.path)
        ],
        "upstream_receipts": [
            record(p, "path receipt_sha256 artifact_id artifact_path artifact_sha256")
            for p in sorted(receipt.upstream_receipts, key=lambda p: p.path)
        ],
        "provider_context": [
            record(
                p,
                "id version derivation contract_version provider_schema_version git_head "
                "git_dirty coverage_sha256 context_sha256 incomplete",
            )
            for p in sorted(receipt.provider_context, key=lambda p: p.id)
        ],
        "compilation": None
        if receipt.compilation is None
        else record(
            receipt.compilation,
            "contract_id contract_sha256 policies_sha256 selection_sha256 task_sha256 "
            "budget_bytes status integrity_status warnings compiler_version",
        )
        | {"warnings": sorted(receipt.compilation.warnings)},
        "known_incomplete": receipt.known_incomplete,
    }


def canonical_json(value: dict) -> str:
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False) + "\n"


def render_receipt(receipt: DerivedReceipt) -> str:
    result = canonical_json(receipt_dict(receipt))
    require(len(result.encode()) <= MAX_RECEIPT_BYTES)
    return result


def render_receipt_text(receipt: DerivedReceipt) -> str:
    artifact = receipt.artifact
    return (
        f"{artifact.id}: {artifact.kind} ({artifact.path})\n"
        f"Provenance: {receipt.provenance_scope}; derivation: {artifact.derivation.kind}; "
        f"producer: {artifact.derivation.producer}\n"
        f"Known incomplete: {str(receipt.known_incomplete).lower()}\n"
        "Declared observations only; no semantic correctness or exhaustive provenance claim.\n"
        + "".join(
            f"  source: {s.path} [{s.observation_basis}]\n"
            for s in sorted(receipt.dependencies, key=lambda s: s.path)
        )
        + "".join(
            f"  upstream: {p.path} ({p.artifact_id})\n"
            for p in sorted(receipt.upstream_receipts, key=lambda p: p.path)
        )
        + "".join(
            f"  provider: {p.id} {p.version}; requires revalidation\n"
            for p in sorted(receipt.provider_context, key=lambda p: p.id)
        )
    )


def _construct(cls, value: dict, **children):
    require(type(value) is dict and set(value) == {f.name for f in fields(cls)})
    return cls(**(value | children))


def parse_receipt(data: bytes) -> DerivedReceipt:
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result)
            result[key] = value
        return result

    try:
        require(type(data) is bytes and len(data) <= MAX_RECEIPT_BYTES)
        raw = json.loads(data, object_pairs_hook=pairs, parse_constant=lambda _: require(False))
        require(type(raw) is dict)
        artifact = raw["artifact"]
        compilation = raw["compilation"]
        if compilation is not None:
            require(type(compilation["warnings"]) is list)
            compilation = _construct(
                CompilationPin, compilation, warnings=tuple(compilation["warnings"])
            )
        children = {}
        for name, cls, limit in (
            ("dependencies", SourcePin, MAX_DEPENDENCIES),
            ("upstream_receipts", UpstreamPin, MAX_PARENTS),
            ("provider_context", ProviderPin, 4),
        ):
            require(type(raw[name]) is list and len(raw[name]) <= limit)
            children[name] = tuple(_construct(cls, item) for item in raw[name])
        return _construct(
            DerivedReceipt,
            raw,
            artifact=_construct(
                Artifact, artifact, derivation=_construct(Derivation, artifact["derivation"])
            ),
            repository=_construct(RepositorySnapshot, raw["repository"]),
            compilation=compilation,
            **children,
        )
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError, OverflowError) as exc:
        raise ReceiptError("Invalid derived receipt.") from exc
