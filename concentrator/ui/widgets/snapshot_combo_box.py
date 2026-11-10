"""List driven by a ``ChoiceFieldSnapshot``."""

from PySide6.QtCore import QSignalBlocker, Signal
from PySide6.QtWidgets import QComboBox, QWidget

from concentrator.presentation.settings.settings_snapshot import ChoiceFieldSnapshot
from concentrator.ui.support.styles import INVALID_PROPERTY, set_dynamic_property


class SnapshotComboBox(QComboBox):
    """Emits ``index_selected(int)`` when the user picks an option; renders never emit it."""

    index_selected = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create an empty list.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self.currentIndexChanged.connect(self.index_selected.emit)

    def apply(self, snapshot: ChoiceFieldSnapshot) -> None:
        """Show a snapshot (idempotent).

        Args:
            snapshot: Field state.
        """
        blocker = QSignalBlocker(self)
        if [self.itemText(index) for index in range(self.count())] != list(snapshot.options):
            self.clear()
            self.addItems(list(snapshot.options))
        self.setCurrentIndex(snapshot.selected)
        self.setToolTip(snapshot.tooltip)
        blocker.unblock()
        set_dynamic_property(self, INVALID_PROPERTY, bool(snapshot.error))
