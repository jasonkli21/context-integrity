"""Bounded local Context Engine schema-v1 transport; no policy or source-body storage."""

import json
import math
import os
import re
import selectors
import signal
import subprocess
import time
from contextlib import suppress
from dataclasses import replace
from hashlib import sha256
from pathlib import Path, PurePosixPath

from context_integrity.evidence import (
    EvidenceContextBatch,
    EvidenceContextRequest,
    EvidenceCoverage,
    EvidenceProviderDescriptor,
    EvidenceProviderError,
    EvidenceProviderState,
    EvidenceRepositorySnapshot,
)
from context_integrity.models import (
    AuthorityClass,
    CandidateOrigin,
    CandidateRelevance,
    ClassificationConfidence,
    ClassificationResult,
    CompilerCandidate,
    GitFileStatus,
    LifecycleState,
    ScanWarning,
    SourceKind,
    SourceRecord,
    SourceRevision,
    make_source_id,
    valid_qualified_symbol_name,
)
from context_integrity.relations import EvidenceRelationBatch, EvidenceRelationRequest

MAX_STDOUT = 64 * 1024 * 1024
MAX_STDERR = 64 * 1024
TIMEOUT_SECONDS = 30
ROLES = {
    "source": SourceKind.SOURCE_CODE,
    "test": SourceKind.TEST,
    "schema": SourceKind.SCHEMA,
    "migration": SourceKind.MIGRATION,
}
COVERAGE_BOOLS = {
    "task_terms_truncated",
    "graph_truncated",
    "content_load_safety_limited",
    "reported_skips_truncated",
}
COVERAGE_COUNTS = {
    "files_considered",
    "files_eligible",
    "excluded_roles",
    "task_terms",
    "lexical_non_utf8_path_omissions",
    "ranking_roots",
    "ranking_roots_omitted",
    "fallback_candidates_omitted",
    "content_load_failures",
    "content_load_attempts",
    "content_load_bytes_reserved",
    "content_load_candidates_omitted",
    "budget_skips",
    "skips_omitted",
    "selection_candidates_omitted",
}
COVERAGE_OPTIONAL_COUNTS = {"sensitive_files_omitted"}
INCOMPLETE_SIGNALS = COVERAGE_BOOLS | {
    "analysis_incomplete",
    "diagnostics_count",
    "scan_warning_count",
    "paths_may_be_lossy",
    "lexical_non_utf8_path_omissions",
    "ranking_roots_omitted",
    "fallback_candidates_omitted",
    "content_load_failures",
    "content_load_candidates_omitted",
    "budget_skips",
    "skips_omitted",
    "selection_candidates_omitted",
    "lossy_candidates_omitted",
    "matched_entities_omitted",
    "unmapped_symbols",
    "ambiguous_symbol_keys",
    "unavailable_symbol_comparisons",
}
SCORE_KEYS = {"total", "lexical_path", "lexical_symbol", "graph", "role", "change", "centrality"}
CHANGE_COUNTS = {
    "changed_files_observed",
    "changed_symbols_observed",
    "current_file_mappings",
    "current_symbol_mappings",
    "unmapped_symbols",
    "ambiguous_symbol_keys",
    "unavailable_symbol_comparisons",
    "deleted_only_entities",
}


