"""Loading spinner widget for async operations."""

from typing import Optional

from textual.widgets import Static


class Spinner(Static):
    """An animated spinner widget for loading states."""

    SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(
        self,
        text: str = "Loading...",
        id: Optional[str] = None,
    ) -> None:
        super().__init__(id=id)
        self._text = text
        self._frame_index = 0

    def on_mount(self) -> None:
        """Start the animation."""
        self._update_content()

    def on_timer(self) -> None:
        """Update the spinner frame."""
        self._frame_index = (self._frame_index + 1) % len(self.SPINNER_FRAMES)
        self._update_content()

    def _update_content(self) -> None:
        """Update the displayed content."""
        frame = self.SPINNER_FRAMES[self._frame_index]
        self.update(f"{frame} {self._text}")

    def set_text(self, text: str) -> None:
        """Set the loading text."""
        self._text = text
        self._update_content()

    @property
    def is_animating(self) -> bool:
        """Check if the spinner is animating."""
        return self._frame_index > 0

    def stop(self) -> None:
        """Stop the spinner animation."""
        self.update(f"✓ {self._text}")


class LoadingOverlay(Static):
    """A full-screen loading overlay."""

    def __init__(
        self,
        message: str = "Loading...",
        id: Optional[str] = None,
    ) -> None:
        super().__init__(id=id)
        self._message = message

    def compose(self):
        from textual.containers import Center
        from textual.widgets import Spinner as TextualSpinner

        yield Center(
            TextualSpinner() + " " + self._message,
            classes="loading-content",
        )
