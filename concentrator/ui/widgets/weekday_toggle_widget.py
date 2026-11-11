"""Seven toggle buttons, one per weekday, driven by ``WeekdayToggleSnapshot`` values."""

from functools import partial

from PySide6.QtCore import QSignalBlocker, Signal
from PySide6.QtWidgets import QHBoxLayout, QToolButton, QWidget

from concentrator.presentation.todo.task_edit_snapshot import WeekdayToggleSnapshot


class WeekdayToggleWidget(QWidget):
    """Emits ``day_toggled(int, bool)`` (weekday value, checked) when the user clicks a day.

    A click shows the new state at once; the next snapshot shows the stored one.
    """

    day_toggled = Signal(int, bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create the row (the buttons come with the first snapshot).

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._buttons: list[QToolButton] = []
        self._values: list[int] = []

    @property
    def buttons(self) -> tuple[QToolButton, ...]:
        """The day buttons, Monday first (for tests)."""
        return tuple(self._buttons)

    def apply(self, days: tuple[WeekdayToggleSnapshot, ...]) -> None:
        """Show the days (idempotent).

        Args:
            days: One snapshot per weekday, in order.
        """
        while len(self._buttons) < len(days):
            button = QToolButton(self)
            button.setCheckable(True)
            button.clicked.connect(partial(self._emit, len(self._buttons)))
            self._layout.addWidget(button)
            self._buttons.append(button)
        self._values = [day.value for day in days]
        for button, day in zip(self._buttons, days, strict=False):
            blocker = QSignalBlocker(button)
            button.setText(day.text)
            button.setToolTip(day.tooltip)
            button.setChecked(day.checked)
            blocker.unblock()

    def _emit(self, index: int) -> None:
        """Send the weekday of a clicked button and its new state.

        Args:
            index: Position of the button.
        """
        if 0 <= index < len(self._values):
            self.day_toggled.emit(self._values[index], self._buttons[index].isChecked())