def _run(argv: list[str], timeout: float, stdout_limit: int, stderr_limit: int) -> bytes:
    """Drain both pipes incrementally; kill on limit/deadline, including pipe-holding children."""
    try:
        process = subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            start_new_session=True,
        )
    except (OSError, ValueError) as exc:
        raise EvidenceProviderError("executable_unavailable") from exc
    output = bytearray()
    sizes = {"stdout": 0, "stderr": 0}
    deadline = time.monotonic() + timeout
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ, "stdout")
            selector.register(process.stderr, selectors.EVENT_READ, "stderr")
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise EvidenceProviderError("timeout")
                for key, _ in selector.select(remaining):
                    chunk = os.read(key.fd, 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    sizes[key.data] += len(chunk)
                    limit = stdout_limit if key.data == "stdout" else stderr_limit
                    if sizes[key.data] > limit:
                        raise EvidenceProviderError("output_limit")
                    if key.data == "stdout":
                        output.extend(chunk)
            try:
                code = process.wait(timeout=max(0.001, deadline - time.monotonic()))
            except subprocess.TimeoutExpired as exc:
                raise EvidenceProviderError("timeout") from exc
            if code:
                raise EvidenceProviderError("process_failed")
        return bytes(output)
    finally:
        # Also terminate descendants that may have inherited a pipe.
        with suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
        process.wait()
        process.stdout.close()
        process.stderr.close()


def _integer(value, minimum=0):
    if type(value) is not int or not minimum <= value <= 2**64 - 1:
        raise ValueError
    return value


def _boolean(value):
    if type(value) is not bool:
        raise ValueError
    return value


def _token(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.+-]{1,100}", value):
        raise ValueError
    return value


def _revision(value):
    if value is not None and (
        not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", value)
    ):
        raise ValueError
    return value


def _path(value):
    if (
        not isinstance(value, str)
        or not value
        or any(c in value for c in "\\:\0\ufffd")
        or any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in value)
        or PurePosixPath(value).is_absolute()
        or any(p in {"", ".", ".."} for p in value.split("/"))
    ):
        raise EvidenceProviderError("unsafe_path")
    return value


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError
        result[key] = value
    return result


def normalize_context(
    payload: bytes, request: EvidenceContextRequest, descriptor: EvidenceProviderDescriptor
) -> EvidenceContextBatch:
    """Validate only the external schema; whitelist metadata and discard full bodies."""
    try:
        return _normalize(payload, request, descriptor)
    except EvidenceProviderError:
        raise
    except (KeyError, TypeError, ValueError, UnicodeError, OverflowError, RecursionError, OSError):
        raise EvidenceProviderError("invalid_response") from None


