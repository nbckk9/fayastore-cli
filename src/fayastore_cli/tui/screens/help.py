"""Help screen."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Static


HELP_TEXT = """\
[bold cyan]Fayastore TUI[/bold cyan]
[dim]Keyboard shortcuts[/dim]

[bold yellow]Navigation[/bold yellow]
  [reverse]↑[/reverse] [reverse]↓[/reverse]     Navigate items
  [reverse]Enter[/reverse]       Select/View item
  [reverse]Tab[/reverse]         Switch panels
  [reverse]Escape[/reverse]      Go back / Close

[bold yellow]Document Operations[/bold yellow]
  [reverse]n[/reverse]           New document
  [reverse]e[/reverse]           Edit selected document
  [reverse]d[/reverse]           Delete selected document
  [reverse]c[/reverse]           Copy JSON (viewer)

[bold yellow]Collection Operations[/bold yellow]
  [reverse]r[/reverse]           Refresh view
  [reverse]/[/reverse]           Search / Query

[bold yellow]General[/bold yellow]
  [reverse]?[/reverse]           Show help
  [reverse]q[/reverse]           Quit

[dim]Press Escape or ? to close[/dim]
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
