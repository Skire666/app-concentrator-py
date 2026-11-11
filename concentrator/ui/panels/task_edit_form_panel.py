"""Fields of the task dialog: text, list, due date, optional due time and the Repeat section."""

from PySide6.QtCore import QDate, QSignalBlocker, QTime, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from concentrator.presentation.todo.task_edit_snapshot import DueFieldSnapshot, TaskEditSnapshot
from concentrator.ui.panels.recurrence_form_panel import RecurrenceFormPanel
from concentrator.ui.support.styles import INVALID_INPUT_STYLE, INVALID_PROPERTY, set_dynamic_property
from concentrator.ui.widgets.field_error_label import FieldErrorLabel
from concentrator.ui.widgets.snapshot_button import SnapshotButton
from concentrator.ui.widgets.snapshot_combo_box import SnapshotComboBox
from concentrator.ui.widgets.text_fields import apply_text

TIME_FORMAT = "HH:mm"


class TaskEditFormPanel(QWidget):
    """Emits the edits of the fields and ``action_requested(int)`` for Save and Cancel.

    Signals:
        text_changed(str): Text as typed.
        list_selected(int): Index of the chosen list.
        due_date_changed(bool, int, int, int): Date check box, year, month, day.
        due_time_changed(bool, int, int): Time check box, hour, minute.
    """

    text_changed = Signal(str)
    list_selected = Signal(int)
    due_date_changed = Signal(bool, int, int, int)
    due_time_changed = Signal(bool, int, int)
    action_requested = Signal(int)

    def __init__(self, spacing_px: int, parent: QWidget | None = None) -> None:
        """Build the fields.

        Args:
            spacing_px: Space between the parts of the dialog.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setStyleSheet(INVALID_INPUT_STYLE)
        self._text = QPlainTextEdit(self)
        self._text_caption = QLabel(self)
        self._text_error = FieldErrorLabel(self)
        self._list = SnapshotComboBox(self)
        self._list_caption = QLabel(self)
        self._has_date = QCheckBox(self)
        self._date = QDateEdit(self)
        self._date.setCalendarPopup(True)
        self._has_time = QCheckBox(self)
        self._time = QTimeEdit(self)
        self._time.setDisplayFormat(TIME_FORMAT)
        self._due_error = FieldErrorLabel(self)
        self._recurrence = RecurrenceFormPanel(self)
        self._save = SnapshotButton(self)
        self._cancel = SnapshotButton(self)
        self._connect()
        self._build_layout(spacing_px)

    @property
    def text_input(self) -> QPlainTextEdit:
        """Text field (for tests and focus)."""
        return self._text

    @property
    def list_input(self) -> SnapshotComboBox:
        """List field (for tests)."""
        return self._list

    @property
    def date_inputs(self) -> tuple[QCheckBox, QDateEdit]:
        """Due date check box and field (for tests)."""
        return self._has_date, self._date

    @property
    def time_inputs(self) -> tuple[QCheckBox, QTimeEdit]:
        """Due time check box and field (for tests)."""
        return self._has_time, self._time

    @property
    def recurrence_panel(self) -> RecurrenceFormPanel:
        """Repeat section."""
        return self._recurrence

    @property
    def buttons(self) -> tuple[SnapshotButton, SnapshotButton]:
        """Save and Cancel (for tests)."""
        return self._save, self._cancel

    @property
    def text_error(self) -> FieldErrorLabel:
        """Inline error of the text (for tests)."""
        return self._text_error

    def render_snapshot(self, snapshot: TaskEditSnapshot) -> None:
        """Show the draft without emitting the field signals.

        Args:
            snapshot: Dialog state.
        """
        self.setUpdatesEnabled(False)
        self._text_caption.setText(snapshot.text.label)
        apply_text(self._text, self._text_error, snapshot.text)
        self._list_caption.setText(snapshot.task_list.label)
        self._list.apply(snapshot.task_list)
        self._apply_due(snapshot.due)
        self._recurrence.render_snapshot(snapshot.recurrence)
        self._save.apply(snapshot.save)
        self._cancel.apply(snapshot.cancel)
        self.setUpdatesEnabled(True)

    def _apply_due(self, due: DueFieldSnapshot) -> None:
        """Show the due date and time fields.

        Args:
            due: Field state.
        """
        widgets = (self._has_date, self._date, self._has_time, self._time)
        blockers = [QSignalBlocker(widget) for widget in widgets]
        self._has_date.setText(due.date_label)
        self._has_date.setChecked(due.has_date)
        self._date.setDisplayFormat(due.date_format)
        self._date.setDate(QDate(due.year, due.month, due.day))
        self._date.setEnabled(due.has_date)
        self._has_time.setText(due.time_label)
        self._has_time.setChecked(due.has_time)
        self._has_time.setEnabled(due.time_enabled)
        self._time.setTime(QTime(due.hour, due.minute))
        self._time.setEnabled(due.has_time and due.time_enabled)
        for blocker in blockers:
            blocker.unblock()
        set_dynamic_property(self._time, INVALID_PROPERTY, bool(due.error))
        self._due_error.set_error(due.error)

    def _connect(self) -> None:
        """Route the field signals to the intent signals."""
        self._text.textChanged.connect(lambda: self.text_changed.emit(self._text.toPlainText()))
        self._list.index_selected.connect(self.list_selected.emit)
        self._has_date.toggled.connect(self._emit_date)
        self._date.dateChanged.connect(self._emit_date)
        self._has_time.toggled.connect(self._emit_time)
        self._time.timeChanged.connect(self._emit_time)
        self._save.action_requested.connect(self.action_requested.emit)
        self._cancel.action_requested.connect(self.action_requested.emit)

    def _emit_date(self, *_args: object) -> None:
        """Send the due date check box and the date."""
        value = self._date.date()
        self.due_date_changed.emit(self._has_date.isChecked(), value.year(), value.month(), value.day())

    def _emit_time(self, *_args: object) -> None:
        """Send the due time check box and the time."""
        value = self._time.time()
        self.due_time_changed.emit(self._has_time.isChecked(), value.hour(), value.minute())

    def _build_layout(self, spacing_px: int) -> None:
        """Text, list, due row, Repeat section, buttons.

        Args:
            spacing_px: Space between the parts.
        """
        due = QHBoxLayout()
        for widget in (self._has_date, self._date, self._has_time, self._time):
            due.addWidget(widget)
        due.addStretch(1)
        form = QFormLayout()
        form.addRow(self._list_caption, self._list)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self._save)
        buttons.addWidget(self._cancel)
        layout = QVBoxLayout(self)
        layout.setSpacing(spacing_px)
        layout.addWidget(self._text_caption)
        layout.addWidget(self._text, 1)
        layout.addWidget(self._text_error)
        layout.addLayout(form)
        layout.addLayout(due)
        layout.addWidget(self._due_error)
        layout.addWidget(self._recurrence)
        layout.addLayout(buttons)
