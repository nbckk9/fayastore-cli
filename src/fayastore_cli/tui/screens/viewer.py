"""Document viewer screen."""

import json
from typing import TYPE_CHECKING, Any, Dict

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from ..widgets import JsonViewer

if TYPE_CHECKING:
    from ...service import FirestoreService


class ViewerScreen(Screen):
    """Screen for viewing a single document."""

    BINDINGS = [
        Binding("e", "edit", "Edit", show=True),
        Binding("d", "delete", "Delete", show=True),
        Binding("c", "copy", "Copy JSON", show=True),
        Binding("escape", "back", "Back", show=True),
    ]

    def __init__(
        self,
        service: "FirestoreService",
        document_path: str,
        document_data: Dict[str, Any],
    ) -> None:
        super().__init__()
        self.service = service
        self.document_path = document_path
        self.document_data = document_data

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static(f"📄 {self.document_path}", id="document-path"),
            ScrollableContainer(
                JsonViewer(self.document_data, title="Document Data", id="json-viewer"),
                id="document-content",
            ),
            id="viewer-container",
        )
        yield Footer()

    def action_edit(self) -> None:
        """Edit this document."""
        from .editor import EditorScreen

        self.app.push_screen(
            EditorScreen(
                self.service,
                document_path=self.document_path,
                document_data=self.document_data,
                is_new=False,
            )
        )

    def action_delete(self) -> None:
        """Delete this document."""
        from .confirm import ConfirmScreen

        def on_confirm(confirmed: bool) -> None:
            if confirmed:
                try:
                    self.service.delete_document(self.document_path)
                    self.notify(f"Deleted: {self.document_path}", severity="information")
                    # Go back twice (viewer -> browser)
                    self.app.pop_screen()
                except Exception as e:
                    self.notify(f"Error: {e}", severity="error")

        self.app.push_screen(
            ConfirmScreen(
                f"Delete document?\n\n{self.document_path}",
                on_confirm,
            )
        )

    def action_copy(self) -> None:
        """Copy document JSON to clipboard."""
        try:
            json_str = json.dumps(self.document_data, indent=2, default=str)
            # Note: Textual doesn't have built-in clipboard support,
            # but we can use pyperclip if available
            try:
                import pyperclip
                pyperclip.copy(json_str)
                self.notify("Copied to clipboard", severity="information")
            except ImportError:
                self.notify("Install pyperclip for clipboard support", severity="warning")
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    def action_back(self) -> None:
        """Go back to browser."""
        self.app.pop_screen()

    def refresh_data(self) -> None:
        """Refresh the document data."""
        try:
            doc = self.service.get_document(self.document_path)
            if doc:
                self.document_data = doc
                viewer = self.query_one("#json-viewer", JsonViewer)
                viewer.set_data(doc)
            else:
                self.notify("Document no longer exists", severity="warning")
                self.app.pop_screen()
        except Exception as e:
            self.notify(f"Error refreshing: {e}", severity="error")
