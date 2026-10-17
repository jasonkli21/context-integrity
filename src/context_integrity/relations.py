"""Body-free structural evidence contract; no architecture policy or provider IDs."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from context_integrity.evidence import (
    EvidenceCoverage,
    EvidenceProviderDescriptor,
    EvidenceRepositorySnapshot,
)
from context_integrity.models import RepositoryRef, _validate_integrity_path


def bounded_text(value: str) -> None:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 1024
        or value.startswith("/")
        or re.match(r"^[A-Za-z]:/", value)
        or any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF or c in "\\\ufffd" for c in value)
    ):
        raise ValueError("Invalid structural identifier.")


def safe_path(value: str) -> None:
    _validate_integrity_path(value)
    if len(value) > 4096 or any(
        ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF or c == "\ufffd" for c in value
    ):
        raise ValueError("Invalid structural path.")


@dataclass(frozen=True, order=True)
class EvidencePoint:
    byte: int
    row: int
    column: int

    def __post_init__(self):
        if any(
            type(v) is not int or not 0 <= v <= 2**63 - 1
            for v in (self.byte, self.row, self.column)
        ):
            raise ValueError("Invalid source point.")


@dataclass(frozen=True, order=True)
class EvidenceRange:
    start: EvidencePoint
    end: EvidencePoint

    def __post_init__(self):
        if (
            not isinstance(self.start, EvidencePoint)
            or not isinstance(self.end, EvidencePoint)
            or (
                self.end.byte < self.start.byte
                or (self.end.row, self.end.column) < (self.start.row, self.start.column)
                or (self.end.byte == self.start.byte)
                != (self.end.row == self.start.row and self.end.column == self.start.column)
            )
        ):
            raise ValueError("Invalid source range.")


@dataclass(frozen=True)
class EvidenceEntity:
    kind: str
    path: str
    qualified_name: str | None = None
    name: str | None = None
    symbol_kind: str | None = None
    language: str | None = None
    range: EvidenceRange | None = None

    def __post_init__(self):
        safe_path(self.path)
        if self.kind not in {"file", "symbol"}:
            raise ValueError("Invalid structural entity kind.")
        fields = (self.qualified_name, self.name, self.symbol_kind, self.language, self.range)
        if self.kind == "file" and any(v is not None for v in fields):
            raise ValueError("File entities cannot contain symbol metadata.")
        if self.kind == "symbol":
            for value in fields[:-1]:
                bounded_text(value)
            if self.language not in {"python", "rust"} or self.symbol_kind not in {
                "module",
                "class",
                "struct",
                "enum",
                "union",
                "trait",
                "function",
                "method",
                "type_alias",
                "constant",
                "static",
            }:
                raise ValueError("Unsupported structural symbol metadata.")
            if not isinstance(self.range, EvidenceRange):
                raise ValueError("Symbol range is required.")

    def identity(self) -> tuple:
        # Entity ranges distinguish repeated definitions; relation occurrence ranges
        # do not affect architectural edge grouping.
        return (
            self.kind,
            self.path,
            self.qualified_name or "",
            self.symbol_kind or "",
            self.language or "",
            (
                (
                    self.range.start.byte,
                    self.range.start.row,
                    self.range.start.column,
                    self.range.end.byte,
                    self.range.end.row,
                    self.range.end.column,
                )
                if self.range
                else ()
            ),
        )


@dataclass(frozen=True)
class EvidenceRelationTarget:
    entity: EvidenceEntity | None = None
    name: str | None = None

    def __post_init__(self):
        if (self.entity is None) == (self.name is None):
            raise ValueError("Exactly one structural target representation is required.")
        if self.entity is not None and not isinstance(self.entity, EvidenceEntity):
            raise ValueError("Invalid resolved target.")
        if self.name is not None:
            bounded_text(self.name)

    def identity(self) -> tuple[str, ...]:
        return ("resolved", *self.entity.identity()) if self.entity else ("unresolved", self.name)


@dataclass(frozen=True)
class EvidenceRelation:
    kind: str
    source: EvidenceEntity
    target: EvidenceRelationTarget
    resolution: str
    evidence_path: str
    range: EvidenceRange
    language: str
    derivation: str

    def __post_init__(self):
        safe_path(self.evidence_path)
        if not isinstance(self.source, EvidenceEntity) or not isinstance(
            self.target, EvidenceRelationTarget
        ):
            raise ValueError("Invalid structural edge.")
        if (
            self.kind not in {"imports", "references"}
            or self.resolution not in {"exact_same_file_qualified_name", "unresolved"}
            or (self.resolution == "unresolved") != (self.target.name is not None)
        ):
            raise ValueError("Invalid relation resolution.")
        if self.evidence_path != self.source.path or not isinstance(self.range, EvidenceRange):
            raise ValueError("Invalid relation location.")
        if self.language not in {"rust", "python"} or self.derivation not in {
            "rust_use_syntax",
            "python_import_syntax",
            "rust_call_syntax",
            "python_call_syntax",
        }:
            raise ValueError("Unsupported structural derivation.")
        expected = (
            self.language + ("_use_syntax" if self.language == "rust" else "_import_syntax")
            if self.kind == "imports"
            else self.language + "_call_syntax"
        )
        if self.derivation != expected:
            raise ValueError("Inconsistent structural derivation.")

    def identity(self) -> tuple:
        return self.kind, self.source.identity(), self.target.identity()

    def sort_key(self) -> tuple:
        return self.identity(), self.evidence_path, self.range, self.resolution, self.derivation


SYMBOL_STATUSES = frozenset(
    {
        "analyzed",
        "unsupported_language",
        "skipped_role",
        "too_large",
        "invalid_utf8",
        "read_failed",
        "parse_failed",
        "analysis_limit_exceeded",
    }
)
RELATION_STATUSES = frozenset(
    {"analyzed", "extraction_failed", "analysis_limit_exceeded", "not_analyzed"}
)


@dataclass(frozen=True)
class EvidenceRelationFileState:
    path: str
    symbol_status: str
    relation_status: str
    syntax_errors: int = 0
    unresolved: int = 0
    unsupported: int = 0

    def __post_init__(self):
        safe_path(self.path)
        if (
            self.symbol_status not in SYMBOL_STATUSES
            or self.relation_status not in RELATION_STATUSES
            or any(
                type(n) is not int or not 0 <= n <= 2**63 - 1
                for n in (self.syntax_errors, self.unresolved, self.unsupported)
            )
        ):
            raise ValueError("Invalid relation file state.")

    @property
    def incomplete(self) -> bool:
        return (
            self.symbol_status != "analyzed"
            or self.relation_status != "analyzed"
            or bool(self.syntax_errors or self.unresolved or self.unsupported)
        )


@dataclass(frozen=True)
class EvidenceRelationCoverage:
    summary: EvidenceCoverage
    files: tuple[EvidenceRelationFileState, ...]
    warning_categories: tuple[str, ...] = ()

    def __post_init__(self):
        if (
            not isinstance(self.summary, EvidenceCoverage)
            or not isinstance(self.files, tuple)
            or any(not isinstance(f, EvidenceRelationFileState) for f in self.files)
        ):
            raise ValueError("Invalid relation coverage.")
        paths = [f.path for f in self.files]
        if (
            paths != sorted(set(paths))
            or not isinstance(self.warning_categories, tuple)
            or (self.warning_categories != tuple(sorted(set(self.warning_categories))))
            or any(
                c
                not in {
                    "diagnostics",
                    "scan_warnings",
                    "snapshot_unknown",
                    "content_identity_unavailable",
                }
                for c in self.warning_categories
            )
        ):
            raise ValueError("Invalid coverage categories/order.")
        if (
            any(f.incomplete for f in self.files) or self.warning_categories
        ) and not self.summary.incomplete:
            raise ValueError("Incomplete coverage must remain explicit.")


@dataclass(frozen=True)
class EvidenceRelationRequest:
    repository_root: Path
    repository: RepositoryRef

    def __post_init__(self):
        if (
            not isinstance(self.repository_root, Path)
            or not self.repository_root.is_absolute()
            or not isinstance(self.repository, RepositoryRef)
        ):
            raise ValueError("Invalid relation request.")


@dataclass(frozen=True)
class EvidenceRelationState:
    descriptor: EvidenceProviderDescriptor
    snapshot: EvidenceRepositorySnapshot
    coverage: EvidenceRelationCoverage
    observed_content: tuple[tuple[str, str | None], ...] = ()

    def __post_init__(self):
        if (
            not isinstance(self.descriptor, EvidenceProviderDescriptor)
            or "relations" not in self.descriptor.capabilities
            or not isinstance(self.snapshot, EvidenceRepositorySnapshot)
            or self.snapshot.command != "graph"
            or not isinstance(self.coverage, EvidenceRelationCoverage)
        ):
            raise ValueError("Invalid relation provider state.")
        if not isinstance(self.observed_content, tuple):
            raise ValueError("Invalid observed content revisions.")
        paths = []
        for item in self.observed_content:
            if not isinstance(item, tuple) or len(item) != 2:
                raise ValueError("Invalid observed content revision.")
            path, digest = item
            safe_path(path)
            paths.append(path)
            if digest is not None and (
                not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest)
            ):
                raise ValueError("Invalid content hash.")
        if paths != sorted(set(paths)) or set(paths) - {f.path for f in self.coverage.files}:
            raise ValueError("Invalid observed content revision paths.")


@dataclass(frozen=True)
class EvidenceRelationBatch:
    state: EvidenceRelationState
    relations: tuple[EvidenceRelation, ...]

    def __post_init__(self):
        if (
            not isinstance(self.state, EvidenceRelationState)
            or not isinstance(self.relations, tuple)
            or any(not isinstance(r, EvidenceRelation) for r in self.relations)
        ):
            raise ValueError("Invalid relation batch.")
        keys = [r.sort_key() for r in self.relations]
        if keys != sorted(set(keys)):
            raise ValueError("Relations must be unique and sorted.")
        unresolved = {}
        for relation in self.relations:
            if relation.target.name is not None:
                unresolved[relation.source.path] = unresolved.get(relation.source.path, 0) + 1
        if any(unresolved.get(f.path, 0) > f.unresolved for f in self.state.coverage.files):
            raise ValueError("Unresolved relations must remain visible in file coverage.")
        paths = {f.path for f in self.state.coverage.files}
        if any(r.source.path not in paths for r in self.relations):
            raise ValueError("Relations require file coverage.")


class RelationEvidenceProvider(Protocol):
    def relations(self, request: EvidenceRelationRequest) -> EvidenceRelationBatch:
        """Return normalized snapshot-scoped structural facts, never policy judgments."""
        ...
