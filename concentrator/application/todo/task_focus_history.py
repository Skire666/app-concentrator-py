"""Records in the history of the tasks that they joined or left the focus queue."""

from collections.abc import Sequence

from concentrator.application.ports.clock_port import ClockPort
from concentrator.application.todo.task_list_commands import TodoStores
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.focus.focus_removal_reason_enum import FocusRemovalReasonEnum
from concentrator.domain.todo.task import Task
from concentrator.domain.todo.task_event import DETAIL_REASON, TaskEvent
from concentrator.domain.todo.task_event_kind_enum import TaskEventKindEnum
from concentrator.domain.todo.todo_limits import TodoLimits


class TaskFocusHistory:
    """Adds ``ADDED_TO_FOCUS`` and ``REMOVED_FROM_FOCUS`` events to tasks (phase 7).

    The focus feature never writes the tasks itself (``AGENTS.md`` section 6.3): it asks this TODO use case.
    It publishes no event; the focus use cases publish ``FocusQueueChangedEvent`` after it.
    """

    def __init__(self, *, stores: TodoStores, clock: ClockPort, limits: TodoLimits) -> None:
        """Create the use case.

        Args:
            stores: Readers and writers of the lists and tasks.
            clock: Event instants.
            limits: History cap.
        """
        self._stores = stores
        self._clock = clock
        self._limits = limits

    def record_added(self, task_ids: Sequence[str]) -> ValidationResult:
        """Record that tasks joined the queue.

        Args:
            task_ids: Queued tasks.

        Returns:
            Success, skipped when none of them exists, or the writer failure.
        """
        return self._record(task_ids, TaskEvent.of(self._clock.now_utc(), TaskEventKindEnum.ADDED_TO_FOCUS))

    def record_removed(self, task_ids: Sequence[str], reason: FocusRemovalReasonEnum) -> ValidationResult:
        """Record that tasks left the queue.

        Args:
            task_ids: Removed tasks (deleted ones are ignored).
            reason: Why they left.

        Returns:
            Success, skipped when none of them exists, or the writer failure.
        """
        event = TaskEvent(
            at=self._clock.now_utc(),
            kind=TaskEventKindEnum.REMOVED_FROM_FOCUS,
            details=((DETAIL_REASON, str(reason.value)),),
        )
        return self._record(task_ids, event)

    def _record(self, task_ids: Sequence[str], event: TaskEvent) -> ValidationResult:
        """Add one event to every existing task, in one write.

        Args:
            task_ids: Tasks concerned.
            event: Event to add.

        Returns:
            Success, skipped, or the writer failure.
        """
        changed: list[Task] = []
        for task_id in task_ids:
            found = self._stores.tasks.read_item(task_id)
            if found.data is not None:
                changed.append(found.data.with_event(event, self._limits.max_history_events))
        if not changed:
            return ValidationResult.skipped()
        written = self._stores.task_writer.update_many(changed)
        return written.validation if written.data is None else ValidationResult.success()
