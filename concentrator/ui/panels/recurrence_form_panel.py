"""Repeat section of the task dialog: frequency, interval, weekdays, end, summary and next dates."""

from PySide6.QtCore import QDate, QSignalBlocker, Signal
from PySide6.QtWidgets import QCheckBox, QDateEdit, QHBoxLayout, QLabel, QSpinBox, QVBoxLayout, QWidget

from concentrator.presentation.todo.task_edit_snapshot import (
    RecurrenceEndSnapshot,
    RecurrenceFieldSnapshot,
    RecurrenceRuleSnapshot,
)
from concentrator.ui.widgets.field_error_label import FieldErrorLabel
from concentrator.ui.widgets.snapshot_combo_box import SnapshotComboBox
from concentrator.ui.widgets.weekday_toggle_widget import WeekdayToggleWidget

_MIN_VALUE = 1
"""Smallest interval and count the spin boxes offer (the rules check the same bound)."""


class RecurrenceFormPanel(QWidget):
    """Emits the edits of the Repeat section; ``render_snapshot`` shows a ``RecurrenceFieldSnapshot``.

    Signals:
        repeat_toggled(bool): Repeat check box.
        interval_changed(int): Every N units.
        frequency_selected(int): Index of the unit.
        weekday_toggled(int, bool): Weekday value and its new state.
        end_selected(int): Index of the end condition.
        end_date_changed(int, int, int): Year, month and day of the end date.
        end_count_changed(int): Number of occurrences.
    """

    repeat_toggled = Signal(bool)
    interval_changed = Signal(int)
    frequency_selected = Signal(int)
    weekday_toggled = Signal(int, bool)
    end_selected = Signal(int)
    end_date_changed = Signal(int, int, int)
    end_count_changed = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build the section.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._repeat = QCheckBox(self)
        self._every = QLabel(self)
        self._interval = QSpinBox(self)
        self._interval.setMinimum(_MIN_VALUE)
        self._frequency = SnapshotComboBox(self)
        self._weekdays = WeekdayToggleWidget(self)
        self._ends = QLabel(self)
        self._end = SnapshotComboBox(self)
        self._end_date = QDateEdit(self)
        self._end_date.setCalendarPopup(True)
        self._end_count = QSpinBox(self)
        self._end_count.setMinimum(_MIN_VALUE)
        self._end_suffix = QLabel(self)
        self._summary = QLabel(self)
        self._summary.setWordWrap(True)
        self._preview = QLabel(self)
        self._preview.setWordWrap(True)
        self._error = FieldErrorLabel(self)
        self._connect()
        self._build_layout()

    @property
    def repeat_box(self) -> QCheckBox:
        """Repeat check box (for tests)."""
        return self._repeat

    @property
    def interval_input(self) -> QSpinBox:
        """Interval (for tests)."""
        return self._interval

    @property
    def frequency_input(self) -> SnapshotComboBox:
        """Unit of the interval (for tests)."""
        return self._frequency

    @property
    def weekday_input(self) -> WeekdayToggleWidget:
        """Weekday buttons (for tests)."""
        return self._weekdays

    @property
    def end_inputs(self) -> tuple[SnapshotComboBox, QDateEdit, QSpinBox]:
        """End condition, end date and count (for tests)."""
        return self._end, self._end_date, self._end_count

    @property
    def texts(self) -> tuple[QLabel, QLabel, FieldErrorLabel]:
        """Summary, next dates and inline error (for tests)."""
        return self._summary, self._preview, self._error

    def render_snapshot(self, snapshot: RecurrenceFieldSnapshot) -> None:
        """Show the section without emitting its signals.

        Args:
            snapshot: Section state.
        """
        blocker = QSignalBlocker(self._repeat)
        self._repeat.setText(snapshot.repeat_label)
        self._repeat.setChecked(snapshot.enabled)
        blocker.unblock()
        self._apply_rule(snapshot.rule)
        self._apply_ending(snapshot.ending)
        for widget in (self._interval, self._frequency, self._weekdays, self._end, self._end_date, self._end_count):
            widget.setEnabled(snapshot.enabled)
        self._summary.setText(snapshot.summary)
        self._preview.setText(snapshot.preview)
        self._error.set_error(snapshot.error)

    def _apply_rule(self, rule: RecurrenceRuleSnapshot) -> None:
        """Show the interval, the unit and the weekdays.

        Args:
            rule: Rule fields.
        """
        blocker = QSignalBlocker(self._interval)
        self._every.setText(rule.every_label)
        self._interval.setMaximum(rule.interval_max)
        self._interval.setValue(rule.interval)
        blocker.unblock()
        self._frequency.apply(rule.frequency)
        self._weekdays.apply(rule.weekdays)
        self._weekdays.setVisible(rule.weekdays_visible)

    def _apply_ending(self, ending: RecurrenceEndSnapshot) -> None:
        """Show the end condition.

        Args:
            ending: End fields.
        """
        blockers = [QSignalBlocker(self._end_date), QSignalBlocker(self._end_count)]
        self._ends.setText(ending.end.label)
        self._end.apply(ending.end)
        self._end_date.setDisplayFormat(ending.date_format)
        self._end_date.setDate(QDate(ending.end_date.year, ending.end_date.month, ending.end_date.day))
        self._end_count.setMaximum(ending.end_count_max)
        self._end_count.setValue(ending.end_count)
        self._end_suffix.setText(ending.end_count_suffix)
        for blocker in blockers:
            blocker.unblock()
        self._end_date.setVisible(ending.end_date_visible)
        self._end_count.setVisible(ending.end_count_visible)
        self._end_suffix.setVisible(ending.end_count_visible)

    def _connect(self) -> None:
        """Route the field signals to the intent signals."""
        self._repeat.toggled.connect(self.repeat_toggled.emit)
        self._interval.valueChanged.connect(self.interval_changed.emit)
        self._frequency.index_selected.connect(self.frequency_selected.emit)
        self._weekdays.day_toggled.connect(self.weekday_toggled.emit)
        self._end.index_selected.connect(self.end_selected.emit)
        self._end_date.dateChanged.connect(self._emit_end_date)
        self._end_count.valueChanged.connect(self.end_count_changed.emit)

    def _emit_end_date(self, value: QDate) -> None:
        """Send the end date.

        Args:
            value: Date of the field.
        """
        self.end_date_changed.emit(value.year(), value.month(), value.day())

    def _build_layout(self) -> None:
        """Repeat check box; Every N unit; weekdays; Ends ...; summary; next dates; error."""
        every = QHBoxLayout()
        for widget in (self._every, self._interval, self._frequency):
            every.addWidget(widget)
        every.addStretch(1)
        ends = QHBoxLayout()
        for widget in (self._ends, self._end, self._end_date, self._end_count, self._end_suffix):
            ends.addWidget(widget)
        ends.addStretch(1)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._repeat)
        layout.addLayout(every)
        layout.addWidget(self._weekdays)
        layout.addLayout(ends)
        layout.addWidget(self._summary)
        layout.addWidget(self._preview)
        layout.addWidget(self._error)
