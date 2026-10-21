"""Explicit local provenance capture and bounded revalidation, with a pure decision core."""

from dataclasses import asdict, dataclass
from hashlib import sha256

from context_integrity import __version__
from context_integrity.acquisition import MAX_SOURCE_BYTES, read_source, read_source_bytes
from context_integrity.authority import effective_policies
from context_integrity.configuration import CONFIG_PATH, ConfigurationError
from context_integrity.contracts import resolve_contract
from context_integrity.derived_models import (
    MAX_DEPTH,
    MAX_GRAPH_BYTES,
    MAX_RECEIPT_BYTES,
    MAX_RECEIPTS,
    Artifact,
    CompilationPin,
    Derivation,
    DerivedReceipt,
    ProviderPin,
    ReceiptError,
    RepositorySnapshot,
    SourcePin,
    UpstreamPin,
    canonical_json,
    parse_receipt,
    path_value,
    require,
)
from context_integrity.inventory import inventory_repository
from context_integrity.models import (
    CandidateDecisionKind,
    CandidateOrigin,
    CompiledContext,
    InventoryManifest,
    SourceRecord,
    make_source_id,
)
from context_integrity.repository import RepositoryContext, RepositoryError


def fingerprint(value) -> str:
    """Internal canonical structured digest; never projects arbitrary input prose."""
    return sha256(canonical_json(value).encode()).hexdigest()


def metadata_fingerprint(source: SourceRecord, manifest: InventoryManifest) -> str:
    return fingerprint(
        {
            "kind": source.kind.value,
            "authority": source.authority_class.value,
            "lifecycle": source.lifecycle.value,
            "metadata": asdict(source.source_metadata) if source.source_metadata else None,
            "supersession": [
                {
                    "source": e.source.path,
                    "superseded_by": e.superseded_by.path,
                    "reason": e.reason,
                    "config_sha256": e.config_sha256,
                }
                for e in manifest.supersession
                if source.id in (e.source.id, e.superseded_by.id)
            ],
        }
    )


def selection_fingerprint(manifest: InventoryManifest) -> str:
    return fingerprint(
        {
            s.path: {
                "sha256": s.revision.content_sha256,
                "metadata": metadata_fingerprint(s, manifest),
            }
            for s in sorted(manifest.sources, key=lambda s: s.path)
        }
    )


@dataclass(frozen=True)
class Observation:
    path: str
    content_sha256: str | None
    state: str  # observed, missing, unobservable, budget_exceeded


class Reader:
    """One command-wide byte/work budget, shared by a memoized receipt DAG."""

    def __init__(self, context: RepositoryContext):
        self.context = context
        self.bytes = 0
        self.work = 0
        self.cache: dict[tuple[str, int], tuple[Observation, bytes | None]] = {}

    def read(self, path: str, limit: int = MAX_SOURCE_BYTES) -> tuple[Observation, bytes | None]:
        path_value(path)
        key = (path, limit)
        if key in self.cache:
            return self.cache[key]
        self.work += 1
        if self.work > 4096 or self.bytes >= MAX_GRAPH_BYTES:
            return Observation(path, None, "budget_exceeded"), None
        start = len(self.context.warnings)
        bound = min(limit, MAX_GRAPH_BYTES - self.bytes)
        data = None
        if limit == MAX_RECEIPT_BYTES:
            data = read_source_bytes(self.context, path, max_bytes=bound)
            content_hash = sha256(data).hexdigest() if data is not None else None
            size = len(data) if data is not None else None
        else:
            size, content_hash, _ = read_source(self.context, path, max_bytes=bound)
        self.bytes += size if content_hash is not None else bound
        if content_hash is None:
            warnings = self.context.warnings[start:]
            missing = any(
                w.message == "Candidate disappeared before it could be opened." for w in warnings
            )
            observation = Observation(path, None, "missing" if missing else "unobservable")
        else:
            observation = Observation(path, content_hash, "observed")
        self.cache[key] = observation, data
        return observation, data


