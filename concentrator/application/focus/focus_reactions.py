"""Keeps the focus queue in step with the tasks changed elsewhere (zone 1, deleted lists)."""

import logging

from concentrator.application.common.event_bus import EventBus
from concentrator.application.focus.focus_removal import FocusRemoval, FocusStores
from concentrator.application.todo.todo_events import (
    TaskDeletedEvent,
    TaskOccurrenceCompletedEvent,
    TaskStateChangedEvent,
)
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.focus.focus_removal_reason_enum import FocusRemovalReasonEnum
from concentrator.domain.todo.task_event import DETAIL_SOURCE, SOURCE_FOCUS
from concentrator.domain.todo.task_event_kind_enum import TaskEventKindEnum
from concentrator.domain.todo.task_state_enum import TaskStateEnum

_logger = logging.getLogger(__name__)

_COMPLETION_KINDS = frozenset({TaskEventKindEnum.COMPLETED, TaskEventKindEnum.OCCURRENCE_COMPLETED})
_REASONS = {
    TaskStateEnum.DONE: FocusRemovalReasonEnum.COMPLETED,
    TaskStateEnum.ARCHIVED: FocusRemovalReasonEnum.ARCHIVED,
}


class FocusReactions:
    """A queued task that is done, archived, has an occurrence completed or is deleted leaves the queue.

    The removal is recorded in the history of the task (``REMOVED_FROM_FOCUS`` with its reason), except
    for a deleted task and for a completion made from the queue, whose event already says
    ``source = "focus"`` (owner decision at the phase 7 plan review). Reopening a task does not queue it
    again.
    """

    def __init__(self, *, stores: FocusStores, removal: FocusRemoval) -> None:
        """Create the reactions.

        Args:
            stores: Queue and tasks.
            removal: Removes the items.
        """
        self._stores = stores
        self._removal = removal

    def subscribe(self, event_bus: EventBus) -> None:
        """Listen to the task events.

        Args:
            event_bus: Bus of the application.
        """
        event_bus.subscribe(TaskStateChangedEvent, self.on_state_changed)
        event_bus.subscribe(TaskOccurrenceCompletedEvent, self.on_occurrence_completed)
        event_bus.subscribe(TaskDeletedEvent, self.on_deleted)

    def on_state_changed(self, event: TaskStateChangedEvent) -> None:
        """Unqueue a task that became done or archived.

        Args:
            event: The change.
        """
        reason = _REASONS.get(event.new_state)
        if reason is not None:
            self._unqueue(event.task_id, reason)

    def on_occurrence_completed(self, event: TaskOccurrenceCompletedEvent) -> None:
        """Unqueue a recurring task whose occurrence was completed (it stays open for the next date).

        Args:
            event: The completion.
        """
        self._unqueue(event.task_id, FocusRemovalReasonEnum.OCCURRENCE_COMPLETED)

    def on_deleted(self, event: TaskDeletedEvent) -> None:
        """Unqueue deleted tasks, recording nothing.

        Args:
            event: The deletion.
        """
        self._log(self._removal.remove(event.task_ids, None))

    def _unqueue(self, task_id: str, reason: FocusRemovalReasonEnum) -> None:
        """Remove the item of a task, if it is queued.

        Args:
            task_id: Task.
            reason: Why it leaves the queue.
        """
        if not self._stores.queue().contains_task(task_id):
            return
        recorded = None if self._completed_from_focus(task_id) else reason
        self._log(self._removal.remove([task_id], recorded))

    def _completed_from_focus(self, task_id: str) -> bool:
        """Tell whether the last event of a task is a completion made from the queue.

        Args:
            task_id: Task.

        Returns:
            Whether its history already says the task left the queue.
        """
        task = self._stores.tasks.read_item(task_id).data
        last = None if task is None else task.history.last
        return last is not None and last.kind in _COMPLETION_KINDS and last.detail(DETAIL_SOURCE) == SOURCE_FOCUS

    @staticmethod
    def _log(result: ValidationResult) -> None:
        """Log a removal that could not be written (an event handler has no caller to report to).

        Args:
            result: Result of the removal.
        """
        if result.is_failure:
            _logger.warning("Focus queue not updated after a task change: %s", result.error_codes)
