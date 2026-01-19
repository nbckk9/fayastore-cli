"""Help screen."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Static


HELP_TEXT = """\
[bold cyan]Fayastore TUI - Keyboard Shortcuts[/bold cyan]

[bold]Navigation[/bold]
  [green]↑/↓[/green]     Navigate items
  [green]Enter[/green]   Select/View item
  [green]Tab[/green]     Switch panels
  [green]Escape[/green]  Go back / Close

[bold]Document Operations[/bold]
  [green]n[/green]       New document
  [green]e[/green]       Edit selected document
  [green]d[/green]       Delete selected document
  [green]c[/green]       Copy document JSON (in viewer)

[bold]Collection Operations[/bold]
  [green]r[/green]       Refresh current view
  [green]/[/green]       Search / Query builder

[bold]General[/bold]
  [green]?[/green]       Show this help
  [green]q[/green]       Quit application

[dim]Press Escape or ? to close this help[/dim]
"""


class HelpScreen(ModalScreen):
    """Modal screen showing keyboard shortcuts."""

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("?", "close", "Close"),
        Binding("q", "close", "Close"),
    ]

    def compose(self) -> ComposeResult:
        yield Container(
            Container(
                Static(HELP_TEXT, id="help-text"),
                id="help-content",
            ),
            id="help-container",
        )

    def action_close(self) -> None:
        """Close the help screen."""
        self.app.pop_screen()
