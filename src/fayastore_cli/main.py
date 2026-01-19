"""Main CLI entry point for fayastore."""

from typing import List, Optional

import typer
from rich import print as rprint

from .auth import get_config, save_config, validate_connection
from .commands import batch, crud, export, query

app = typer.Typer(
    name="fayastore",
    help="A CLI and TUI tool to query and manage Firestore data",
    no_args_is_help=True,
)

# Register sub-apps for grouped operations
app.add_typer(batch.app, name="batch", help="Batch operations")
app.add_typer(export.app, name="data", help="Export and import data")


# ============== Document Operations ==============

@app.command("get")
def get_document(
    document_path: str = typer.Argument(..., help="Document path (e.g., 'users/abc123')"),
    credentials: Optional[str] = typer.Option(None, "--credentials", "-c", help="Path to service account JSON"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Google Cloud project ID"),
    raw: bool = typer.Option(False, "--raw", "-r", help="Output raw JSON"),
):
    """Get a document by path."""
    crud.get_document(document_path, credentials, project, raw)


@app.command("create")
def create_document(
    collection: str = typer.Argument(..., help="Collection path (e.g., 'users')"),
    data: str = typer.Option(..., "--data", "-d", help="Document data as JSON string"),
    document_id: Optional[str] = typer.Option(None, "--id", "-i", help="Document ID (auto-generated if not provided)"),
    credentials: Optional[str] = typer.Option(None, "--credentials", "-c", help="Path to service account JSON"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Google Cloud project ID"),
):
    """Create a new document in a collection."""
    crud.create_document(collection, data, document_id, credentials, project)


@app.command("update")
def update_document(
    document_path: str = typer.Argument(..., help="Document path (e.g., 'users/abc123')"),
    data: str = typer.Option(..., "--data", "-d", help="Data to update as JSON string"),
    merge: bool = typer.Option(True, "--merge/--overwrite", help="Merge with existing data or overwrite"),
    credentials: Optional[str] = typer.Option(None, "--credentials", "-c", help="Path to service account JSON"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Google Cloud project ID"),
):
    """Update an existing document."""
    crud.update_document(document_path, data, merge, credentials, project)


@app.command("delete")
def delete_document(
    document_path: str = typer.Argument(..., help="Document path (e.g., 'users/abc123')"),
    force: bool = typer.Option(False, "--force", "-f", help="Delete without confirmation"),
    credentials: Optional[str] = typer.Option(None, "--credentials", "-c", help="Path to service account JSON"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Google Cloud project ID"),
):
    """Delete a document."""
    crud.delete_document(document_path, force, credentials, project)


# ============== Query Operations ==============

@app.command("list")
def list_documents(
    collection: str = typer.Argument(..., help="Collection path (e.g., 'users')"),
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum documents to return"),
    fields: Optional[str] = typer.Option(None, "--fields", "-f", help="Comma-separated fields to display"),
    credentials: Optional[str] = typer.Option(None, "--credentials", "-c", help="Path to service account JSON"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Google Cloud project ID"),
    raw: bool = typer.Option(False, "--raw", "-r", help="Output raw JSON"),
):
    """List documents in a collection."""
    query.list_documents(collection, limit, fields, credentials, project, raw)


@app.command("query")
def query_documents(
    collection: str = typer.Argument(..., help="Collection path (e.g., 'users')"),
    where: Optional[List[str]] = typer.Option(None, "--where", "-w", help="Filter (e.g., 'age>25'). Repeatable."),
    order: Optional[List[str]] = typer.Option(None, "--order", "-o", help="Order by (e.g., 'name:asc'). Repeatable."),
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum documents to return"),
    fields: Optional[str] = typer.Option(None, "--fields", "-f", help="Comma-separated fields to display"),
    credentials: Optional[str] = typer.Option(None, "--credentials", "-c", help="Path to service account JSON"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Google Cloud project ID"),
    raw: bool = typer.Option(False, "--raw", "-r", help="Output raw JSON"),
):
    """Query documents with filters and ordering."""
    query.query_documents(collection, where, order, limit, fields, credentials, project, raw)


@app.command("count")
def count_documents(
    collection: str = typer.Argument(..., help="Collection path (e.g., 'users')"),
    where: Optional[List[str]] = typer.Option(None, "--where", "-w", help="Filter (e.g., 'age>25'). Repeatable."),
    credentials: Optional[str] = typer.Option(None, "--credentials", "-c", help="Path to service account JSON"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Google Cloud project ID"),
):
    """Count documents in a collection."""
    query.count_documents(collection, where, credentials, project)


@app.command("collections")
def list_collections(
    document_path: Optional[str] = typer.Argument(None, help="Document path for subcollections (optional)"),
    credentials: Optional[str] = typer.Option(None, "--credentials", "-c", help="Path to service account JSON"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Google Cloud project ID"),
):
    """List root collections or subcollections of a document."""
    query.list_collections(document_path, credentials, project)


# ============== Configuration ==============

@app.command("config")
def configure(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Google Cloud project ID"),
    credentials: Optional[str] = typer.Option(None, "--credentials", "-c", help="Path to service account JSON file"),
    database: Optional[str] = typer.Option(None, "--database", "-d", help="Firestore database ID"),
    show: bool = typer.Option(False, "--show", "-s", help="Show current configuration"),
) -> None:
    """Configure Firestore connection settings."""
    config = get_config()

    if show:
        rprint("\n[bold]Current Configuration[/bold]")
        rprint(f"  Project: {config.get('project', '[dim]not set[/dim]')}")
        rprint(f"  Credentials: {config.get('credentials', '[dim]not set[/dim]')}")
        rprint(f"  Database: {config.get('database', '[dim](default)[/dim]')}")
        rprint("")

        success, message = validate_connection()
        if success:
            rprint(f"  [green]✓ {message}[/green]")
        else:
            rprint(f"  [red]✗ {message}[/red]")
        return

    if not any([project, credentials, database]):
        rprint("[yellow]No configuration options provided. Use --show to view current config.[/yellow]")
        rprint("Use --help to see available options.")
        return

    if project:
        config["project"] = project
    if credentials:
        config["credentials"] = credentials
    if database:
        config["database"] = database

    save_config(config)

    rprint("[green]✓ Configuration saved[/green]")
    rprint(f"  Project: {config.get('project', 'not set')}")
    rprint(f"  Credentials: {config.get('credentials', 'not set')}")
    rprint(f"  Database: {config.get('database', '(default)')}")


@app.command("status")
def status(
    credentials: Optional[str] = typer.Option(None, "--credentials", "-c"),
    project: Optional[str] = typer.Option(None, "--project", "-p"),
) -> None:
    """Check connection status to Firestore."""
    from .service import get_service

    rprint("\n[bold]Fayastore Status[/bold]\n")

    try:
        service = get_service(credentials_path=credentials, project=project)
        collections = service.list_collections()

        rprint(f"  [green]✓ Connected to project:[/green] {service.project}")
        rprint(f"  [green]✓ Root collections:[/green] {len(collections)}")

        if collections:
            rprint("\n  Collections:")
            for col in collections[:10]:
                rprint(f"    📁 {col}")
            if len(collections) > 10:
                rprint(f"    ... and {len(collections) - 10} more")

    except Exception as e:
        rprint(f"  [red]✗ Connection failed:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("tui")
def launch_tui(
    credentials: Optional[str] = typer.Option(None, "--credentials", "-c", help="Path to service account JSON"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Google Cloud project ID"),
) -> None:
    """Launch the interactive TUI (Terminal User Interface)."""
    try:
        from .tui.app import FayastoreApp

        tui_app = FayastoreApp(credentials_path=credentials, project=project)
        tui_app.run()
    except ImportError as e:
        rprint(f"[red]Error loading TUI:[/red] {e}")
        rprint("Make sure textual is installed: pip install textual")
        raise typer.Exit(code=1)
    except Exception as e:
        rprint(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


# ============== Shortcuts for export/import ==============

@app.command("export")
def export_collection(
    collection: str = typer.Argument(..., help="Collection path to export"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    where: Optional[List[str]] = typer.Option(None, "--where", "-w", help="Filter conditions"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Maximum documents to export"),
    credentials: Optional[str] = typer.Option(None, "--credentials", "-c"),
    project: Optional[str] = typer.Option(None, "--project", "-p"),
):
    """Export a collection to JSON file."""
    from pathlib import Path
    output_path = Path(output) if output else None
    export.export_collection(collection, output_path, where, limit, credentials, project, True)


@app.command("import")
def import_collection(
    collection: str = typer.Argument(..., help="Collection path to import into"),
    input_file: str = typer.Option(..., "--input", "-i", help="Input JSON file path"),
    id_field: str = typer.Option("id", "--id-field", help="Field to use as document ID"),
    merge: bool = typer.Option(False, "--merge", "-m", help="Merge with existing documents"),
    credentials: Optional[str] = typer.Option(None, "--credentials", "-c"),
    project: Optional[str] = typer.Option(None, "--project", "-p"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Preview without executing"),
):
    """Import documents from JSON file to a collection."""
    from pathlib import Path
    export.import_collection(collection, Path(input_file), id_field, merge, credentials, project, dry_run)


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