@dataclass(frozen=True, order=True)
class Reason:
    code: str
    path: str
    artifact_id: str
    effect: str  # review, uncertainty, caveat
    pinned_sha256: str | None = None
    observed_sha256: str | None = None


@dataclass(frozen=True)
class DerivedResult:
    artifact_id: str
    artifact_path: str
    provenance_scope: str
    status: str
    reasons: tuple[Reason, ...]
    receipts_observed: int


def aggregate(reasons: list[Reason]) -> str:
    if any(r.effect == "review" for r in reasons):
        return "review_required"
    if any(r.effect == "uncertainty" for r in reasons):
        return "inconclusive"
    return "unchanged_observed_inputs"


def compare_pin(
    artifact_id: str, label: str, pinned: str | None, observed: Observation
) -> list[Reason]:
    """Pure direct comparison; None is a pinned absence only for config."""
    if observed.state == "missing":
        return (
            []
            if pinned is None
            else [Reason(f"{label}_missing", observed.path, artifact_id, "review", pinned)]
        )
    if observed.state != "observed":
        return [
            Reason(f"{label}_{observed.state}", observed.path, artifact_id, "uncertainty", pinned)
        ]
    if pinned != observed.content_sha256:
        return [
            Reason(
                f"{label}_changed",
                observed.path,
                artifact_id,
                "review",
                pinned,
                observed.content_sha256,
            )
        ]
    return []


def _snapshot(context):
    r = context.repository
    return RepositorySnapshot(r.id, r.git_head, r.git_dirty)


def _source_pin(path, observed, manifest):
    source = next((s for s in manifest.sources if s.path == path), None)
    if source:
        require(source.revision.content_sha256 == observed.content_sha256)
    return SourcePin(
        path,
        make_source_id(manifest.repository.id, path),
        observed.content_sha256,
        source.lifecycle.value if source else None,
        source.authority_class.value if source else None,
        metadata_fingerprint(source, manifest) if source else None,
        "inventory" if source else "explicit_file",
    )


def _hash_required(reader: Reader, path: str) -> Observation:
    observed, _ = reader.read(path)
    require(observed.state == "observed")
    return observed


def _config_pin(reader: Reader, manifest: InventoryManifest) -> str | None:
    observed, _ = reader.read(CONFIG_PATH)
    require(observed.state in ("observed", "missing"))
    expected = manifest.repository_config.content_sha256
    require(observed.content_sha256 == expected)
    return expected


def capture_receipt(
    context: RepositoryContext,
    manifest: InventoryManifest,
    artifact_path: str,
    *,
    artifact_id: str,
    kind: str,
    derivation: Derivation,
    depends_on: tuple[str, ...] = (),
    upstream_receipts: tuple[str, ...] = (),
    receipt_path: str,
) -> DerivedReceipt:
    path_value(receipt_path)
    path_value(artifact_path)
    require(len(depends_on) <= 256 and len(upstream_receipts) <= 16)
    require(
        len(set(depends_on)) == len(depends_on)
        and len(set(upstream_receipts)) == len(upstream_receipts)
    )
    require(receipt_path not in (artifact_path, CONFIG_PATH, *depends_on, *upstream_receipts))
    reader = Reader(context)
    artifact = Artifact(
        artifact_id,
        kind,
        artifact_path,
        _hash_required(reader, artifact_path).content_sha256,
        derivation,
    )
    pins = tuple(_source_pin(p, _hash_required(reader, p), manifest) for p in sorted(depends_on))
    parents = []
    checker = Checker(context, manifest, reader)
    for path in sorted(upstream_receipts):
        parent = checker.load(path)
        # A declaration cannot import stale/unknown provenance as a trusted new baseline.
        result = checker.evaluate(path)
        require(result.status == "unchanged_observed_inputs")
        require(parent.artifact.id != artifact.id and parent.artifact.path != artifact.path)
        require(receipt_path not in checker.input_paths)
        observed, _ = reader.read(path, MAX_RECEIPT_BYTES)
        parents.append(
            UpstreamPin(
                path,
                observed.content_sha256,
                parent.artifact.id,
                parent.artifact.path,
                parent.artifact.content_sha256,
            )
        )
    receipt = DerivedReceipt(
        artifact,
        _snapshot(context),
        "declared",
        _config_pin(reader, manifest),
        pins,
        tuple(parents),
        known_incomplete=not pins and not parents,
    )
    # Also reject an indirect edge back to this artifact/identity.
    require(artifact.id not in checker.identities and artifact.path not in checker.artifacts)
    return receipt


