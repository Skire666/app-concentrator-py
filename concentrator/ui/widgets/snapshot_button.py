"""Push button driven by a ``ButtonSnapshot``."""

from PySide6.QtCore import QSignalBlocker, Signal
from PySide6.QtWidgets import QPushButton, QWidget

from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.button_snapshot import ButtonSnapshot


class SnapshotButton(QPushButton):
    """Shows a snapshot and emits ``action_requested(int)`` with the snapshot's action on click."""

    action_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create an empty button.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._action = ActionIdEnum.UNSET
        self.clicked.connect(self._emit_action)

    def apply(self, snapshot: ButtonSnapshot) -> None:
        """Show a snapshot (idempotent).

        Args:
            snapshot: Button state.
        """
        blocker = QSignalBlocker(self)
        self._action = snapshot.action
        self.setText(snapshot.text)
        self.setToolTip(snapshot.tooltip)
        self.setEnabled(snapshot.enabled)
        self.setVisible(snapshot.visible)
        self.setChecked(snapshot.checked)
        blocker.unblock()

    def _emit_action(self) -> None:
        """Forward a click as the snapshot's action."""
        self.action_requested.emit(int(self._action))