def _normalize(payload, request, descriptor):
    envelope = json.loads(
        payload.decode("utf-8"),
        object_pairs_hook=_unique_object,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
    )
    if (
        type(envelope["schema_version"]) is not int
        or envelope["schema_version"] != 1
        or envelope["command"] != "context"
    ):
        raise EvidenceProviderError("unsupported_contract")
    data = envelope["data"]
    repository = data["repository"]
    if (
        not isinstance(repository["root"], str)
        or not Path(repository["root"]).is_absolute()
        or Path(repository["root"]).resolve() != request.repository_root.resolve()
    ):
        raise EvidenceProviderError("repository_mismatch")
    head = _revision(data["git_head"])
    dirty = data["git_dirty"]
    if dirty is not None:
        _boolean(dirty)
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
    if data["task"] != request.task:
        raise EvidenceProviderError("query_mismatch")
    ranker = _token(data["ranker_version"])
    fallback = data["fallback_mode"]
    if fallback not in {None, "centrality"}:
        raise ValueError
    budget = data["budget"]
    if (
        budget["unit"] != "utf8_content_bytes"
        or _integer(budget["max"], 1) != request.acquisition_budget_bytes
    ):
        raise ValueError
    used, remaining = _integer(budget["used"]), _integer(budget["remaining"])
    if used + remaining != request.acquisition_budget_bytes:
        raise ValueError
    signals = {k: _boolean(data["coverage"][k]) for k in COVERAGE_BOOLS}
    signals.update({k: _integer(data["coverage"][k]) for k in COVERAGE_COUNTS})
    signals.update(
        {
            k: _integer(data["coverage"][k])
            for k in COVERAGE_OPTIONAL_COUNTS
            if k in data["coverage"]
        }
    )
    signals.update(
        {
            k: _boolean(repository["coverage"][k])
            for k in ("analysis_incomplete", "paths_may_be_lossy")
        }
    )
    for k in ("diagnostics_count", "scan_warning_count"):
        signals[k] = _integer(repository["coverage"][k])
    change = data["change"]
    change_metadata = {}
    if request.change_range is None:
        if change is not None:
            raise EvidenceProviderError("query_mismatch")
    else:
        if (
            "change_context" not in descriptor.capabilities
            or change["range"] != request.change_range
        ):
            raise EvidenceProviderError("query_mismatch")
        change_metadata = {
            "range": request.change_range,
            "base": _revision(change["base"]),
            "head": _revision(change["head"]),
        }
        if (
            change_metadata["base"] is None
            or change_metadata["head"] is None
            or head != change_metadata["head"]
            or dirty is not False
        ):
            raise EvidenceProviderError("snapshot_mismatch")
        for k in CHANGE_COUNTS:
            change_metadata[k] = _integer(change[k])
            if k in INCOMPLETE_SIGNALS:
                signals[k] = change_metadata[k]
    selected = data["selected"]
    if not isinstance(selected, list) or not isinstance(data["skipped"], list):
        raise ValueError
    candidates, seen, ranks = [], set(), set()
    total = 0
    signals.update(lossy_candidates_omitted=0, matched_entities_omitted=0)
    for item in selected:
        lossy = _boolean(item["path_lossy"])
        # Lossy identities are omitted explicitly, never repaired into invented paths.
        if lossy:
            signals["lossy_candidates_omitted"] += 1
        else:
            path = _path(item["path"])
            if path in seen:
                raise EvidenceProviderError("duplicate_path")
            seen.add(path)
        rank = _integer(item["rank"], 1)
        if rank in ranks:
            raise ValueError
        ranks.add(rank)
        content = item["content"]
        if not isinstance(content, str):
            raise ValueError
        raw = content.encode("utf-8")
        size = _integer(item["content_bytes"])
        if size != len(raw):
            raise EvidenceProviderError("content_size_mismatch")
        total += size
        digest = sha256(raw).hexdigest()
        del raw, content
        kind = ROLES.get(_token(item["role"]))
        if kind is None or lossy:
            continue
        score = {k: _integer(item["score"][k]) for k in SCORE_KEYS}
        if score["total"] != sum(v for k, v in score.items() if k != "total"):
            raise ValueError
        if not isinstance(item["reasons"], list) or not isinstance(item["matched_symbols"], list):
            raise ValueError
        reasons = tuple(sorted({_token(v) for v in item["reasons"]}))
        entities = []
        for symbol in item["matched_symbols"]:
            if _path(symbol["path"]) != path:
                raise ValueError
            name = symbol["qualified_name"]
            if not valid_qualified_symbol_name(name):
                raise ValueError
            start = _integer(symbol["range"]["start"]["byte"])
            end = _integer(symbol["range"]["end"]["byte"])
            if end < start or end > size:
                raise ValueError
            entities.append((name, _token(symbol["kind"]), start, end))
        omitted = _integer(item["matched_symbols_omitted"])
        signals["matched_entities_omitted"] += omitted
        distances = [
            None if item[k] is None else _integer(item[k])
            for k in ("graph_distance", "change_distance")
        ]
        revision = SourceRevision(
            digest,
            head,
            GitFileStatus.TRACKED_CLEAN if dirty is False and head else GitFileStatus.UNKNOWN,
            "provider_content_sha256",
        )
        source = SourceRecord(
            make_source_id(request.repository.id, path),
            path,
            kind,
            AuthorityClass.EXECUTABLE_TRUTH,
            LifecycleState.UNKNOWN,
            revision,
            ClassificationResult(
                kind,
                AuthorityClass.EXECUTABLE_TRUTH,
                LifecycleState.UNKNOWN,
                ClassificationConfidence.EXPLICIT,
                ("provider-role-v1",),
                (),
            ),
            size,
        )
        candidates.append(
            replace(
                CompilerCandidate.from_source(source),
                origin=CandidateOrigin.EVIDENCE_PROVIDER,
                provider_id=descriptor.id,
                provider_version=descriptor.version,
                derivation=descriptor.derivation + ":" + ranker,
                evidence_location=path,
                relevance=CandidateRelevance(
                    rank,
                    score["total"],
                    tuple(sorted(score.items())),
                    reasons,
                    tuple(sorted(entities)),
                    omitted,
                    *distances,
                ),
            )
        )
    if total != used:
        raise ValueError
    incomplete = any(signals.get(k, 0) for k in INCOMPLETE_SIGNALS)
    warnings = []
    if incomplete:
        warnings.append(
            ScanWarning(
                "provider_incomplete",
                None,
                "Provider analysis or candidate acquisition is incomplete; see provider coverage.",
            )
        )
    if (head is None and request.repository.git_head is not None) or (
        dirty is None and request.repository.git_dirty is not None
    ):
        warnings.append(
            ScanWarning(
                "provider_snapshot_unknown",
                None,
                "Provider snapshot metadata is partially unavailable; "
                "content hashes scope candidates.",
            )
        )
    state = EvidenceProviderState(
        descriptor,
        EvidenceRepositorySnapshot(request.repository.id, head, dirty),
        request.task,
        ranker,
        request.acquisition_budget_bytes,
        EvidenceCoverage(tuple(sorted(signals.items())), bool(incomplete)),
        tuple(sorted(change_metadata.items())),
        fallback,
        tuple(warnings),
    )
    return EvidenceContextBatch(state, tuple(sorted(candidates, key=lambda c: c.path)))


