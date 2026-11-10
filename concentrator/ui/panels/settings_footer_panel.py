"""Bottom line of the settings page, always visible: unsaved changes, Revert and Save."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from concentrator.presentation.settings.settings_snapshot import SettingsFormSnapshot
from concentrator.ui.support.styles import WARNING_PROPERTY, WARNING_TEXT_STYLE, set_dynamic_property
from concentrator.ui.widgets.snapshot_button import SnapshotButton


class SettingsFooterPanel(QWidget):
    """Emits ``action_requested(int)`` for Revert and Save."""

    action_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build the line.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._status = QLabel(self)
        self._status.setStyleSheet(WARNING_TEXT_STYLE)
        self._revert = SnapshotButton(self)
        self._save = SnapshotButton(self)
        for button in (self._revert, self._save):
            button.action_requested.connect(self.action_requested)
        row = QHBoxLayout(self)
        row.addWidget(self._status)
        row.addStretch(1)
        row.addWidget(self._revert)
        row.addWidget(self._save)

    @property
    def status(self) -> str:
        """Unsaved changes text (for tests)."""
        return self._status.text()

    @property
    def save_button(self) -> SnapshotButton:
        """Save (for tests)."""
        return self._save

    @property
    def revert_button(self) -> SnapshotButton:
        """Revert (for tests)."""
        return self._revert

    def render_snapshot(self, snapshot: SettingsFormSnapshot) -> None:
        """Show the buttons and the unsaved changes text.

        Args:
            snapshot: Form state.
        """
        self._status.setText(snapshot.status)
        set_dynamic_property(self._status, WARNING_PROPERTY, bool(snapshot.status))
        self._revert.apply(snapshot.revert)
        self._save.apply(snapshot.save)
