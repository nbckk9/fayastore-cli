"""Batch operation CLI commands."""

import json
from pathlib import Path
from typing import List, Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..service import get_service, parse_filter

console = Console()
app = typer.Typer(help="Batch operations on Firestore documents")


@app.command("run")
def batch_operations(
    file: Path = typer.Argument(
        ...,
        help="Path to JSON file containing batch operations",
        exists=True,
        readable=True,
    ),
    credentials: Optional[str] = typer.Option(
        None, "--credentials", "-c", help="Path to service account JSON file"
    ),
    project: Optional[str] = typer.Option(
        None, "--project", "-p", help="Google Cloud project ID"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show what would be done without executing"
    ),
) -> None:
    """
    Execute batch operations from a JSON file.

    The JSON file should contain an array of operations:

    \b
    [
      {"action": "create", "collection": "users", "id": "abc", "data": {"name": "John"}},
      {"action": "update", "path": "users/abc", "data": {"age": 30}},
      {"action": "delete", "path": "users/xyz"}
    ]

    Supported actions: create, update, delete
    """
    try:
        # Load operations from file
        with open(file) as f:
            operations = json.load(f)

        if not isinstance(operations, list):
            rprint("[red]Error:[/red] JSON file must contain an array of operations")
            raise typer.Exit(code=1)

        rprint(f"[bold]Loaded {len(operations)} operations from {file}[/bold]\n")

        # Group operations by type
        creates = [op for op in operations if op.get("action") == "create"]
        updates = [op for op in operations if op.get("action") == "update"]
        deletes = [op for op in operations if op.get("action") == "delete"]

        rprint(f"  • Create: {len(creates)}")
        rprint(f"  • Update: {len(updates)}")
        rprint(f"  • Delete: {len(deletes)}")
        rprint("")

        if dry_run:
            rprint("[yellow]Dry run mode - no changes will be made[/yellow]\n")

            if creates:
                rprint("[bold]Creates:[/bold]")
                for op in creates[:10]:
                    col = op.get("collection", "?")
                    doc_id = op.get("id", "auto")
                    rprint(f"  + {col}/{doc_id}")
                if len(creates) > 10:
                    rprint(f"  ... and {len(creates) - 10} more")

            if updates:
                rprint("[bold]Updates:[/bold]")
                for op in updates[:10]:
                    path = op.get("path", "?")
                    rprint(f"  ~ {path}")
                if len(updates) > 10:
                    rprint(f"  ... and {len(updates) - 10} more")

            if deletes:
                rprint("[bold]Deletes:[/bold]")
                for op in deletes[:10]:
                    path = op.get("path", "?")
                    rprint(f"  - {path}")
                if len(deletes) > 10:
                    rprint(f"  ... and {len(deletes) - 10} more")

            return

        service = get_service(credentials_path=credentials, project=project)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Execute creates
            if creates:
                task = progress.add_task(f"Creating {len(creates)} documents...", total=None)
                for op in creates:
                    collection = op.get("collection")
                    data = op.get("data", {})
                    doc_id = op.get("id")

                    if not collection:
                        rprint(f"[yellow]Skipping create: missing collection[/yellow]")
                        continue

                    service.create_document(
                        collection_path=collection,
                        data=data,
                        document_id=doc_id,
                    )
                progress.update(task, description=f"[green]✓ Created {len(creates)} documents[/green]")

            # Execute updates
            if updates:
                task = progress.add_task(f"Updating {len(updates)} documents...", total=None)
                update_ops = []
                for op in updates:
                    path = op.get("path")
                    data = op.get("data", {})

                    if not path:
                        rprint(f"[yellow]Skipping update: missing path[/yellow]")
                        continue

                    update_ops.append({"path": path, "data": data})

                if update_ops:
                    service.batch_update_documents(update_ops)
                progress.update(task, description=f"[green]✓ Updated {len(updates)} documents[/green]")

            # Execute deletes
            if deletes:
                task = progress.add_task(f"Deleting {len(deletes)} documents...", total=None)
                delete_paths = []
                for op in deletes:
                    path = op.get("path")
                    if not path:
                        rprint(f"[yellow]Skipping delete: missing path[/yellow]")
                        continue
                    delete_paths.append(path)

                if delete_paths:
                    service.batch_delete_documents(delete_paths)
                progress.update(task, description=f"[green]✓ Deleted {len(deletes)} documents[/green]")

        rprint(f"\n[green]✓ Batch operations completed successfully[/green]")

    except json.JSONDecodeError as e:
        rprint(f"[red]Invalid JSON in file:[/red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        rprint(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("update-query")
def batch_update_with_query(
    collection: str = typer.Argument(
        ...,
        help="Collection path to update documents in",
    ),
    data: str = typer.Option(
        ...,
        "--data",
        "-d",
        help="Data to update as JSON string",
    ),
    where: Optional[List[str]] = typer.Option(
        None,
        "--where",
        "-w",
        help="Filter conditions (e.g., 'age>25', 'status=active'). Can be repeated.",
    ),
    limit: Optional[int] = typer.Option(
        None, "--limit", "-l", help="Maximum number of documents to update"
    ),
    credentials: Optional[str] = typer.Option(
        None, "--credentials", "-c", help="Path to service account JSON file"
    ),
    project: Optional[str] = typer.Option(
        None, "--project", "-p", help="Google Cloud project ID"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Execute without confirmation"
    ),
) -> None:
    """
    Batch update documents matching a query.

    Example:
        fayastore batch update-query users -d '{"status":"inactive"}' -w "lastLogin<2024-01-01"
    """
    try:
        # Parse JSON data
        try:
            update_data = json.loads(data)
        except json.JSONDecodeError as e:
            rprint(f"[red]Invalid JSON:[/red] {e}")
            raise typer.Exit(code=1)

        # Parse filters
        filters = []
        if where:
            for w in where:
                try:
                    field, op, value = parse_filter(w)
                    filters.append((field, op, value))
                except ValueError as e:
                    rprint(f"[red]Invalid filter:[/red] {e}")
                    raise typer.Exit(code=1)

        service = get_service(credentials_path=credentials, project=project)

        # Count matching documents first
        count = service.count_documents(
            collection_path=collection,
            filters=filters if filters else None,
        )

        if count == 0:
            rprint("[yellow]No documents match the query[/yellow]")
            return

        actual_count = min(count, limit) if limit else count

        if not force:
            filter_desc = ", ".join(where) if where else "none"
            rprint(f"\n[bold]Batch Update Preview[/bold]")
            rprint(f"  Collection: {collection}")
            rprint(f"  Filters: {filter_desc}")
            rprint(f"  Documents to update: {actual_count}")
            rprint(f"  Data: {json.dumps(update_data)}")
            rprint("")

            confirm = typer.confirm("Proceed with batch update?")
            if not confirm:
                rprint("[yellow]Cancelled[/yellow]")
                return

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(f"Updating {actual_count} documents...", total=None)

            result = service.batch_update_with_query(
                collection_path=collection,
                data=update_data,
                filters=filters if filters else None,
                limit=limit,
            )

            progress.update(
                task,
                description=f"[green]✓ Updated {result['count']} documents[/green]",
            )

        rprint(f"\n[green]✓ {result['message']}[/green]")

    except Exception as e:
        rprint(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("delete-query")
def batch_delete_with_query(
    collection: str = typer.Argument(
        ...,
        help="Collection path to delete documents from",
    ),
    where: Optional[List[str]] = typer.Option(
        None,
        "--where",
        "-w",
        help="Filter conditions. Can be repeated. REQUIRED for safety.",
    ),
    limit: Optional[int] = typer.Option(
        None, "--limit", "-l", help="Maximum number of documents to delete"
    ),
    credentials: Optional[str] = typer.Option(
        None, "--credentials", "-c", help="Path to service account JSON file"
    ),
    project: Optional[str] = typer.Option(
        None, "--project", "-p", help="Google Cloud project ID"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Execute without confirmation"
    ),
    allow_all: bool = typer.Option(
        False, "--allow-all", help="Allow deletion without filters (dangerous!)"
    ),
) -> None:
    """
    Batch delete documents matching a query.

    For safety, filters are required unless --allow-all is specified.

    Example:
        fayastore batch delete-query users -w "status=deleted" -w "deletedAt<2024-01-01"
    """
    try:
        if not where and not allow_all:
            rprint(
                "[red]Error:[/red] Filters are required for batch delete. "
                "Use --allow-all to delete all documents (dangerous!)."
            )
            raise typer.Exit(code=1)

        # Parse filters
        filters = []
        if where:
            for w in where:
                try:
                    field, op, value = parse_filter(w)
                    filters.append((field, op, value))
                except ValueError as e:
                    rprint(f"[red]Invalid filter:[/red] {e}")
                    raise typer.Exit(code=1)

        service = get_service(credentials_path=credentials, project=project)

        # Count matching documents
        count = service.count_documents(
            collection_path=collection,
            filters=filters if filters else None,
        )

        if count == 0:
            rprint("[yellow]No documents match the query[/yellow]")
            return

        actual_count = min(count, limit) if limit else count

        filter_desc = ", ".join(where) if where else "[red]ALL DOCUMENTS[/red]"

        if not force:
            rprint(f"\n[bold red]⚠️  Batch Delete Warning[/bold red]")
            rprint(f"  Collection: {collection}")
            rprint(f"  Filters: {filter_desc}")
            rprint(f"  Documents to delete: {actual_count}")
            rprint("")

            confirm = typer.confirm("Are you SURE you want to delete these documents?")
            if not confirm:
                rprint("[yellow]Cancelled[/yellow]")
                return

        # Get documents to delete
        docs = service.query_documents(
            collection_path=collection,
            filters=filters if filters else None,
            limit=limit,
            select_fields=["__name__"],
        )

        paths = [f"{collection}/{doc['id']}" for doc in docs]

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(f"Deleting {len(paths)} documents...", total=None)
            deleted = service.batch_delete_documents(paths)
            progress.update(
                task,
                description=f"[green]✓ Deleted {deleted} documents[/green]",
            )

        rprint(f"\n[green]✓ Batch delete completed: {deleted} documents deleted[/green]")

    except Exception as e:
        rprint(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)
