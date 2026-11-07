"""One-line status bar under the pages: save state and instance warning (left), language button (right)."""

from typing import Final

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QWidget

from concentrator.presentation.shell.shell_snapshot import StatusBarSnapshot
from concentrator.ui.support.styles import WARNING_PROPERTY, WARNING_TEXT_STYLE
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
        self.setStyleSheet(WARNING_TEXT_STYLE)
        self._save_state = QLabel(self)
        self._save_state.setTextFormat(Qt.TextFormat.PlainText)
        self._instance_warning = QLabel(self)
        self._instance_warning.setTextFormat(Qt.TextFormat.PlainText)
        self._instance_warning.setProperty(WARNING_PROPERTY, True)
        self._instance_warning.setVisible(False)
        self._language = SnapshotButton(self)
        self._language.setFlat(True)
        self._language.action_requested.connect(self.action_requested)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            _HORIZONTAL_MARGIN_PX, _VERTICAL_MARGIN_PX, _HORIZONTAL_MARGIN_PX, _VERTICAL_MARGIN_PX
        )
        layout.addWidget(self._save_state)
        layout.addSpacing(_HORIZONTAL_MARGIN_PX * 2)
        layout.addWidget(self._instance_warning)
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

    @property
    def save_state_tooltip(self) -> str:
        """Tooltip of the save state label (for tests)."""
        return self._save_state.toolTip()

    @property
    def instance_warning(self) -> QLabel:
        """Unguarded single-instance indicator (for tests)."""
        return self._instance_warning

    def render_snapshot(self, snapshot: StatusBarSnapshot) -> None:
        """Show a status bar snapshot.

        Args:
            snapshot: Status bar state.
        """
        self.setUpdatesEnabled(False)
        self._save_state.setText(snapshot.save_state_text)
        self._save_state.setToolTip(snapshot.save_state_tooltip)
        self._instance_warning.setText(snapshot.instance_warning_text)
        self._instance_warning.setToolTip(snapshot.instance_warning_tooltip)
        self._instance_warning.setVisible(bool(snapshot.instance_warning_text))
        self._language.apply(snapshot.language_button)
        self.setUpdatesEnabled(True)
