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
class TaskEditSnapshot:
    """Everything the task dialog shows.

    Attributes:
        title: Window title ("New task" or "Edit task").
        text: Multi-line text; the first line is the title of the task.
        task_list: List of the task.
        due: Due date and time.
        save: Save button.
        cancel: Cancel button.
    """

    title: str
    text: TextFieldSnapshot
    task_list: ChoiceFieldSnapshot
    due: DueFieldSnapshot
    save: ButtonSnapshot
    cancel: ButtonSnapshot