def compiler_receipt(
    context: RepositoryContext,
    manifest: InventoryManifest,
    compiled: CompiledContext,
    artifact_path: str,
    artifact_bytes: bytes,
) -> DerivedReceipt:
    """Build exclusively from typed selection; local observations must match provider pins."""
    reader = Reader(context)
    require(len(artifact_bytes) <= MAX_SOURCE_BYTES)
    require(compiled.repository == manifest.repository)
    pins = []
    for decision in sorted(compiled.decisions, key=lambda d: d.source.path):
        if decision.decision != CandidateDecisionKind.SELECTED:
            continue
        source = decision.source
        observed = _hash_required(reader, source.path)
        require(observed.content_sha256 == source.revision.content_sha256)
        if source.origin == CandidateOrigin.EVIDENCE_PROVIDER:
            pins.append(
                SourcePin(
                    source.path,
                    make_source_id(manifest.repository.id, source.path),
                    observed.content_sha256,
                    source.lifecycle.value,
                    source.authority_class.value,
                    None,
                    "provider",
                    source.provider_id,
                    source.provider_version,
                    source.derivation,
                )
            )
        else:
            pins.append(_source_pin(source.path, observed, manifest))
    providers = tuple(
        ProviderPin(
            p.descriptor.id,
            p.descriptor.version,
            p.descriptor.derivation,
            p.descriptor.contract_version,
            p.snapshot.provider_schema_version,
            p.snapshot.git_head,
            p.snapshot.git_dirty,
            fingerprint(asdict(p.coverage)),
            fingerprint(asdict(p)),
            p.coverage.incomplete,
        )
        for p in compiled.providers
    )
    compilation = CompilationPin(
        compiled.contract.id,
        fingerprint(asdict(compiled.contract)),
        fingerprint([asdict(p) for p in compiled.authority_policies]),
        selection_fingerprint(manifest),
        sha256(compiled.task.encode()).hexdigest() if compiled.task is not None else None,
        compiled.budget.effective_bytes,
        compiled.status.value,
        compiled.integrity_state.evaluation_status.value,
        tuple(sorted({w.code for w in compiled.warnings})),
        __version__,
    )
    return DerivedReceipt(
        Artifact(
            "compiled-" + sha256(artifact_path.encode()).hexdigest()[:24],
            "compiled_context",
            artifact_path,
            sha256(artifact_bytes).hexdigest(),
            Derivation("tool", "context-integrity", __version__),
        ),
        _snapshot(context),
        "compiler_selection",
        _config_pin(reader, manifest),
        tuple(pins),
        provider_context=providers,
        compilation=compilation,
        known_incomplete=compiled.status.value != "complete"
        or any(p.incomplete for p in providers)
        or any(s.revision.content_sha256 is None for s in manifest.sources)
        or bool(manifest.warnings),
    )


