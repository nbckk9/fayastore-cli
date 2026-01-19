"""Export and import CLI commands."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..service import get_service, parse_filter

console = Console()
app = typer.Typer(help="Export and import Firestore data")


def serialize_document(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Serialize a document for JSON export, handling special types."""
    result = {}
    for key, value in doc.items():
        if hasattr(value, "isoformat"):  # datetime
            result[key] = {"_type": "datetime", "value": value.isoformat()}
        elif hasattr(value, "latitude"):  # GeoPoint
            result[key] = {
                "_type": "geopoint",
                "latitude": value.latitude,
                "longitude": value.longitude,
            }
        elif hasattr(value, "path"):  # DocumentReference
            result[key] = {"_type": "reference", "path": value.path}
        elif isinstance(value, bytes):
            result[key] = {"_type": "bytes", "value": value.hex()}
        elif isinstance(value, dict):
            result[key] = serialize_document(value)
        elif isinstance(value, list):
            result[key] = [
                serialize_document(v) if isinstance(v, dict) else v for v in value
            ]
        else:
            result[key] = value
    return result


@app.command("export")
def export_collection(
    collection: str = typer.Argument(
        ...,
        help="Collection path to export (e.g., 'users')",
    ),
    output: Path = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (default: {collection}.json)",
    ),
    where: Optional[List[str]] = typer.Option(
        None,
        "--where",
        "-w",
        help="Filter conditions. Can be repeated.",
    ),
    limit: Optional[int] = typer.Option(
        None, "--limit", "-l", help="Maximum number of documents to export"
    ),
    credentials: Optional[str] = typer.Option(
        None, "--credentials", "-c", help="Path to service account JSON file"
    ),
    project: Optional[str] = typer.Option(
        None, "--project", "-p", help="Google Cloud project ID"
    ),
    pretty: bool = typer.Option(
        True, "--pretty/--compact", help="Pretty print JSON output"
    ),
) -> None:
    """
    Export documents from a collection to a JSON file.

    The export includes document IDs and handles special Firestore types.
    """
    try:
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

        # Default output filename
        if output is None:
            safe_name = collection.replace("/", "_")
            output = Path(f"{safe_name}.json")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Exporting documents...", total=None)

            docs = service.export_collection(
                collection_path=collection,
                filters=filters if filters else None,
                limit=limit,
            )

            progress.update(task, description=f"Serializing {len(docs)} documents...")

            # Serialize documents
            serialized = [serialize_document(doc) for doc in docs]

            # Build export metadata
            export_data = {
                "_metadata": {
                    "collection": collection,
                    "exported_at": datetime.utcnow().isoformat(),
                    "count": len(serialized),
                    "filters": where if where else None,
                    "project": service.project,
                },
                "documents": serialized,
            }

            progress.update(task, description=f"Writing to {output}...")

            # Write to file
            with open(output, "w") as f:
                if pretty:
                    json.dump(export_data, f, indent=2, default=str)
                else:
                    json.dump(export_data, f, default=str)

            progress.update(
                task,
                description=f"[green]✓ Exported {len(docs)} documents to {output}[/green]",
            )

        rprint(f"\n[green]✓ Export completed:[/green] {len(docs)} documents → {output}")

    except Exception as e:
        rprint(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("import")
def import_collection(
    collection: str = typer.Argument(
        ...,
        help="Collection path to import into (e.g., 'users')",
    ),
    input_file: Path = typer.Option(
        ...,
        "--input",
        "-i",
        help="Input JSON file path",
        exists=True,
        readable=True,
    ),
    id_field: str = typer.Option(
        "id",
        "--id-field",
        help="Field to use as document ID",
    ),
    merge: bool = typer.Option(
        False,
        "--merge",
        "-m",
        help="Merge with existing documents instead of overwriting",
    ),
    credentials: Optional[str] = typer.Option(
        None, "--credentials", "-c", help="Path to service account JSON file"
    ),
    project: Optional[str] = typer.Option(
        None, "--project", "-p", help="Google Cloud project ID"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show what would be imported without executing"
    ),
) -> None:
    """
    Import documents from a JSON file to a collection.

    The JSON file can be:
    - An export file with _metadata and documents fields
    - A simple array of documents
    """
    try:
        # Load input file
        with open(input_file) as f:
            data = json.load(f)

        # Handle both export format and simple array
        if isinstance(data, dict) and "documents" in data:
            documents = data["documents"]
            rprint(f"[dim]Detected export format with metadata[/dim]")
            if "_metadata" in data:
                meta = data["_metadata"]
                rprint(f"[dim]Original collection: {meta.get('collection', 'unknown')}[/dim]")
                rprint(f"[dim]Exported at: {meta.get('exported_at', 'unknown')}[/dim]")
        elif isinstance(data, list):
            documents = data
        else:
            rprint("[red]Error:[/red] Invalid JSON format. Expected array or export object.")
            raise typer.Exit(code=1)

        rprint(f"\n[bold]Import Preview[/bold]")
        rprint(f"  Target collection: {collection}")
        rprint(f"  Documents to import: {len(documents)}")
        rprint(f"  ID field: {id_field}")
        rprint(f"  Merge mode: {'yes' if merge else 'no (overwrite)'}")
        rprint("")

        if dry_run:
            rprint("[yellow]Dry run mode - no changes will be made[/yellow]\n")

            # Show sample documents
            rprint("[bold]Sample documents:[/bold]")
            for doc in documents[:3]:
                doc_id = doc.get(id_field, "auto")
                rprint(f"  • {doc_id}: {list(doc.keys())[:5]}...")

            if len(documents) > 3:
                rprint(f"  ... and {len(documents) - 3} more")

            return

        service = get_service(credentials_path=credentials, project=project)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(f"Importing {len(documents)} documents...", total=None)

            imported = service.import_documents(
                collection_path=collection,
                documents=documents,
                id_field=id_field,
                merge=merge,
            )

            progress.update(
                task,
                description=f"[green]✓ Imported {imported} documents[/green]",
            )

        rprint(f"\n[green]✓ Import completed:[/green] {imported} documents → {collection}")

    except json.JSONDecodeError as e:
        rprint(f"[red]Invalid JSON in file:[/red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        rprint(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("backup")
def backup_database(
    output_dir: Path = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory (default: backup_{timestamp})",
    ),
    collections: Optional[List[str]] = typer.Option(
        None,
        "--collection",
        "-c",
        help="Specific collections to backup. If not provided, backs up all.",
    ),
    credentials: Optional[str] = typer.Option(
        None, "--credentials", help="Path to service account JSON file"
    ),
    project: Optional[str] = typer.Option(
        None, "--project", "-p", help="Google Cloud project ID"
    ),
) -> None:
    """
    Backup multiple collections to JSON files.

    Creates a directory with one JSON file per collection.
    """
    try:
        service = get_service(credentials_path=credentials, project=project)

        # Default output directory
        if output_dir is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = Path(f"backup_{timestamp}")

        output_dir.mkdir(parents=True, exist_ok=True)

        # Get collections to backup
        if collections:
            cols_to_backup = list(collections)
        else:
            cols_to_backup = service.list_collections()

        if not cols_to_backup:
            rprint("[yellow]No collections found to backup[/yellow]")
            return

        rprint(f"[bold]Backing up {len(cols_to_backup)} collections to {output_dir}[/bold]\n")

        total_docs = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            for col in cols_to_backup:
                task = progress.add_task(f"Backing up {col}...", total=None)

                docs = service.export_collection(collection_path=col)
                serialized = [serialize_document(doc) for doc in docs]

                export_data = {
                    "_metadata": {
                        "collection": col,
                        "exported_at": datetime.utcnow().isoformat(),
                        "count": len(serialized),
                        "project": service.project,
                    },
                    "documents": serialized,
                }

                safe_name = col.replace("/", "_")
                output_file = output_dir / f"{safe_name}.json"

                with open(output_file, "w") as f:
                    json.dump(export_data, f, indent=2, default=str)

                total_docs += len(docs)
                progress.update(
                    task,
                    description=f"[green]✓ {col}: {len(docs)} documents[/green]",
                )

        rprint(f"\n[green]✓ Backup completed:[/green]")
        rprint(f"  Collections: {len(cols_to_backup)}")
        rprint(f"  Total documents: {total_docs}")
        rprint(f"  Output: {output_dir}/")

    except Exception as e:
        rprint(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)
