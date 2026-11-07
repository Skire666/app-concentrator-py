"""Volume slider with its value and a "Preview" button."""

from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSlider, QWidget

from concentrator.presentation.common.button_snapshot import ButtonSnapshot
from concentrator.ui.support.styles import INVALID_INPUT_STYLE, INVALID_PROPERTY, set_dynamic_property
from concentrator.ui.widgets.snapshot_button import SnapshotButton


class VolumeSliderWidget(QWidget):
    """Emits ``volume_changed(percent)`` and the button's ``action_requested(int)``."""

    volume_changed = Signal(int)
    action_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create the slider.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setStyleSheet(INVALID_INPUT_STYLE)
        self._slider = QSlider(Qt.Orientation.Horizontal, self)
        self._slider.valueChanged.connect(self.volume_changed)
        self._value = QLabel(self)
        self._value.setTextFormat(Qt.TextFormat.PlainText)
        self._preview = SnapshotButton(self)
        self._preview.action_requested.connect(self.action_requested)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._slider, 1)
        layout.addWidget(self._value)
        layout.addWidget(self._preview)

    @property
    def slider(self) -> QSlider:
        """The slider (for tests)."""
        return self._slider

    @property
    def preview_button(self) -> SnapshotButton:
        """The "Preview" button (for tests)."""
        return self._preview

    def apply(self, value: int, maximum: int, value_text: str, *, preview: ButtonSnapshot, invalid: bool) -> None:
        """Show a volume without emitting ``volume_changed``.

        Args:
            value: Volume in percent.
            maximum: Highest value.
            value_text: Text shown next to the slider.
            preview: State of the "Preview" button.
            invalid: Whether to show the invalid style.
        """
        blocker = QSignalBlocker(self._slider)
        self._slider.setMaximum(maximum)
        self._slider.setValue(value)
        blocker.unblock()
        set_dynamic_property(self._slider, INVALID_PROPERTY, invalid)
        self._value.setText(value_text)
        self._preview.apply(preview)
