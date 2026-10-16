"""Deterministic review signals over inventory, bounded text, and changed paths."""

import re
from hashlib import sha256
from pathlib import PurePosixPath

from context_integrity.acquisition import normalize_path
from context_integrity.configuration import verify_config_revision
from context_integrity.evidence import changed_paths, source_text
from context_integrity.lifecycle import lifecycle_authority_eligible
from context_integrity.models import (
    ChangeScope,
    ChangeSet,
    FindingSeverity,
    InstructionPolicySpec,
    IntegrityEvidence,
    IntegrityFinding,
    IntegrityOverview,
    InventoryManifest,
    RepositoryConfig,
    ScanWarning,
    SourceKind,
    SourceRecord,
)
from context_integrity.repository import RepositoryContext

INSTRUCTION_RULE = "instruction.canonical_reference.v1"
NAVIGATION_RULE = "current_state.navigation.v1"
DELIVERY_RULE = "current_state.delivery_evidence.v1"
DEPENDENCY_RULE = "document_dependency.change_review.v1"


def usable(source: SourceRecord) -> bool:
    return (
        lifecycle_authority_eligible(source.lifecycle)
        and source.revision.content_sha256 is not None
    )


def _delivered_status(status: str) -> tuple[bool, bool]:
    """Return (requires delivery evidence, ambiguously decorated delivered token)."""
    value = status.strip()
    wrapped = re.match(r"^(\*\*|__|`)(.+?)\1(.*)$", value)
    if wrapped:
        value = f"{wrapped[2].strip()}{wrapped[3]}"
    if re.match(r"(?:implemented|delivered|complete|completed|verified)\b", value, re.I):
        return True, False

    # Unknown Markdown decoration must not turn a likely delivered state into a pass.
    undecorated = value.lstrip("*_`").lstrip()
    if value != undecorated and re.match(
        r"(?:implemented|delivered|complete|completed|verified)\b", undecorated, re.I
    ):
        return True, True
    return False, False


def evidence(
    role: str, path: str, sources: dict[str, SourceRecord], derivation: str = "inventory"
) -> IntegrityEvidence:
    source = sources.get(path)
    return IntegrityEvidence(
        role, path, source.id if source else None, source.revision if source else None, derivation
    )


def finding(
    rule: str,
    code: str,
    message: str,
    items: tuple[IntegrityEvidence, ...],
    dependency_id: str | None = None,
) -> IntegrityFinding:
    paths = tuple(sorted({e.path for e in items}))
    identity = "\0".join((rule, code, dependency_id or "", *paths))
    identifier = "finding_" + sha256(identity.encode("utf-8", "surrogateescape")).hexdigest()[:32]
    return IntegrityFinding(
        identifier, rule, code, FindingSeverity.MEDIUM, message, paths, items, dependency_id
    )


def references_canonical(text: str, canonical: str) -> bool:
    # Literal repository-root path tokens; avoid matching suffixes of unrelated paths/URLs.
    return (
        re.search(r"(?<![\w./:\\-])(?:/|\./)?" + re.escape(canonical) + r"(?![\w./\\-])", text)
        is not None
    )


