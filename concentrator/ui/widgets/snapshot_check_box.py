"""Check box driven by a ``ButtonSnapshot``."""

from PySide6.QtCore import QSignalBlocker, Signal
from PySide6.QtWidgets import QCheckBox, QWidget

from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.button_snapshot import ButtonSnapshot


class SnapshotCheckBox(QCheckBox):
    """Shows a snapshot (``checked`` is the stored value) and emits ``action_requested(int)`` on a user click.

    A click toggles the box at once; the next snapshot shows the stored value again if the action did
    not change it (refused, failed or ignored while busy).
    """

    action_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create an empty check box.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._action = ActionIdEnum.UNSET
        self.clicked.connect(self._emit_action)

    def apply(self, snapshot: ButtonSnapshot) -> None:
        """Show a snapshot (idempotent).

        Args:
            snapshot: Check box state.
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
