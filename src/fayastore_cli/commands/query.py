"""Query CLI commands: list, query, count."""

import json
from typing import List, Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from ..service import get_service, parse_filter, parse_order

console = Console()
app = typer.Typer(help="Query operations on Firestore collections")

# Maximum columns to show by default (to keep output readable)
DEFAULT_MAX_COLUMNS = 5


def format_value(value, max_length: int = 40) -> str:
    """Format a value for table display."""
    if value is None:
        return "[dim]null[/dim]"
    if isinstance(value, bool):
        return "[green]true[/green]" if value else "[red]false[/red]"
    if isinstance(value, dict):
        return "[dim]{...}[/dim]"
    if isinstance(value, list):
        return f"[dim][{len(value)} items][/dim]"

    str_value = str(value)
    if len(str_value) > max_length:
        return str_value[: max_length - 3] + "..."
    return str_value


def get_display_columns(docs: List[dict], user_fields: Optional[str], max_cols: int) -> tuple[List[str], int]:
    """
    Determine which columns to display.
    Returns (columns_to_show, total_columns_available)
    """
    if user_fields:
        # User specified fields - use those
        return ["id"] + [f.strip() for f in user_fields.split(",")], 0

    # Collect all keys from documents
    all_keys = set()
    for doc in docs:
        all_keys.update(doc.keys())

    all_columns = ["id"] + sorted([k for k in all_keys if k != "id"])
    total = len(all_columns)

    if total <= max_cols:
        return all_columns, 0

    # Too many columns - select the most useful ones
    # Priority: id, then common short-named fields, then alphabetically
    priority_fields = ["id", "name", "title", "status", "type", "email", "created_at", "updated_at"]
    selected = []

    for field in priority_fields:
        if field in all_columns and len(selected) < max_cols:
            selected.append(field)

    # Fill remaining slots with other fields
    for field in all_columns:
        if field not in selected and len(selected) < max_cols:
            selected.append(field)

    return selected, total - len(selected)


def print_documents_table(
    docs: List[dict],
    collection: str,
    fields: Optional[str] = None,
    caption: Optional[str] = None,
    max_cols: int = DEFAULT_MAX_COLUMNS,
) -> None:
    """Print documents as a formatted table."""
    columns, hidden_count = get_display_columns(docs, fields, max_cols)

    # Build title
    title = f"📁 {collection} ({len(docs)} documents)"
    if hidden_count > 0:
        title += f" [dim]• {hidden_count} more fields hidden[/dim]"

    table = Table(title=title, caption=caption, show_lines=False)

    # Add columns with appropriate styling
    for col in columns:
        if col == "id":
            table.add_column(col, style="cyan", no_wrap=True, max_width=36)
        else:
            table.add_column(col, overflow="ellipsis", max_width=30)

    # Add rows
    for doc in docs:
        row = [format_value(doc.get(col)) for col in columns]
        table.add_row(*row)

    console.print(table)

    if hidden_count > 0:
        rprint(f"\n[dim]Tip: Use --fields to select specific columns, or --raw for full JSON output[/dim]")


