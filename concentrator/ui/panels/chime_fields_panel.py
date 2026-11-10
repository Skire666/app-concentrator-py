"""The four hourly chime fields: sound, volume and preview, first and last hour (dialog and settings page)."""

from PySide6.QtCore import QSignalBlocker, Signal
from PySide6.QtWidgets import QComboBox, QFormLayout, QLabel, QVBoxLayout, QWidget

from concentrator.presentation.timer.chime_settings_snapshot import ChimeFieldsSnapshot, HourRangeSnapshot
from concentrator.ui.support.styles import INVALID_INPUT_STYLE, INVALID_PROPERTY, set_dynamic_property
from concentrator.ui.widgets.field_error_label import FieldErrorLabel
from concentrator.ui.widgets.sound_picker_widget import SoundPickerWidget
from concentrator.ui.widgets.volume_slider_widget import VolumeSliderWidget


class ChimeFieldsPanel(QWidget):
    """Exposes one signal per field and ``action_requested(int)`` for Preview and "Choose an MP3 file..."."""

    sound_selected = Signal(int)
    volume_changed = Signal(int)
    start_hour_changed = Signal(int)
    end_hour_changed = Signal(int)
    action_requested = Signal(int)

    def __init__(self, spacing_px: int, parent: QWidget | None = None) -> None:
        """Build the fields.

        Args:
            spacing_px: ``ui.dialog_spacing_px``.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setStyleSheet(INVALID_INPUT_STYLE)
        self._sound = SoundPickerWidget(self)
        self._volume = VolumeSliderWidget(self)
        self._start = QComboBox(self)
        self._end = QComboBox(self)
        self._captions = tuple(QLabel(self) for _row in range(4))
        self._errors = tuple(FieldErrorLabel(self) for _row in range(4))
        self._connect()
        self._build_layout(spacing_px)

    @property
    def sound_picker(self) -> SoundPickerWidget:
        """Sound field (for tests)."""
        return self._sound

    @property
    def volume_slider(self) -> VolumeSliderWidget:
        """Volume field (for tests)."""
        return self._volume

    @property
    def start_hour(self) -> QComboBox:
        """First hour (for tests)."""
        return self._start

    @property
    def end_hour(self) -> QComboBox:
        """Last hour (for tests)."""
        return self._end

    @property
    def end_hour_error(self) -> FieldErrorLabel:
        """Inline error of the last hour (for tests)."""
        return self._errors[3]

    def render_snapshot(self, snapshot: ChimeFieldsSnapshot) -> None:
        """Show the draft without emitting the field signals.

        Args:
            snapshot: Fields state.
        """
        sound, volume = snapshot.sound, snapshot.volume
        self._sound.apply(
            sound.options, sound.tooltips, sound.selected, choose=sound.choose_file, invalid=bool(sound.error)
        )
        self._volume.apply(
            volume.value, volume.maximum, volume.value_text, preview=volume.preview, invalid=bool(volume.error)
        )
        self._render_hours(snapshot.hours)
        self._render_rows(snapshot)

    def _render_rows(self, snapshot: ChimeFieldsSnapshot) -> None:
        """Show the row labels and the inline errors.

        Args:
            snapshot: Fields state.
        """
        sound, volume, hours = snapshot.sound, snapshot.volume, snapshot.hours
        texts = (
            (sound.label, sound.error),
            (volume.label, volume.error),
            (hours.start_label, hours.start_error),
            (hours.end_label, hours.end_error),
        )
        for caption, error, (text, message) in zip(self._captions, self._errors, texts, strict=True):
            caption.setText(text)
            error.set_error(message)

    def _render_hours(self, hours: HourRangeSnapshot) -> None:
        """Show both hour lists.

        Args:
            hours: Active hours.
        """
        for combo, selected, error in (
            (self._start, hours.start, hours.start_error),
            (self._end, hours.end, hours.end_error),
        ):
            blocker = QSignalBlocker(combo)
            if [combo.itemText(index) for index in range(combo.count())] != list(hours.options):
                combo.clear()
                combo.addItems(list(hours.options))
            combo.setCurrentIndex(selected)
            blocker.unblock()
            set_dynamic_property(combo, INVALID_PROPERTY, bool(error))

    def _connect(self) -> None:
        """Forward the widget signals."""
        self._sound.sound_selected.connect(self.sound_selected)
        self._sound.action_requested.connect(self.action_requested)
        self._volume.volume_changed.connect(self.volume_changed)
        self._volume.action_requested.connect(self.action_requested)
        self._start.currentIndexChanged.connect(self.start_hour_changed)
        self._end.currentIndexChanged.connect(self.end_hour_changed)

    def _build_layout(self, spacing_px: int) -> None:
        """One form row per field, the inline error under the field.

        Args:
            spacing_px: ``ui.dialog_spacing_px``.
        """
        form = QFormLayout(self)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(spacing_px)
        fields: tuple[QWidget, ...] = (self._sound, self._volume, self._start, self._end)
        for caption, field, error in zip(self._captions, fields, self._errors, strict=True):
            form.addRow(caption, self._cell(field, error))

    def _cell(self, field: QWidget, error: FieldErrorLabel) -> QWidget:
        """Put a field and its inline error in one cell.

        Args:
            field: Field widget.
            error: Its inline error.

        Returns:
            The cell.
        """
        cell = QWidget(self)
        column = QVBoxLayout(cell)
        column.setContentsMargins(0, 0, 0, 0)
        field.setParent(cell)
        error.setParent(cell)
        column.addWidget(field)
        column.addWidget(error)
        return cell
