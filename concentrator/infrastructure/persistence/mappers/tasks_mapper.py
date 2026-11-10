"""``TaskSchema`` elements <-> ``TasksCollection``."""

import logging
from collections.abc import Sequence

from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.multiline_text import MultilineText
from concentrator.domain.todo.task import Task, TaskId, due_minutes
from concentrator.domain.todo.task_event import TaskEvent
from concentrator.domain.todo.task_event_kind_enum import TaskEventKindEnum
from concentrator.domain.todo.task_history import TaskHistory
from concentrator.domain.todo.task_list import TaskListId
from concentrator.domain.todo.task_lists_collection import TaskListsCollection
from concentrator.domain.todo.task_rules import TaskRules
from concentrator.domain.todo.task_state_enum import TaskStateEnum
from concentrator.domain.todo.tasks_collection import TasksCollection
from concentrator.domain.todo.todo_limits import TodoLimits
from concentrator.infrastructure.persistence.schemas.task_schema import TaskEventSchema, TaskSchema

_logger = logging.getLogger(__name__)


def _event(schema: TaskEventSchema) -> TaskEvent:
    """Build one history event; an unknown kind integer becomes ``UNKNOWN``.

    Args:
        schema: Validated DTO.

    Returns:
        The event.
    """
    return TaskEvent(at=schema.at, kind=TaskEventKindEnum.parse(schema.kind), details=tuple(schema.details.items()))


def _task(schema: TaskSchema, max_events: int) -> Task:
    """Build one task; a history longer than the cap keeps its origin and newest events.

    Args:
        schema: Validated DTO.
        max_events: ``todo.max_history_events``.

    Returns:
        The task, not validated yet.
    """
    return Task(
        id=TaskId(schema.id),
        created_at=schema.created_at,
        updated_at=schema.updated_at,
        list_id=TaskListId(schema.list_id),
        text=MultilineText.from_lines(schema.text),
        due_date=schema.due_date,
        due_time=due_minutes(schema.due_time),
        state=TaskStateEnum.parse(schema.state),
        completed_at=schema.completed_at,
        history=TaskHistory.capped((_event(event) for event in schema.history), max_events),
    )


def _event_schema(event: TaskEvent) -> TaskEventSchema:
    """Build the DTO of one history event.

    Args:
        event: Event.

    Returns:
        The DTO.
    """
    return TaskEventSchema(at=event.at, kind=event.kind.value, details=dict(event.details))


class TasksMapper:
    """Converts the ``[[tasks]]`` elements."""

    @staticmethod
    def to_domain(
        schemas: Sequence[TaskSchema], field_prefix: str, lists: TaskListsCollection, limits: TodoLimits
    ) -> DataResult[TasksCollection]:
        """Build and validate the tasks; every task must belong to one of the lists.

        Args:
            schemas: Validated DTOs, in file order.
            field_prefix: Dotted path of the collection in the file (``tasks``).
            lists: Lists of the file (``TASK_LIST_NOT_FOUND`` for any other ``list_id``).
            limits: Bounds from ``concentrator.ini``.

        Returns:
            The tasks, or the rule failures with fields such as ``tasks.3.list_id``.
        """
        tasks = [_task(schema, limits.max_history_events) for schema in schemas]
        capped = sum(len(task.history) < len(schema.history) for task, schema in zip(tasks, schemas, strict=True))
        if capped:
            _logger.info("History of %d tasks shortened to %d events", capped, limits.max_history_events)
        validation = TaskRules.validate_all(tasks, lists, limits).prefixed(field_prefix)
        if validation.is_failure:
            return DataResult.fail(validation)
        collection = TasksCollection.from_items(tasks, field_prefix)
        if collection.data is None:
            return DataResult.fail(collection.validation)
        return DataResult.ok(collection.data, validation)

    @staticmethod
    def to_schema(tasks: TasksCollection) -> tuple[TaskSchema, ...]:
        """Build the DTOs written to the file, in stored order; unset optional values are ``None``.

        Args:
            tasks: Validated tasks.

        Returns:
            The DTOs.
        """
        return tuple(
            TaskSchema(
                id=task.id,
                created_at=task.created_at,
                updated_at=task.updated_at,
                list_id=task.list_id,
                text=task.text.lines,
                due_date=task.due_date,
                due_time=task.due_time,
                state=task.state.value,
                completed_at=task.completed_at,
                history=tuple(_event_schema(event) for event in task.history),
            )
            for task in tasks
        )