@app.command("list")
def list_documents(
    collection: str = typer.Argument(
        ...,
        help="Collection path (e.g., 'users' or 'users/abc123/posts')",
    ),
    limit: int = typer.Option(
        20, "--limit", "-l", help="Maximum number of documents to return"
    ),
    fields: Optional[str] = typer.Option(
        None,
        "--fields",
        "-f",
        help="Comma-separated list of fields to display (e.g., 'name,email,status')",
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
    """List documents in a collection."""
    try:
        service = get_service(credentials_path=credentials, project=project)

        select_fields = [f.strip() for f in fields.split(",")] if fields else None
        docs = service.list_documents(
            collection_path=collection,
            limit=limit,
            select_fields=select_fields,
        )

        if not docs:
            rprint(f"[yellow]No documents found in:[/yellow] {collection}")
            return

        if raw:
            print(json.dumps(docs, indent=2, default=str))
            return

        print_documents_table(docs, collection, fields)

    except Exception as e:
        rprint(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("query")
def query_documents(
    collection: str = typer.Argument(
        ...,
        help="Collection path (e.g., 'users')",
    ),
    where: Optional[List[str]] = typer.Option(
        None,
        "--where",
        "-w",
        help="Filter conditions (e.g., 'age>25', 'status=active'). Can be repeated.",
    ),
    order: Optional[List[str]] = typer.Option(
        None,
        "--order",
        "-o",
        help="Order by field (e.g., 'name:asc', 'age:desc'). Can be repeated.",
    ),
    limit: int = typer.Option(
        20, "--limit", "-l", help="Maximum number of documents to return"
    ),
    fields: Optional[str] = typer.Option(
        None,
        "--fields",
        "-f",
        help="Comma-separated list of fields to display (e.g., 'name,email,status')",
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
    """Query documents with filters and ordering."""
    try:
        service = get_service(credentials_path=credentials, project=project)

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

        # Parse order
        order_by = []
        if order:
            for o in order:
                try:
                    field, direction = parse_order(o)
                    order_by.append((field, direction))
                except ValueError as e:
                    rprint(f"[red]Invalid order:[/red] {e}")
                    raise typer.Exit(code=1)

        select_fields = [f.strip() for f in fields.split(",")] if fields else None

        docs = service.query_documents(
            collection_path=collection,
            filters=filters if filters else None,
            order_by=order_by if order_by else None,
            limit=limit,
            select_fields=select_fields,
        )

        if not docs:
            rprint(f"[yellow]No documents found matching query in:[/yellow] {collection}")
            return

        if raw:
            print(json.dumps(docs, indent=2, default=str))
            return

        # Build query description for caption
        query_desc = []
        if where:
            query_desc.append(f"where: {', '.join(where)}")
        if order:
            query_desc.append(f"order: {', '.join(order)}")
        query_desc.append(f"limit: {limit}")
        caption = " | ".join(query_desc)

        print_documents_table(docs, collection, fields, caption)

    except Exception as e:
        rprint(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("count")
def count_documents(
    collection: str = typer.Argument(
        ...,
        help="Collection path (e.g., 'users')",
    ),
    where: Optional[List[str]] = typer.Option(
        None,
        "--where",
        "-w",
        help="Filter conditions (e.g., 'age>25', 'status=active'). Can be repeated.",
    ),
    credentials: Optional[str] = typer.Option(
        None, "--credentials", "-c", help="Path to service account JSON file"
    ),
    project: Optional[str] = typer.Option(
        None, "--project", "-p", help="Google Cloud project ID"
    ),
) -> None:
    """Count documents in a collection with optional filters."""
    try:
        service = get_service(credentials_path=credentials, project=project)

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

        count = service.count_documents(
            collection_path=collection,
            filters=filters if filters else None,
        )

        if where:
            filter_desc = ", ".join(where)
            rprint(f"[bold]{collection}[/bold] (where {filter_desc}): [green]{count}[/green] documents")
        else:
            rprint(f"[bold]{collection}[/bold]: [green]{count}[/green] documents")

    except Exception as e:
        rprint(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("collections")
def list_collections(
    document_path: Optional[str] = typer.Argument(
        None,
        help="Document path to list subcollections of (optional, lists root collections if not provided)",
    ),
    credentials: Optional[str] = typer.Option(
        None, "--credentials", "-c", help="Path to service account JSON file"
    ),
    project: Optional[str] = typer.Option(
        None, "--project", "-p", help="Google Cloud project ID"
    ),
) -> None:
    """List collections (root or subcollections of a document)."""
    try:
        service = get_service(credentials_path=credentials, project=project)

        if document_path:
            collections = service.list_subcollections(document_path)
            title = f"Subcollections of {document_path}"
        else:
            collections = service.list_collections()
            title = "Root Collections"

        if not collections:
            rprint(f"[yellow]No collections found[/yellow]")
            return

        rprint(f"\n[bold]{title}[/bold]")
        for col in collections:
            rprint(f"  📁 {col}")
        rprint(f"\n[dim]Total: {len(collections)} collections[/dim]")

    except Exception as e:
        rprint(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)
