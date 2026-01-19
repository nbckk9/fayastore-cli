"""Confirmation dialog screen."""

from typing import Callable

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class ConfirmScreen(ModalScreen[bool]):
    """A modal confirmation dialog."""

    BINDINGS = [
        Binding("y", "confirm", "Yes"),
        Binding("n", "cancel", "No"),
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(
        self,
        message: str,
        callback: Callable[[bool], None],
        title: str = "Confirm",
    ) -> None:
        super().__init__()
        self.message = message
        self.callback = callback
        self.title = title

    def compose(self) -> ComposeResult:
        yield Container(
            Container(
                Static(f"⚠️ {self.title}", id="confirm-title"),
                Static(self.message, id="confirm-message"),
                Horizontal(
                    Button("Yes", variant="error", id="yes-btn"),
                    Button("No", variant="default", id="no-btn"),
                    id="confirm-buttons",
                ),
                id="confirm-content",
            ),
            id="confirm-dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "yes-btn":
            self.action_confirm()
        else:
            self.action_cancel()

    def action_confirm(self) -> None:
        self.callback(True)
        self.app.pop_screen()

    def action_cancel(self) -> None:
        self.callback(False)
        self.app.pop_screen()
