"""Ordered, deterministic kind rules and independent lifecycle overlay."""

from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import PurePosixPath

from context_integrity.models import (
    AuthorityClass as A,
)
from context_integrity.models import (
    ClassificationConfidence as C,
)
from context_integrity.models import (
    ClassificationResult,
    RuleMatch,
)
from context_integrity.models import (
    LifecycleState as L,
)
from context_integrity.models import (
    SourceKind as K,
)


@dataclass(frozen=True)
class KindRule:
    id: str
    kind: K
    basis: str
    confidence: C = C.STRONG
    filenames: tuple[str, ...] = ()
    directories: tuple[str, ...] = ()
    paths: tuple[str, ...] = ()

    def matches(self, path: PurePosixPath) -> bool:
        return (
            any(fnmatchcase(path.name.lower(), p) for p in self.filenames)
            or any(s.lower() in self.directories for s in path.parts[:-1])
            or any(fnmatchcase(path.as_posix().lower(), p) for p in self.paths)
        )


# First matching kind rule wins. This is kind disambiguation, never authority ranking.
KIND_RULES = (
    KindRule(
        "kind.agent_instruction.filename",
        K.AGENT_INSTRUCTION,
        "exact_filename",
        filenames=("agents.md", "claude.md", "gemini.md"),
    ),
    KindRule(
        "kind.agent_instruction.copilot",
        K.AGENT_INSTRUCTION,
        "path_rule",
        paths=(".github/copilot-instructions.md",),
    ),
    KindRule(
        "kind.current_state.filename",
        K.CURRENT_STATE,
        "exact_filename",
        filenames=("current-state.md", "current_state.md"),
    ),
    KindRule(
        "kind.architecture.exact_filename",
        K.ARCHITECTURE,
        "exact_filename",
        filenames=("architecture.md", "system-design.md"),
    ),
    KindRule(
        "kind.product.exact_filename",
        K.PRODUCT_REQUIREMENT,
        "exact_filename",
        filenames=("prd.md",),
    ),
    KindRule(
        "kind.readme.filename",
        K.README,
        "exact_filename",
        filenames=("readme.md", "readme.rst", "readme.mdx", "readme.txt", "readme.adoc"),
    ),
    KindRule(
        "kind.decision.directory",
        K.DECISION_RECORD,
        "directory_rule",
        directories=("adr", "adrs", "decisions"),
    ),
    KindRule(
        "kind.plan.directory",
        K.IMPLEMENTATION_PLAN,
        "directory_rule",
        directories=("plans", "planning"),
    ),
    KindRule("kind.review.directory", K.REVIEW, "directory_rule", directories=("reviews",)),
    KindRule(
        "kind.verification.directory",
        K.VERIFICATION_RECORD,
        "directory_rule",
        directories=("verification",),
    ),
    KindRule(
        "kind.release.directory", K.RELEASE_RECORD, "directory_rule", directories=("releases",)
    ),
    KindRule(
        "kind.current_state.status_path",
        K.CURRENT_STATE,
        "path_rule",
        paths=("status/current*.md", "*/status/current*.md"),
    ),
    KindRule(
        "kind.architecture.directory",
        K.ARCHITECTURE,
        "directory_rule",
        directories=("architecture",),
    ),
    KindRule(
        "kind.product.requirements_path",
        K.PRODUCT_REQUIREMENT,
        "path_rule",
        paths=("requirements/product*", "*/requirements/product*"),
    ),
    KindRule(
        "kind.generated.directory",
        K.GENERATED_SUMMARY,
        "directory_rule",
        directories=("summary", "generated"),
    ),
    KindRule(
        "kind.decision.filename",
        K.DECISION_RECORD,
        "filename_pattern",
        C.HEURISTIC,
        filenames=("adr-*",),
    ),
    KindRule(
        "kind.plan.filename",
        K.IMPLEMENTATION_PLAN,
        "filename_pattern",
        C.HEURISTIC,
        filenames=("*implementation-plan*", "phase-*-plan*"),
    ),
    KindRule(
        "kind.review.filename",
        K.REVIEW,
        "filename_pattern",
        C.HEURISTIC,
        filenames=("*-review.*", "*post-implementation-review*", "*independent-review*"),
    ),
    KindRule(
        "kind.verification.filename",
        K.VERIFICATION_RECORD,
        "filename_pattern",
        C.HEURISTIC,
        filenames=("*-verification.*", "*verification-record*"),
    ),
    KindRule(
        "kind.release.filename",
        K.RELEASE_RECORD,
        "filename_pattern",
        C.HEURISTIC,
        filenames=("release-*",),
    ),
    KindRule(
        "kind.architecture.filename",
        K.ARCHITECTURE,
        "filename_pattern",
        C.HEURISTIC,
        filenames=("*-architecture.*",),
    ),
    KindRule(
        "kind.product.filename",
        K.PRODUCT_REQUIREMENT,
        "filename_pattern",
        C.HEURISTIC,
        filenames=("*-prd.*", "product-requirements*"),
    ),
    KindRule(
        "kind.handoff.filename",
        K.HANDOFF,
        "filename_pattern",
        C.HEURISTIC,
        filenames=("handoff.*", "handoff-*", "*-handoff.*", "*_handoff.*"),
    ),
    KindRule(
        "kind.generated.filename",
        K.GENERATED_SUMMARY,
        "filename_pattern",
        C.HEURISTIC,
        filenames=("*-summary.*",),
    ),
)
HISTORICAL_DIRECTORIES = ("history", "historical", "archive", "archived", "deprecated")
AUTHORITY_BY_KIND = {
    K.AGENT_INSTRUCTION: A.OPERATING_INSTRUCTION,
    K.DECISION_RECORD: A.DECISION,
    K.IMPLEMENTATION_PLAN: A.PLAN,
    K.REVIEW: A.VERIFICATION_EVIDENCE,
    K.VERIFICATION_RECORD: A.VERIFICATION_EVIDENCE,
    K.RELEASE_RECORD: A.VERIFICATION_EVIDENCE,
    K.CURRENT_STATE: A.GENERATED_DERIVATIVE,
    K.ARCHITECTURE: A.ARCHITECTURE_PRODUCT,
    K.PRODUCT_REQUIREMENT: A.ARCHITECTURE_PRODUCT,
    K.HANDOFF: A.GENERATED_DERIVATIVE,
    K.GENERATED_SUMMARY: A.GENERATED_DERIVATIVE,
    K.README: A.ARCHITECTURE_PRODUCT,
    K.OTHER_DOCUMENT: A.UNKNOWN,
}


