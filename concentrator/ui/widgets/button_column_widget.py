"""A column of ``SnapshotButton``s, one per ``ButtonSnapshot``, created as the snapshots require."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QVBoxLayout, QWidget

from concentrator.presentation.common.button_snapshot import ButtonSnapshot
from concentrator.ui.widgets.snapshot_button import SnapshotButton


class ButtonColumnWidget(QWidget):
    """Emits ``action_requested(int)`` when one of its buttons is clicked."""

    action_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create an empty column.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._buttons: list[SnapshotButton] = []

    @property
    def buttons(self) -> tuple[SnapshotButton, ...]:
        """The buttons, in order (for tests)."""
        return tuple(self._buttons)

    def render_snapshot(self, snapshots: tuple[ButtonSnapshot, ...]) -> None:
        """Show one button per snapshot, in order.

        Args:
            snapshots: Button states.
        """
        while len(self._buttons) < len(snapshots):
            button = SnapshotButton(self)
            button.action_requested.connect(self.action_requested)
            self._layout.addWidget(button)
            self._buttons.append(button)
        for button, snapshot in zip(self._buttons, snapshots, strict=False):
            button.apply(snapshot)
        for button in self._buttons[len(snapshots) :]:
            button.setVisible(False)
