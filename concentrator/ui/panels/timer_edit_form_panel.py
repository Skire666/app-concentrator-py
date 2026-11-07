"""Fields of the timer edit dialog."""

from typing import Final

from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtWidgets import QCheckBox, QFormLayout, QHBoxLayout, QLabel, QSpinBox, QVBoxLayout, QWidget

from concentrator.presentation.timer.timer_edit_snapshot import (
    AutoStopInputSnapshot,
    LoopInputSnapshot,
    TimerEditSnapshot,
)
from concentrator.presentation.timer.timer_layout import TimerLayout
from concentrator.ui.support.styles import INVALID_INPUT_STYLE, INVALID_PROPERTY, set_dynamic_property
from concentrator.ui.widgets.duration_input_widget import DurationInputWidget
from concentrator.ui.widgets.field_error_label import FieldErrorLabel
from concentrator.ui.widgets.snapshot_button import SnapshotButton
from concentrator.ui.widgets.sound_picker_widget import SoundPickerWidget
from concentrator.ui.widgets.volume_slider_widget import VolumeSliderWidget

ROWS: Final = ("duration", "sound", "volume", "loops", "auto_stop")
MIN_LOOP_COUNT: Final = 1


class TimerEditFormPanel(QWidget):
    """Exposes one signal per field and ``action_requested(int)`` for its buttons."""

    duration_changed = Signal(int, int, int)
    sound_selected = Signal(int)
    volume_changed = Signal(int)
    loop_count_changed = Signal(int)
    loop_forever_changed = Signal(bool)
    auto_stop_changed = Signal(int)
    auto_restart_changed = Signal(bool)
    action_requested = Signal(int)

    def __init__(self, layout: TimerLayout, parent: QWidget | None = None) -> None:
        """Build the fields.

        Args:
            layout: Spacing of the dialog.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setStyleSheet(INVALID_INPUT_STYLE)
        self._duration = DurationInputWidget(self)
        self._sound = SoundPickerWidget(self)
        self._volume = VolumeSliderWidget(self)
        self._loop_count = QSpinBox(self)
        self._loop_count.setMinimum(MIN_LOOP_COUNT)
        self._loop_forever = QCheckBox(self)
        self._auto_stop = QSpinBox(self)
        self._auto_stop_unit = QLabel(self)
        self._auto_restart = QCheckBox(self)
        self._note = QLabel(self)
        self._save = SnapshotButton(self)
        self._cancel = SnapshotButton(self)
        self._labels = {row: QLabel(self) for row in ROWS}
        self._errors = {row: FieldErrorLabel(self) for row in ROWS}
        self._connect()
        self._build_layout(layout.spacing_px)

    @property
    def duration_input(self) -> DurationInputWidget:
        """Duration field (for tests)."""
        return self._duration

    @property
    def sound_picker(self) -> SoundPickerWidget:
        """Sound field (for tests)."""
        return self._sound

    @property
    def volume_slider(self) -> VolumeSliderWidget:
        """Volume field (for tests)."""
        return self._volume

    @property
    def loop_count(self) -> QSpinBox:
        """Play count (for tests)."""
        return self._loop_count

    @property
    def loop_forever(self) -> QCheckBox:
        """The "Repeat until stopped" check box (for tests)."""
        return self._loop_forever

    @property
    def auto_stop(self) -> QSpinBox:
        """Automatic stop (for tests)."""
        return self._auto_stop

    @property
    def auto_restart(self) -> QCheckBox:
        """The "Restart automatically" check box (for tests)."""
        return self._auto_restart

    @property
    def note(self) -> QLabel:
        """Note shown while the timer runs (for tests)."""
        return self._note

    @property
    def save_button(self) -> SnapshotButton:
        """Save (for tests)."""
        return self._save

    @property
    def cancel_button(self) -> SnapshotButton:
        """Cancel (for tests)."""
        return self._cancel

    def error_label(self, row: str) -> FieldErrorLabel:
        """Return the inline error of a row (for tests).

        Args:
            row: One of ``ROWS``.

        Returns:
            The label.
        """
        return self._errors[row]

    def render_snapshot(self, snapshot: TimerEditSnapshot) -> None:
        """Show the draft without emitting the field signals.

        Args:
            snapshot: Dialog state.
        """
        self.setUpdatesEnabled(False)
        self._render_inputs(snapshot)
        self._render_loops(snapshot.loops)
        self._render_auto_stop(snapshot.auto_stop)
        self._render_rows(snapshot)
        self._note.setText(snapshot.note)
        self._note.setVisible(bool(snapshot.note))
        self._save.apply(snapshot.save)
        self._cancel.apply(snapshot.cancel)
        self.setUpdatesEnabled(True)

    def _render_inputs(self, snapshot: TimerEditSnapshot) -> None:
        """Show the duration, sound and volume fields.

        Args:
            snapshot: Dialog state.
        """
        duration = snapshot.duration
        units = (duration.hours_unit, duration.minutes_unit, duration.seconds_unit)
        values = (duration.hours, duration.minutes, duration.seconds)
        self._duration.apply(values, max_hours=duration.max_hours, units=units, invalid=bool(duration.error))
        sound = snapshot.sound
        self._sound.apply(
            sound.options, sound.tooltips, sound.selected, choose=sound.choose_file, invalid=bool(sound.error)
        )
        volume = snapshot.volume
        self._volume.apply(
            volume.value, volume.maximum, volume.value_text, preview=volume.preview, invalid=bool(volume.error)
        )

    def _render_loops(self, loops: LoopInputSnapshot) -> None:
        """Show the play count field.

        Args:
            loops: Field state.
        """
        blockers = (QSignalBlocker(self._loop_count), QSignalBlocker(self._loop_forever))
        self._loop_count.setMaximum(loops.maximum)
        self._loop_count.setValue(loops.count)
        self._loop_count.setEnabled(loops.count_enabled)
        self._loop_forever.setText(loops.forever_label)
        self._loop_forever.setChecked(loops.forever)
        for blocker in blockers:
            blocker.unblock()
        set_dynamic_property(self._loop_count, INVALID_PROPERTY, bool(loops.error))

    def _render_auto_stop(self, auto_stop: AutoStopInputSnapshot) -> None:
        """Show the automatic stop field.

        Args:
            auto_stop: Field state.
        """
        blockers = (QSignalBlocker(self._auto_stop), QSignalBlocker(self._auto_restart))
        self._auto_stop.setMaximum(auto_stop.maximum)
        self._auto_stop.setValue(auto_stop.seconds)
        self._auto_stop_unit.setText(auto_stop.unit)
        self._auto_restart.setText(auto_stop.restart_label)
        self._auto_restart.setChecked(auto_stop.restart)
        self._auto_restart.setEnabled(auto_stop.restart_enabled)
        for blocker in blockers:
            blocker.unblock()
        set_dynamic_property(self._auto_stop, INVALID_PROPERTY, bool(auto_stop.error))

    def _render_rows(self, snapshot: TimerEditSnapshot) -> None:
        """Show the row labels and the inline errors.

        Args:
            snapshot: Dialog state.
        """
        fields = (snapshot.duration, snapshot.sound, snapshot.volume, snapshot.loops, snapshot.auto_stop)
        for row, field in zip(ROWS, fields, strict=True):
            self._labels[row].setText(field.label)
            self._errors[row].set_error(field.error)

    def _connect(self) -> None:
        """Forward the widget signals."""
        self._duration.duration_changed.connect(self.duration_changed)
        self._sound.sound_selected.connect(self.sound_selected)
        self._sound.action_requested.connect(self.action_requested)
        self._volume.volume_changed.connect(self.volume_changed)
        self._volume.action_requested.connect(self.action_requested)
        self._loop_count.valueChanged.connect(self.loop_count_changed)
        self._loop_forever.toggled.connect(self.loop_forever_changed)
        self._auto_stop.valueChanged.connect(self.auto_stop_changed)
        self._auto_restart.toggled.connect(self.auto_restart_changed)
        self._save.action_requested.connect(self.action_requested)
        self._cancel.action_requested.connect(self.action_requested)

    def _build_layout(self, spacing_px: int) -> None:
        """Lay the rows out, then the note and the buttons.

        Args:
            spacing_px: ``ui.dialog_spacing_px``.
        """
        loops = QHBoxLayout()
        loops.addWidget(self._loop_count)
        loops.addWidget(self._loop_forever, 1)
        auto_stop = QHBoxLayout()
        auto_stop.addWidget(self._auto_stop)
        auto_stop.addWidget(self._auto_stop_unit, 1)
        form = QFormLayout()
        form.setSpacing(spacing_px)
        for row, field in zip(ROWS, (self._duration, self._sound, self._volume, loops, auto_stop), strict=True):
            form.addRow(self._labels[row], self._field(field, row))
        form.addRow("", self._auto_restart)
        self._note.setWordWrap(True)
        self._note.setTextFormat(Qt.TextFormat.PlainText)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self._cancel)
        buttons.addWidget(self._save)
        column = QVBoxLayout(self)
        column.setSpacing(spacing_px)
        column.addLayout(form)
        column.addWidget(self._note)
        column.addLayout(buttons)

    def _field(self, content: QWidget | QHBoxLayout, row: str) -> QWidget:
        """Put a field and its inline error in one cell.

        Args:
            content: Field widget or layout.
            row: Row name.

        Returns:
            The cell.
        """
        cell = QWidget(self)
        column = QVBoxLayout(cell)
        column.setContentsMargins(0, 0, 0, 0)
        if isinstance(content, QWidget):
            content.setParent(cell)
            column.addWidget(content)
        else:
            column.addLayout(content)
        column.addWidget(self._errors[row])
        return cell