def classify_source(path: str) -> ClassificationResult:
    pure = PurePosixPath(path)
    rule = next((r for r in KIND_RULES if r.matches(pure)), None)
    kind = rule.kind if rule else K.OTHER_DOCUMENT
    confidence = rule.confidence if rule else C.UNKNOWN
    matches = [
        RuleMatch(
            rule.id if rule else "kind.other_document.fallback",
            "kind",
            kind.value,
            confidence,
            rule.basis if rule else "extension_fallback",
        )
    ]
    authority = AUTHORITY_BY_KIND[kind]
    matches.append(
        RuleMatch(
            f"authority.kind.{kind.value}",
            "authority_class",
            authority.value,
            confidence,
            "kind_mapping",
        )
    )
    historical = next(
        (d for d in HISTORICAL_DIRECTORIES if d in tuple(s.lower() for s in pure.parts[:-1])), None
    )
    lifecycle = L.HISTORICAL if historical else L.UNKNOWN
    matches.append(
        RuleMatch(
            f"lifecycle.historical.directory_{historical}"
            if historical
            else "lifecycle.unknown.fallback",
            "lifecycle",
            lifecycle.value,
            C.STRONG if historical else C.UNKNOWN,
            "directory_rule" if historical else "no_historical_signal",
        )
    )
    if historical:
        authority = A.HISTORICAL
        matches.append(
            RuleMatch(
                "authority.historical.overlay",
                "authority_class",
                authority.value,
                C.STRONG,
                "historical_lifecycle",
            )
        )
    return ClassificationResult(
        kind, authority, lifecycle, confidence, tuple(m.rule_id for m in matches), tuple(matches)
    )