def instruction_findings(
    context: RepositoryContext, manifest: InventoryManifest
) -> tuple[IntegrityFinding, ...]:
    sources = {s.path: s for s in manifest.sources}
    policy = manifest.repository_config.instruction_policy if manifest.repository_config else None
    if policy is None:
        root = sources.get("AGENTS.md")
        if root is None or root.kind != SourceKind.AGENT_INSTRUCTION:
            return ()
        policy = InstructionPolicySpec(
            "AGENTS.md",
            tuple(
                p
                for p in ("CLAUDE.md", "GEMINI.md", ".github/copilot-instructions.md")
                if p in sources
            ),
        )
    results = []
    for role, path in (
        ("canonical_instruction", policy.canonical),
        *(("compatibility_instruction", p) for p in policy.compatibility),
    ):
        item = evidence(role, path, sources)
        source = sources.get(path)
        if source is None:
            code = (
                "instruction_canonical_missing"
                if path == policy.canonical
                else "instruction_compatibility_missing"
            )
            results.append(
                finding(
                    INSTRUCTION_RULE,
                    code,
                    "Expected instruction source is absent from inventory.",
                    (item,),
                )
            )
        elif source.kind != SourceKind.AGENT_INSTRUCTION:
            results.append(
                finding(
                    INSTRUCTION_RULE,
                    "instruction_source_kind_mismatch",
                    "Expected source is not an agent instruction.",
                    (item,),
                )
            )
        elif not usable(source):
            results.append(
                finding(
                    INSTRUCTION_RULE,
                    "instruction_source_unusable",
                    "Instruction source is not eligible as current policy evidence.",
                    (item,),
                )
            )
        elif path != policy.canonical:
            text = source_text(context, source)
            if text is not None and not references_canonical(text, policy.canonical):
                results.append(
                    finding(
                        INSTRUCTION_RULE,
                        "instruction_reference_missing",
                        "Compatibility instruction lacks a structural canonical path reference.",
                        (evidence("canonical_instruction", policy.canonical, sources), item),
                    )
                )
    return tuple(results)


def current_state_findings(
    context: RepositoryContext, manifest: InventoryManifest
) -> tuple[IntegrityFinding, ...]:
    sources = {s.path: s for s in manifest.sources}
    candidates = [s for s in manifest.sources if s.kind == SourceKind.CURRENT_STATE and usable(s)]
    if not candidates:
        return ()
    if len(candidates) > 1:
        return (
            finding(
                NAVIGATION_RULE,
                "current_state_multiple_candidates",
                "Multiple usable current-state sources require explicit resolution.",
                tuple(evidence("current_state", s.path, sources) for s in candidates),
            ),
        )
    current = candidates[0]
    text = source_text(context, current)
    if text is None:
        return ()
    item = evidence("current_state", current.path, sources)
    phase = re.search(r"^\*\*Current phase:\*\*\s+Phase\s+(\d{1,9})\b", text, re.M | re.I)
    plan = re.search(r"^\*\*Active plan:\*\*\s+`([^`\n]+)`", text, re.M)
    status = re.search(r"^\*\*Status:\*\*[^\S\n]+([^\n]+)", text, re.M)
    next_section = re.search(r"^## Next expected step\s*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    next_phase = (
        re.search(r"\bPhase\s+(\d{1,9})\b", next_section[1], re.I) if next_section else None
    )
    results = []
    delivered, ambiguous_status = _delivered_status(status[1]) if status else (False, False)
    if not all((phase, plan, status, next_phase)) or ambiguous_status:
        results.append(
            finding(
                NAVIGATION_RULE,
                "current_state_metadata_incomplete",
                "Current-state navigation metadata is incomplete or ambiguous.",
                (item,),
            )
        )
    if plan:
        try:
            raw = plan[1]
            if "\\" in raw or ":" in raw:
                raise ValueError
            plan_path = normalize_path(raw)
        except ValueError:
            # Never expose malformed source-body text as an output path.
            results.append(
                finding(
                    NAVIGATION_RULE,
                    "current_state_active_plan_unsafe",
                    "Active plan metadata is not a safe relative path.",
                    (item,),
                )
            )
        else:
            target = sources.get(plan_path)
            items = (item, evidence("active_plan", plan_path, sources))
            code = None
            if target is None:
                code = "current_state_active_plan_missing"
            elif target.kind != SourceKind.IMPLEMENTATION_PLAN:
                code = "current_state_active_plan_kind_mismatch"
            elif not usable(target):
                code = "current_state_active_plan_unusable"
            if code:
                results.append(
                    finding(
                        NAVIGATION_RULE,
                        code,
                        "Active plan is absent, unusable, or has the wrong source role.",
                        items,
                    )
                )
            plan_phase = re.search(r"phase-(\d{1,9})\b", PurePosixPath(plan_path).name, re.I)
            if phase and plan_phase and int(phase[1]) != int(plan_phase[1]):
                results.append(
                    finding(
                        NAVIGATION_RULE,
                        "current_state_phase_plan_mismatch",
                        "Active plan phase differs from current phase.",
                        items,
                    )
                )
    if phase and next_phase and int(next_phase[1]) <= int(phase[1]):
        results.append(
            finding(
                NAVIGATION_RULE,
                "current_state_next_phase_invalid",
                "Next phase must be numerically greater than current phase.",
                (item,),
            )
        )
    if phase:
        reports = []
        for source in manifest.sources:
            match = re.fullmatch(
                r"phase-(\d{1,9})-implementation-report(?:[.-].*)?",
                PurePosixPath(source.path).name,
                re.I,
            )
            if source.kind == SourceKind.VERIFICATION_RECORD and usable(source) and match:
                reports.append((int(match[1]), source))
        number = int(phase[1])
        if delivered and not any(n == number for n, _ in reports):
            results.append(
                finding(
                    DELIVERY_RULE,
                    "current_state_delivery_evidence_missing",
                    "Delivered status lacks a matching phase implementation report; "
                    "plans do not establish delivery.",
                    (item,),
                )
            )
        later = tuple(
            evidence("verification_record", s.path, sources) for n, s in reports if n > number
        )
        if later:
            results.append(
                finding(
                    DELIVERY_RULE,
                    "current_state_lags_verification_evidence",
                    "Later numeric phase implementation evidence warrants current-state review.",
                    (item, *later),
                )
            )
    return tuple(results)


