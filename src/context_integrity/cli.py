"""Command-line adapter for local context inventories."""

from dataclasses import replace
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from context_integrity import __version__
from context_integrity.acquisition import is_context_candidate, normalize_path
from context_integrity.authority import effective_policies, resolve_authority
from context_integrity.claims import claims_overview
from context_integrity.compiler import compile_context
from context_integrity.configuration import ConfigurationError
from context_integrity.context_engine import ContextEngineProvider
from context_integrity.contracts import effective_contracts, resolve_contract, validate_contract
from context_integrity.derived import (
    capture_receipt,
    check_receipt,
    compiler_receipt,
    render_result,
)
from context_integrity.derived_models import (
    Derivation,
    ReceiptError,
    render_receipt,
    render_receipt_text,
)
from context_integrity.derived_output import DerivedOutputError, output_path, write_outputs
from context_integrity.evidence import EvidenceContextRequest, EvidenceProviderError
from context_integrity.integrity import IntegrityEvaluationError, integrity_overview
from context_integrity.inventory import inventory_repository
from context_integrity.lifecycle import lifecycle_overview
from context_integrity.models import AuthorityPolicy, InventoryManifest
from context_integrity.relations import EvidenceRelationRequest
from context_integrity.rendering import (
    render_authority_json,
    render_authority_text,
    render_claims_json,
    render_claims_text,
    render_compiled_context_json,
    render_compiled_context_text,
    render_contract_validation_json,
    render_contract_validation_text,
    render_contracts,
    render_explanation,
    render_integrity_json,
    render_integrity_text,
    render_json,
    render_lifecycle_json,
    render_lifecycle_text,
    render_policy,
    render_policy_list,
    render_text,
)
from context_integrity.repository import RepositoryContext, RepositoryError, discover_repository

app = typer.Typer(
    name="context-integrity",
    help="Inspect and validate software-development context.",
    no_args_is_help=True,
)


class OutputFormat(StrEnum):
    TEXT = "text"
    JSON = "json"


def load_inventory(
    path: Path, *, bounded: bool = False
) -> tuple[RepositoryContext, InventoryManifest]:
    try:
        context = discover_repository(path)
        return context, inventory_repository(
            context,
            max_observation_bytes=64 * 1024 * 1024 if bounded else None,
            max_sources=4096 if bounded else None,
        )
    except ConfigurationError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(6) from exc
    except RepositoryError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(3) from exc


@app.command()
def version() -> None:
    """Print the installed Context Integrity version."""
    typer.echo(__version__)


@app.command()
def scan(
    path: Annotated[Path, typer.Argument(help="Repository or directory to scan.")] = Path("."),
    format: Annotated[OutputFormat, typer.Option("--format")] = OutputFormat.TEXT,
    output: Annotated[Path | None, typer.Option(help="Write output to this file.")] = None,
    summary_only: Annotated[bool, typer.Option(help="Omit the text source table.")] = False,
    include_runtime_meta: Annotated[bool, typer.Option()] = False,
    fail_on_warning: Annotated[bool, typer.Option()] = False,
) -> None:
    """Inventory context sources with provisional deterministic classifications."""
    context, manifest = load_inventory(path)
    runtime = (
        {
            "resolved_root": str(context.root),
            "observed_at": datetime.now(UTC).isoformat(),
            "application_version": __version__,
        }
        if include_runtime_meta
        else None
    )
    rendered = (
        render_json(manifest, runtime)
        if format == OutputFormat.JSON
        else render_text(manifest, summary_only)
    )
    if output:
        try:
            output.write_text(rendered, encoding="utf-8")
        except (OSError, ValueError) as exc:
            typer.echo("Output file could not be written.", err=True)
            raise typer.Exit(4) from exc
    else:
        typer.echo(rendered, nl=False)
    if fail_on_warning and manifest.warnings:
        raise typer.Exit(5)


@app.command()
def explain(
    source_path: Annotated[str, typer.Argument(help="Repository-relative source path to explain.")],
    root: Annotated[Path, typer.Option(help="Repository or directory to scan.")] = Path("."),
) -> None:
    """Explain classification rules and observed revision for one inventoried source."""
    try:
        path = normalize_path(source_path)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    _, manifest = load_inventory(root)
    source = next((s for s in manifest.sources if s.path == path), None)
    if source is None:
        typer.echo("Source is not an inventoried context candidate.", err=True)
        raise typer.Exit(2)
    entry = next(e for e in lifecycle_overview(manifest).sources if e.source.path == path)
    typer.echo(render_explanation(source, entry), nl=False)
    for warning in manifest.warnings:
        if warning.path in {None, path}:
            typer.echo(f"Warning: {warning.code}: {warning.message}")


