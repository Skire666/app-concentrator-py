"""Display texts of the focus queue: one row per queued task, one entry per task proposed by the search."""

from datetime import datetime
from typing import Final

from concentrator.application.focus.focus_queries import FocusEntry
from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.domain.focus.focus_items_collection import FocusItemsCollection
from concentrator.domain.todo.due_marks import due_marks
from concentrator.domain.todo.task import Task
from concentrator.presentation.common.action_button import action_button
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.row_tone_enum import RowToneEnum
from concentrator.presentation.common.ui_texts import UiTexts
from concentrator.presentation.focus.focus_queue_snapshot import FocusRowSnapshot, PickerChoiceSnapshot
from concentrator.presentation.todo.task_row_formatter import TaskRowFormatter

UP: Final = -1
DOWN: Final = 1
LINE_BREAK: Final = "\n"


class FocusRowFormatter:
    """Builds the rows of the queue and the entries of the search field in the current language."""

    def __init__(self, translator: TranslatorPort, gate: ActionGate, tasks: TaskRowFormatter) -> None:
        """Create the formatter.

        Args:
            translator: Current-language translator.
            gate: Busy actions (their controls are disabled).
            tasks: Due date texts, shared with the task table.
        """
        self._translator = translator
        self._texts = UiTexts(translator)
        self._gate = gate
        self._tasks = tasks

    def row(self, entry: FocusEntry, now: datetime, queue: FocusItemsCollection) -> FocusRowSnapshot:
        """Describe one queued task.

        Args:
            entry: Item, task and list name.
            now: Current local time (due marks).
            queue: The whole queue (moves at both ends).

        Returns:
            The row.
        """
        task = entry.task
        item_id = entry.item.id
        tooltip_lines = (*task.text.lines, self._translator.tr("focus.row.list", name=entry.list_name))
        return FocusRowSnapshot(
            item_id=item_id,
            text=first_line(task),
            tooltip=LINE_BREAK.join(tooltip_lines),
            list_name=entry.list_name,
            due_text=self._tasks.due_text(task),
            tone=_tone(task, now),
            complete=action_button(self._texts, self._gate, ActionIdEnum.FOCUS_COMPLETE),
            remove=action_button(self._texts, self._gate, ActionIdEnum.FOCUS_REMOVE),
            menu=(
                action_button(self._texts, self._gate, ActionIdEnum.FOCUS_MOVE_UP, enabled=queue.can_move(item_id, UP)),
                action_button(
                    self._texts, self._gate, ActionIdEnum.FOCUS_MOVE_DOWN, enabled=queue.can_move(item_id, DOWN)
                ),
                action_button(self._texts, self._gate, ActionIdEnum.FOCUS_SHOW_IN_LIST),
            ),
        )

    def choice(self, task: Task, list_name: str) -> PickerChoiceSnapshot:
        """Describe a task proposed by the search field.

        Args:
            task: Open task not queued yet.
            list_name: Name of its list.

        Returns:
            ``Call the bank — Home``.
        """
        return PickerChoiceSnapshot(
            task_id=task.id, text=self._translator.tr("focus.picker.choice", text=first_line(task), list=list_name)
        )


def first_line(task: Task) -> str:
    """First line of the text of a task.

    Args:
        task: Task.

    Returns:
        The line, ``""`` for an empty text.
    """
    return task.text.lines[0] if task.text.lines else ""


def _tone(task: Task, now: datetime) -> RowToneEnum:
    """Emphasis of a queued task, as in the task table.

    Args:
        task: Open task.
        now: Current local time.

    Returns:
        ERROR when overdue, WARNING when due today, NORMAL otherwise.
    """
    marks = due_marks(task, now)
    if marks.is_overdue:
        return RowToneEnum.ERROR
    return RowToneEnum.WARNING if marks.is_today else RowToneEnum.NORMAL
