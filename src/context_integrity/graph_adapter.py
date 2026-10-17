"""Decode the public Context Engine graph schema v1 into stable structural facts."""

import json
from collections import Counter
from pathlib import Path

from context_integrity.evidence import (
    EvidenceCoverage,
    EvidenceProviderError,
    EvidenceRepositorySnapshot,
)
from context_integrity.relations import (
    RELATION_STATUSES,
    EvidenceEntity,
    EvidencePoint,
    EvidenceRange,
    EvidenceRelation,
    EvidenceRelationBatch,
    EvidenceRelationCoverage,
    EvidenceRelationFileState,
    EvidenceRelationState,
    EvidenceRelationTarget,
    safe_path,
)


def normalize_graph(payload, request, descriptor):
    # Shared strict JSON/scalar decoding with the context adapter. Imported locally to
    # keep transport ownership in context_engine without a module import cycle.
    from context_integrity.context_engine import _boolean, _integer, _revision, _unique_object

    try:
        return _decode(payload, request, descriptor, _unique_object, _integer, _boolean, _revision)
    except EvidenceProviderError:
        raise
    except (KeyError, TypeError, ValueError, UnicodeError, OverflowError, RecursionError, OSError):
        raise EvidenceProviderError("invalid_graph_response") from None


def _range(raw):
    return EvidenceRange(
        *(
            EvidencePoint(**{k: raw[end][k] for k in ("byte", "row", "column")})
            for end in ("start", "end")
        )
    )


def _array(value):
    if not isinstance(value, list):
        raise ValueError
    return value


