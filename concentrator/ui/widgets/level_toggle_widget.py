"""Checkable button of one journal level, driven by a ``LevelToggleSnapshot``."""

from typing import override

from PySide6.QtCore import QSignalBlocker, Signal
from PySide6.QtWidgets import QToolButton, QWidget

from concentrator.presentation.journal.journal_snapshot import LevelToggleSnapshot


class LevelToggleWidget(QToolButton):
    """Emits ``level_toggled(int)`` on click; its checked state only comes from the snapshot."""

    level_toggled = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create the button.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setCheckable(True)
        self.setAutoRaise(True)
        self._level = 0
        self.clicked.connect(lambda _checked=False: self.level_toggled.emit(self._level))

    @override
    def nextCheckState(self) -> None:
        """Keep the checked state on click: the next render decides it."""

    def apply(self, snapshot: LevelToggleSnapshot) -> None:
        """Show a snapshot (idempotent).

        Args:
            snapshot: Toggle state.
        """
        blocker = QSignalBlocker(self)
        self._level = snapshot.level
        self.setText(snapshot.text)
        self.setToolTip(snapshot.tooltip)
        self.setChecked(snapshot.checked)
        self.setEnabled(snapshot.enabled)
        blocker.unblock()
