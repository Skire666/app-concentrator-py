"""Fields of the favorite dialog: label and duration."""

import re

from PySide6.QtCore import QRegularExpression, QSignalBlocker, Signal
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import QFormLayout, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from concentrator.presentation.timer.preset_edit_snapshot import PresetEditSnapshot
from concentrator.presentation.timer.timer_layout import TimerLayout
from concentrator.ui.support.styles import INVALID_INPUT_STYLE, INVALID_PROPERTY, set_dynamic_property
from concentrator.ui.widgets.duration_input_widget import DurationInputWidget
from concentrator.ui.widgets.field_error_label import FieldErrorLabel
from concentrator.ui.widgets.snapshot_button import SnapshotButton


class PresetEditFormPanel(QWidget):
    """Exposes ``label_changed``, ``duration_changed`` and ``action_requested(int)`` for its buttons."""

    label_changed = Signal(str)
    duration_changed = Signal(int, int, int)
    action_requested = Signal(int)

    def __init__(self, layout: TimerLayout, parent: QWidget | None = None) -> None:
        """Build the fields.

        Args:
            layout: Spacing of the dialog.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setStyleSheet(INVALID_INPUT_STYLE)
        self._label = QLineEdit(self)
        self._label.setClearButtonEnabled(True)
        self._blocked: str | None = None
        self._duration = DurationInputWidget(self)
        self._label_caption = QLabel(self)
        self._duration_caption = QLabel(self)
        self._label_error = FieldErrorLabel(self)
        self._duration_error = FieldErrorLabel(self)
        self._save = SnapshotButton(self)
        self._cancel = SnapshotButton(self)
        self._label.textEdited.connect(self.label_changed)
        self._duration.duration_changed.connect(self.duration_changed)
        self._save.action_requested.connect(self.action_requested)
        self._cancel.action_requested.connect(self.action_requested)
        self._build_layout(layout.spacing_px)

    @property
    def label_input(self) -> QLineEdit:
        """Label field (for tests)."""
        return self._label

    @property
    def duration_input(self) -> DurationInputWidget:
        """Duration field (for tests)."""
        return self._duration

    @property
    def label_error(self) -> FieldErrorLabel:
        """Inline error of the label (for tests)."""
        return self._label_error

    @property
    def duration_error(self) -> FieldErrorLabel:
        """Inline error of the duration (for tests)."""
        return self._duration_error

    @property
    def save_button(self) -> SnapshotButton:
        """Save (for tests)."""
        return self._save

    @property
    def cancel_button(self) -> SnapshotButton:
        """Cancel (for tests)."""
        return self._cancel

    def render_snapshot(self, snapshot: PresetEditSnapshot) -> None:
        """Show the draft without emitting the field signals; the cursor stays where the user types.

        Args:
            snapshot: Dialog state.
        """
        self.setUpdatesEnabled(False)
        label = snapshot.label
        self._label_caption.setText(label.label)
        if self._label.text() != label.text:
            blocker = QSignalBlocker(self._label)
            self._label.setText(label.text)
            blocker.unblock()
        self._label.setPlaceholderText(label.placeholder)
        self._block_characters(label.blocked_characters)
        set_dynamic_property(self._label, INVALID_PROPERTY, bool(label.error))
        self._label_error.set_error(label.error)
        duration = snapshot.duration
        self._duration_caption.setText(duration.label)
        self._duration.apply(
            (duration.hours, duration.minutes, duration.seconds),
            max_hours=duration.max_hours,
            units=(duration.hours_unit, duration.minutes_unit, duration.seconds_unit),
            invalid=bool(duration.error),
        )
        self._duration_error.set_error(duration.error)
        self._save.apply(snapshot.save)
        self._cancel.apply(snapshot.cancel)
        self.setUpdatesEnabled(True)

    def _block_characters(self, characters: str) -> None:
        """Make the label field refuse some characters (typed or pasted).

        Args:
            characters: Characters to refuse, ``""`` for none.
        """
        if self._blocked == characters:
            return
        self._blocked = characters
        pattern = f"[^{re.escape(characters)}]*" if characters else ".*"
        self._label.setValidator(QRegularExpressionValidator(QRegularExpression(pattern), self._label))

    def _build_layout(self, spacing_px: int) -> None:
        """Lay the two rows out, then the buttons.

        Args:
            spacing_px: ``ui.dialog_spacing_px``.
        """
        form = QFormLayout()
        form.setSpacing(spacing_px)
        form.addRow(self._label_caption, self._cell(self._label, self._label_error))
        form.addRow(self._duration_caption, self._cell(self._duration, self._duration_error))
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self._cancel)
        buttons.addWidget(self._save)
        column = QVBoxLayout(self)
        column.setSpacing(spacing_px)
        column.addLayout(form)
        column.addLayout(buttons)

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
