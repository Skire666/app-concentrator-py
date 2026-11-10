"""Business rules of the TODO lists."""

from collections.abc import Iterable
from typing import Final

from concentrator.domain.common.entity_rules import EntityRules
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.multiline_text import MultilineText
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.todo.priority_enum import PriorityEnum
from concentrator.domain.todo.task_list import TaskList, normalize_list_name
from concentrator.domain.todo.task_lists_collection import TaskListsCollection
from concentrator.domain.todo.todo_limits import TodoLimits

NAME_FIELD: Final = "name"
DESCRIPTION_FIELD: Final = "description"
PRIORITY_FIELD: Final = "priority"
POSITION_FIELD: Final = "position"
MIN_POSITION: Final = 0
MIN_LISTS: Final = 1


class TaskListRules:
    """Stateless validation of the lists. Field paths are those of a ``[[task_lists]]`` element."""

    @staticmethod
    def validate(task_list: TaskList, limits: TodoLimits) -> ValidationResult:
        """Check the identity, the editable values and the position of one list.

        Args:
            task_list: List to check.
            limits: Bounds from ``concentrator.ini``.

        Returns:
            The merged result.
        """
        position = (
            ValidationResult.success()
            if task_list.position >= MIN_POSITION
            else ValidationResult.failure(ErrorCodeEnum.VALUE_OUT_OF_RANGE, field=POSITION_FIELD, min=MIN_POSITION)
        )
        return EntityRules.validate_identity(task_list).merge(
            TaskListRules.validate_values(task_list.name, task_list.description, task_list.priority, limits), position
        )

    @staticmethod
    def validate_values(
        name: str, description: MultilineText, priority: PriorityEnum, limits: TodoLimits
    ) -> ValidationResult:
        """Check the values of the list dialog.

        Args:
            name: Name (as typed or normalized).
            description: Description.
            priority: Priority.
            limits: Bounds from ``concentrator.ini``.

        Returns:
            The merged result, one issue per failing field.
        """
        return TaskListRules.validate_name(name, limits).merge(
            TaskListRules.validate_description(description, limits), TaskListRules.validate_priority(priority)
        )

    @staticmethod
    def validate_name(name: str, limits: TodoLimits) -> ValidationResult:
        """Check that a name is not blank and not too long.

        Args:
            name: Name.
            limits: Bounds from ``concentrator.ini``.

        Returns:
            Success, ``LIST_NAME_EMPTY`` or ``LIST_NAME_TOO_LONG`` (``max``).
        """
        normalized = normalize_list_name(name)
        if not normalized:
            return ValidationResult.failure(ErrorCodeEnum.LIST_NAME_EMPTY, field=NAME_FIELD)
        if len(normalized) > limits.max_list_name_length:
            return ValidationResult.failure(
                ErrorCodeEnum.LIST_NAME_TOO_LONG, field=NAME_FIELD, max=limits.max_list_name_length
            )
        return ValidationResult.success()

    @staticmethod
    def validate_description(description: MultilineText, limits: TodoLimits) -> ValidationResult:
        """Check the length of a description (lines joined with one line break).

        Args:
            description: Description.
            limits: Bounds from ``concentrator.ini``.

        Returns:
            Success or ``LIST_DESCRIPTION_TOO_LONG`` (``max``).
        """
        if len(description.as_text()) <= limits.max_list_description_length:
            return ValidationResult.success()
        return ValidationResult.failure(
            ErrorCodeEnum.LIST_DESCRIPTION_TOO_LONG, field=DESCRIPTION_FIELD, max=limits.max_list_description_length
        )

    @staticmethod
    def validate_priority(priority: PriorityEnum) -> ValidationResult:
        """Check that a real priority is chosen.

        Args:
            priority: Priority.

        Returns:
            Success, ``LIST_PRIORITY_UNSET`` or ``ENUM_VALUE_UNKNOWN``.
        """
        if priority is PriorityEnum.UNSET:
            return ValidationResult.failure(ErrorCodeEnum.LIST_PRIORITY_UNSET, field=PRIORITY_FIELD)
        if priority is PriorityEnum.UNKNOWN:
            return ValidationResult.failure(ErrorCodeEnum.ENUM_VALUE_UNKNOWN, field=PRIORITY_FIELD)
        return ValidationResult.success()

    @staticmethod
    def validate_unique_name(lists: TaskListsCollection, name: str, except_id: str = "") -> ValidationResult:
        """Check that no other list has the same name without regard to case.

        Args:
            lists: Current lists.
            name: Name of the new or edited list.
            except_id: List being edited.

        Returns:
            Success or ``LIST_NAME_DUPLICATE`` on ``name``.
        """
        if lists.with_name(name, except_id) is None:
            return ValidationResult.success()
        return ValidationResult.failure(ErrorCodeEnum.LIST_NAME_DUPLICATE, field=NAME_FIELD)

    @staticmethod
    def validate_deletion(
        lists: TaskListsCollection, list_id: str, task_count: int, *, delete_tasks: bool
    ) -> ValidationResult:
        """Check that a list may be deleted.

        Args:
            lists: Current lists.
            list_id: List to delete.
            task_count: Number of tasks of the list.
            delete_tasks: Whether the user confirmed that its tasks are deleted too.

        Returns:
            Success, ``ENTITY_NOT_FOUND``, ``LIST_LAST_CANNOT_DELETE`` or ``LIST_NOT_EMPTY`` (``count``).
        """
        found = lists.get(list_id)
        if not found.is_success:
            return found.validation
        if len(lists) <= MIN_LISTS:
            return ValidationResult.failure(ErrorCodeEnum.LIST_LAST_CANNOT_DELETE)
        if task_count and not delete_tasks:
            return ValidationResult.failure(ErrorCodeEnum.LIST_NOT_EMPTY, count=task_count)
        return ValidationResult.success()

    @staticmethod
    def validate_all(lists: Iterable[TaskList], limits: TodoLimits) -> ValidationResult:
        """Check the lists read from a file: each list, then the unique names.

        Args:
            lists: Lists in file order.
            limits: Bounds from ``concentrator.ini``.

        Returns:
            The merged result, fields ``<position in the file>.<field>``.
        """
        result = ValidationResult.success()
        seen: set[str] = set()
        for index, task_list in enumerate(lists):
            result = result.merge(TaskListRules.validate(task_list, limits).prefixed(str(index)))
            folded = task_list.name.casefold()
            if folded in seen:
                duplicate = ValidationResult.failure(ErrorCodeEnum.LIST_NAME_DUPLICATE, field=NAME_FIELD)
                result = result.merge(duplicate.prefixed(str(index)))
            seen.add(folded)
        return result
