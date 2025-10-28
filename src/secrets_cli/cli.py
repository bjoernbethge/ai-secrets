from __future__ import annotations

import json
import sys
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import typer
from rich.console import Console
from rich.table import Table

from .storage import SecretsStore

app = typer.Typer(help="AI-friendly Secrets Management CLI")
console = Console()


class OutputFormat(str, Enum):
    JSON = "json"
    TEXT = "text"
    TABLE = "table"
    BASH = "bash"


def output_result(
    result: dict[str, Any],
    format: OutputFormat,
    success_msg: str = "",
    error: bool = False,
) -> None:
    """Output result in specified format."""
    if format == OutputFormat.JSON:
        print(json.dumps(result, indent=2))
    else:
        style = "bold red" if error else None
        prefix = "[red]Error:[/red]" if error else "[green]✓[/green]"
        console.print(f"{prefix} {success_msg}", style=style)


@app.callback()
def main(
    ctx: typer.Context,
    service_name: str = typer.Option(
        "ai-keys", "--service-name", help="Service name namespace in keyring"
    ),
    base_dir: Optional[Path] = typer.Option(
        None, "--base-dir", help="Directory for metadata index (defaults to ~/.secrets)"
    ),
) -> None:
    """Initialize store based on global options."""
    if not service_name or not service_name.strip():
        console.print("[red]Error:[/red] service-name cannot be empty")
        raise typer.Exit(1)

    if base_dir and not base_dir.parent.exists():
        console.print(f"[red]Error:[/red] Parent directory does not exist: {base_dir.parent}")
        raise typer.Exit(1)

    ctx.obj = {"store": SecretsStore(service_name=service_name.strip(), base_dir=base_dir)}


@app.command()
def set(
    ctx: typer.Context,
    name: str = typer.Argument(
        ..., help="Secret name (e.g., HF_TOKEN, OPENAI_API_KEY, AWS_SECRET_KEY)"
    ),
    value: str = typer.Argument(..., help="Secret value"),
    format: OutputFormat = typer.Option(
        OutputFormat.TEXT, "--format", "-f", help="Output format: json|text"
    ),
) -> None:
    """Store secret in OS keyring."""
    try:
        store: SecretsStore = ctx.obj["store"]
        store.set(name, value)
        result = {
            "success": True,
            "name": name,
            "message": f"Secret '{name}' stored securely in OS keyring",
        }
        if format == OutputFormat.JSON:
            print(json.dumps(result, indent=2))
        else:
            console.print(f"[green]✓[/green] Secret '{name}' stored securely")
    except (ValueError, OSError) as e:
        error = {"error": str(e), "name": name}
        if format == OutputFormat.JSON:
            print(json.dumps(error, indent=2))
        else:
            console.print(f"[red]Error:[/red] {e}", style="bold red")
        raise typer.Exit(1)


@app.command()
def get(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Secret name"),
    print_value: bool = typer.Option(
        False, "--print", help="Print secret value (INSECURE!)"
    ),
    format: OutputFormat = typer.Option(
        OutputFormat.TEXT, "--format", "-f", help="Output format: json|text"
    ),
    reveal: bool = typer.Option(
        False, "--reveal", help="[AI-friendly] Always return value in JSON mode (ignores --print)"
    ),
) -> None:
    """Retrieve secret from OS keyring."""
    try:
        store: SecretsStore = ctx.obj["store"]
        value = store.get(name)
        if value is None:
            error = {"success": False, "error": f"Secret '{name}' not found", "name": name}
            if format == OutputFormat.JSON:
                print(json.dumps(error, indent=2))
            else:
                console.print(f"[red]Error:[/red] Secret '{name}' not found")
            raise typer.Exit(1)

        # AI-friendly: in JSON mode with --reveal, always include value
        include_value = print_value or (reveal and format == OutputFormat.JSON)
        
        result = {"success": True, "name": name, "exists": True}
        if include_value:
            result["value"] = value

        if format == OutputFormat.JSON:
            print(json.dumps(result, indent=2))
        else:
            if print_value:
                console.print(f"{name}: {value}")
            else:
                console.print(f"[green]✓[/green] Secret '{name}' exists")
                console.print(
                    "\n[yellow]Use --print to display value (insecure!)[/yellow]"
                )
    except (ValueError, OSError) as e:
        error = {"success": False, "error": str(e), "name": name}
        if format == OutputFormat.JSON:
            print(json.dumps(error, indent=2))
        else:
            console.print(f"[red]Error:[/red] {e}", style="bold red")
        raise typer.Exit(1)


