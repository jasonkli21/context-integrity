"""Command-line adapter for local context inventories."""

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from context_integrity import __version__
from context_integrity.acquisition import normalize_path
from context_integrity.authority import effective_policies, resolve_authority
from context_integrity.configuration import ConfigurationError
from context_integrity.inventory import inventory_repository
from context_integrity.models import AuthorityPolicy, InventoryManifest
from context_integrity.rendering import (
    render_authority_json,
    render_authority_text,
    render_explanation,
    render_json,
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


def load_inventory(path: Path) -> tuple[RepositoryContext, InventoryManifest]:
    try:
        context = discover_repository(path)
        return context, inventory_repository(context)
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
    typer.echo(render_explanation(source), nl=False)
    for warning in manifest.warnings:
        if warning.path in {None, path}:
            typer.echo(f"Warning: {warning.code}: {warning.message}")


authority_app = typer.Typer(
    help="Inspect question-specific source-role authority.", no_args_is_help=True
)
app.add_typer(authority_app, name="authority")


def requested_policy(manifest: InventoryManifest, policy_id: str) -> AuthorityPolicy:
    policy = next(
        (p for p in effective_policies(manifest.authority_config) if p.id == policy_id), None
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
            effective_policies(manifest.authority_config), format == OutputFormat.JSON
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


if __name__ == "__main__":
    app()
