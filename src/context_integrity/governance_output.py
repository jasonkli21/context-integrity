"""Evidence-light report v1, strict baselines, bounded rendering and safe publication."""

import json
from collections import Counter
from pathlib import Path

from context_integrity.derived import fingerprint
from context_integrity.derived_models import (
    canonical_json,
    digest,
    path_value,
    repo_value,
    require,
    token,
)
from context_integrity.derived_output import DerivedOutputError, write_outputs
from context_integrity.governance import gate_for, metrics
from context_integrity.governance_config import iso_date, owner, read_input, review
from context_integrity.governance_models import (
    MAX_EVIDENCE,
    MAX_OBSERVATIONS,
    MAX_REPORT_BYTES,
    SEVERITIES,
    GovernanceError,
)
from context_integrity.workspace_config import array, keys, safe_directory

OBSERVATION_KEYS = (
    "target",
    "rule_id",
    "code",
    "entity",
    "signal",
    "effect",
    "intrinsic_severity",
    "effective_severity",
    "owner",
    "owner_basis",
    "evidence",
    "material_sha256",
    "reasons",
    "fingerprint",
    "waiver_eligible",
    "waiver_id",
    "blocking",
    "pinned_sha256",
    "observed_sha256",
    "related_ids",
)


def _text(value, limit=512):
    require(type(value) is str and 0 < len(value) <= limit)
    require(all(32 <= ord(c) < 127 for c in value) and not value.startswith("/"))


def _bool(value):
    require(type(value) is bool)


def _count(value):
    require(type(value) is int and 0 <= value <= 2**31 - 1)


def _metadata(entry, fields):
    keys(entry, fields)
    owner(entry["owner"])
    digest(entry["reason_sha256"])
    review(entry["review_ref"])


def _pairs(items):
    result = {}
    for key, value in items:
        require(key not in result)
        result[key] = value
    return result


