"""The selected journal entry in full: message and traceback, selectable."""

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget

from concentrator.presentation.journal.journal_snapshot import JournalDetailSnapshot


class JournalDetailPanel(QWidget):
    """Read-only text in a fixed-width font, so tracebacks keep their alignment."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build the panel.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._text = QPlainTextEdit(self)
        self._text.setReadOnly(True)
        self._text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._text.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._text)

    @property
    def text(self) -> str:
        """Text shown (for tests)."""
        return self._text.toPlainText()

    def render_snapshot(self, snapshot: JournalDetailSnapshot) -> None:
        """Show the entry (idempotent: the text is replaced only when it changed).

        Args:
            snapshot: Detail state.
        """
        if self._text.toPlainText() != snapshot.text:
            self._text.setPlainText(snapshot.text)
        self._text.setPlaceholderText(snapshot.placeholder)