def _decode(payload, request, descriptor, unique_object, integer, boolean, revision):
    envelope = json.loads(
        payload.decode("utf-8"),
        object_pairs_hook=unique_object,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
    )
    if (
        type(envelope["schema_version"]) is not int
        or envelope["schema_version"] != 1
        or envelope["command"] != "graph"
    ):
        raise EvidenceProviderError("unsupported_contract")
    data = envelope["data"]
    if (
        not isinstance(data["root"], str)
        or not Path(data["root"]).is_absolute()
        or Path(data["root"]).resolve() != request.repository_root.resolve()
    ):
        raise EvidenceProviderError("repository_mismatch")
    git = data["git"]
    head = revision(git["head_commit"]) if git is not None else None
    dirty = git["is_dirty"] if git is not None else None
    if dirty is not None:
        boolean(dirty)
    if (
        head is not None
        and request.repository.git_head is not None
        and head != request.repository.git_head
    ) or (
        dirty is not None
        and request.repository.git_dirty is not None
        and dirty != request.repository.git_dirty
    ):
        raise EvidenceProviderError("snapshot_mismatch")
    entities = {}
    repository_entities = 0
    for raw in _array(data["entities"]):
        identifier = integer(raw["id"])
        if identifier in entities:
            raise EvidenceProviderError("duplicate_entity_id")
        kind = raw["kind"]
        if kind == "repository":
            if raw["path"] is not None or raw["symbol"] is not None:
                raise ValueError
            entity = None
            repository_entities += 1
        elif kind == "file":
            if raw["symbol"] is not None:
                raise ValueError
            entity = EvidenceEntity(kind, raw["path"])
        elif kind == "symbol":
            symbol = raw["symbol"]
            if symbol["path"] != raw["path"]:
                raise ValueError
            span, name_span = _range(symbol["range"]), _range(symbol["name_range"])
            if name_span.start.byte < span.start.byte or name_span.end.byte > span.end.byte:
                raise ValueError
            entity = EvidenceEntity(
                kind,
                raw["path"],
                symbol["qualified_name"],
                symbol["name"],
                symbol["kind"],
                symbol["language"],
                span,
            )
        else:
            raise ValueError
        entities[identifier] = entity
    if repository_entities != 1:
        raise ValueError
    file_entities = [e.path for e in entities.values() if e and e.kind == "file"]
    if len(file_entities) != len(set(file_entities)):
        raise ValueError
    file_paths = set(file_entities)
    if any(e.path not in file_paths for e in entities.values() if e):
        raise ValueError
    relations, relation_ids = [], set()
    raw_relations = _array(data["relations"])
    counts = Counter()
    per_file = {}
    for raw in raw_relations:
        identifier = integer(raw["id"])
        if identifier in relation_ids:
            raise EvidenceProviderError("duplicate_relation_id")
        relation_ids.add(identifier)
        source_id = integer(raw["source_id"])
        if source_id not in entities:
            raise EvidenceProviderError("dangling_entity")
        source = entities[source_id]
        target = raw["target"]
        if target["state"] == "resolved":
            target_id = integer(target["entity_id"])
            if target_id not in entities or entities[target_id] is None:
                raise EvidenceProviderError("dangling_entity")
            normalized_target = EvidenceRelationTarget(entity=entities[target_id])
            counts["resolved"] += 1
        elif target["state"] == "unresolved":
            normalized_target = EvidenceRelationTarget(name=target["name"])
            counts["unresolved"] += 1
        else:
            raise ValueError
        evidence = raw["evidence"]
        safe_path(evidence["path"])
        span = _range(evidence["range"]) if evidence["range"] is not None else None
        if raw["kind"] == "contains":
            if (
                raw["resolution"] != "direct_structural"
                or normalized_target.entity is None
                or evidence["derivation"]
                not in {"repository_contains_file", "lexical_range_containment"}
            ):
                raise ValueError
            continue
        relation = EvidenceRelation(
            raw["kind"],
            source,
            normalized_target,
            raw["resolution"],
            evidence["path"],
            span,
            evidence["language"],
            evidence["derivation"],
        )
        relations.append(relation)
        bucket = per_file.setdefault(source.path, Counter())
        bucket[relation.kind] += 1
        bucket["unresolved"] += relation.resolution == "unresolved"
    symbol_counts = Counter(e.path for e in entities.values() if e and e.kind == "symbol")
    files = {}
    for raw in _array(data["files"]):
        safe_path(raw["path"])
        if raw["path"] in files:
            raise ValueError
        if integer(raw["symbol_count"]) != symbol_counts[raw["path"]]:
            raise ValueError
        files[raw["path"]] = EvidenceRelationFileState(
            raw["path"], raw["symbol_status"], "not_analyzed", integer(raw["syntax_error_count"])
        )
    if set(files) != file_paths:
        raise ValueError
    statuses = Counter()
    unsupported = 0
    seen = set()
    for raw in _array(data["relation_files"]):
        path = raw["path"]
        safe_path(path)
        if (
            path not in files
            or path in seen
            or raw["status"] not in RELATION_STATUSES - {"not_analyzed"}
        ):
            raise ValueError
        seen.add(path)
        for key, relation_kind in (
            ("import_count", "imports"),
            ("reference_count", "references"),
            ("unresolved_count", "unresolved"),
        ):
            if integer(raw[key]) != per_file.get(path, {}).get(relation_kind, 0):
                raise ValueError
        count = integer(raw["unsupported_candidate_count"])
        unsupported += count
        statuses[raw["status"]] += 1
        previous = files[path]
        files[path] = EvidenceRelationFileState(
            path,
            previous.symbol_status,
            raw["status"],
            previous.syntax_errors,
            raw["unresolved_count"],
            count,
        )
    if set(per_file) - seen:
        raise ValueError
    summary = data["summary"]
    expected = dict(
        entities=len(entities),
        relations=len(raw_relations),
        resolved=counts["resolved"],
        unresolved=counts["unresolved"],
        symbol_analysis_unavailable=sum(f.symbol_status != "analyzed" for f in files.values()),
        unsupported_candidates=unsupported,
    )
    if any(integer(summary[k]) != value for k, value in expected.items()):
        raise ValueError
    if not isinstance(summary["relation_statuses"], dict) or {
        k: integer(v) for k, v in summary["relation_statuses"].items()
    } != dict(statuses):
        raise ValueError
    categories = []
    signals = expected | {
        "diagnostics_count": len(_array(data["diagnostics"])),
        "scan_warning_count": len(_array(data["scan_warnings"])),
    }
    for key, category in (
        ("diagnostics_count", "diagnostics"),
        ("scan_warning_count", "scan_warnings"),
    ):
        if signals[key]:
            categories.append(category)
    if head is None or dirty is None:
        categories.append("snapshot_unknown")
    if dirty is not False:
        categories.append("content_identity_unavailable")
    for key, value in statuses.items():
        signals["relation_status_" + key] = value
    ordered_files = tuple(files[p] for p in sorted(files))
    incomplete = bool(categories) or any(f.incomplete for f in ordered_files)
    coverage = EvidenceRelationCoverage(
        EvidenceCoverage(tuple(sorted(signals.items())), incomplete),
        ordered_files,
        tuple(sorted(categories)),
    )
    state = EvidenceRelationState(
        descriptor,
        EvidenceRepositorySnapshot(request.repository.id, head, dirty, command="graph"),
        coverage,
    )
    # Duplicate syntax occurrences with identical normalized facts add no information.
    return EvidenceRelationBatch(state, tuple(sorted(set(relations), key=lambda r: r.sort_key())))