@app.command()
def list(
    ctx: typer.Context,
    format: OutputFormat = typer.Option(
        OutputFormat.TABLE, "--format", "-f", help="Output format: json|table"
    ),
) -> None:
    """List all stored secrets (names only, not values!)."""
    try:
        store: SecretsStore = ctx.obj["store"]
        secrets = store.list_names()

        if format == OutputFormat.JSON:
            print(json.dumps({"success": True, "secrets": secrets, "count": len(secrets)}, indent=2))
        elif format == OutputFormat.TABLE:
            if not secrets:
                console.print("[yellow]No secrets stored[/yellow]")
                return
            table = Table()
            table.add_column("Name")
            for name in sorted(secrets):
                table.add_row(name)
            console.print(table)
        else:
            console.print(f"[yellow]Unknown format:[/yellow] {format}")
    except (ValueError, OSError) as e:
        error = {"error": str(e)}
        if format == OutputFormat.JSON:
            print(json.dumps(error, indent=2))
        else:
            console.print(f"[red]Error:[/red] {e}", style="bold red")
        raise typer.Exit(1)


@app.command()
def delete(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Secret name"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    format: OutputFormat = typer.Option(
        OutputFormat.TEXT, "--format", "-f", help="Output format: json|text"
    ),
) -> None:
    """Delete secret from OS keyring."""
    try:
        store: SecretsStore = ctx.obj["store"]
        exists = store.get(name) is not None
        if not exists:
            error = {"error": f"Secret '{name}' not found"}
            if format == OutputFormat.JSON:
                print(json.dumps(error, indent=2))
            else:
                console.print(f"[red]Error:[/red] Secret '{name}' not found")
            raise typer.Exit(1)

        if not yes:
            if format == OutputFormat.JSON:
                error = {
                    "error": "Confirmation required. Use --yes to confirm deletion"
                }
                print(json.dumps(error, indent=2))
                raise typer.Exit(1)
            else:
                console.print(
                    f"[yellow]Warning:[/yellow] This will permanently delete secret: {name}"
                )
                confirm = typer.confirm("Are you sure?", default=False)
                if not confirm:
                    console.print("Deletion cancelled")
                    raise typer.Exit(0)

        store.delete(name)

        result = {"success": True, "name": name, "deleted": True}
        if format == OutputFormat.JSON:
            print(json.dumps(result, indent=2))
        else:
            console.print(f"[green]✓[/green] Secret '{name}' deleted")
    except (ValueError, OSError) as e:
        error = {"error": str(e), "name": name}
        if format == OutputFormat.JSON:
            print(json.dumps(error, indent=2))
        else:
            console.print(f"[red]Error:[/red] {e}", style="bold red")
        raise typer.Exit(1)


@app.command()
def export(
    ctx: typer.Context,
    format: OutputFormat = typer.Option(
        OutputFormat.BASH, "--format", "-f", help="Output format: bash|json"
    ),
) -> None:
    """Export secrets as environment variables (WARNING: exposes secrets in plaintext!)."""
    try:
        store: SecretsStore = ctx.obj["store"]
        exports = store.export_env()
        
        if format == OutputFormat.BASH:
            # Print warning to stderr using standard print
            print(
                "WARNING: This exposes secrets in plaintext!",
                file=sys.stderr
            )
            for name, value in exports.items():
                print(f"export {name}={value}")
        elif format == OutputFormat.JSON:
            print(json.dumps({"success": True, "secrets": exports, "count": len(exports)}, indent=2))
        else:
            console.print(f"[yellow]Unknown format:[/yellow] {format}")
    except (ValueError, OSError) as e:
        error = {"error": str(e)}
        print(json.dumps(error, indent=2), file=sys.stderr)
        raise typer.Exit(1)


@app.command()
def status(
    ctx: typer.Context,
    format: OutputFormat = typer.Option(
        OutputFormat.JSON, "--format", "-f", help="Output format: json|table"
    ),
) -> None:
    """Show secrets manager status."""
    try:
        store: SecretsStore = ctx.obj["store"]
        secrets = store.list_names()
        status_data = {
            "success": True,
            "service_name": store.service_name,
            "secrets_file": str(store.metadata_file),
            "secret_count": len(secrets),
            "secrets": secrets,
        }
        if format == OutputFormat.JSON:
            print(json.dumps(status_data, indent=2))
        elif format == OutputFormat.TABLE:
            console.print(f"[bold]Secrets Manager Status[/bold]\n")
            console.print(f"Service Name: {store.service_name}")
            console.print(f"Secrets File: {store.metadata_file}")
            console.print(f"Secrets Count: {len(secrets)}")
            if secrets:
                console.print(f"\nStored Secrets: {', '.join(secrets)}")
        else:
            console.print(f"[yellow]Unknown format:[/yellow] {format}")
    except (ValueError, OSError) as e:
        error = {"error": str(e)}
        if format == OutputFormat.JSON:
            print(json.dumps(error, indent=2))
        else:
            console.print(f"[red]Error:[/red] {e}", style="bold red")
        raise typer.Exit(1)
