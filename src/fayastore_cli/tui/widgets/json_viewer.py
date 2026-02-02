"""JSON viewer widget for displaying document data."""

import json
from typing import Any, Dict, Optional

from rich.console import RenderableType
from rich.json import JSON
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from textual.widgets import Static


class JsonViewer(Static):
    """A widget for displaying JSON data with syntax highlighting."""

    THEMES = {
        "dark": "monokai",
        "light": "github-light",
        "auto": "auto",
    }

    def __init__(
        self,
        data: Optional[Dict[str, Any]] = None,
        title: str = "Document",
        id: Optional[str] = None,
        theme: str = "dark",
    ) -> None:
        super().__init__(id=id)
        self._data = data
        self._title = title
        self._theme = self.THEMES.get(theme, "monokai")

    def set_data(self, data: Dict[str, Any], title: Optional[str] = None) -> None:
        """Set the data to display."""
        self._data = data
        if title:
            self._title = title
        self.refresh()

    def clear_data(self) -> None:
        """Clear the displayed data."""
        self._data = None
        self.refresh()

    def render(self) -> RenderableType:
        """Render the JSON data."""
        if self._data is None:
            return Panel(
                "[dim]No document selected[/dim]",
                title=self._title,
                border_style="dim",
            )

        # Check if data is empty
        if not self._data:
            return Panel(
                "[yellow]Empty document[/yellow]",
                title=self._title,
                border_style="yellow",
            )

        try:
            json_str = json.dumps(self._data, indent=2, default=str)
            syntax = Syntax(
                json_str,
                "json",
                theme=self._theme,
                line_numbers=True,
                word_wrap=True,
            )
            return Panel(
                syntax,
                title=self._title,
                border_style="green",
                padding=(0, 1),
            )
        except Exception as e:
            return Panel(
                f"[red]Error rendering JSON: {e}[/red]",
                title=self._title,
                border_style="red",
            )

    @property
    def data(self) -> Optional[Dict[str, Any]]:
        """Get the current data."""
        return self._data

    def to_json_string(self) -> str:
        """Get the data as a JSON string."""
        if self._data is None:
            return "{}"
        return json.dumps(self._data, indent=2, default=str)

    def get_summary(self) -> str:
        """Get a brief summary of the document."""
        if self._data is None:
            return "No data"

        keys = list(self._data.keys())
        if not keys:
            return "Empty"

        # Count types
        type_counts = {}
        for key, value in self._data.items():
            type_name = type(value).__name__
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

        type_str = ", ".join(f"{v} {k}s" for k, v in type_counts.items())
        return f"{len(keys)} fields, {type_str}"


class DocumentSummary(Static):
    """A widget showing a quick summary of a document."""

    def __init__(
        self,
        document_data: Optional[Dict[str, Any]] = None,
        document_path: Optional[str] = None,
        id: Optional[str] = None,
    ) -> None:
        super().__init__(id=id)
        self._document_data = document_data
        self._document_path = document_path

    def set_document(
        self,
        document_data: Dict[str, Any],
        document_path: Optional[str] = None,
    ) -> None:
        """Set the document to display."""
        self._document_data = document_data
        self._document_path = document_path
        self.refresh()

    def render(self) -> RenderableType:
        """Render the document summary."""
        if not self._document_data:
            return "[dim]No document selected[/dim]"

        # Create a compact summary table
        table = Table(show_header=False, box=None, padding=0)
        table.add_column("Key", style="cyan", width=15)
        table.add_column("Value", style="green")

        for key, value in list(self._document_data.items())[:10]:  # Show first 10 fields
            formatted_value = self._format_value(value)
            table.add_row(key, formatted_value)

        if len(self._document_data) > 10:
            table.add_row("...", f"[dim]+{len(self._document_data) - 10} more fields[/dim]")

        return table

    def _format_value(self, value: Any) -> str:
        """Format a value for display."""
        if value is None:
            return "[dim]null[/dim]"
        if isinstance(value, bool):
            return "[green]true[/green]" if value else "[red]false[/red]"
        if isinstance(value, str):
            if len(value) > 50:
                return f'"{value[:47]}..."'
            return f'"{value}"'
        if isinstance(value, (int, float)):
            return f"[yellow]{value}[/yellow]"
        if isinstance(value, dict):
            return f"[dim]{{...}} ({len(value)} keys)[/dim]"
        if isinstance(value, list):
            return f"[dim][...]({len(value)} items)[/dim]"
        return str(value)
