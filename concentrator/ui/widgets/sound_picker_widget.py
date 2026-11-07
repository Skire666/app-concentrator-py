"""Sound list with a "Choose a file..." button."""

from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QWidget

from concentrator.presentation.common.button_snapshot import ButtonSnapshot
from concentrator.ui.support.styles import INVALID_INPUT_STYLE, INVALID_PROPERTY, set_dynamic_property
from concentrator.ui.widgets.snapshot_button import SnapshotButton


class SoundPickerWidget(QWidget):
    """Emits ``sound_selected(index)`` and the button's ``action_requested(int)``."""

    sound_selected = Signal(int)
    action_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create the picker.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setStyleSheet(INVALID_INPUT_STYLE)
        self._combo = QComboBox(self)
        self._combo.currentIndexChanged.connect(self.sound_selected)
        self._choose = SnapshotButton(self)
        self._choose.action_requested.connect(self.action_requested)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._combo, 1)
        layout.addWidget(self._choose)

    @property
    def combo(self) -> QComboBox:
        """The list (for tests)."""
        return self._combo

    @property
    def choose_button(self) -> SnapshotButton:
        """The "Choose a file..." button (for tests)."""
        return self._choose

    def apply(
        self,
        options: tuple[str, ...],
        tooltips: tuple[str, ...],
        selected: int,
        *,
        choose: ButtonSnapshot,
        invalid: bool,
    ) -> None:
        """Show the choices without emitting ``sound_selected``.

        Args:
            options: Text of each choice.
            tooltips: Tooltip of each choice.
            selected: Index of the selected choice.
            choose: State of the "Choose a file..." button.
            invalid: Whether to show the invalid style.
        """
        blocker = QSignalBlocker(self._combo)
        if [self._combo.itemText(index) for index in range(self._combo.count())] != list(options):
            self._combo.clear()
            self._combo.addItems(list(options))
        for index, tooltip in enumerate(tooltips):
            self._combo.setItemData(index, tooltip, Qt.ItemDataRole.ToolTipRole)
        self._combo.setCurrentIndex(selected)
        self._combo.setToolTip(tooltips[selected] if 0 <= selected < len(tooltips) else "")
        blocker.unblock()
        set_dynamic_property(self._combo, INVALID_PROPERTY, invalid)
        self._choose.apply(choose)
