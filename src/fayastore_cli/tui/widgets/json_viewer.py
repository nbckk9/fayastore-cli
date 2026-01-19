"""JSON viewer widget for displaying document data."""

import json
from typing import Any, Dict, Optional

from rich.console import RenderableType
from rich.json import JSON
from rich.panel import Panel
from rich.syntax import Syntax
from textual.widgets import Static


class JsonViewer(Static):
    """A widget for displaying JSON data with syntax highlighting."""

    def __init__(
        self,
        data: Optional[Dict[str, Any]] = None,
        title: str = "Document",
        id: Optional[str] = None,
    ) -> None:
        super().__init__(id=id)
        self._data = data
        self._title = title

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

        try:
            json_str = json.dumps(self._data, indent=2, default=str)
            syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True)
            return Panel(syntax, title=self._title, border_style="green")
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