def validate_report(raw):
    """Validate consumed v1 grammar and counters, never trust historical enforcement."""
    keys(
        raw,
        (
            "governance_report_schema_version",
            "policy",
            "evaluation",
            "observations",
            "waivers",
            "gate",
            "metrics",
            "comparison",
            "limitations",
        ),
    )
    require(
        type(raw["governance_report_schema_version"]) is int
        and raw["governance_report_schema_version"] == 1
    )
    p = raw["policy"]
    keys(p, ("id", "owner", "sha256", "fail_on", "on_inconclusive", "rule_policies"))
    token(p["id"])
    owner(p["owner"])
    digest(p["sha256"])
    require(type(p["fail_on"]) is str and p["fail_on"] in SEVERITIES)
    require(p["on_inconclusive"] in ("fail", "warn"))
    for r in array(p["rule_policies"], 128):
        _metadata(
            r, ("target", "rule_id", "severity", "owner", "reason_sha256", "review_ref", "used")
        )
        token(r["target"])
        token(r["rule_id"])
        require(r["severity"] in SEVERITIES)
        _bool(r["used"])
    require(
        len({(r["target"], r["rule_id"]) for r in p["rule_policies"]}) == len(p["rule_policies"])
    )
    evaluation = raw["evaluation"]
    keys(evaluation, ("as_of_utc_date", "subjects"))
    iso_date(evaluation["as_of_utc_date"])
    subjects = array(evaluation["subjects"], 16)
    require(len(subjects) >= 1)
    for s in subjects:
        keys(
            s,
            (
                "id",
                "kind",
                "repositories",
                "config_sha256",
                "review_severity",
                "require_architecture",
                "scope",
                "evaluated",
                "complete",
                "limitations",
            ),
        )
        token(s["id"])
        require(s["kind"] in ("repository", "workspace", "derived"))
        digest(s["config_sha256"], nullable=True)
        require(s["review_severity"] is None or s["review_severity"] in SEVERITIES)
        require((s["kind"] == "repository") == (s["review_severity"] is None))
        _bool(s["require_architecture"])
        _bool(s["evaluated"])
        _bool(s["complete"])
        for r in array(s["repositories"], 8):
            keys(r, ("alias", "repository_id", "identity_basis", "git_head", "git_dirty"))
            if r["alias"] is not None:
                token(r["alias"])
            repo_value(r["repository_id"])
            token(r["identity_basis"])
            from context_integrity.derived_models import head_value

            head_value(r["git_head"])
            require(r["git_dirty"] is None or type(r["git_dirty"]) is bool)
        scope = s["scope"]
        require(type(scope) is dict and scope.get("kind") == s["kind"])
        if not s["evaluated"]:
            keys(scope, ("kind",))
        elif s["kind"] == "repository":
            keys(
                scope, ("kind", "change_scope", "base_revision", "target_revision", "architecture")
            )
            require(scope["change_scope"] in ("working_tree", "git_range", "unavailable"))
            head_value(scope["base_revision"])
            head_value(scope["target_revision"])
            architecture = scope["architecture"]
            keys(architecture, ("evaluation_status", "invariants_declared", "provider"))
            require(architecture["evaluation_status"] in ("evaluated", "not_evaluated"))
            _count(architecture["invariants_declared"])
            provider = architecture["provider"]
            if provider is not None:
                keys(
                    provider,
                    (
                        "id",
                        "version",
                        "derivation",
                        "coverage_incomplete",
                        "coverage_signals",
                        "warning_categories",
                    ),
                )
                for field in ("id", "version", "derivation"):
                    token(provider[field])
                _bool(provider["coverage_incomplete"])
                require(
                    type(provider["coverage_signals"]) is dict
                    and len(provider["coverage_signals"]) <= 128
                )
                for key, value in provider["coverage_signals"].items():
                    token(key)
                    require(type(value) in (int, bool) and 0 <= value <= 2**63 - 1)
                for code in array(provider["warning_categories"], 4):
                    token(code)
        elif s["kind"] == "workspace":
            keys(scope, ("kind", "checks_declared"))
            _count(scope["checks_declared"])
        else:
            keys(
                scope,
                (
                    "kind",
                    "receipt",
                    "artifact_id",
                    "artifact_path",
                    "provenance_scope",
                    "receipts_observed",
                ),
            )
            path_value(scope["receipt"])
            path_value(scope["artifact_path"])
            token(scope["artifact_id"])
            require(scope["provenance_scope"] in ("declared", "compiler_selection"))
            _count(scope["receipts_observed"])
        for value in array(s["limitations"], 32):
            token(value)
    ids = {s["id"] for s in subjects}
    require(len(ids) == len(subjects))
    observations = array(raw["observations"], MAX_OBSERVATIONS)
    evidence_count = 0
    for o in observations:
        keys(o, OBSERVATION_KEYS)
        require(type(o["target"]) is str and o["target"] in ids)
        for field in ("rule_id", "code", "signal"):
            token(o[field])
        _text(o["entity"], 1024)
        require(o["effect"] in ("finding", "uncertainty", "caveat", "observation"))
        require(o["intrinsic_severity"] is None or o["intrinsic_severity"] in SEVERITIES)
        if o["effect"] == "finding":
            require(o["effective_severity"] in SEVERITIES)
        else:
            require(
                o["effective_severity"] is None
                and o["fingerprint"] is None
                and o["waiver_id"] is None
                and not o["blocking"]
            )
        owner(o["owner"])
        require(o["owner_basis"] in ("policy", "rule_policy"))
        digest(o["material_sha256"], nullable=True)
        digest(o["pinned_sha256"], nullable=True)
        digest(o["observed_sha256"], nullable=True)
        for value in array(o["related_ids"], 256):
            token(value)
        digest(o["fingerprint"], nullable=True)
        for value in array(o["reasons"], 128):
            _text(value, 256)
        for field in ("waiver_eligible", "blocking"):
            _bool(o[field])
        require(o["waiver_eligible"] == (o["fingerprint"] is not None))
        if o["waiver_id"] is not None:
            token(o["waiver_id"])
        evidence = array(o["evidence"], MAX_EVIDENCE)
        evidence_count += len(evidence)
        require(evidence_count <= MAX_EVIDENCE)
        for e in evidence:
            keys(e, ("repository_id", "path", "state", "sha256", "basis"))
            repo_value(e["repository_id"])
            path_value(e["path"])
            require(
                e["state"]
                in ("observed", "missing", "unobservable", "too_large", "budget_exceeded")
            )
            digest(e["sha256"], nullable=True)
            require((e["state"] == "observed") == (e["sha256"] is not None))
            token(e["basis"])
    subject_map = {s["id"]: s for s in subjects}
    overrides = {(r["target"], r["rule_id"]): r for r in p["rule_policies"]}
    require(all(r["target"] in ids for r in p["rule_policies"]))
    for o in observations:
        subject = subject_map[o["target"]]
        require(
            all(
                e["repository_id"] in {r["repository_id"] for r in subject["repositories"]}
                for e in o["evidence"]
            )
        )
        if o["fingerprint"] is not None:
            require(o["effect"] == "finding" and o["material_sha256"] is not None)
            require(
                o["fingerprint"]
                == fingerprint(
                    {
                        "fingerprint_version": 1,
                        "target": {"id": subject["id"], "kind": subject["kind"]},
                        "repositories": sorted(r["repository_id"] for r in subject["repositories"]),
                        "rule_id": o["rule_id"],
                        "code": o["code"],
                        "entity": o["entity"],
                        "signal": o["signal"],
                        "material_sha256": o["material_sha256"],
                        "evidence": o["evidence"],
                    }
                )
            )
        override = overrides.get((o["target"], o["rule_id"])) if o["effect"] == "finding" else None
        require(o["owner_basis"] == ("rule_policy" if override else "policy"))
        require(o["owner"] == (override["owner"] if override else p["owner"]))
        if o["effect"] == "finding":
            require(
                o["effective_severity"]
                == (
                    override["severity"]
                    if override
                    else o["intrinsic_severity"] or subject["review_severity"]
                )
            )
    waivers = array(raw["waivers"], 256)
    for w in waivers:
        _metadata(
            w,
            (
                "id",
                "target",
                "finding_fingerprint",
                "status",
                "owner",
                "reason_sha256",
                "review_ref",
                "expires_on",
            ),
        )
        token(w["id"])
        require(type(w["target"]) is str and w["target"] in ids)
        digest(w["finding_fingerprint"])
        iso_date(w["expires_on"])
        require(w["status"] in ("expired", "unused", "ambiguous", "applied"))
    require(len({w["id"] for w in waivers}) == len(waivers))
    require(len({(w["target"], w["finding_fingerprint"]) for w in waivers}) == len(waivers))
    matches = Counter((o["target"], o["fingerprint"]) for o in observations if o["fingerprint"])
    active = {}
    evaluation_date = iso_date(evaluation["as_of_utc_date"])
    for w in waivers:
        count = matches[(w["target"], w["finding_fingerprint"])]
        expected = (
            "expired"
            if evaluation_date > iso_date(w["expires_on"])
            else "unused"
            if not count
            else "ambiguous"
            if count != 1
            else "applied"
        )
        require(w["status"] == expected)
        if expected == "applied":
            active[(w["target"], w["finding_fingerprint"])] = w["id"]
    for o in observations:
        require(o["waiver_id"] == active.get((o["target"], o["fingerprint"])))
        blocking = (
            o["effect"] == "finding"
            and o["waiver_id"] is None
            and SEVERITIES.index(o["effective_severity"]) >= SEVERITIES.index(p["fail_on"])
        )
        require(o["blocking"] == blocking)
    require(raw["metrics"] == metrics(observations, subjects))
    # Equality alone would accept bool-as-integer in counters; check leaf types too.
    for value in raw["metrics"].values():
        for number in value.values() if type(value) is dict else (value,):
            _count(number)
    require(raw["gate"] == gate_for(p, observations))
    _count(raw["gate"]["exit_code"])
    _bool(raw["gate"]["has_blocking_findings"])
    _bool(raw["gate"]["has_incomplete_coverage"])
    for s in subjects:
        require(
            s["complete"]
            == (
                not any(
                    o["effect"] == "uncertainty" and o["target"] == s["id"] for o in observations
                )
            )
        )
    comparison = raw["comparison"]
    require(type(comparison) is dict)
    status = comparison.get("status")
    if status == "not_requested":
        keys(comparison, ("status",))
    elif status == "incomparable":
        keys(comparison, ("status", "reasons"))
        for code in array(comparison["reasons"], 8):
            token(code)
    elif status == "comparable":
        keys(comparison, ("status", "metric_deltas", "added", "removed", "persisting"))
        for name in ("added", "removed", "persisting"):
            for value in array(comparison[name], MAX_OBSERVATIONS):
                digest(value)
        require(
            type(comparison["metric_deltas"]) is dict
            and set(comparison["metric_deltas"]) == set(raw["metrics"])
        )
        for value in comparison["metric_deltas"].values():
            values = value.values() if type(value) is dict else (value,)
            for number in values:
                require(type(number) is int and abs(number) <= 2**31 - 1)
    else:
        require(False)
    for value in array(raw["limitations"], 32):
        token(value)


