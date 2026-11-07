"""Inline error under a form field."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QWidget

from concentrator.ui.support.styles import FIELD_ERROR_STYLE


class FieldErrorLabel(QLabel):
    """Hidden when there is no message."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create an empty, hidden label.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setWordWrap(True)
        self.setStyleSheet(FIELD_ERROR_STYLE)
        self.setVisible(False)

    def set_error(self, message: str) -> None:
        """Show a message, or hide the label.

        Args:
            message: Translated message, ``""`` for none.
        """
        self.setText(message)
        self.setVisible(bool(message))
