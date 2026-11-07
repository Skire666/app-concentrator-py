"""Timer at the top of zone 2: digits, caption, three buttons."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from concentrator.presentation.timer.timer_layout import TimerLayout
from concentrator.presentation.timer.timer_snapshot import TimerSnapshot
from concentrator.ui.widgets.duration_display_widget import DurationDisplayWidget
from concentrator.ui.widgets.snapshot_button import SnapshotButton


class TimerPanel(QWidget):
    """Emits ``action_requested(int)`` with the action shown by the clicked button."""

    action_requested = Signal(int)

    def __init__(self, layout: TimerLayout, parent: QWidget | None = None) -> None:
        """Build the panel.

        Args:
            layout: Font of the digits.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._digits = DurationDisplayWidget(layout.font_family, layout.font_size_px, self)
        self._caption = QLabel(self)
        self._caption.setTextFormat(Qt.TextFormat.PlainText)
        self._caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._buttons = (SnapshotButton(self), SnapshotButton(self), SnapshotButton(self))
        buttons = QHBoxLayout()
        for button in self._buttons:
            button.action_requested.connect(self.action_requested)
            buttons.addWidget(button)
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.addWidget(self._digits)
        column.addWidget(self._caption)
        column.addLayout(buttons)

    @property
    def digits(self) -> DurationDisplayWidget:
        """The digits (for tests)."""
        return self._digits

    @property
    def caption(self) -> QLabel:
        """The caption (for tests)."""
        return self._caption

    @property
    def buttons(self) -> tuple[SnapshotButton, SnapshotButton, SnapshotButton]:
        """Left, middle and right button (for tests)."""
        return self._buttons

    def render_snapshot(self, snapshot: TimerSnapshot) -> None:
        """Show a timer snapshot.

        Args:
            snapshot: Timer state.
        """
        self.setUpdatesEnabled(False)
        self._digits.apply(snapshot.digits, alert=snapshot.alert)
        self._caption.setText(snapshot.caption)
        for button, state in zip(self._buttons, (snapshot.left, snapshot.middle, snapshot.right), strict=True):
            button.apply(state)
        self.setUpdatesEnabled(True)