def load_baseline(path):
    try:
        data = read_input(path, MAX_REPORT_BYTES)
        raw = json.loads(data, object_pairs_hook=_pairs, parse_constant=lambda _: require(False))
        require(type(raw) is dict)
        version = raw.get("governance_report_schema_version")
        # Unsupported integer versions are explicitly incomparable, never consumed as v1.
        if type(version) is int and version != 1:
            return {"governance_report_schema_version": version}
        validate_report(raw)
        return raw
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError, OverflowError) as exc:
        raise GovernanceError("invalid_governance_baseline") from exc


def compare(report, previous):
    if previous["governance_report_schema_version"] != 1:
        return {"status": "incomparable", "reasons": ["unsupported_schema"]}
    reasons = []
    if report["policy"]["id"] != previous["policy"]["id"]:
        reasons.append("policy_id_changed")
    if report["policy"]["sha256"] != previous["policy"]["sha256"]:
        reasons.append("policy_hash_changed")

    def scopes(value):
        return [
            (
                s["id"],
                s["kind"],
                sorted(r["repository_id"] for r in s["repositories"]),
                s["scope"].get("change_scope"),
                s["scope"].get("receipt"),
                s["config_sha256"] if s["kind"] == "workspace" else None,
            )
            for s in value["evaluation"]["subjects"]
        ]

    if scopes(report) != scopes(previous):
        reasons.append("target_repository_scope_changed")
    if any(not s["evaluated"] for v in (report, previous) for s in v["evaluation"]["subjects"]):
        reasons.append("scope_unobserved")
    if reasons:
        return {"status": "incomparable", "reasons": reasons}
    deltas = {}
    for key, value in report["metrics"].items():
        old = previous["metrics"][key]
        deltas[key] = (
            {
                name: value.get(name, 0) - old.get(name, 0)
                for name in sorted(value.keys() | old.keys())
            }
            if type(value) is dict
            else value - old
        )
    current = {o["fingerprint"] for o in report["observations"] if o["fingerprint"]}
    old = {o["fingerprint"] for o in previous["observations"] if o["fingerprint"]}
    return {
        "status": "comparable",
        "metric_deltas": deltas,
        "added": sorted(current - old),
        "removed": sorted(old - current),
        "persisting": sorted(current & old),
    }


