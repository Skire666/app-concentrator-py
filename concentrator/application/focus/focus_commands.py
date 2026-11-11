"""Write use cases of the focus queue."""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from concentrator.application.common.event_bus import EventBus
from concentrator.application.focus.focus_events import FocusQueueChangedEvent
from concentrator.application.focus.focus_removal import FocusRemoval, FocusStores
from concentrator.application.focus.quick_add_list import QuickAddList
from concentrator.application.ports.clock_port import ClockPort
from concentrator.application.ports.id_generator_port import IdGeneratorPort
from concentrator.application.todo.task_commands import TaskCommands
from concentrator.application.todo.task_focus_history import TaskFocusHistory
from concentrator.application.todo.task_lookup import find_tasks
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.focus.focus_item import FocusItem, FocusItemId
from concentrator.domain.focus.focus_items_collection import FocusItemsCollection
from concentrator.domain.focus.focus_limits import FocusLimits
from concentrator.domain.focus.focus_removal_reason_enum import FocusRemovalReasonEnum
from concentrator.domain.focus.focus_rules import FocusRules
from concentrator.domain.todo.task import Task
from concentrator.domain.todo.task_event import SOURCE_FOCUS
from concentrator.domain.todo.task_rules import TEXT_FIELD

_logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class FocusTodo:
    """The TODO use cases the queue relies on (ADR-013: every item is a real task).

    Attributes:
        tasks: Creates and completes the tasks.
        history: Records the queue changes in the history of the tasks.
        quick_add_list: List of the tasks created by the quick-add field.
    """

    tasks: TaskCommands
    history: TaskFocusHistory
    quick_add_list: QuickAddList