def dependency_findings(
    manifest: InventoryManifest, changes: ChangeSet
) -> tuple[IntegrityFinding, ...]:
    sources = {s.path: s for s in manifest.sources}
    config = manifest.repository_config or RepositoryConfig()
    results = []
    for spec in config.drift_dependencies:
        item = evidence("dependent_document", spec.dependent, sources)
        if spec.dependent not in sources or not usable(sources[spec.dependent]):
            results.append(
                finding(
                    DEPENDENCY_RULE,
                    "drift_dependent_missing",
                    "Configured dependent is absent or unavailable as a current context source.",
                    (item,),
                    spec.id,
                )
            )
        elif (
            changes.scope != ChangeScope.UNAVAILABLE and spec.dependent not in changes.changed_paths
        ):
            upstream = tuple(
                evidence("changed_upstream", p, sources, changes.derivation)
                for p in spec.upstream
                if p in changes.changed_paths
            )
            if upstream:
                results.append(
                    finding(
                        DEPENDENCY_RULE,
                        "document_dependency_changed",
                        "Declared upstream paths changed without the dependent document; "
                        "review is required.",
                        (item, *upstream),
                        spec.id,
                    )
                )
    return tuple(results)


def integrity_overview(
    context: RepositoryContext, manifest: InventoryManifest, diff: str | None = None
) -> IntegrityOverview:
    changes = changed_paths(context, diff)
    findings = (
        *instruction_findings(context, manifest),
        *current_state_findings(context, manifest),
        *dependency_findings(manifest, changes),
    )
    warnings = set((*manifest.warnings, *context.warnings))
    if changes.scope == ChangeScope.UNAVAILABLE:
        warnings.add(
            ScanWarning(
                "change_evidence_unavailable",
                None,
                "Local change evidence unavailable; change-dependent checks skipped.",
            )
        )
    config = manifest.repository_config or RepositoryConfig()
    # Text evaluation must not silently use a different policy than the inventoried one.
    verify_config_revision(context, config, config.content_sha256)
    return IntegrityOverview(
        manifest.repository,
        config.content_sha256,
        changes,
        tuple(sorted(findings, key=lambda f: (f.rule_id, f.code, f.affected_paths, f.id))),
        tuple(sorted(warnings, key=lambda w: (w.path or "", w.code, w.message))),
    )
