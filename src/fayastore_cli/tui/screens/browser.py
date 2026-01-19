"""Browser screen for navigating collections and documents."""

from typing import TYPE_CHECKING, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from ..widgets import (
    CollectionSelected,
    CollectionTree,
    DocumentRowSelected,
    DocumentSelected,
    DocumentTable,
)

if TYPE_CHECKING:
    from ...service import FirestoreService


class BrowserScreen(Screen):
    """Main browser screen for exploring Firestore data."""

    BINDINGS = [
        Binding("r", "refresh", "Refresh", show=True),
        Binding("n", "new_document", "New", show=True),
        Binding("e", "edit_document", "Edit", show=True),
        Binding("d", "delete_document", "Delete", show=True),
        Binding("enter", "view_document", "View", show=True),
        Binding("/", "search", "Search", show=True),
    ]

    def __init__(self, service: "FirestoreService") -> None:
        super().__init__()
        self.service = service
        self._current_collection: Optional[str] = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Vertical(
                Static(f"📁 {self.service.project}", classes="panel-header"),
                CollectionTree(self.service, id="collection-tree"),
                id="collections-panel",
            ),
            Vertical(
                Static("Select a collection", id="documents-header", classes="panel-header"),
                DocumentTable(self.service, id="document-table"),
                Static("", id="status-bar"),
                id="documents-panel",
            ),
            id="browser-container",
        )
        yield Footer()

    def on_collection_selected(self, event: CollectionSelected) -> None:
        """Handle collection selection from tree."""
        self._current_collection = event.collection_path
        self._load_documents(event.collection_path)

    def on_document_selected(self, event: DocumentSelected) -> None:
        """Handle document selection from tree."""
        self._view_document(event.document_path)

    def on_document_row_selected(self, event: DocumentRowSelected) -> None:
        """Handle document row double-click in table."""
        self._view_document(event.document_path)

    def _load_documents(self, collection_path: str) -> None:
        """Load documents for the selected collection."""
        table = self.query_one("#document-table", DocumentTable)
        header = self.query_one("#documents-header", Static)
        status = self.query_one("#status-bar", Static)

        header.update(f"📁 {collection_path}")
        table.load_collection(collection_path)
        status.update(f"{table.document_count} documents loaded")

    def _view_document(self, document_path: str) -> None:
        """Open document viewer for the selected document."""
        from .viewer import ViewerScreen

        doc = self.service.get_document(document_path)
        if doc:
            self.app.push_screen(ViewerScreen(self.service, document_path, doc))

    def action_refresh(self) -> None:
        """Refresh the current view."""
        tree = self.query_one("#collection-tree", CollectionTree)
        table = self.query_one("#document-table", DocumentTable)

        tree.refresh_tree()
        if self._current_collection:
            table.refresh_data()

        self.notify("Refreshed", severity="information")

    def action_new_document(self) -> None:
        """Create a new document."""
        if not self._current_collection:
            self.notify("Select a collection first", severity="warning")
            return

        from .editor import EditorScreen

        self.app.push_screen(
            EditorScreen(
                self.service,
                collection_path=self._current_collection,
                is_new=True,
            )
        )

    def action_edit_document(self) -> None:
        """Edit the selected document."""
        table = self.query_one("#document-table", DocumentTable)
        doc_path = table.get_selected_document_path()
        doc_data = table.get_selected_document()

        if not doc_path or not doc_data:
            self.notify("Select a document first", severity="warning")
            return

        from .editor import EditorScreen

        self.app.push_screen(
            EditorScreen(
                self.service,
                document_path=doc_path,
                document_data=doc_data,
                is_new=False,
            )
        )

    def action_delete_document(self) -> None:
        """Delete the selected document."""
        table = self.query_one("#document-table", DocumentTable)
        doc_path = table.get_selected_document_path()

        if not doc_path:
            self.notify("Select a document first", severity="warning")
            return

        from .confirm import ConfirmScreen

        def on_confirm(confirmed: bool) -> None:
            if confirmed:
                try:
                    self.service.delete_document(doc_path)
                    self.notify(f"Deleted: {doc_path}", severity="information")
                    table.refresh_data()
                except Exception as e:
                    self.notify(f"Error: {e}", severity="error")

        self.app.push_screen(
            ConfirmScreen(
                f"Delete document?\n\n{doc_path}",
                on_confirm,
            )
        )

    def action_view_document(self) -> None:
        """View the selected document."""
        table = self.query_one("#document-table", DocumentTable)
        doc_path = table.get_selected_document_path()
        doc_data = table.get_selected_document()

        if doc_path and doc_data:
            self._view_document(doc_path)

    def action_search(self) -> None:
        """Open search/filter dialog."""
        if not self._current_collection:
            self.notify("Select a collection first", severity="warning")
            return

        from .query import QueryScreen

        self.app.push_screen(QueryScreen(self.service, self._current_collection))

    def on_screen_resume(self) -> None:
        """Called when returning to this screen."""
        # Refresh data in case changes were made
        if self._current_collection:
            table = self.query_one("#document-table", DocumentTable)
            table.refresh_data()
