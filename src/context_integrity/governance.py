"""Explicit local orchestration, evidence fingerprints, independent gate factors."""

from collections import Counter
from dataclasses import asdict
from datetime import date
from hashlib import sha256
from pathlib import Path

from context_integrity.derived import fingerprint
from context_integrity.governance_adapters import (
    bind_repository,
    derived_subject,
    local_provider,
    repository_subject,
    resolve_workspace_subject,
    validate_diff_scope,
    workspace_subject,
)
from context_integrity.governance_models import (
    MAX_EVIDENCE,
    MAX_OBSERVATIONS,
    SEVERITIES,
    GovernanceError,
    Observation,
    Subject,
)


def metrics(observations, subjects):
    findings = [o for o in observations if o["effect"] == "finding"]
    return {
        "targets_requested": len(subjects),
        "targets_evaluated": sum(s["evaluated"] for s in subjects),
        "targets_incomplete": sum(not s["complete"] for s in subjects),
        "findings": len(findings),
        "blocking": sum(o["blocking"] for o in findings),
        "waived": sum(o["waiver_id"] is not None for o in findings),
        "unwaived": sum(o["waiver_id"] is None for o in findings),
        "coverage_gaps": sum(o["effect"] == "uncertainty" for o in observations),
        "by_severity": {v: sum(o["effective_severity"] == v for o in findings) for v in SEVERITIES},
        "by_rule": dict(sorted(Counter(o["rule_id"] for o in findings).items())),
        "by_target": {s["id"]: sum(o["target"] == s["id"] for o in findings) for s in subjects},
        "derived_review_required": len(
            {o["target"] for o in findings if o["rule_id"].startswith("derived.")}
        ),
        "workspace_disagreements": sum(
            o["rule_id"] == "workspace.claim_match.v1" for o in findings
        ),
    }


def gate_for(policy, observations):
    blocking = any(o["blocking"] for o in observations)
    incomplete = any(o["effect"] == "uncertainty" for o in observations)
    code = 8 if blocking else 9 if incomplete and policy["on_inconclusive"] == "fail" else 0
    outcome = (
        "fail"
        if code == 8
        else "inconclusive"
        if code == 9
        else "allow_with_incomplete"
        if incomplete
        else "allow"
    )
    return {
        "outcome": outcome,
        "has_blocking_findings": blocking,
        "has_incomplete_coverage": incomplete,
        "exit_code": code,
    }


def _evaluate(target, parent, roots, identities, diff, provider):
    context = None
    repositories = ()
    try:
        if target.kind == "workspace":
            workspace = resolve_workspace_subject(parent / target.manifest, roots)
            contexts = tuple(r.context for r in workspace.repositories)
        else:
            # Register lexical root even if discovery fails; output cannot enter a failed target.
            roots.add(parent if target.root == "." else parent / target.root)
            context = bind_repository(parent / target.root, target.repository_id)
            contexts = (context,)
        for item in contexts:
            old = identities.setdefault(item.repository.id, item.root)
            if old != item.root:
                raise GovernanceError("repository_identity_collision")
        if target.kind == "workspace":
            return workspace_subject(target, workspace)
        from context_integrity.governance_adapters import descriptor

        repositories = (descriptor(context),)
        if target.kind == "repository":
            return repository_subject(target, context, diff, provider)
        return derived_subject(target, context)
    except GovernanceError:
        raise  # Resource limits cannot produce partial reports.
    except Exception:
        # Deliberately sanitized; all remaining targets are still evaluated.
        return Subject(
            target,
            repositories,
            None,
            {"kind": target.kind},
            (
                Observation(
                    "governance.coverage.v1",
                    "target_evaluation_failed",
                    "target",
                    "not_evaluated",
                    "uncertainty",
                ),
            ),
            ("evaluation_failed", "no_semantic_validation"),
        )