authority_app = typer.Typer(
    help="Inspect question-specific source-role authority.", no_args_is_help=True
)
app.add_typer(authority_app, name="authority")


def requested_policy(manifest: InventoryManifest, policy_id: str) -> AuthorityPolicy:
    policy = next(
        (p for p in effective_policies(manifest.repository_config) if p.id == policy_id), None
    )
    if policy is None:
        raise typer.BadParameter("Unknown authority policy ID.")
    return policy


@authority_app.command("list")
def authority_list(
    path: Annotated[Path, typer.Argument()] = Path("."),
    format: Annotated[OutputFormat, typer.Option("--format")] = OutputFormat.TEXT,
) -> None:
    """List built-in and repository-defined policies."""
    _, manifest = load_inventory(path)
    typer.echo(
        render_policy_list(
            effective_policies(manifest.repository_config), format == OutputFormat.JSON
        ),
        nl=False,
    )


@authority_app.command("show")
def authority_show(
    policy_id: Annotated[str, typer.Argument()],
    path: Annotated[Path, typer.Argument()] = Path("."),
    format: Annotated[OutputFormat, typer.Option("--format")] = OutputFormat.TEXT,
) -> None:
    """Show ordered policy tiers and provenance."""
    _, manifest = load_inventory(path)
    typer.echo(
        render_policy(requested_policy(manifest, policy_id), format == OutputFormat.JSON), nl=False
    )


@authority_app.command("resolve")
def authority_resolve(
    policy_id: Annotated[str, typer.Argument()],
    path: Annotated[Path, typer.Argument()] = Path("."),
    format: Annotated[OutputFormat, typer.Option("--format")] = OutputFormat.TEXT,
    output: Annotated[Path | None, typer.Option()] = None,
) -> None:
    """Resolve observed source-role precedence; never claim correctness or agreement."""
    _, manifest = load_inventory(path)
    resolution = resolve_authority(manifest, requested_policy(manifest, policy_id))
    rendered = (
        render_authority_json(resolution)
        if format == OutputFormat.JSON
        else render_authority_text(resolution)
    )
    if output:
        try:
            output.write_text(rendered, encoding="utf-8")
        except (OSError, ValueError) as exc:
            typer.echo("Output file could not be written.", err=True)
            raise typer.Exit(4) from exc
    else:
        typer.echo(rendered, nl=False)


lifecycle_app = typer.Typer(help="Inspect explicit source lifecycle.", no_args_is_help=True)
app.add_typer(lifecycle_app, name="lifecycle")


def _lifecycle_output(
    manifest: InventoryManifest,
    format: OutputFormat,
    output: Path | None,
    source_path: str | None = None,
) -> None:
    overview = lifecycle_overview(manifest)
    if source_path is not None:
        try:
            normalized = normalize_path(source_path)
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc
        entries = tuple(e for e in overview.sources if e.source.path == normalized)
        if not entries:
            typer.echo("Source is not an inventoried context candidate.", err=True)
            raise typer.Exit(2)
        # Keep the same schema with one source and its direct relations only.
        edges = tuple(
            e for e in overview.supersession if normalized in {e.source.path, e.superseded_by.path}
        )
        overview = replace(overview, sources=entries, supersession=edges)
    rendered = (
        render_lifecycle_json(overview)
        if format == OutputFormat.JSON
        else render_lifecycle_text(overview, detail=source_path is not None)
    )
    if output:
        try:
            output.write_text(rendered, encoding="utf-8")
        except (OSError, ValueError) as exc:
            typer.echo("Output file could not be written.", err=True)
            raise typer.Exit(4) from exc
    else:
        typer.echo(rendered, nl=False)


@lifecycle_app.command("list")
def lifecycle_list(
    path: Annotated[Path, typer.Argument()] = Path("."),
    format: Annotated[OutputFormat, typer.Option("--format")] = OutputFormat.TEXT,
    output: Annotated[Path | None, typer.Option()] = None,
) -> None:
    """List effective lifecycle, provenance, and direct supersession."""
    _, manifest = load_inventory(path)
    _lifecycle_output(manifest, format, output)


