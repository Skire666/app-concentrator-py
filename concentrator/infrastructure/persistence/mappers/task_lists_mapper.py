"""``TaskListSchema`` elements <-> ``TaskListsCollection``."""

from collections.abc import Sequence

from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.multiline_text import MultilineText
from concentrator.domain.todo.priority_enum import PriorityEnum
from concentrator.domain.todo.task_list import TaskList, TaskListId, normalize_list_name
from concentrator.domain.todo.task_list_rules import TaskListRules
from concentrator.domain.todo.task_lists_collection import TaskListsCollection
from concentrator.domain.todo.todo_limits import TodoLimits
from concentrator.infrastructure.persistence.schemas.task_list_schema import TaskListSchema


class TaskListsMapper:
    """Converts the ``[[task_lists]]`` elements."""

    @staticmethod
    def to_domain(
        schemas: Sequence[TaskListSchema], field_prefix: str, limits: TodoLimits
    ) -> DataResult[TaskListsCollection]:
        """Build and validate the lists; an unknown priority integer becomes ``UNKNOWN``.

        Args:
            schemas: Validated DTOs, in file order.
            field_prefix: Dotted path of the collection in the file (``task_lists``).
            limits: Bounds from ``concentrator.ini``.

        Returns:
            The lists, or the rule failures with fields such as ``task_lists.0.name``.
        """
        lists = [
            TaskList(
                id=TaskListId(schema.id),
                created_at=schema.created_at,
                updated_at=schema.updated_at,
                name=normalize_list_name(schema.name),
                description=MultilineText.from_lines(schema.description),
                priority=PriorityEnum.parse(schema.priority),
                position=schema.position,
            )
            for schema in schemas
        ]
        validation = TaskListRules.validate_all(lists, limits).prefixed(field_prefix)
        if validation.is_failure:
            return DataResult.fail(validation)
        collection = TaskListsCollection.from_items(lists, field_prefix)
        if collection.data is None:
            return DataResult.fail(collection.validation)
        return DataResult.ok(collection.data, validation)

    @staticmethod
    def to_schema(lists: TaskListsCollection) -> tuple[TaskListSchema, ...]:
        """Build the DTOs written to the file, in display order.

        Args:
            lists: Validated lists.

        Returns:
            The DTOs.
        """
        return tuple(
            TaskListSchema(
                id=task_list.id,
                created_at=task_list.created_at,
                updated_at=task_list.updated_at,
                name=task_list.name,
                description=task_list.description.lines,
                priority=task_list.priority.value,
                position=task_list.position,
            )
            for task_list in lists.ordered()
        )
