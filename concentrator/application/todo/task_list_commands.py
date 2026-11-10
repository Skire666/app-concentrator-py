"""Write use cases of the TODO lists."""

import logging
from dataclasses import dataclass

from concentrator.application.common.event_bus import EventBus
from concentrator.application.ports.clock_port import ClockPort
from concentrator.application.ports.id_generator_port import IdGeneratorPort
from concentrator.application.ports.task_list_reader_port import TaskListReaderPort
from concentrator.application.ports.task_list_writer_port import TaskListWriterPort
from concentrator.application.ports.task_reader_port import TaskReaderPort
from concentrator.application.ports.task_writer_port import TaskWriterPort
from concentrator.application.todo.todo_events import TaskDeletedEvent, TaskListChangedEvent
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.multiline_text import MultilineText
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.todo.priority_enum import PriorityEnum
from concentrator.domain.todo.task_list import TaskList, TaskListId
from concentrator.domain.todo.task_list_rules import TaskListRules
from concentrator.domain.todo.task_lists_collection import TaskListsCollection
from concentrator.domain.todo.tasks_collection import TasksCollection
from concentrator.domain.todo.todo_limits import TodoLimits

_logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class ListValues:
    """What the list dialog edits.

    Attributes:
        name: Name as typed.
        description: Description.
        priority: Priority.
    """

    name: str
    description: MultilineText
    priority: PriorityEnum


@dataclass(frozen=True, slots=True, kw_only=True)
class TodoStores:
    """Readers and writers of the lists and tasks.

    Attributes:
        lists: Lists reader.
        list_writer: Lists writer.
        tasks: Tasks reader.
        task_writer: Tasks writer.
    """

    lists: TaskListReaderPort
    list_writer: TaskListWriterPort
    tasks: TaskReaderPort
    task_writer: TaskWriterPort


class TaskListCommands:
    """Create, update, delete and move a list. Each successful change publishes ``TaskListChangedEvent``.

    Names never reach the log.
    """

    def __init__(
        self, *, stores: TodoStores, ids: IdGeneratorPort, clock: ClockPort, event_bus: EventBus, limits: TodoLimits
    ) -> None:
        """Create the use cases.

        Args:
            stores: Readers and writers of the lists and tasks.
            ids: Ids of new lists.
            clock: Change instants.
            event_bus: Receives the events.
            limits: Bounds from ``concentrator.ini``.
        """
        self._stores = stores
        self._ids = ids
        self._clock = clock
        self._event_bus = event_bus
        self._limits = limits

    def create(self, values: ListValues) -> DataResult[TaskList]:
        """Add a list, last among the lists of its priority.

        Args:
            values: Name, description and priority.

        Returns:
            The stored list, or the rule failures (``LIST_NAME_DUPLICATE`` included).
        """
        lists = self._lists()
        task_list = TaskList.create(
            TaskListId(self._ids.new_id()),
            self._clock.now_utc(),
            name=values.name,
            description=values.description,
            priority=values.priority,
            position=lists.next_position(),
        )
        validation = TaskListRules.validate(task_list, self._limits).merge(
            TaskListRules.validate_unique_name(lists, task_list.name)
        )
        if validation.is_failure:
            return DataResult.fail(validation)
        return self._published(self._stores.list_writer.create(task_list), "created")

    def update(self, list_id: str, values: ListValues) -> DataResult[TaskList]:
        """Change a list; a new priority puts it last among the lists of that priority.

        Args:
            list_id: List to change.
            values: New name, description and priority.

        Returns:
            The stored list (unchanged values are not written), ``ENTITY_NOT_FOUND`` or the rule failures.
        """
        current = self._stores.lists.read_item(list_id)
        if current.data is None:
            return current
        now = self._clock.now_utc()
        changed = current.data.with_values(values.name, values.description, values.priority, now)
        if (changed.name, changed.description, changed.priority) == (
            current.data.name,
            current.data.description,
            current.data.priority,
        ):
            return current
        if changed.priority is not current.data.priority:
            changed = changed.with_position(self._lists().next_position(), now)
        validation = TaskListRules.validate(changed, self._limits).merge(
            TaskListRules.validate_unique_name(self._lists(), changed.name, except_id=list_id)
        )
        if validation.is_failure:
            return DataResult.fail(validation)
        return self._published(self._stores.list_writer.update(changed), "updated")

    def delete(self, list_id: str, *, delete_tasks: bool) -> ValidationResult:
        """Delete a list, and its tasks when the user confirmed it.

        Args:
            list_id: List to delete.
            delete_tasks: Whether its tasks may be deleted with it.

        Returns:
            Success, ``ENTITY_NOT_FOUND``, ``LIST_LAST_CANNOT_DELETE`` or ``LIST_NOT_EMPTY``.
        """
        tasks = self._stores.tasks.all_items().value_or(TasksCollection()).in_list(list_id)
        validation = TaskListRules.validate_deletion(self._lists(), list_id, len(tasks), delete_tasks=delete_tasks)
        if validation.is_failure:
            return validation
        task_ids = tuple(task.id for task in tasks)
        if task_ids:
            removed = self._stores.task_writer.delete_many(task_ids)
            if removed.data is None:
                return removed.validation
            self._event_bus.publish(TaskDeletedEvent(task_ids=task_ids))
        return self._published(self._stores.list_writer.delete(list_id), "deleted").validation

    def move(self, list_id: str, offset: int) -> ValidationResult:
        """Swap a list with its neighbor of the same priority.

        Args:
            list_id: List to move.
            offset: ``-1`` (earlier) or ``1`` (later).

        Returns:
            Success, ``ENTITY_NOT_FOUND``, or a skipped result at the edge of its priority group.
        """
        lists = self._lists()
        moved = lists.moved(list_id, offset, self._clock.now_utc())
        if moved.data is None:
            return moved.validation
        changed = [item for item in moved.data if lists.get(item.id).data != item]
        written = self._stores.list_writer.update_many(changed)
        if written.data is None:
            return written.validation
        _logger.info("Task list moved")
        self._event_bus.publish(TaskListChangedEvent(list_ids=tuple(item.id for item in changed)))
        return ValidationResult.success()

    def _lists(self) -> TaskListsCollection:
        """Return the current lists.

        Returns:
            The lists (empty if the in-memory read ever failed).
        """
        return self._stores.lists.all_items().value_or(TaskListsCollection())

    def _published(self, written: DataResult[TaskList], change: str) -> DataResult[TaskList]:
        """Publish the change of a successful write.

        Args:
            written: Writer result.
            change: What happened, for the log.

        Returns:
            The writer result.
        """
        if written.data is not None:
            _logger.info("Task list %s", change)
            self._event_bus.publish(TaskListChangedEvent(list_ids=(written.data.id,)))
        return written