class Checker:
    def __init__(self, context, manifest=None, reader=None):
        self.context = context
        self.manifest = manifest
        self.reader = reader or Reader(context)
        self.loaded: dict[str, DerivedReceipt] = {}
        self.rejected: set[str] = set()
        self.results: dict[str, DerivedResult] = {}
        self.identities: dict[str, str] = {}
        self.artifacts: dict[str, str] = {}
        self.input_paths: set[str] = {CONFIG_PATH}

    def load(self, path: str) -> DerivedReceipt:
        path_value(path)
        require(path not in self.rejected)
        try:
            return self._load(path)
        except ReceiptError:
            self.rejected.add(path)
            raise

    def _load(self, path: str) -> DerivedReceipt:
        if path in self.loaded:
            return self.loaded[path]
        require(len(self.loaded) + len(self.rejected) < MAX_RECEIPTS)
        observed, data = self.reader.read(path, MAX_RECEIPT_BYTES)
        require(observed.state == "observed")
        receipt = parse_receipt(data)
        require(receipt.repository.id == self.context.repository.id)
        require(
            path
            not in (
                receipt.artifact.path,
                CONFIG_PATH,
                *(p.path for p in receipt.dependencies),
                *(p.path for p in receipt.upstream_receipts),
            )
        )
        require(
            receipt.artifact.id not in self.identities
            or self.identities[receipt.artifact.id] == path
        )
        require(
            receipt.artifact.path not in self.artifacts
            or self.artifacts[receipt.artifact.path] == path
        )
        self.identities[receipt.artifact.id] = path
        self.artifacts[receipt.artifact.path] = path
        self.loaded[path] = receipt
        self.input_paths.update(
            (path, receipt.artifact.path, *(p.path for p in receipt.dependencies))
        )
        return receipt

    def evaluate(self, path: str, stack: tuple[str, ...] = ()) -> DerivedResult:
        require(path not in stack and len(stack) < MAX_DEPTH)
        if path in self.results:
            return self.results[path]
        receipt = self.load(path)
        artifact = receipt.artifact
        reasons = [
            Reason("declared_inputs_not_semantic_validation", artifact.path, artifact.id, "caveat")
        ]
        if receipt.known_incomplete or (not receipt.dependencies and not receipt.upstream_receipts):
            reasons.append(
                Reason("provenance_incomplete", artifact.path, artifact.id, "uncertainty")
            )
        for label, pin_path, digest in (
            ("artifact", artifact.path, artifact.content_sha256),
            ("config", CONFIG_PATH, receipt.config_sha256),
        ):
            observed, _ = self.reader.read(pin_path)
            reasons.extend(compare_pin(artifact.id, label, digest, observed))
        for source in receipt.dependencies:
            observed, _ = self.reader.read(source.path)
            reasons.extend(compare_pin(artifact.id, "source", source.content_sha256, observed))
            if source.observation_basis == "inventory":
                current = (
                    next((s for s in self.manifest.sources if s.path == source.path), None)
                    if self.manifest
                    else None
                )
                if current is None:
                    reasons.append(
                        Reason(
                            "source_metadata_unobservable", source.path, artifact.id, "uncertainty"
                        )
                    )
                elif (
                    source.metadata_sha256 != metadata_fingerprint(current, self.manifest)
                    or source.observed_lifecycle != current.lifecycle.value
                    or source.observed_authority != current.authority_class.value
                ):
                    reasons.append(
                        Reason(
                            "source_metadata_changed",
                            source.path,
                            artifact.id,
                            "review",
                            source.metadata_sha256,
                            metadata_fingerprint(current, self.manifest),
                        )
                    )
        if receipt.provider_context:
            reasons.append(
                Reason("provider_not_revalidated", artifact.path, artifact.id, "uncertainty")
            )
        if receipt.compilation:
            pin = receipt.compilation
            reasons.append(Reason("selection_not_replayed", artifact.path, artifact.id, "caveat"))
            if self.manifest is None:
                reasons.append(
                    Reason(
                        "compilation_context_unobservable",
                        artifact.path,
                        artifact.id,
                        "uncertainty",
                    )
                )
            else:
                if self.manifest.warnings:
                    reasons.append(
                        Reason(
                            "compilation_context_unobservable",
                            artifact.path,
                            artifact.id,
                            "uncertainty",
                        )
                    )
                try:
                    contract = resolve_contract(self.manifest.repository_config, pin.contract_id)
                    pairs = (
                        ("contract_changed", pin.contract_sha256, fingerprint(asdict(contract))),
                        (
                            "policies_changed",
                            pin.policies_sha256,
                            fingerprint(
                                [
                                    asdict(p)
                                    for p in effective_policies(self.manifest.repository_config)
                                    if p.id in {r.authority_policy for r in contract.rules}
                                ]
                            ),
                        ),
                        (
                            "selection_context_changed",
                            pin.selection_sha256,
                            selection_fingerprint(self.manifest),
                        ),
                    )
                    for code, old, new in pairs:
                        if old != new:
                            reasons.append(
                                Reason(code, artifact.path, artifact.id, "review", old, new)
                            )
                except ValueError:
                    reasons.append(Reason("contract_missing", artifact.path, artifact.id, "review"))
            if pin.compiler_version != __version__:
                reasons.append(
                    Reason("compiler_version_changed", artifact.path, artifact.id, "review")
                )
        for parent in sorted(receipt.upstream_receipts, key=lambda p: p.path):
            self.input_paths.add(parent.path)
            observed, _ = self.reader.read(parent.path, MAX_RECEIPT_BYTES)
            differences = compare_pin(
                artifact.id, "upstream_receipt", parent.receipt_sha256, observed
            )
            reasons.extend(differences)
            if differences:
                continue  # changed pins are not trusted and must never be adopted
            try:
                upstream = self.load(parent.path)
                require(
                    (upstream.artifact.id, upstream.artifact.path, upstream.artifact.content_sha256)
                    == (parent.artifact_id, parent.artifact_path, parent.artifact_sha256)
                )
                result = self.evaluate(parent.path, (*stack, path))
                reasons.extend(result.reasons)
                if result.status != "unchanged_observed_inputs":
                    reasons.append(
                        Reason(
                            "upstream_review_required"
                            if result.status == "review_required"
                            else "upstream_inconclusive",
                            parent.path,
                            artifact.id,
                            "review" if result.status == "review_required" else "uncertainty",
                        )
                    )
            except ReceiptError:
                reasons.append(
                    Reason("upstream_receipt_untrusted", parent.path, artifact.id, "uncertainty")
                )
        result = DerivedResult(
            artifact.id,
            artifact.path,
            receipt.provenance_scope,
            aggregate(reasons),
            tuple(sorted(set(reasons))),
            len(self.loaded),
        )
        self.results[path] = result
        return result