@lifecycle_app.command("show")
def lifecycle_show(
    source_path: Annotated[str, typer.Argument()],
    path: Annotated[Path, typer.Argument()] = Path("."),
    format: Annotated[OutputFormat, typer.Option("--format")] = OutputFormat.TEXT,
    output: Annotated[Path | None, typer.Option()] = None,
) -> None:
    """Inspect one source's lifecycle and revision without resolving an authority policy."""
    _, manifest = load_inventory(path)
    _lifecycle_output(manifest, format, output, source_path)


claims_app = typer.Typer(help="Inspect explicit claims and provenance.", no_args_is_help=True)
app.add_typer(claims_app, name="claims")


def _claims_output(
    manifest: InventoryManifest,
    format: OutputFormat,
    output: Path | None,
    claim_id: str | None = None,
) -> None:
    try:
        overview = claims_overview(manifest)
    except ConfigurationError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(6) from exc
    if claim_id is not None:
        claims = tuple(c for c in overview.claims if c.id == claim_id)
        if not claims:
            typer.echo("Unknown claim ID.", err=True)
            raise typer.Exit(2)
        # Global observation warnings remain visible; claim diagnostics are scoped.
        diagnostics = tuple(d for d in overview.diagnostics if d.claim_id == claim_id)
        overview = replace(overview, claims=claims, diagnostics=diagnostics)
    rendered = (
        render_claims_json(overview)
        if format == OutputFormat.JSON
        else render_claims_text(overview, detail=claim_id is not None)
    )
    if output:
        try:
            output.write_text(rendered, encoding="utf-8")
        except (OSError, ValueError) as exc:
            typer.echo("Output file could not be written.", err=True)
            raise typer.Exit(4) from exc
    else:
        typer.echo(rendered, nl=False)


@claims_app.command("list")
def claims_list(
    path: Annotated[Path, typer.Argument()] = Path("."),
    format: Annotated[OutputFormat, typer.Option("--format")] = OutputFormat.TEXT,
    output: Annotated[Path | None, typer.Option()] = None,
) -> None:
    """List explicit claims, independent validity, and provenance completeness."""
    _, manifest = load_inventory(path)
    _claims_output(manifest, format, output)


@claims_app.command("show")
def claims_show(
    claim_id: Annotated[str, typer.Argument()],
    path: Annotated[Path, typer.Argument()] = Path("."),
    format: Annotated[OutputFormat, typer.Option("--format")] = OutputFormat.TEXT,
    output: Annotated[Path | None, typer.Option()] = None,
) -> None:
    """Show one claim's declaration and dependency revisions without verifying its assertion."""
    _, manifest = load_inventory(path)
    _claims_output(manifest, format, output, claim_id)


@app.command()
def check(
    path: Annotated[Path, typer.Argument()] = Path("."),
    diff: Annotated[str | None, typer.Option(help="Local two-commit range BASE..TARGET.")] = None,
    format: Annotated[OutputFormat, typer.Option("--format")] = OutputFormat.TEXT,
    output: Annotated[Path | None, typer.Option()] = None,
    evidence_provider: Annotated[str | None, typer.Option()] = None,
    context_engine_bin: Annotated[str | None, typer.Option()] = None,
) -> None:
    """Evaluate deterministic integrity review signals; findings do not fail the command."""
    if evidence_provider not in {None, "context-engine"}:
        raise typer.BadParameter("Unknown evidence provider.")
    if context_engine_bin is not None and evidence_provider is None:
        raise typer.BadParameter("Evidence options require --evidence-provider.")
    context, manifest = load_inventory(path)
    try:
        relations = None
        if evidence_provider:
            relations = ContextEngineProvider(context_engine_bin or "ctx").relations(
                EvidenceRelationRequest(context.root, manifest.repository)
            )
        overview = integrity_overview(context, manifest, diff, relation_batch=relations)
    except EvidenceProviderError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(7) from exc
    except IntegrityEvaluationError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(7) from exc
    except ConfigurationError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(6) from exc
    except RepositoryError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(3) from exc
    rendered = (
        render_integrity_json(overview)
        if format == OutputFormat.JSON
        else render_integrity_text(overview)
    )
    if output:
        try:
            output.write_text(rendered, encoding="utf-8")
        except (OSError, ValueError) as exc:
            typer.echo("Output file could not be written.", err=True)
            raise typer.Exit(4) from exc
    else:
        typer.echo(rendered, nl=False)


contracts_app = typer.Typer(
    help="Inspect and validate explicit context packages.", no_args_is_help=True
)
app.add_typer(contracts_app, name="contracts")


