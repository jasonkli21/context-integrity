"""Allowlisted workspace projections and exclusive, root-free publication."""

from hashlib import sha256
from pathlib import Path

from context_integrity.derived import fingerprint
from context_integrity.derived_models import canonical_json, path_value
from context_integrity.derived_output import DerivedOutputError, write_outputs
from context_integrity.models import make_source_id
from context_integrity.workspace_config import safe_directory
from context_integrity.workspace_models import QualifiedSourceRef, aggregate

CAVEATS = ["declared_checks_only", "sequential_non_atomic_observations", "no_semantic_validation"]


def qualified(ref):
    return {"repo_alias": ref.repo_alias, "repository_id": ref.repository_id, "path": ref.path}


def observation(source):
    return {
        "source": qualified(source.ref),
        "state": source.state,
        "source_id": make_source_id(source.ref.repository_id, source.ref.path),
        "content_sha256": source.content_sha256,
        "lifecycle": source.lifecycle,
        "authority": source.authority,
    }


def revision(value):
    return {
        "content_sha256": value.content_sha256,
        "git_head": value.git_head,
        "git_status": value.git_status.value,
        "observed_revision_basis": value.observed_revision_basis,
    }


def claim_observation(value):
    claim = value.claim
    return {
        "claim": {
            "repo_alias": value.ref.repo_alias,
            "repository_id": value.ref.repository_id,
            "claim_id": value.ref.claim_id,
        },
        "validity": claim.validity.value if claim else None,
        "declaration": {
            "claim_type": claim.claim_type,
            "subject": claim.subject,
            "predicate": claim.predicate,
            "scope": claim.scope,
            "value": claim.value,
        }
        if claim
        else None,
        "provenance": {
            "source": qualified(
                QualifiedSourceRef(
                    value.ref.repo_alias, value.ref.repository_id, claim.provenance.path
                )
            ),
            "source_id": claim.provenance.source_id,
            "locator": claim.provenance.locator,
            "extraction_method": claim.provenance.extraction_method,
            "extractor_version": claim.provenance.extractor_version,
            "revision": revision(claim.provenance.revision),
            "provenance_complete": claim.provenance_complete,
        }
        if claim
        else None,
        "dependencies": [
            {
                "source": qualified(
                    QualifiedSourceRef(value.ref.repo_alias, value.ref.repository_id, d.path)
                ),
                "source_id": d.source_id,
                "revision": revision(d.revision) if d.revision else None,
                "resolved": d.resolved,
            }
            for d in claim.dependencies
        ]
        if claim
        else [],
        "sources": [observation(s) for s in value.sources],
        "reasons": [{"code": r} for r in value.reasons],
    }


def finding(value):
    return {
        "id": value.id,
        "rule_id": f"workspace.{value.kind.value}.v1",
        "kind": value.kind.value,
        "evaluation_status": value.evaluation_status,
        "signal": value.signal.value,
        "reasons": [{"code": r} for r in value.reasons],
        "sources": [observation(s) for s in value.sources],
        "claims": [claim_observation(c) for c in value.claims],
        "accepted_sha256": value.accepted_sha256,
    }


def repositories(workspace):
    return [
        {
            "alias": r.alias,
            "repository_id": r.context.repository.id,
            "identity_basis": r.context.repository.identity_basis,
            "git_head": r.context.repository.git_head,
            "git_dirty": r.context.repository.git_dirty,
            "warnings": sorted({w.code for w in r.context.warnings}),
            "limitations": ["local_identity_nonportable"]
            if r.context.repository.identity_basis == "local_fallback"
            else [],
        }
        for r in workspace.repositories
    ]


def check_dict(workspace, findings):
    return {
        "workspace_check_schema_version": 1,
        "manifest_sha256": workspace.spec.manifest_sha256,
        "repositories": repositories(workspace),
        "status": aggregate(findings),
        "coverage": {
            "checks_declared": len(findings),
            "checks_evaluated": sum(f.evaluation_status == "evaluated" for f in findings),
            "limitations": CAVEATS + ([] if findings else ["no_checks_declared"]),
        },
        "findings": [finding(f) for f in findings],
    }