def check_receipt(context: RepositoryContext, path: str) -> tuple[DerivedResult, set[str]]:
    checker = Checker(context)
    checker.load(path)  # top-level invalid input is exit 6, unlike an invalid upstream
    try:
        checker.manifest = inventory_repository(
            context, max_observation_bytes=MAX_GRAPH_BYTES, max_sources=4096
        )
    except (ConfigurationError, RepositoryError):
        checker.manifest = None  # byte differences still dominate observation uncertainty
    result = checker.evaluate(path)
    return result, checker.input_paths


def result_dict(result: DerivedResult) -> dict:
    return {
        "derived_result_schema_version": 1,
        "artifact_id": result.artifact_id,
        "artifact_path": result.artifact_path,
        "provenance_scope": result.provenance_scope,
        "status": result.status,
        "receipts_observed": result.receipts_observed,
        "reasons": [
            {
                "code": r.code,
                "path": r.path,
                "artifact_id": r.artifact_id,
                "effect": r.effect,
                "pinned_sha256": r.pinned_sha256,
                "observed_sha256": r.observed_sha256,
            }
            for r in result.reasons
        ],
    }


def render_result(result: DerivedResult, as_json: bool = False) -> str:
    if as_json:
        return canonical_json(result_dict(result))
    return (
        f"{result.artifact_id}: {result.status}\n"
        "Declared inputs only; byte equality does not establish semantic correctness "
        "or exhaustive provenance.\n"
        + "".join(f"  {r.code}: {r.path} ({r.artifact_id})\n" for r in result.reasons)
    )