class FocusCommands:
    """Queue, unqueue, reorder and complete tasks from zone 2. Every change publishes ``FocusQueueChangedEvent``.

    Texts never reach the log.
    """

    def __init__(
        self,
        *,
        stores: FocusStores,
        todo: FocusTodo,
        ids: IdGeneratorPort,
        clock: ClockPort,
        event_bus: EventBus,
        limits: FocusLimits,
    ) -> None:
        """Create the use cases.

        Args:
            stores: Queue, tasks and lists.
            todo: TODO use cases.
            ids: Ids of new items.
            clock: Change instants.
            event_bus: Receives the events.
            limits: Bounds from ``concentrator.ini``.
        """
        self._stores = stores
        self._todo = todo
        self._ids = ids
        self._clock = clock
        self._event_bus = event_bus
        self._limits = limits
        self._removal = FocusRemoval(stores=stores, history=todo.history, event_bus=event_bus)

    def add_tasks(self, task_ids: Sequence[str]) -> ValidationResult:
        """Queue the selected tasks that are open and not queued yet, at the end of the queue.

        Args:
            task_ids: Tasks to queue.

        Returns:
            Success; skipped for no task; ``ENTITY_NOT_FOUND``; when none can be queued, the reason for the
            first one (``FOCUS_TASK_NOT_OPEN``, ``FOCUS_TASK_ALREADY_QUEUED``); ``FOCUS_QUEUE_FULL`` when
            they do not all fit (nothing queued).
        """
        found = find_tasks(self._stores.tasks, task_ids)
        if found.data is None:
            return found.validation
        queue = self._stores.queue()
        tasks = [task for task in found.data if FocusRules.can_queue(task, queue)]
        if not tasks:
            return FocusRules.validate_add(found.data.items[0], queue, self._limits)
        room = FocusRules.validate_room(queue, len(tasks), self._limits)
        if room.is_failure:
            return room
        written = self._queued(tasks, queue, self._clock.now_utc())
        if written.is_failure:
            return written
        queued = tuple(task.id for task in tasks)
        _logger.info("%d tasks added to the focus queue", len(queued))
        recorded = self._todo.history.record_added(queued)
        self._event_bus.publish(FocusQueueChangedEvent(task_ids=queued))
        return recorded if recorded.is_failure else ValidationResult.success()

    def toggle_task(self, task_id: str) -> ValidationResult:
        """Queue a task, or take it out of the queue (star of the task table).

        Args:
            task_id: Task.

        Returns:
            The result of ``add_tasks`` or ``remove_tasks``.
        """
        if self._stores.queue().contains_task(task_id):
            return self.remove_tasks([task_id])
        return self.add_tasks([task_id])

    def remove_tasks(self, task_ids: Sequence[str]) -> ValidationResult:
        """Take tasks out of the queue; the tasks are untouched, their history says it.

        Args:
            task_ids: Tasks to unqueue (tasks not queued are ignored).

        Returns:
            Success, skipped when none is queued, or the writer failure.
        """
        return self._removal.remove(task_ids, FocusRemovalReasonEnum.BY_USER)

    def remove(self, item_id: str) -> ValidationResult:
        """Take one item out of the queue (x button of a row).

        Args:
            item_id: Item.

        Returns:
            Success, ``ENTITY_NOT_FOUND`` or the writer failure.
        """
        found = self._stores.items.read_item(item_id)
        if found.data is None:
            return found.validation
        return self.remove_tasks([found.data.task_id])

    def move(self, item_id: str, offset: int) -> ValidationResult:
        """Move an item up (negative offset) or down.

        Args:
            item_id: Item.
            offset: Number of places.

        Returns:
            Success, skipped at an end of the queue, ``ENTITY_NOT_FOUND`` or the writer failure.
        """
        queue = self._stores.queue()
        found = queue.get(item_id)
        if found.data is None:
            return found.validation
        if not queue.can_move(item_id, offset):
            return ValidationResult.skipped()
        moved = queue.moved(item_id, offset, self._clock.now_utc())
        changed = [item for item in moved if queue.get(item.id).data != item]
        written = self._stores.item_writer.update_many(changed)
        if written.data is None:
            return written.validation
        self._event_bus.publish(FocusQueueChangedEvent(task_ids=(found.data.task_id,)))
        return ValidationResult.success()

    def complete(self, item_id: str) -> ValidationResult:
        """Complete the task of an item (its check box); the reactions then take it out of the queue.

        A recurring task completes its current occurrence and stays open. The completion event says
        ``source = "focus"``.

        Args:
            item_id: Item.

        Returns:
            The result of ``TaskCommands.complete``, or ``ENTITY_NOT_FOUND``.
        """
        found = self._stores.items.read_item(item_id)
        if found.data is None:
            return found.validation
        return self._todo.tasks.complete([found.data.task_id], source=SOURCE_FOCUS)

    def quick_add(self, text: str, preferred_list_id: str) -> DataResult[Task]:
        """Create a task in the quick-add list and queue it.

        Args:
            text: Text as typed.
            preferred_list_id: List chosen for the quick add (``""`` for the Inbox).

        Returns:
            The created task; ``FOCUS_QUEUE_FULL`` (no task created), ``TASK_TEXT_EMPTY`` or the other
            creation failures.
        """
        room = FocusRules.validate_room(self._stores.queue(), 1, self._limits)
        if room.is_failure:
            return DataResult.fail(room)
        if not text.strip():
            return DataResult.fail(ValidationResult.failure(ErrorCodeEnum.TASK_TEXT_EMPTY, field=TEXT_FIELD))
        target = self._todo.quick_add_list.resolve(preferred_list_id)
        if target.data is None:
            return DataResult.fail(target.validation)
        created = self._todo.tasks.quick_add(target.data.id, text)
        if created.data is None:
            return created
        queued = self.add_tasks([created.data.id])
        if queued.is_failure:
            return DataResult.fail(queued)
        return created

    def _queued(self, tasks: Sequence[Task], queue: FocusItemsCollection, now: datetime) -> ValidationResult:
        """Write one item per task at the end of the queue.

        Args:
            tasks: Tasks to queue (checked).
            queue: Current queue.
            now: Creation instant.

        Returns:
            Success or the first writer failure.
        """
        position = queue.next_position()
        for offset, task in enumerate(tasks):
            item = FocusItem.create(FocusItemId(self._ids.new_id()), now, task_id=task.id, position=position + offset)
            written = self._stores.item_writer.create(item)
            if written.data is None:
                return written.validation
        return ValidationResult.success()