def context_dict(workspace, findings, compilations, task):
    targets = []
    for alias, contract_id, requested_budget, compiled in compilations:
        context = workspace.contexts[alias]

        def ref(path, alias=alias, context=context):
            return qualified(QualifiedSourceRef(alias, context.repository.id, path))

        base = {
            "repo_alias": alias,
            "repository_id": context.repository.id,
            "contract_id": contract_id,
            "requested_budget_bytes": requested_budget,
            "status": "incomplete",
            "config_sha256": None,
            "contract_sha256": None,
            "authority_policies": [],
            "budget": None,
            "selected_sources": [],
            "decisions": [],
            "dependencies": [],
            "validation": [],
            "integrity_status": "not_evaluated",
            "warnings": ["inventory_unavailable"],
            "coverage": "inventory_unavailable",
        }
        if compiled is not None:
            base.update(
                status=compiled.status.value,
                config_sha256=compiled.config_sha256,
                contract_sha256=fingerprint_contract(compiled),
                authority_policies=[
                    {
                        "id": p.id,
                        "version": p.policy_version,
                        "tiers": [list(t.classes) for t in p.tiers],
                    }
                    for p in compiled.authority_policies
                ],
                budget={
                    "configured_bytes": compiled.budget.configured_bytes,
                    "effective_bytes": compiled.budget.effective_bytes,
                    "used_bytes": compiled.budget.used_bytes,
                },
                selected_sources=[
                    {
                        "source": ref(s.path),
                        "source_id": s.id,
                        "revision": revision(s.revision),
                        "kind": s.kind.value,
                        "authority": s.authority_class.value,
                        "lifecycle": s.lifecycle.value,
                        "size_bytes": s.size_bytes,
                        "derivation": "inventory_classification",
                    }
                    for s in compiled.selected_sources
                ],
                decisions=[
                    {
                        "source": ref(d.source.path),
                        "source_id": d.source.id,
                        "revision": revision(d.source.revision),
                        "origin": d.source.origin.value,
                        "derivation": d.source.derivation or "inventory_classification",
                        "decision": d.decision.value,
                        "matched_rule_ids": list(d.matched_rule_ids),
                        "contributing_rule_ids": list(d.contributing_rule_ids),
                        "rule_decisions": [
                            {
                                "rule_id": r.rule_id,
                                "reason": r.reason.value,
                                "authority_policy": r.authority_policy,
                                "tier_index": r.tier_index,
                                "highest_tier_index": r.highest_tier_index,
                                "equal_tier_sources": [ref(p) for p in r.equal_tier_paths],
                                "authority_exclusion": r.authority_exclusion,
                            }
                            for r in d.rule_decisions
                        ],
                    }
                    for d in compiled.decisions
                ],
                dependencies=[
                    {
                        "source": ref(d.path),
                        "source_id": d.source_id,
                        "revision": revision(d.source_revision),
                    }
                    for d in compiled.dependencies
                ],
                validation=[
                    {
                        "code": f.code,
                        "rule_id": f.rule_id,
                        "sources": [ref(p) for p in f.affected_paths],
                    }
                    for f in compiled.validation.findings
                ],
                integrity_status=compiled.integrity_state.evaluation_status.value,
                warnings=sorted({w.code for w in compiled.warnings}),
                coverage="inventory_warnings" if compiled.warnings else "observed_inventory",
            )
        targets.append(base)
    checks = check_dict(workspace, findings)
    complete = all(t["status"] == "complete" for t in targets)
    return {
        "workspace_context_schema_version": 1,
        "manifest_sha256": workspace.spec.manifest_sha256,
        "task_sha256": sha256(task.encode("utf-8")).hexdigest(),
        "repositories": checks["repositories"],
        "selection_complete": complete,
        "checks_status": checks["status"],
        "review_required": checks["status"] == "review_required",
        "status": "incomplete" if not complete else checks["status"],
        "targets": targets,
        "findings": checks["findings"],
        "coverage": checks["coverage"],
        "limitations": ["providers_disabled", "index_not_durable_receipt", "no_global_ranking"],
    }


def fingerprint_contract(compiled):
    from context_integrity.rendering import _contract_v1

    contract = _contract_v1(compiled.contract)
    contract["budget_bytes"] = compiled.contract.budget_bytes
    contract["selection_policy"] = [
        {"id": r.id, "priority": r.priority, "authority_policy": r.authority_policy}
        for r in compiled.contract.rules
    ]
    return fingerprint(contract)


def render_workspace(value: dict, *, as_json: bool) -> str:
    # Text retains the complete structured evidence, with a concise summary heading.
    body = canonical_json(value)
    if as_json:
        return body
    return f"Workspace: {value['status']}\nDeclared checks: {len(value['findings'])}\n\n{body}"


def publish_workspace(workspace, output: Path, rendered: str):
    try:
        absolute = output.absolute()
        parent = safe_directory(absolute.parent)
        path_value(absolute.name)
        for repository in workspace.repositories:
            root = repository.context.root
            if parent == root or root in parent.parents:
                raise DerivedOutputError("workspace_output_must_be_outside_repositories")
        # The parent was verified from /; helper traverses it again from a pinned / FD.
        write_outputs(
            Path("/"),
            ((str(parent / absolute.name).removeprefix("/"), rendered.encode()),),
            forbidden=set(),
        )
    except (OSError, ValueError) as exc:
        raise DerivedOutputError("workspace_output_path_unsafe") from exc