class ContextEngineProvider:
    def __init__(
        self,
        executable: str = "ctx",
        *,
        timeout: float = TIMEOUT_SECONDS,
        stdout_limit: int = MAX_STDOUT,
        stderr_limit: int = MAX_STDERR,
    ):
        if (
            type(timeout) not in {int, float}
            or not math.isfinite(timeout)
            or timeout <= 0
            or type(stdout_limit) is not int
            or stdout_limit <= 0
            or type(stderr_limit) is not int
            or stderr_limit <= 0
        ):
            raise ValueError("Provider process limits must be positive.")
        self.executable = executable
        self.timeout, self.stdout_limit, self.stderr_limit = timeout, stdout_limit, stderr_limit

    def relations(self, request: EvidenceRelationRequest) -> EvidenceRelationBatch:
        from context_integrity.graph_adapter import normalize_graph

        version = _run(
            [self.executable, "--version"],
            self.timeout,
            min(self.stdout_limit, 4096),
            self.stderr_limit,
        )
        match = re.fullmatch(rb"ctx ([A-Za-z0-9_.+-]{1,80})\s*", version)
        if match is None:
            raise EvidenceProviderError("invalid_version")
        descriptor = EvidenceProviderDescriptor(
            "context-engine",
            match[1].decode("ascii"),
            capabilities=("relations",),
            derivation="context-engine-cli-json-v1",
        )
        payload = _run(
            [self.executable, "graph", str(request.repository_root.resolve()), "--format", "json"],
            self.timeout,
            self.stdout_limit,
            self.stderr_limit,
        )
        batch = normalize_graph(payload, request, descriptor)
        from context_integrity.acquisition import MAX_SOURCE_BYTES, read_source
        from context_integrity.repository import RepositoryContext

        context = RepositoryContext(request.repository_root, request.repository, {}, False, [])
        remaining = 64 * 1024 * 1024
        observed = []
        for file in batch.state.coverage.files:
            digest = None
            if remaining >= MAX_SOURCE_BYTES:
                remaining -= MAX_SOURCE_BYTES
                _, digest, _ = read_source(context, file.path)
            observed.append((file.path, digest))
        return replace(batch, state=replace(batch.state, observed_content=tuple(observed)))

    def context_candidates(self, request: EvidenceContextRequest) -> EvidenceContextBatch:
        version = _run(
            [self.executable, "--version"],
            self.timeout,
            min(self.stdout_limit, 4096),
            self.stderr_limit,
        )
        match = re.fullmatch(rb"ctx ([A-Za-z0-9_.+-]{1,80})\s*", version)
        if match is None:
            raise EvidenceProviderError("invalid_version")
        descriptor = EvidenceProviderDescriptor(
            "context-engine",
            match[1].decode("ascii"),
            capabilities=("context_candidates", "change_context"),
            derivation="context-engine-cli-json-v1",
        )
        argv = [
            self.executable,
            "context",
            str(request.repository_root.resolve()),
            "--task",
            request.task,
            "--budget",
            str(request.acquisition_budget_bytes),
            "--format",
            "json",
        ]
        if request.change_range is not None:
            argv.extend(["--change", request.change_range])
        payload = _run(argv, self.timeout, self.stdout_limit, self.stderr_limit)
        return normalize_context(payload, request, descriptor)
