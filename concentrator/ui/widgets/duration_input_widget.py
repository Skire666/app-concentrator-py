"""Hours, minutes and seconds input."""

from typing import Final

from PySide6.QtCore import QSignalBlocker, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSpinBox, QWidget

from concentrator.ui.support.styles import INVALID_INPUT_STYLE, INVALID_PROPERTY, set_dynamic_property

MAX_MINUTE: Final = 59
MAX_SECOND: Final = 59


class DurationInputWidget(QWidget):
    """Three spin boxes; emits ``duration_changed(hours, minutes, seconds)`` on every change."""

    duration_changed = Signal(int, int, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create the input.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setStyleSheet(INVALID_INPUT_STYLE)
        self._spins = (QSpinBox(self), QSpinBox(self), QSpinBox(self))
        self._units = (QLabel(self), QLabel(self), QLabel(self))
        self._spins[1].setMaximum(MAX_MINUTE)
        self._spins[2].setMaximum(MAX_SECOND)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        for spin, unit in zip(self._spins, self._units, strict=True):
            spin.valueChanged.connect(self._emit)
            layout.addWidget(spin)
            layout.addWidget(unit)
        layout.addStretch(1)

    @property
    def spin_boxes(self) -> tuple[QSpinBox, QSpinBox, QSpinBox]:
        """Hours, minutes and seconds (for tests)."""
        return self._spins

    def apply(
        self, values: tuple[int, int, int], *, max_hours: int, units: tuple[str, str, str], invalid: bool
    ) -> None:
        """Show a duration without emitting ``duration_changed``.

        Args:
            values: Hours, minutes, seconds.
            max_hours: Highest hour value.
            units: Unit texts after the three boxes.
            invalid: Whether to show the invalid style.
        """
        self._spins[0].setMaximum(max_hours)
        for spin, value in zip(self._spins, values, strict=True):
            blocker = QSignalBlocker(spin)
            spin.setValue(value)
            blocker.unblock()
            set_dynamic_property(spin, INVALID_PROPERTY, invalid)
        for label, text in zip(self._units, units, strict=True):
            label.setText(text)

    def _emit(self) -> None:
        """Forward the current values."""
        hours, minutes, seconds = (spin.value() for spin in self._spins)
        self.duration_changed.emit(hours, minutes, seconds)
