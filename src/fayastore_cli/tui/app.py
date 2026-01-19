"""Main Textual TUI application for Fayastore."""

from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Footer, Header, Static

from ..service import FirestoreService, get_service
from .screens.browser import BrowserScreen
from .screens.editor import EditorScreen
from .screens.viewer import ViewerScreen


class FayastoreApp(App):
    """Main Fayastore TUI application."""

    TITLE = "Fayastore"
    SUB_TITLE = "Firestore CLI & TUI"
    CSS_PATH = "styles.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("?", "help", "Help", show=True),
    ]

    SCREENS = {
        "browser": BrowserScreen,
        "viewer": ViewerScreen,
        "editor": EditorScreen,
    }

    def __init__(
        self,
        credentials_path: Optional[str] = None,
        project: Optional[str] = None,
    ):
        """Initialize the Fayastore TUI app."""
        super().__init__()
        self.credentials_path = credentials_path
        self.project = project
        self._service: Optional[FirestoreService] = None

    @property
    def service(self) -> FirestoreService:
        """Get or create the Firestore service."""
        if self._service is None:
            self._service = get_service(
                credentials_path=self.credentials_path,
                project=self.project,
            )
        return self._service

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        # Push the browser screen as the main screen
        self.push_screen(BrowserScreen(self.service))

    def action_back(self) -> None:
        """Go back to previous screen (only if not on home screen)."""
        # screen_stack includes the base screen, so >2 means we have pushed screens beyond browser
        if len(self.screen_stack) > 2:
            self.pop_screen()

    def action_help(self) -> None:
        """Show help dialog."""
        from .screens.help import HelpScreen
        self.push_screen(HelpScreen())


class LoadingScreen(Static):
    """A simple loading indicator."""

    def compose(self) -> ComposeResult:
        yield Static("Loading...", id="loading-text")
