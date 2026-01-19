"""Document editor screen for creating and updating documents."""

import json
from typing import TYPE_CHECKING, Any, Dict, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Static, TextArea

if TYPE_CHECKING:
    from ...service import FirestoreService


class EditorScreen(Screen):
    """Screen for editing or creating documents."""

    BINDINGS = [
        Binding("ctrl+s", "save", "Save", show=True),
        Binding("escape", "cancel", "Cancel", show=True),
    ]

    def __init__(
        self,
        service: "FirestoreService",
        document_path: Optional[str] = None,
        document_data: Optional[Dict[str, Any]] = None,
        collection_path: Optional[str] = None,
        is_new: bool = False,
    ) -> None:
        super().__init__()
        self.service = service
        self.document_path = document_path
        self.document_data = document_data or {}
        self.collection_path = collection_path
        self.is_new = is_new

        # Remove 'id' from editable data for existing documents
        if not is_new and "id" in self.document_data:
            self._doc_id = self.document_data.pop("id")
        else:
            self._doc_id = None

    def compose(self) -> ComposeResult:
        if self.is_new:
            title = f"New Document in {self.collection_path}"
        else:
            title = f"Edit: {self.document_path}"

        yield Header()
        yield Container(
            Static(f"✏️ {title}", id="editor-header"),
            Container(
                Static("Document ID:", classes="label") if self.is_new else Static(""),
                Input(
                    placeholder="Leave empty for auto-generated ID",
                    id="doc-id-input",
                )
                if self.is_new
                else Static(""),
                Static("JSON Data:", classes="label"),
                TextArea(
                    json.dumps(self.document_data, indent=2, default=str),
                    language="json",
                    id="json-editor",
                    show_line_numbers=True,
                ),
                id="editor-form",
            ),
            Horizontal(
                Button("Save", variant="primary", id="save-btn"),
                Button("Cancel", variant="default", id="cancel-btn"),
                id="editor-buttons",
            ),
            id="editor-container",
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "save-btn":
            self.action_save()
        elif event.button.id == "cancel-btn":
            self.action_cancel()

    def action_save(self) -> None:
        """Save the document."""
        editor = self.query_one("#json-editor", TextArea)
        json_text = editor.text

        # Validate JSON
        try:
            data = json.loads(json_text)
        except json.JSONDecodeError as e:
            self.notify(f"Invalid JSON: {e}", severity="error")
            return

        if not isinstance(data, dict):
            self.notify("Document must be a JSON object", severity="error")
            return

        try:
            if self.is_new:
                # Creating new document
                doc_id_input = self.query_one("#doc-id-input", Input)
                doc_id = doc_id_input.value.strip() or None

                new_id = self.service.create_document(
                    collection_path=self.collection_path,
                    data=data,
                    document_id=doc_id,
                )
                self.notify(f"Created: {self.collection_path}/{new_id}", severity="information")
            else:
                # Updating existing document
                self.service.update_document(
                    document_path=self.document_path,
                    data=data,
                    merge=True,
                )
                self.notify(f"Updated: {self.document_path}", severity="information")

            self.app.pop_screen()

        except Exception as e:
            self.notify(f"Error saving: {e}", severity="error")

    def action_cancel(self) -> None:
        """Cancel editing."""
        self.app.pop_screen()


class QuickEditScreen(Screen):
    """Quick edit screen for single field updates."""

    BINDINGS = [
        Binding("ctrl+s", "save", "Save"),
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(
        self,
        service: "FirestoreService",
        document_path: str,
        field_name: str,
        current_value: Any,
    ) -> None:
        super().__init__()
        self.service = service
        self.document_path = document_path
        self.field_name = field_name
        self.current_value = current_value

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static(f"Edit field: {self.field_name}", id="editor-header"),
            Container(
                Static(f"Document: {self.document_path}", classes="label"),
                Static(f"Field: {self.field_name}", classes="label"),
                TextArea(
                    json.dumps(self.current_value, indent=2, default=str),
                    language="json",
                    id="field-editor",
                    show_line_numbers=True,
                ),
                id="editor-form",
            ),
            Horizontal(
                Button("Save", variant="primary", id="save-btn"),
                Button("Cancel", variant="default", id="cancel-btn"),
                id="editor-buttons",
            ),
            id="editor-container",
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-btn":
            self.action_save()
        elif event.button.id == "cancel-btn":
            self.action_cancel()

    def action_save(self) -> None:
        editor = self.query_one("#field-editor", TextArea)
        json_text = editor.text

        try:
            value = json.loads(json_text)
        except json.JSONDecodeError as e:
            self.notify(f"Invalid JSON: {e}", severity="error")
            return

        try:
            self.service.update_document(
                document_path=self.document_path,
                data={self.field_name: value},
                merge=True,
            )
            self.notify(f"Updated {self.field_name}", severity="information")
            self.app.pop_screen()
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    def action_cancel(self) -> None:
        self.app.pop_screen()
