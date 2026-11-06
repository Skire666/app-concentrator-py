"""Centered text shown where a feature panel will appear in a later phase."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class PlaceholderWidget(QWidget):
    """A centered, word-wrapped label."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create an empty placeholder.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._label = QLabel(self)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setWordWrap(True)
        self._label.setEnabled(False)
        layout = QVBoxLayout(self)
        layout.addWidget(self._label)

    @property
    def text(self) -> str:
        """Text currently shown."""
        return self._label.text()

    def set_text(self, text: str) -> None:
        """Show a text (plain text, never rich text).

        Args:
            text: Translated text.
        """
        self._label.setTextFormat(Qt.TextFormat.PlainText)
        self._label.setText(text)
