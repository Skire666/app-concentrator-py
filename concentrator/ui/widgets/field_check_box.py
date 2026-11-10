"""Check box editing a form value, driven by a ``ToggleFieldSnapshot``."""

from PySide6.QtCore import QSignalBlocker, Signal
from PySide6.QtWidgets import QCheckBox, QWidget

from concentrator.presentation.settings.settings_snapshot import ToggleFieldSnapshot


class FieldCheckBox(QCheckBox):
    """Emits ``value_changed(bool)`` when the user clicks it; renders never emit it."""

    value_changed = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create the check box.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self.toggled.connect(self.value_changed.emit)

    def apply(self, snapshot: ToggleFieldSnapshot) -> None:
        """Show a snapshot (idempotent).

        Args:
            snapshot: Field state.
        """
        blocker = QSignalBlocker(self)
        self.setText(snapshot.text)
        self.setChecked(snapshot.checked)
        blocker.unblock()
