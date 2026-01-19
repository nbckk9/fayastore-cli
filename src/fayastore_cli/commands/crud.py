"""CRUD CLI commands: get, create, update, delete."""

import json
from typing import Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.json import JSON
from rich.panel import Panel

from ..service import get_service

console = Console()
app = typer.Typer(help="CRUD operations on Firestore documents")


@app.command("get")
def get_document(
    document_path: str = typer.Argument(
        ...,
        help="Full document path (e.g., 'users/abc123' or 'users/abc123/posts/post1')",
    ),
    credentials: Optional[str] = typer.Option(
        None, "--credentials", "-c", help="Path to service account JSON file"
    ),
    project: Optional[str] = typer.Option(
        None, "--project", "-p", help="Google Cloud project ID"
    ),
    raw: bool = typer.Option(
        False, "--raw", "-r", help="Output raw JSON without formatting"
    ),
) -> None:
    """Get a document by its path."""
    try:
        service = get_service(credentials_path=credentials, project=project)
        doc = service.get_document(document_path)

        if doc is None:
            rprint(f"[yellow]Document not found:[/yellow] {document_path}")
            raise typer.Exit(code=1)

        if raw:
            print(json.dumps(doc, indent=2, default=str))
        else:
            rprint(Panel(JSON(json.dumps(doc, default=str)), title=f"📄 {document_path}"))

    except ValueError as e:
        rprint(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        rprint(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("create")
def create_document(
    collection: str = typer.Argument(
        ...,
        help="Collection path (e.g., 'users' or 'users/abc123/posts')",
    ),
    data: str = typer.Option(
        ...,
        "--data",
        "-d",
        help="Document data as JSON string",
    ),
    document_id: Optional[str] = typer.Option(
        None, "--id", "-i", help="Document ID (auto-generated if not provided)"
    ),
    credentials: Optional[str] = typer.Option(
        None, "--credentials", "-c", help="Path to service account JSON file"
    ),
    project: Optional[str] = typer.Option(
        None, "--project", "-p", help="Google Cloud project ID"
    ),
) -> None:
    """Create a new document in a collection."""
    try:
        # Parse JSON data
        try:
            doc_data = json.loads(data)
        except json.JSONDecodeError as e:
            rprint(f"[red]Invalid JSON:[/red] {e}")
            raise typer.Exit(code=1)

        service = get_service(credentials_path=credentials, project=project)
        doc_id = service.create_document(
            collection_path=collection,
            data=doc_data,
            document_id=document_id,
        )

        rprint(f"[green]✓ Document created:[/green] {collection}/{doc_id}")

    except Exception as e:
        rprint(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("update")
def update_document(
    document_path: str = typer.Argument(
        ...,
        help="Full document path (e.g., 'users/abc123')",
    ),
    data: str = typer.Option(
        ...,
        "--data",
        "-d",
        help="Data to update as JSON string",
    ),
    merge: bool = typer.Option(
        True,
        "--merge/--overwrite",
        help="Merge with existing data (default) or overwrite completely",
    ),
    credentials: Optional[str] = typer.Option(
        None, "--credentials", "-c", help="Path to service account JSON file"
    ),
    project: Optional[str] = typer.Option(
        None, "--project", "-p", help="Google Cloud project ID"
    ),
) -> None:
    """Update an existing document."""
    try:
        # Parse JSON data
        try:
            update_data = json.loads(data)
        except json.JSONDecodeError as e:
            rprint(f"[red]Invalid JSON:[/red] {e}")
            raise typer.Exit(code=1)

        service = get_service(credentials_path=credentials, project=project)
        service.update_document(
            document_path=document_path,
            data=update_data,
            merge=merge,
        )

        rprint(f"[green]✓ Document updated:[/green] {document_path}")

    except ValueError as e:
        rprint(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        rprint(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("delete")
def delete_document(
    document_path: str = typer.Argument(
        ...,
        help="Full document path (e.g., 'users/abc123')",
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Delete without confirmation"
    ),
    credentials: Optional[str] = typer.Option(
        None, "--credentials", "-c", help="Path to service account JSON file"
    ),
    project: Optional[str] = typer.Option(
        None, "--project", "-p", help="Google Cloud project ID"
    ),
) -> None:
    """Delete a document."""
    try:
        if not force:
            confirm = typer.confirm(f"Are you sure you want to delete '{document_path}'?")
            if not confirm:
                rprint("[yellow]Cancelled[/yellow]")
                raise typer.Exit(code=0)

        service = get_service(credentials_path=credentials, project=project)
        service.delete_document(document_path)

        rprint(f"[green]✓ Document deleted:[/green] {document_path}")

    except ValueError as e:
        rprint(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        rprint(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)
