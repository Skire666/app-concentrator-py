"""Page made of one placeholder text, used until a page gets its feature panels."""

from PySide6.QtWidgets import QVBoxLayout, QWidget

from concentrator.ui.widgets.placeholder_widget import PlaceholderWidget


class PlaceholderPage(QWidget):
    """A page showing one placeholder text (Journal and Settings until phase 4)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build the page.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._placeholder = PlaceholderWidget(self)
        QVBoxLayout(self).addWidget(self._placeholder)

    @property
    def text(self) -> str:
        """Text shown (for tests)."""
        return self._placeholder.text

    def render_snapshot(self, text: str) -> None:
        """Show the page text.

        Args:
            text: Translated text.
        """
        self._placeholder.set_text(text)
