"""Bulk due date use cases of the tasks (phase 6)."""

import logging
from collections.abc import Sequence
from datetime import date

from concentrator.application.common.event_bus import EventBus
from concentrator.application.ports.clock_port import ClockPort
from concentrator.application.todo.task_list_commands import TodoStores
from concentrator.application.todo.task_lookup import find_tasks
from concentrator.application.todo.todo_events import TaskChangedEvent
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.todo.task import Task
from concentrator.domain.todo.task_rules import TaskRules
from concentrator.domain.todo.todo_limits import TodoLimits

_logger = logging.getLogger(__name__)


class TaskScheduleCommands:
    """Set or clear the due date of selected tasks: every task, or none; one ``DUE_CHANGED`` event per task.

    A split of ``TaskCommands`` (AGENTS.md 6.3: about ten use cases per class).
    """

    def __init__(self, *, stores: TodoStores, clock: ClockPort, event_bus: EventBus, limits: TodoLimits) -> None:
        """Create the use cases.

        Args:
            stores: Readers and writers of the tasks.
            clock: Change instants.
            event_bus: Receives the events.
            limits: Bounds from ``concentrator.ini``.
        """
        self._stores = stores
        self._clock = clock
        self._event_bus = event_bus
        self._limits = limits

    def set_due_date(self, task_ids: Sequence[str], due_date: date) -> ValidationResult:
        """Give tasks a due date; each keeps its due time, and a recurring task starts its series on that date.

        Args:
            task_ids: Tasks to change.
            due_date: New due date.

        Returns:
            Success, skipped when nothing changes, ``ENTITY_NOT_FOUND`` or a rule failure
            (``RECURRENCE_END_DATE_BEFORE_DUE``); nothing is written on failure.
        """
        return self._changed(task_ids, due_date)

    def clear_due_date(self, task_ids: Sequence[str]) -> ValidationResult:
        """Remove the due date and time of tasks.

        Args:
            task_ids: Tasks to change.

        Returns:
            Success, skipped when nothing changes, ``ENTITY_NOT_FOUND`` or ``RECURRENCE_REQUIRES_DUE_DATE`` when a
            selected task repeats; nothing is written on failure.
        """
        return self._changed(task_ids, None)

    def _changed(self, task_ids: Sequence[str], due_date: date | None) -> ValidationResult:
        """Change the due date of every task, or of none.

        Args:
            task_ids: Tasks to change.
            due_date: New due date, ``None`` to clear it.

        Returns:
            Success, skipped, ``ENTITY_NOT_FOUND`` or the first rule failure.
        """
        found = find_tasks(self._stores.tasks, task_ids)
        if found.data is None:
            return found.validation
        now = self._clock.now_utc()
        changed: list[Task] = []
        for task in found.data:
            after = task.with_due_date(due_date, now, self._limits.max_history_events)
            if after is task:
                continue
            validation = TaskRules.validate(after, self._limits)
            if validation.is_failure:
                return validation
            changed.append(after)
        if not changed:
            return ValidationResult.skipped()
        written = self._stores.task_writer.update_many(changed)
        if written.data is None:
            return written.validation
        _logger.info("Due date of %d tasks %s", len(changed), "set" if due_date else "cleared")
        self._event_bus.publish(TaskChangedEvent(task_ids=tuple(task.id for task in changed)))
        return ValidationResult.success()