def evaluate(
    policy, parent: Path, *, as_of: date, diffs=None, evidence_provider=False, binary=None
):
    diffs = diffs or {}
    roots, identities = set(), {}
    subjects = []
    observation_count = evidence_count = 0
    provider = local_provider(binary) if evidence_provider else None
    for target in policy.targets:
        subject = _evaluate(target, parent, roots, identities, diffs.get(target.id), provider)
        subjects.append(subject)
        observation_count += len(subject.observations)
        evidence_count += sum(len(o.evidence) for o in subject.observations)
        if observation_count > MAX_OBSERVATIONS or evidence_count > MAX_EVIDENCE:
            raise GovernanceError("governance_observation_limit_exceeded")
    # Recheck every explicit repository range after all other subjects have finished. This catches
    # a checkout change that occurs after that repository's own evaluation but before the report.
    for subject in subjects:
        target = subject.target
        diff = diffs.get(target.id)
        if target.kind != "repository" or diff is None:
            continue
        try:
            context = bind_repository(parent / target.root, target.repository_id)
            changes = validate_diff_scope(context, diff)
        except Exception as exc:
            raise GovernanceError("governance_diff_scope_invalid") from exc
        if (
            not subject.repositories
            or subject.repositories[0]["repository_id"] != context.repository.id
            or subject.scope.get("base_revision") != changes.base_revision
            or subject.scope.get("target_revision") != changes.target_revision
        ):
            raise GovernanceError("governance_diff_scope_invalid")
    rules = {(r.target, r.rule_id): r for r in policy.rule_policies}
    projected, descriptors, used_rules = [], [], set()
    for subject in subjects:
        target = subject.target
        repositories = sorted(
            subject.repositories, key=lambda r: (r["repository_id"], r["alias"] or "")
        )
        descriptors.append(
            {
                "id": target.id,
                "kind": target.kind,
                "repositories": repositories,
                "config_sha256": subject.config_sha256,
                "review_severity": target.review_severity,
                "require_architecture": target.require_architecture,
                "scope": subject.scope,
                "evaluated": not any(
                    o.signal == "not_evaluated" and o.code == "target_evaluation_failed"
                    for o in subject.observations
                ),
                "complete": not any(o.effect == "uncertainty" for o in subject.observations),
                "limitations": list(subject.limitations),
            }
        )
        for observation in subject.observations:
            o = observation
            intrinsic = o.severity
            severity, owner, ownership = None, policy.owner, "policy"
            override = rules.get((target.id, o.rule_id))
            if o.effect == "finding":
                severity = intrinsic or target.review_severity
                if severity not in SEVERITIES:
                    raise GovernanceError("governance_severity_unmapped")
                if override:
                    severity, owner, ownership = override.severity, override.owner, "rule_policy"
                    used_rules.add((target.id, o.rule_id))
            evidence = [asdict(e) for e in o.evidence]
            preimage = {
                "fingerprint_version": 1,
                "target": {"id": target.id, "kind": target.kind},
                "repositories": sorted(r["repository_id"] for r in repositories),
                "rule_id": o.rule_id,
                "code": o.code,
                "entity": o.entity,
                "signal": o.signal,
                "material_sha256": o.material_sha256,
                "evidence": evidence,
            }
            digest = fingerprint(preimage) if o.effect == "finding" and o.waiver_eligible else None
            projected.append(
                {
                    "target": target.id,
                    "rule_id": o.rule_id,
                    "code": o.code,
                    "entity": o.entity,
                    "signal": o.signal,
                    "effect": o.effect,
                    "intrinsic_severity": intrinsic,
                    "effective_severity": severity,
                    "owner": owner,
                    "owner_basis": ownership,
                    "evidence": evidence,
                    "material_sha256": o.material_sha256,
                    "reasons": list(o.reasons),
                    "related_ids": list(o.related_ids),
                    "pinned_sha256": o.pinned_sha256,
                    "observed_sha256": o.observed_sha256,
                    "fingerprint": digest,
                    "waiver_eligible": o.waiver_eligible and o.effect == "finding",
                    "waiver_id": None,
                    "blocking": False,
                }
            )
    matches = Counter((o["target"], o["fingerprint"]) for o in projected if o["fingerprint"])
    finding_by_fingerprint = {
        (o["target"], o["fingerprint"]): o
        for o in projected
        if o["effect"] == "finding" and o["fingerprint"]
    }
    waivers = []
    active = {}
    for waiver in policy.waivers:
        key = waiver.target, waiver.finding_fingerprint
        count = matches[key]
        status = (
            "expired"
            if as_of > waiver.expires_on
            else "unused"
            if not count
            else "ambiguous"
            if count != 1
            else "stale_context"
            if policy.schema_version == 1
            or waiver.approved_severity != finding_by_fingerprint[key]["effective_severity"]
            or waiver.approved_owner != finding_by_fingerprint[key]["owner"]
            or waiver.approved_fail_on != policy.fail_on
            else "applied"
        )
        if status == "applied":
            active[key] = waiver.id
        waivers.append(
            {
                "id": waiver.id,
                "target": waiver.target,
                "finding_fingerprint": waiver.finding_fingerprint,
                "status": status,
                "owner": waiver.owner,
                "reason_sha256": sha256(waiver.reason.encode()).hexdigest(),
                "review_ref": waiver.review_ref,
                "expires_on": waiver.expires_on.isoformat(),
                "approved_severity": waiver.approved_severity,
                "approved_owner": waiver.approved_owner,
                "approved_fail_on": waiver.approved_fail_on,
            }
        )
    for o in projected:
        if o["effect"] == "finding":
            o["waiver_id"] = active.get((o["target"], o["fingerprint"]))
            o["blocking"] = o["waiver_id"] is None and SEVERITIES.index(
                o["effective_severity"]
            ) >= SEVERITIES.index(policy.fail_on)
    projected.sort(
        key=lambda o: (o["target"], o["rule_id"], o["code"], o["entity"], o["fingerprint"] or "")
    )
    policy_info = {
        "schema_version": policy.schema_version,
        "id": policy.id,
        "owner": policy.owner,
        "sha256": policy.sha256,
        "fail_on": policy.fail_on,
        "on_inconclusive": policy.on_inconclusive,
        "rule_policies": [
            {
                "target": r.target,
                "rule_id": r.rule_id,
                "severity": r.severity,
                "owner": r.owner,
                "reason_sha256": sha256(r.reason.encode()).hexdigest(),
                "review_ref": r.review_ref,
                "used": (r.target, r.rule_id) in used_rules,
            }
            for r in policy.rule_policies
        ],
    }
    report = {
        "governance_report_schema_version": 2,
        "policy": policy_info,
        "evaluation": {"as_of_utc_date": as_of.isoformat(), "subjects": descriptors},
        "observations": projected,
        "waivers": waivers,
        "gate": gate_for(policy_info, projected),
        "metrics": metrics(projected, descriptors),
        "comparison": {"status": "not_requested"},
        "limitations": [
            "declared_scope_only",
            "no_semantic_proof",
            "owners_and_reviews_unauthenticated",
            "sequential_non_atomic_observations",
            "prior_report_never_changes_enforcement",
        ],
    }
    return report, roots
