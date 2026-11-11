"""Business rules of the tasks."""

from collections.abc import Iterable
from datetime import date, time
from typing import Final

from concentrator.domain.common.entity_rules import EntityRules
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.multiline_text import MultilineText
from concentrator.domain.common.time_rules import TimeRules
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.todo.recurrence_rules import RecurrenceRules
from concentrator.domain.todo.task import STATE_FIELD, Task
from concentrator.domain.todo.task_draft import TaskDraft
from concentrator.domain.todo.task_lists_collection import TaskListsCollection
from concentrator.domain.todo.task_state_enum import TaskStateEnum
from concentrator.domain.todo.todo_limits import TodoLimits

TEXT_FIELD: Final = "text"
DUE_TIME_FIELD: Final = "due_time"
LIST_ID_FIELD: Final = "list_id"
COMPLETED_AT_FIELD: Final = "completed_at"
HISTORY_FIELD: Final = "history"
EVENT_AT_FIELD: Final = "at"


class TaskRules:
    """Stateless validation of the tasks. Field paths are those of a ``[[tasks]]`` element."""

    @staticmethod
    def validate(task: Task, limits: TodoLimits) -> ValidationResult:
        """Check one task: identity, editable values, state, recurrence and timestamps.

        Args:
            task: Task to check.
            limits: Bounds from ``concentrator.ini``.

        Returns:
            The merged result.
        """
        result = EntityRules.validate_identity(task).merge(
            TaskRules.validate_text(task.text, limits),
            TaskRules.validate_due(task.due_date, task.due_time),
            TaskRules.validate_state(task.state),
            RecurrenceRules.validate(task.recurrence, task.due_date, limits),
        )
        if task.completed_at is not None:
            result = result.merge(TimeRules.validate_utc(task.completed_at, COMPLETED_AT_FIELD))
        for index, event in enumerate(task.history):
            at = TimeRules.validate_utc(event.at, EVENT_AT_FIELD)
            result = result.merge(at.prefixed(f"{HISTORY_FIELD}.{index}"))
        return result

    @staticmethod
    def validate_draft(draft: TaskDraft, limits: TodoLimits) -> ValidationResult:
        """Check the values of the task editor or of the quick add field.

        Args:
            draft: Values entered.
            limits: Bounds from ``concentrator.ini``.

        Returns:
            The merged result, one issue per failing field.
        """
        return TaskRules.validate_text(draft.text, limits).merge(
            TaskRules.validate_due(draft.due_date, draft.due_time),
            RecurrenceRules.validate(draft.recurrence, draft.due_date, limits),
        )

    @staticmethod
    def validate_text(text: MultilineText, limits: TodoLimits) -> ValidationResult:
        """Check that the first line is not blank and that the text is not too long.

        Args:
            text: Text.
            limits: Bounds from ``concentrator.ini``.

        Returns:
            Success, ``TASK_TEXT_EMPTY`` or ``TASK_TEXT_TOO_LONG`` (``max``).
        """
        if not text.first_line.strip():
            return ValidationResult.failure(ErrorCodeEnum.TASK_TEXT_EMPTY, field=TEXT_FIELD)
        if len(text.as_text()) > limits.max_task_text_length:
            return ValidationResult.failure(
                ErrorCodeEnum.TASK_TEXT_TOO_LONG, field=TEXT_FIELD, max=limits.max_task_text_length
            )
        return ValidationResult.success()

    @staticmethod
    def validate_due(due_date: date | None, due_time: time | None) -> ValidationResult:
        """Check that a due time comes with a due date.

        Args:
            due_date: Due date.
            due_time: Due time.

        Returns:
            Success or ``TASK_DUE_TIME_WITHOUT_DATE`` on ``due_time``.
        """
        if due_time is not None and due_date is None:
            return ValidationResult.failure(ErrorCodeEnum.TASK_DUE_TIME_WITHOUT_DATE, field=DUE_TIME_FIELD)
        return ValidationResult.success()

    @staticmethod
    def validate_state(state: TaskStateEnum) -> ValidationResult:
        """Check that the state is a real one.

        Args:
            state: State.

        Returns:
            Success, ``ENUM_VALUE_UNSET`` or ``ENUM_VALUE_UNKNOWN`` on ``state``.
        """
        if state is TaskStateEnum.UNSET:
            return ValidationResult.failure(ErrorCodeEnum.ENUM_VALUE_UNSET, field=STATE_FIELD)
        if state is TaskStateEnum.UNKNOWN:
            return ValidationResult.failure(ErrorCodeEnum.ENUM_VALUE_UNKNOWN, field=STATE_FIELD)
        return ValidationResult.success()

    @staticmethod
    def validate_list_exists(lists: TaskListsCollection, list_id: str) -> ValidationResult:
        """Check that a task points at an existing list.

        Args:
            lists: Current lists.
            list_id: List of the task.

        Returns:
            Success or ``TASK_LIST_NOT_FOUND`` on ``list_id``.
        """
        if lists.contains(list_id):
            return ValidationResult.success()
        return ValidationResult.failure(ErrorCodeEnum.TASK_LIST_NOT_FOUND, field=LIST_ID_FIELD)

    @staticmethod
    def validate_all(tasks: Iterable[Task], lists: TaskListsCollection, limits: TodoLimits) -> ValidationResult:
        """Check the tasks read from a file, including their list.

        Args:
            tasks: Tasks in file order.
            lists: Lists of the file.
            limits: Bounds from ``concentrator.ini``.

        Returns:
            The merged result, fields ``<position in the file>.<field>``.
        """
        result = ValidationResult.success()
        for index, task in enumerate(tasks):
            own = TaskRules.validate(task, limits).merge(TaskRules.validate_list_exists(lists, task.list_id))
            result = result.merge(own.prefixed(str(index)))
        return result
