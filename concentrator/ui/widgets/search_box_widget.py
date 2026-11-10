"""Search field driven by a ``SearchBoxSnapshot``; it is never disabled, so typing is never cut."""

from PySide6.QtCore import QSignalBlocker, Signal
from PySide6.QtWidgets import QLineEdit, QWidget

from concentrator.presentation.journal.journal_snapshot import SearchBoxSnapshot


class SearchBoxWidget(QLineEdit):
    """Emits ``search_changed(str)`` on every change made by the user (keys or the clear button)."""

    search_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create the field with a clear button.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setClearButtonEnabled(True)
        self.textChanged.connect(self.search_changed.emit)

    def apply(self, snapshot: SearchBoxSnapshot) -> None:
        """Show a snapshot; the text is set only when it differs, so the cursor stays where it is.

        Args:
            snapshot: Field state.
        """
        blocker = QSignalBlocker(self)
        if self.text() != snapshot.text:
            self.setText(snapshot.text)
        self.setPlaceholderText(snapshot.placeholder)
        self.setToolTip(snapshot.tooltip)
        blocker.unblock()
