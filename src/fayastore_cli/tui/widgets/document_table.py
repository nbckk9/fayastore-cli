"""Document table widget for displaying Firestore documents."""

import json
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from rich.text import Text
from textual.message import Message
from textual.widgets import DataTable

if TYPE_CHECKING:
    from ...service import FirestoreService


class DocumentRowSelected(Message):
    """Message sent when a document row is selected."""

    def __init__(self, document_path: str, document_data: Dict[str, Any]) -> None:
        self.document_path = document_path
        self.document_data = document_data
        super().__init__()


class DocumentTable(DataTable):
    """A data table for displaying Firestore documents."""

    def __init__(
        self,
        service: "FirestoreService",
        id: Optional[str] = None,
    ) -> None:
        super().__init__(id=id)
        self.service = service
        self._current_collection: Optional[str] = None
        self._documents: List[Dict[str, Any]] = []
        self.cursor_type = "row"
        self.zebra_stripes = True

    def load_collection(self, collection_path: str, limit: int = 50) -> None:
        """Load documents from a collection."""
        self._current_collection = collection_path
        self.clear(columns=True)
        self._documents = []

        try:
            docs = self.service.list_documents(collection_path, limit=limit)
            self._documents = docs

            if not docs:
                self.add_column("Message", key="message")
                self.add_row(Text("No documents found", style="dim italic"))
                return

            # Determine columns from all documents
            all_keys = set()
            for doc in docs:
                all_keys.update(doc.keys())

            # Always show 'id' first, then sort others
            columns = ["id"] + sorted([k for k in all_keys if k != "id"])

            # Limit columns for display
            max_columns = 8
            if len(columns) > max_columns:
                columns = columns[:max_columns]

            # Add columns
            for col in columns:
                self.add_column(col, key=col)

            # Add rows
            for doc in docs:
                row_values = []
                for col in columns:
                    value = doc.get(col)
                    row_values.append(self._format_cell_value(value))
                self.add_row(*row_values, key=doc.get("id", str(len(self._documents))))

        except Exception as e:
            self.add_column("Error", key="error")
            self.add_row(Text(f"Error loading documents: {e}", style="red"))

    def _format_cell_value(self, value: Any, max_length: int = 40) -> Text:
        """Format a value for display in a table cell."""
        if value is None:
            return Text("null", style="dim")
        if isinstance(value, bool):
            return Text("true" if value else "false", style="green" if value else "red")
        if isinstance(value, dict):
            return Text("{...}", style="dim")
        if isinstance(value, list):
            return Text(f"[{len(value)} items]", style="dim")

        str_value = str(value)
        if len(str_value) > max_length:
            str_value = str_value[: max_length - 3] + "..."

        return Text(str_value)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection."""
        if not self._documents or not self._current_collection:
            return

        row_key = event.row_key
        if row_key is None:
            return

        # Find the document by ID
        doc_id = str(row_key.value)
        for doc in self._documents:
            if doc.get("id") == doc_id:
                document_path = f"{self._current_collection}/{doc_id}"
                self.post_message(DocumentRowSelected(document_path, doc))
                break

    def get_selected_document(self) -> Optional[Dict[str, Any]]:
        """Get the currently selected document."""
        if not self._documents:
            return None

        row_key = self.cursor_row
        if row_key is None or row_key >= len(self._documents):
            return None

        return self._documents[row_key]

    def get_selected_document_path(self) -> Optional[str]:
        """Get the path of the currently selected document."""
        doc = self.get_selected_document()
        if doc and self._current_collection:
            return f"{self._current_collection}/{doc.get('id')}"
        return None

    @property
    def current_collection(self) -> Optional[str]:
        """Get the current collection path."""
        return self._current_collection

    @property
    def document_count(self) -> int:
        """Get the number of loaded documents."""
        return len(self._documents)

    def refresh_data(self) -> None:
        """Refresh the current collection data."""
        if self._current_collection:
            self.load_collection(self._current_collection)
