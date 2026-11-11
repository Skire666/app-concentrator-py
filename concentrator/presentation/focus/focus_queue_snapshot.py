"""Snapshot of the focus queue of zone 2 (``FOCUS_QUEUE``)."""

from dataclasses import dataclass

from concentrator.presentation.common.button_snapshot import ButtonSnapshot
from concentrator.presentation.common.row_tone_enum import RowToneEnum


@dataclass(frozen=True, slots=True, kw_only=True)
class FocusRowSnapshot:
    """One queued task.

    Attributes:
        item_id: Item sent back with the row actions.
        text: First line of the task (user text: shown as typed).
        tooltip: Every line of the task, then its list.
        list_name: Name of the list of the task.
        due_text: Due date badge, ``""`` without a due date.
        tone: ERROR when overdue, WARNING when due today, NORMAL otherwise.
        complete: Check box: completes the task (``FOCUS_COMPLETE``).
        remove: The x button: takes the task out of the queue (``FOCUS_REMOVE``).
        menu: Move up, Move down, Show in list.
    """

    item_id: str
    text: str
    tooltip: str
    list_name: str
    due_text: str
    tone: RowToneEnum
    complete: ButtonSnapshot
    remove: ButtonSnapshot
    menu: tuple[ButtonSnapshot, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class PickerChoiceSnapshot:
    """One task proposed by the search field of the queue.

    Attributes:
        task_id: Task queued when the entry is chosen.
        text: First line of the task and its list (user text).
    """

    task_id: str
    text: str


@dataclass(frozen=True, slots=True, kw_only=True)
class FocusFieldSnapshot:
    """A one-line field of the queue (search or quick add).

    Attributes:
        text: Text of the field (emptied after a task was added).
        placeholder: Hint shown while empty.
        tooltip: What Enter does.
        cleared_count: Grows each time the field is emptied by an addition, so the field is emptied even when
            the last rendered snapshot already had an empty text (keys typed between two renders).
    """

    text: str
    placeholder: str
    tooltip: str
    cleared_count: int


@dataclass(frozen=True, slots=True, kw_only=True)
class FocusQueueSnapshot:
    """Everything the queue panel shows.

    Attributes:
        title: "Focus" header.
        capacity: Number of items out of the capacity (``4 / 20``).
        capacity_tooltip: Explains the capacity.
        rows: Queued tasks, in order.
        empty_text: Shown instead of the rows when the queue is empty.
        picker: Search field over the open tasks of every list.
        choices: Tasks matching the search, at most ``focus.picker_max_results``.
        quick_add: Field that creates a task in the quick-add list and queues it.
        error: Inline message of the last refused action, ``""`` when none.

    The fields are never disabled, so they keep the focus between two additions; an Enter during the
    cooldown is ignored by the action gate.
    """

    title: str
    capacity: str
    capacity_tooltip: str
    rows: tuple[FocusRowSnapshot, ...]
    empty_text: str
    picker: FocusFieldSnapshot
    choices: tuple[PickerChoiceSnapshot, ...]
    quick_add: FocusFieldSnapshot
    error: str
