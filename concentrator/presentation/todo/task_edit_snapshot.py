"""Snapshot of the task dialog (``TASK_EDIT``) and the text field shared with the list dialog."""

from dataclasses import dataclass

from concentrator.presentation.common.button_snapshot import ButtonSnapshot
from concentrator.presentation.settings.settings_snapshot import ChoiceFieldSnapshot


@dataclass(frozen=True, slots=True, kw_only=True)
class TextFieldSnapshot:
    """A text field (one line or several).

    Attributes:
        label: Field label.
        text: Text of the draft, as typed.
        placeholder: Hint shown while the field is empty.
        max_length: Longest text accepted by the rules (shown as a hint, never cut).
        error: Inline message, ``""`` when valid.
    """

    label: str
    text: str
    placeholder: str
    max_length: int
    error: str


@dataclass(frozen=True, slots=True, kw_only=True)
class DueFieldSnapshot:
    """Due date (check box and calendar) and optional due time (check box and time field).

    Attributes:
        date_label: Text of the due date check box.
        has_date: Whether the task has a due date ("No date" when unchecked).
        year: Year shown by the date field (the draft's, or today's).
        month: Month shown by the date field.
        day: Day shown by the date field.
        date_format: Display format of the date field, from the catalog (``dd/MM/yyyy``).
        time_label: Text of the due time check box.
        has_time: Whether the task has a due time.
        time_enabled: Whether the time check box can be used (only with a date).
        hour: Hour shown by the time field.
        minute: Minute shown by the time field.
        error: Inline message, ``""`` when valid.
    """

    date_label: str
    has_date: bool
    year: int
    month: int
    day: int
    date_format: str
    time_label: str
    has_time: bool
    time_enabled: bool
    hour: int
    minute: int
    error: str


@dataclass(frozen=True, slots=True, kw_only=True)
class WeekdayToggleSnapshot:
    """One weekday button of a weekly series.

    Attributes:
        value: ``WeekdayEnum`` value sent back when it is toggled.
        text: Short name (``Mon``).
        tooltip: Full name (``Monday``).
        checked: Whether the day is chosen.
    """

    value: int
    text: str
    tooltip: str
    checked: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class DateValueSnapshot:
    """A date shown by a date field.

    Attributes:
        year: Year.
        month: Month.
        day: Day.
    """

    year: int
    month: int
    day: int


@dataclass(frozen=True, slots=True, kw_only=True)
class RecurrenceRuleSnapshot:
    """How often the task repeats.

    Attributes:
        every_label: Caption before the interval (``Every``).
        interval: Number of units.
        interval_max: Largest interval (``todo.max_recurrence_interval``).
        frequency: Unit of the interval (days, weeks, months, years).
        weekdays_visible: Whether the weekday buttons are shown (weekly series).
        weekdays: The seven weekday buttons, Monday first.
    """

    every_label: str
    interval: int
    interval_max: int
    frequency: ChoiceFieldSnapshot
    weekdays_visible: bool
    weekdays: tuple[WeekdayToggleSnapshot, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class RecurrenceEndSnapshot:
    """When the series ends.

    Attributes:
        end: Never, on a date, after a count (``label`` is the caption ``Ends``).
        end_date_visible: Whether the end date field is shown.
        end_date: Date shown by the end date field.
        date_format: Display format of the date field.
        end_count_visible: Whether the count field is shown.
        end_count: Count shown by the count field.
        end_count_max: Largest count (``todo.max_recurrence_count``).
        end_count_suffix: Text after the count (``times``).
    """

    end: ChoiceFieldSnapshot
    end_date_visible: bool
    end_date: DateValueSnapshot
    date_format: str
    end_count_visible: bool
    end_count: int
    end_count_max: int
    end_count_suffix: str


@dataclass(frozen=True, slots=True, kw_only=True)
class RecurrenceFieldSnapshot:
    """The Repeat section: rule, end, summary and the next dates.

    Attributes:
        repeat_label: Text of the Repeat check box.
        enabled: Whether the task repeats (the other fields are enabled only then).
        rule: Interval, unit and weekdays.
        ending: End condition.
        summary: ``Every 2 weeks on Monday and Friday, 10 times``, ``""`` when off.
        preview: The next dates after the due date, ``""`` when off or invalid.
        error: First inline message of the section, ``""`` when valid.
    """

    repeat_label: str
    enabled: bool
    rule: RecurrenceRuleSnapshot
    ending: RecurrenceEndSnapshot
    summary: str
    preview: str
    error: str


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskEditSnapshot:
    """Everything the task dialog shows.

    Attributes:
        title: Window title ("New task" or "Edit task").
        text: Multi-line text; the first line is the title of the task.
        task_list: List of the task.
        due: Due date and time.
        recurrence: Repeat section.
        save: Save button.
        cancel: Cancel button.
    """

    title: str
    text: TextFieldSnapshot
    task_list: ChoiceFieldSnapshot
    due: DueFieldSnapshot
    recurrence: RecurrenceFieldSnapshot
    save: ButtonSnapshot
    cancel: ButtonSnapshot
