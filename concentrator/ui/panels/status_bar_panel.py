"""One-line status bar under the pages: save state (left), language button (right)."""

from typing import Final

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QWidget

from concentrator.presentation.shell.shell_snapshot import StatusBarSnapshot
from concentrator.ui.widgets.snapshot_button import SnapshotButton

_HORIZONTAL_MARGIN_PX: Final = 8
_VERTICAL_MARGIN_PX: Final = 2


class StatusBarPanel(QWidget):
    """Emits ``action_requested(int)`` when the language button is clicked."""

    action_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build the bar.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self._save_state = QLabel(self)
        self._save_state.setTextFormat(Qt.TextFormat.PlainText)
        self._language = SnapshotButton(self)
        self._language.setFlat(True)
        self._language.action_requested.connect(self.action_requested)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            _HORIZONTAL_MARGIN_PX, _VERTICAL_MARGIN_PX, _HORIZONTAL_MARGIN_PX, _VERTICAL_MARGIN_PX
        )
        layout.addWidget(self._save_state)
        layout.addStretch(1)
        layout.addWidget(self._language)

    @property
    def language_button(self) -> SnapshotButton:
        """Language toggle (for tests)."""
        return self._language

    @property
    def save_state_text(self) -> str:
        """Text of the save state label (for tests)."""
        return self._save_state.text()

    def render_snapshot(self, snapshot: StatusBarSnapshot) -> None:
        """Show a status bar snapshot.

        Args:
            snapshot: Status bar state.
        """
        self.setUpdatesEnabled(False)
        self._save_state.setText(snapshot.save_state_text)
        self._language.apply(snapshot.language_button)
        self.setUpdatesEnabled(True)
