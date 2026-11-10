"""General and Hourly chime sections of the settings page (the values stored in the data file)."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFormLayout, QGroupBox, QLabel, QVBoxLayout, QWidget

from concentrator.presentation.settings.settings_snapshot import (
    ChimeSectionSnapshot,
    GeneralSectionSnapshot,
    SettingsFormSnapshot,
)
from concentrator.ui.panels.chime_fields_panel import ChimeFieldsPanel
from concentrator.ui.support.styles import INVALID_INPUT_STYLE
from concentrator.ui.widgets.field_check_box import FieldCheckBox
from concentrator.ui.widgets.field_error_label import FieldErrorLabel
from concentrator.ui.widgets.snapshot_combo_box import SnapshotComboBox


class SettingsFormPanel(QWidget):
    """Exposes one signal per field and ``action_requested(int)`` for Preview and "Choose an MP3 file..."."""

    language_selected = Signal(int)
    log_level_selected = Signal(int)
    notify_toggled = Signal(bool)
    chime_enabled_toggled = Signal(bool)
    sound_selected = Signal(int)
    volume_changed = Signal(int)
    start_hour_changed = Signal(int)
    end_hour_changed = Signal(int)
    action_requested = Signal(int)

    def __init__(self, spacing_px: int, parent: QWidget | None = None) -> None:
        """Build both sections.

        Args:
            spacing_px: ``ui.dialog_spacing_px``.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setStyleSheet(INVALID_INPUT_STYLE)
        self._general = QGroupBox(self)
        self._language = SnapshotComboBox(self._general)
        self._log_level = SnapshotComboBox(self._general)
        self._captions = (QLabel(self._general), QLabel(self._general))
        self._errors = (FieldErrorLabel(self._general), FieldErrorLabel(self._general))
        self._notify = FieldCheckBox(self._general)
        self._chime = QGroupBox(self)
        self._chime_enabled = FieldCheckBox(self._chime)
        self._chime_fields = ChimeFieldsPanel(spacing_px, self._chime)
        self._chime_hint = QLabel(self._chime)
        self._chime_hint.setWordWrap(True)
        self._chime_hint.setTextFormat(Qt.TextFormat.PlainText)
        self._connect()
        self._build_layout(spacing_px)

    @property
    def language(self) -> SnapshotComboBox:
        """Language list (for tests)."""
        return self._language

    @property
    def log_level(self) -> SnapshotComboBox:
        """Journal detail level list (for tests)."""
        return self._log_level

    @property
    def notify(self) -> FieldCheckBox:
        """Taskbar alert check box (for tests)."""
        return self._notify

    @property
    def chime_enabled(self) -> FieldCheckBox:
        """The "Chime every hour" check box (for tests)."""
        return self._chime_enabled

    @property
    def chime_fields(self) -> ChimeFieldsPanel:
        """Chime sound, volume and hours (for tests)."""
        return self._chime_fields

    def render_snapshot(self, snapshot: SettingsFormSnapshot) -> None:
        """Show the draft without emitting the field signals.

        Args:
            snapshot: Form state.
        """
        self._render_general(snapshot.general)
        self._render_chime(snapshot.chime)

    def _render_general(self, general: GeneralSectionSnapshot) -> None:
        """Show the General section.

        Args:
            general: Section state.
        """
        self._general.setTitle(general.title)
        for field, combo, caption, error in zip(
            (general.language, general.log_level),
            (self._language, self._log_level),
            self._captions,
            self._errors,
            strict=True,
        ):
            combo.apply(field)
            caption.setText(field.label)
            caption.setToolTip(field.tooltip)
            error.set_error(field.error)
        self._notify.apply(general.notify_when_inactive)

    def _render_chime(self, chime: ChimeSectionSnapshot) -> None:
        """Show the Hourly chime section.

        Args:
            chime: Section state.
        """
        self._chime.setTitle(chime.title)
        self._chime_enabled.apply(chime.enabled)
        self._chime_fields.render_snapshot(chime.fields)
        self._chime_hint.setText(chime.hint)

    def _connect(self) -> None:
        """Forward the field signals."""
        self._language.index_selected.connect(self.language_selected)
        self._log_level.index_selected.connect(self.log_level_selected)
        self._notify.value_changed.connect(self.notify_toggled)
        self._chime_enabled.value_changed.connect(self.chime_enabled_toggled)
        fields = self._chime_fields
        fields.sound_selected.connect(self.sound_selected)
        fields.volume_changed.connect(self.volume_changed)
        fields.start_hour_changed.connect(self.start_hour_changed)
        fields.end_hour_changed.connect(self.end_hour_changed)
        fields.action_requested.connect(self.action_requested)

    def _build_layout(self, spacing_px: int) -> None:
        """General rows, then the chime switch, fields and hint.

        Args:
            spacing_px: ``ui.dialog_spacing_px``.
        """
        general = QFormLayout(self._general)
        general.setSpacing(spacing_px)
        for caption, combo, error in zip(self._captions, (self._language, self._log_level), self._errors, strict=True):
            cell = QVBoxLayout()
            cell.addWidget(combo)
            cell.addWidget(error)
            general.addRow(caption, cell)
        general.addRow(self._notify)
        chime = QVBoxLayout(self._chime)
        chime.setSpacing(spacing_px)
        chime.addWidget(self._chime_enabled)
        chime.addWidget(self._chime_fields)
        chime.addWidget(self._chime_hint)
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(spacing_px)
        column.addWidget(self._general)
        column.addWidget(self._chime)