def render_report(report, *, as_json=False):
    try:
        validate_report(report)
        prefix = (
            ""
            if as_json
            else (
                f"Governance: {report['gate']['outcome']} (exit {report['gate']['exit_code']})\n"
                f"Blocking: {report['metrics']['blocking']}; "
                f"waived: {report['metrics']['waived']}; "
                f"coverage gaps: {report['metrics']['coverage_gaps']}\n"
                "Declared scope only; no semantic proof. Complete evidence follows.\n"
            )
        )
        size = len(prefix) + 1
        encoder = json.JSONEncoder(sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False)
        for chunk in encoder.iterencode(report):
            size += len(chunk)
            if size > MAX_REPORT_BYTES:
                raise GovernanceError("governance_report_limit_exceeded")
        return prefix + canonical_json(report)
    except GovernanceError:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError) as exc:
        raise GovernanceError("invalid_governance_report") from exc


def publish_report(roots, output, rendered, *, forbidden=()):
    try:
        absolute = output.absolute()
        parent = safe_directory(absolute.parent)
        path_value(absolute.name)
        destination = parent / absolute.name
        for root in roots:
            if parent == root or root in parent.parents:
                raise DerivedOutputError("governance_output_must_be_outside_repositories")
        if destination in forbidden:
            raise DerivedOutputError("governance_output_input_collision")
        write_outputs(
            Path("/"), ((str(destination).removeprefix("/"), rendered.encode()),), forbidden=set()
        )
    except (OSError, ValueError) as exc:
        raise DerivedOutputError("governance_output_path_unsafe") from exc
