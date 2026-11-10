"""A task of a TODO list."""

from dataclasses import dataclass, replace
from datetime import date, datetime, time
from typing import Final, NewType, Self

from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.multiline_text import MultilineText
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.todo.task_draft import TaskDraft, due_text
from concentrator.domain.todo.task_event import DETAIL_FROM, DETAIL_SOURCE, DETAIL_TO, TaskEvent
from concentrator.domain.todo.task_event_kind_enum import TaskEventKindEnum
from concentrator.domain.todo.task_history import TaskHistory
from concentrator.domain.todo.task_list import TaskListId
from concentrator.domain.todo.task_state_enum import TaskStateEnum
from concentrator.domain.todo.task_transitions import TRANSITION_KINDS, transition_target

TaskId = NewType("TaskId", str)

STATE_FIELD: Final = "state"


def due_minutes(value: time | None) -> time | None:
    """Drop the seconds of a due time.

    Args:
        value: Time as entered.

    Returns:
        The time to the minute, or ``None``.
    """
    return None if value is None else value.replace(second=0, microsecond=0)


def _change(kind: TaskEventKindEnum, now: datetime, old: str, new: str) -> TaskEvent:
    """Build an event that records a previous and a new value.

    Args:
        kind: ``DUE_CHANGED`` or ``MOVED``.
        now: Instant of the change.
        old: Previous value (ISO date or list id).
        new: New value.

    Returns:
        The event with ``from`` and ``to`` details.
    """
    return TaskEvent(at=now, kind=kind, details=((DETAIL_FROM, old), (DETAIL_TO, new)))


@dataclass(frozen=True, slots=True, kw_only=True)
class Task:
    """One task (``[[tasks]]``); checked by ``TaskRules``. Every change of state adds a history event.

    Attributes:
        id: UUIDv7 identifying the task.
        created_at: Creation instant, timezone-aware UTC.
        updated_at: Last change instant, timezone-aware UTC.
        list_id: List the task belongs to.
        text: Text; the first line is the title shown in the table.
        due_date: Due date (local), ``None`` for no date.
        due_time: Due time (local, to the minute), ``None`` for the whole day; requires a date.
        state: Open, done or archived.
        completed_at: Instant of the last completion, ``None`` when the task was never completed or
            was reopened.
        history: Events of the task, oldest first.
    """

    id: TaskId
    created_at: datetime
    updated_at: datetime
    list_id: TaskListId
    text: MultilineText
    due_date: date | None
    due_time: time | None
    state: TaskStateEnum
    completed_at: datetime | None
    history: TaskHistory

    @classmethod
    def create(cls, new_id: TaskId, now: datetime, draft: TaskDraft) -> Self:
        """Create an open task with a ``CREATED`` event.

        Args:
            new_id: Id from ``IdGeneratorPort``.
            now: Creation instant (timezone-aware UTC).
            draft: Values entered by the user.

        Returns:
            The task; validate it with ``TaskRules``.
        """
        return cls(
            id=new_id,
            created_at=now,
            updated_at=now,
            list_id=draft.list_id,
            text=draft.text,
            due_date=draft.due_date,
            due_time=due_minutes(draft.due_time),
            state=TaskStateEnum.OPEN,
            completed_at=None,
            history=TaskHistory.started(TaskEvent.of(now, TaskEventKindEnum.CREATED)),
        )

    @property
    def draft(self) -> TaskDraft:
        """Editable values, as the task editor starts with them."""
        return TaskDraft(list_id=self.list_id, text=self.text, due_date=self.due_date, due_time=self.due_time)

    @property
    def due_text(self) -> str:
        """ISO text of the due date and time (``""`` for no date)."""
        return due_text(self.due_date, self.due_time)

    def with_draft(self, draft: TaskDraft, now: datetime, max_events: int) -> Self:
        """Apply edited values; one event per changed part (text, due, list).

        Args:
            draft: New values.
            now: Change instant (timezone-aware UTC).
            max_events: Most history events kept.

        Returns:
            The changed task, or this task when nothing changed.
        """
        due_time = due_minutes(draft.due_time)
        new_due = due_text(draft.due_date, due_time)
        events: list[TaskEvent] = []
        if draft.text != self.text:
            events.append(TaskEvent.of(now, TaskEventKindEnum.TEXT_EDITED))
        if new_due != self.due_text:
            events.append(_change(TaskEventKindEnum.DUE_CHANGED, now, self.due_text, new_due))
        if draft.list_id != self.list_id:
            events.append(_change(TaskEventKindEnum.MOVED, now, self.list_id, draft.list_id))
        if not events:
            return self
        history = self.history
        for event in events:
            history = history.with_event(event, max_events)
        return replace(
            self,
            list_id=draft.list_id,
            text=draft.text,
            due_date=draft.due_date,
            due_time=due_time,
            history=history,
            updated_at=now,
        )

    def moved_to(self, list_id: TaskListId, now: datetime, max_events: int) -> Self:
        """Move the task to another list (``MOVED`` event).

        Args:
            list_id: Target list.
            now: Change instant (timezone-aware UTC).
            max_events: Most history events kept.

        Returns:
            The moved task, or this task when it is already in that list.
        """
        if list_id == self.list_id:
            return self
        event = _change(TaskEventKindEnum.MOVED, now, self.list_id, list_id)
        return replace(self, list_id=list_id, history=self.history.with_event(event, max_events), updated_at=now)

    def transitioned(self, kind: TaskEventKindEnum, now: datetime, max_events: int) -> DataResult[Self]:
        """Complete, reopen, archive or unarchive the task.

        Args:
            kind: ``COMPLETED``, ``REOPENED``, ``ARCHIVED`` or ``UNARCHIVED``.
            now: Change instant (timezone-aware UTC).
            max_events: Most history events kept.

        Returns:
            The changed task, or ``TASK_STATE_TRANSITION_INVALID`` on ``state``.
        """
        target = transition_target(self.state, kind, was_completed=self.completed_at is not None)
        if kind not in TRANSITION_KINDS or target is None:
            return DataResult.fail(
                ValidationResult.failure(ErrorCodeEnum.TASK_STATE_TRANSITION_INVALID, field=STATE_FIELD)
            )
        completed_at = self.completed_at
        if kind is TaskEventKindEnum.COMPLETED:
            completed_at = now
        elif kind is TaskEventKindEnum.REOPENED:
            completed_at = None
        history = self.history.with_event(TaskEvent.of(now, kind), max_events)
        return DataResult.ok(replace(self, state=target, completed_at=completed_at, history=history, updated_at=now))

    def business_copy(self, new_id: str, now: datetime) -> Self:
        """Return an open duplicate with a new identity (``BusinessCopyable``, ADR-012).

        Args:
            new_id: Id of the duplicate.
            now: Creation instant of the duplicate.

        Returns:
            The duplicate: same list, text and due date; history restarted with ``COPIED_FROM``.
        """
        event = TaskEvent(at=now, kind=TaskEventKindEnum.COPIED_FROM, details=((DETAIL_SOURCE, self.id),))
        return replace(
            self,
            id=TaskId(new_id),
            created_at=now,
            updated_at=now,
            state=TaskStateEnum.OPEN,
            completed_at=None,
            history=TaskHistory.started(event),
        )
