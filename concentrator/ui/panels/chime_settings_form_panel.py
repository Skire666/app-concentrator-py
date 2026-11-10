"""Content of the hourly chime dialog: the chime fields, a hint, Cancel and Save."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from concentrator.presentation.timer.chime_settings_snapshot import ChimeSettingsSnapshot
from concentrator.presentation.timer.timer_layout import TimerLayout
from concentrator.ui.panels.chime_fields_panel import ChimeFieldsPanel
from concentrator.ui.widgets.field_error_label import FieldErrorLabel
from concentrator.ui.widgets.snapshot_button import SnapshotButton
from concentrator.ui.widgets.sound_picker_widget import SoundPickerWidget
from concentrator.ui.widgets.volume_slider_widget import VolumeSliderWidget


class ChimeSettingsFormPanel(QWidget):
    """Exposes one signal per field and ``action_requested(int)`` for its buttons."""

    sound_selected = Signal(int)
    volume_changed = Signal(int)
    start_hour_changed = Signal(int)
    end_hour_changed = Signal(int)
    action_requested = Signal(int)

    def __init__(self, layout: TimerLayout, parent: QWidget | None = None) -> None:
        """Build the panel.

        Args:
            layout: Spacing of the dialog.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._fields = ChimeFieldsPanel(layout.spacing_px, self)
        self._hint = QLabel(self)
        self._hint.setWordWrap(True)
        self._hint.setTextFormat(Qt.TextFormat.PlainText)
        self._save = SnapshotButton(self)
        self._cancel = SnapshotButton(self)
        self._connect()
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self._cancel)
        buttons.addWidget(self._save)
        column = QVBoxLayout(self)
        column.setSpacing(layout.spacing_px)
        column.addWidget(self._fields)
        column.addWidget(self._hint)
        column.addLayout(buttons)

    @property
    def sound_picker(self) -> SoundPickerWidget:
        """Sound field (for tests)."""
        return self._fields.sound_picker

    @property
    def volume_slider(self) -> VolumeSliderWidget:
        """Volume field (for tests)."""
        return self._fields.volume_slider

    @property
    def start_hour(self) -> QComboBox:
        """First hour (for tests)."""
        return self._fields.start_hour

    @property
    def end_hour(self) -> QComboBox:
        """Last hour (for tests)."""
        return self._fields.end_hour

    @property
    def end_hour_error(self) -> FieldErrorLabel:
        """Inline error of the last hour (for tests)."""
        return self._fields.end_hour_error

    @property
    def save_button(self) -> SnapshotButton:
        """Save (for tests)."""
        return self._save

    @property
    def cancel_button(self) -> SnapshotButton:
        """Cancel (for tests)."""
        return self._cancel

    def render_snapshot(self, snapshot: ChimeSettingsSnapshot) -> None:
        """Show the draft without emitting the field signals.

        Args:
            snapshot: Dialog state.
        """
        self.setUpdatesEnabled(False)
        self._fields.render_snapshot(snapshot.fields)
        self._hint.setText(snapshot.hint)
        self._save.apply(snapshot.save)
        self._cancel.apply(snapshot.cancel)
        self.setUpdatesEnabled(True)

    def _connect(self) -> None:
        """Forward the field and button signals."""
        fields = self._fields
        fields.sound_selected.connect(self.sound_selected)
        fields.volume_changed.connect(self.volume_changed)
        fields.start_hour_changed.connect(self.start_hour_changed)
        fields.end_hour_changed.connect(self.end_hour_changed)
        fields.action_requested.connect(self.action_requested)
        self._save.action_requested.connect(self.action_requested)
        self._cancel.action_requested.connect(self.action_requested)