def _write_contract_output(rendered: str, output: Path | None) -> None:
    if output is None:
        typer.echo(rendered, nl=False)
        return
    try:
        output.write_text(rendered, encoding="utf-8")
    except (OSError, ValueError) as exc:
        typer.echo("Output file could not be written.", err=True)
        raise typer.Exit(4) from exc


@contracts_app.command("list")
def contracts_list(
    path: Annotated[Path, typer.Argument()] = Path("."),
    format: Annotated[OutputFormat, typer.Option("--format")] = OutputFormat.TEXT,
    output: Annotated[Path | None, typer.Option()] = None,
) -> None:
    """List repository-defined contracts."""
    _, manifest = load_inventory(path)
    _write_contract_output(
        render_contracts(
            effective_contracts(manifest.repository_config), format == OutputFormat.JSON
        ),
        output,
    )


@contracts_app.command("show")
def contracts_show(
    contract_id: Annotated[str, typer.Argument()],
    path: Annotated[Path, typer.Argument()] = Path("."),
    format: Annotated[OutputFormat, typer.Option("--format")] = OutputFormat.TEXT,
    output: Annotated[Path | None, typer.Option()] = None,
) -> None:
    """Show a contract's explicit selectors and cardinalities."""
    _, manifest = load_inventory(path)
    try:
        contract = resolve_contract(manifest.repository_config, contract_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    _write_contract_output(
        render_contracts((contract,), format == OutputFormat.JSON, detail=True),
        output,
    )


@contracts_app.command("validate")
def contracts_validate(
    contract_id: Annotated[str, typer.Argument()],
    path: Annotated[Path, typer.Argument()] = Path("."),
    source: Annotated[list[str] | None, typer.Option("--source")] = None,
    format: Annotated[OutputFormat, typer.Option("--format")] = OutputFormat.TEXT,
    output: Annotated[Path | None, typer.Option()] = None,
) -> None:
    """Validate supplied inventory sources; findings retain exit zero."""
    _, manifest = load_inventory(path)
    try:
        contract = resolve_contract(manifest.repository_config, contract_id)
        overview = validate_contract(manifest, contract, tuple(source or ()))
    except ValueError as exc:
        raise typer.BadParameter("Unknown contract or invalid package source path.") from exc
    rendered = (
        render_contract_validation_json(overview)
        if format == OutputFormat.JSON
        else render_contract_validation_text(overview)
    )
    _write_contract_output(rendered, output)


@app.command("compile")
def compile_command(
    contract_id: Annotated[str, typer.Argument()],
    path: Annotated[Path, typer.Argument()] = Path("."),
    task: Annotated[str | None, typer.Option()] = None,
    budget_bytes: Annotated[int | None, typer.Option(min=1)] = None,
    format: Annotated[OutputFormat, typer.Option("--format")] = OutputFormat.TEXT,
    output: Annotated[Path | None, typer.Option()] = None,
    receipt_output: Annotated[Path | None, typer.Option()] = None,
    evidence_provider: Annotated[str | None, typer.Option()] = None,
    context_engine_bin: Annotated[str | None, typer.Option()] = None,
    evidence_budget_bytes: Annotated[int | None, typer.Option(min=1, max=16777216)] = None,
    evidence_change: Annotated[str | None, typer.Option()] = None,
) -> None:
    """Compile deterministic bounded context; incomplete results retain exit zero."""
    if receipt_output is not None and (format != OutputFormat.JSON or output is None):
        raise typer.BadParameter("--receipt-output requires --format json --output.")
    if evidence_provider not in {None, "context-engine"}:
        raise typer.BadParameter("Unknown evidence provider.")
    if evidence_provider is None and any(
        v is not None for v in (context_engine_bin, evidence_budget_bytes, evidence_change)
    ):
        raise typer.BadParameter("Evidence options require --evidence-provider.")
    if evidence_provider and (task is None or not task.strip()):
        raise typer.BadParameter("Provider compilation requires nonblank --task.")
    context, manifest = load_inventory(path, bounded=receipt_output is not None)
    try:
        contract = resolve_contract(manifest.repository_config, contract_id)
        evidence = None
        if evidence_provider:
            evidence = ContextEngineProvider(context_engine_bin or "ctx").context_candidates(
                EvidenceContextRequest(
                    context.root,
                    manifest.repository,
                    task,
                    evidence_budget_bytes if evidence_budget_bytes is not None else 1024 * 1024,
                    evidence_change,
                )
            )
        compiled = compile_context(
            manifest, contract, task=task, budget_bytes=budget_bytes, evidence=evidence
        )
    except EvidenceProviderError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(7) from exc
    except ConfigurationError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(6) from exc
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    rendered = (
        render_compiled_context_json(compiled)
        if format == OutputFormat.JSON
        else render_compiled_context_text(compiled)
    )
    if receipt_output is not None:
        try:
            artifact_path = output_path(context.root, output)
            receipt_path = output_path(context.root, receipt_output)
            # New inventory candidates could change the very selection being pinned.
            if is_context_candidate(artifact_path) or is_context_candidate(receipt_path):
                raise DerivedOutputError(
                    "Compiler receipt outputs must use non-inventory paths (for example .json)."
                )
            receipt = compiler_receipt(
                context, manifest, compiled, artifact_path, rendered.encode()
            )
            forbidden = (
                {s.path for s in manifest.sources}
                | {p.path for p in receipt.dependencies}
                | {".context-integrity.toml"}
            )
            write_outputs(
                context.root,
                (
                    (artifact_path, rendered.encode()),
                    (receipt_path, render_receipt(receipt).encode()),
                ),
                forbidden=forbidden,
            )
        except ReceiptError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(6) from exc
        except DerivedOutputError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(4) from exc
    else:
        _write_contract_output(rendered, output)


derived_app = typer.Typer(
    help="Capture and recheck declared derived-context provenance.", no_args_is_help=True
)
app.add_typer(derived_app, name="derived")


@derived_app.command("capture")
def derived_capture(
    artifact: Annotated[str, typer.Argument()],
    path: Annotated[Path, typer.Argument()] = Path("."),
    artifact_id: Annotated[str, typer.Option("--id")] = "derived-context",
    kind: Annotated[str, typer.Option()] = "summary",
    derivation: Annotated[str, typer.Option()] = "manual",
    producer: Annotated[str, typer.Option()] = "user",
    producer_version: Annotated[str | None, typer.Option()] = None,
    depends_on: Annotated[list[str] | None, typer.Option()] = None,
    upstream_receipt: Annotated[list[str] | None, typer.Option()] = None,
    receipt_output: Annotated[Path, typer.Option()] = ...,
) -> None:
    """Write an explicit receipt of actual artifact/input bytes; never replace a file."""
    context, manifest = load_inventory(path, bounded=True)
    try:
        receipt_path = output_path(context.root, receipt_output)
        if is_context_candidate(receipt_path):
            raise DerivedOutputError(
                "Receipt outputs must use non-inventory paths (for example .json)."
            )
        receipt = capture_receipt(
            context,
            manifest,
            artifact,
            artifact_id=artifact_id,
            kind=kind,
            derivation=Derivation(derivation, producer, producer_version),
            depends_on=tuple(depends_on or ()),
            upstream_receipts=tuple(upstream_receipt or ()),
            receipt_path=receipt_path,
        )
        write_outputs(
            context.root,
            ((receipt_path, render_receipt(receipt).encode()),),
            forbidden={
                artifact,
                ".context-integrity.toml",
                *(depends_on or ()),
                *(upstream_receipt or ()),
            },
        )
    except ReceiptError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(6) from exc
    except DerivedOutputError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(4) from exc
    typer.echo(render_receipt_text(receipt), nl=False)
    typer.echo(f"Receipt: {receipt_path}")


@derived_app.command("check")
def derived_check(
    receipt: Annotated[str, typer.Argument()],
    path: Annotated[Path, typer.Argument()] = Path("."),
    format: Annotated[OutputFormat, typer.Option("--format")] = OutputFormat.TEXT,
    output: Annotated[Path | None, typer.Option()] = None,
) -> None:
    """Recheck pinned inputs; leave artifact and receipt bytes untouched."""
    try:
        context = discover_repository(path)
        result, inputs = check_receipt(context, receipt)
        rendered = render_result(result, format == OutputFormat.JSON)
        if output is None:
            typer.echo(rendered, nl=False)
        else:
            report_path = output_path(context.root, output)
            if is_context_candidate(report_path):
                raise DerivedOutputError(
                    "Report outputs must use non-inventory paths (for example .json)."
                )
            write_outputs(
                context.root,
                ((report_path, rendered.encode()),),
                forbidden=inputs,
            )
    except RepositoryError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(3) from exc
    except ReceiptError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(6) from exc
    except DerivedOutputError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(4) from exc


if __name__ == "__main__":
    app()
