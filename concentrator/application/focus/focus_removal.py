"""Removes tasks from the focus queue: shared by the commands and the reactions to task events."""

import logging
from collections.abc import Sequence
from dataclasses import dataclass

from concentrator.application.common.event_bus import EventBus
from concentrator.application.focus.focus_events import FocusQueueChangedEvent
from concentrator.application.ports.focus_item_reader_port import FocusItemReaderPort
from concentrator.application.ports.focus_item_writer_port import FocusItemWriterPort
from concentrator.application.ports.task_list_reader_port import TaskListReaderPort
from concentrator.application.ports.task_reader_port import TaskReaderPort
from concentrator.application.todo.task_focus_history import TaskFocusHistory
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.focus.focus_items_collection import FocusItemsCollection
from concentrator.domain.focus.focus_removal_reason_enum import FocusRemovalReasonEnum

_logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class FocusStores:
    """Readers and writer used by the focus queue.

    Attributes:
        items: Queue reader.
        item_writer: Queue writer.
        tasks: Tasks reader.
        lists: Lists reader.
    """

    items: FocusItemReaderPort
    item_writer: FocusItemWriterPort
    tasks: TaskReaderPort
    lists: TaskListReaderPort

    def queue(self) -> FocusItemsCollection:
        """Return the current queue.

        Returns:
            The items (``ordered()`` gives the queue order).
        """
        return self.items.all_items().value_or(FocusItemsCollection())


class FocusRemoval:
    """Deletes the items of some tasks in one write, records the removal, publishes the change."""

    def __init__(self, *, stores: FocusStores, history: TaskFocusHistory, event_bus: EventBus) -> None:
        """Create the helper.

        Args:
            stores: Queue and tasks.
            history: Records ``REMOVED_FROM_FOCUS``.
            event_bus: Receives ``FocusQueueChangedEvent``.
        """
        self._stores = stores
        self._history = history
        self._event_bus = event_bus

    def remove(self, task_ids: Sequence[str], reason: FocusRemovalReasonEnum | None) -> ValidationResult:
        """Remove the items of some tasks (tasks not queued are ignored).

        Args:
            task_ids: Tasks to take out of the queue.
            reason: Recorded in their history; ``None`` records nothing (deleted task, completion made
                from the queue, whose event already says so).

        Returns:
            Success, skipped when none is queued, or the writer failure.
        """
        items = self._stores.queue().items_of_tasks(task_ids)
        if not items:
            return ValidationResult.skipped()
        deleted = self._stores.item_writer.delete_many([item.id for item in items])
        if deleted.data is None:
            return deleted.validation
        removed = tuple(item.task_id for item in items)
        reason_name = "none" if reason is None else reason.name
        _logger.info("%d tasks removed from the focus queue (%s)", len(removed), reason_name)
        recorded = ValidationResult.skipped() if reason is None else self._history.record_removed(removed, reason)
        self._event_bus.publish(FocusQueueChangedEvent(task_ids=removed))
        return recorded if recorded.is_failure else ValidationResult.success()
