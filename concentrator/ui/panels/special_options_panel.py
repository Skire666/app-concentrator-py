"""Special options of zone 2: "Chime every hour", its active hours and the "..." button."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from concentrator.presentation.timer.chime_settings_snapshot import SpecialOptionsSnapshot
from concentrator.ui.support.styles import SECTION_TITLE_STYLE
from concentrator.ui.widgets.snapshot_button import SnapshotButton
from concentrator.ui.widgets.snapshot_check_box import SnapshotCheckBox


class SpecialOptionsPanel(QWidget):
    """Emits ``action_requested(int)`` for the check box and the "..." button."""

    action_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build the panel.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._title = QLabel(self)
        self._title.setTextFormat(Qt.TextFormat.PlainText)
        self._title.setStyleSheet(SECTION_TITLE_STYLE)
        self._chime = SnapshotCheckBox(self)
        self._hours = QLabel(self)
        self._hours.setTextFormat(Qt.TextFormat.PlainText)
        self._edit = SnapshotButton(self)
        self._chime.action_requested.connect(self.action_requested)
        self._edit.action_requested.connect(self.action_requested)
        row = QHBoxLayout()
        row.addWidget(self._chime)
        row.addWidget(self._hours)
        row.addStretch(1)
        row.addWidget(self._edit)
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.addWidget(self._title)
        column.addLayout(row)

    @property
    def chime_check_box(self) -> SnapshotCheckBox:
        """The "Chime every hour" check box (for tests)."""
        return self._chime

    @property
    def chime_hours(self) -> QLabel:
        """Active hours (for tests)."""
        return self._hours

    @property
    def chime_edit_button(self) -> SnapshotButton:
        """The "..." button (for tests)."""
        return self._edit

    def render_snapshot(self, snapshot: SpecialOptionsSnapshot) -> None:
        """Show the special options.

        Args:
            snapshot: Special options state.
        """
        self.setUpdatesEnabled(False)
        self._title.setText(snapshot.title)
        self._chime.apply(snapshot.chime)
        self._hours.setText(snapshot.chime_hours)
        self._edit.apply(snapshot.chime_edit)
        self.setUpdatesEnabled(True)
