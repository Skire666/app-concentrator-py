"""A task of a TODO list."""

from dataclasses import dataclass, replace
from datetime import date, datetime, time
from typing import Final, NewType, Self

from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.multiline_text import MultilineText
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.todo.recurrence import Recurrence, anchored
from concentrator.domain.todo.recurrence_calculator import NextOccurrence, RecurrenceCalculator
from concentrator.domain.todo.recurrence_end_enum import RecurrenceEndEnum
from concentrator.domain.todo.task_draft import TaskDraft, due_text
from concentrator.domain.todo.task_event import (
    DETAIL_DUE,
    DETAIL_FROM,
    DETAIL_NEXT,
    DETAIL_OCCURRENCE,
    DETAIL_SKIPPED,
    DETAIL_SOURCE,
    DETAIL_TO,
    TaskEvent,
)
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


def _same_rule(old: Recurrence | None, new: Recurrence | None) -> bool:
    """Tell whether two recurrences repeat the same way, whatever their anchor.

    Args:
        old: Stored recurrence.
        new: Recurrence entered.

    Returns:
        Whether only the anchor (or nothing) differs.
    """
    if old is None or new is None:
        return old is new
    return new.with_anchor(old.anchor_date) == old


def _series_ends(recurrence: Recurrence, occurrence: int, following: date | None) -> bool:
    """Tell whether completing an occurrence ends the series.

    Args:
        recurrence: Recurrence of the task.
        occurrence: Number of the occurrence just completed.
        following: Next due date, ``None`` when there is none.

    Returns:
        Whether the task becomes done.
    """
    if following is None:
        return True
    if recurrence.end_kind is RecurrenceEndEnum.AFTER_COUNT:
        return occurrence >= (recurrence.end_count or 0)
    if recurrence.end_kind is RecurrenceEndEnum.ON_DATE:
        return recurrence.end_date is None or following > recurrence.end_date
    return False


def _source_details(source: str) -> tuple[tuple[str, str], ...]:
    """Details naming where a completion was made.

    Args:
        source: ``SOURCE_FOCUS``, or ``""`` for zone 1.

    Returns:
        ``(("source", source),)``, or nothing for an empty source.
    """
    return ((DETAIL_SOURCE, source),) if source else ()


def _occurrence_event(
    now: datetime, occurrence: int, due: date, following: NextOccurrence | None, source: str
) -> TaskEvent:
    """Build the ``OCCURRENCE_COMPLETED`` event.

    Args:
        now: Completion instant.
        occurrence: Number of the occurrence (1 for the first).
        due: Its due date.
        following: Where the task goes, ``None`` when the series ended.
        source: Where the completion was made (``SOURCE_FOCUS``), ``""`` for zone 1.

    Returns:
        The event with ``occurrence``, ``due``, while the series goes on ``next`` and ``skipped``, then
        ``source`` when given.
    """
    details = [(DETAIL_OCCURRENCE, str(occurrence)), (DETAIL_DUE, due.isoformat())]
    if following is not None and following.due_date is not None:
        details.append((DETAIL_NEXT, following.due_date.isoformat()))
        if following.skipped:
            details.append((DETAIL_SKIPPED, str(following.skipped)))
    details.extend(_source_details(source))
    return TaskEvent(at=now, kind=TaskEventKindEnum.OCCURRENCE_COMPLETED, details=tuple(details))


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
            was reopened (an occurrence completed while the series goes on does not set it).
        history: Events of the task, oldest first.
        recurrence: Repetition, ``None`` for a one-off task.
        occurrences_done: Occurrences completed so far.
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
    recurrence: Recurrence | None = None
    occurrences_done: int = 0

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
            recurrence=anchored(draft.recurrence, draft.due_date, due_changed=True),
        )

    @property
    def draft(self) -> TaskDraft:
        """Editable values, as the task editor starts with them."""
        return TaskDraft(
            list_id=self.list_id,
            text=self.text,
            due_date=self.due_date,
            due_time=self.due_time,
            recurrence=self.recurrence,
        )

    @property
    def due_text(self) -> str:
        """ISO text of the due date and time (``""`` for no date)."""
        return due_text(self.due_date, self.due_time)

    def with_draft(self, draft: TaskDraft, now: datetime, max_events: int) -> Self:
        """Apply edited values; one event per changed part (text, due, list, recurrence).

        A due date changed by hand starts the series of a recurring task again on that date.

        Args:
            draft: New values.
            now: Change instant (timezone-aware UTC).
            max_events: Most history events kept.

        Returns:
            The changed task, or this task when nothing changed.
        """
        due_time = due_minutes(draft.due_time)
        due_changed = draft.due_date != self.due_date or self.recurrence is None
        recurrence = anchored(draft.recurrence, draft.due_date, due_changed=due_changed)
        edited = replace(draft, due_time=due_time, recurrence=recurrence)
        events = self._edit_events(edited, now)
        if not events and recurrence == self.recurrence:
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
            recurrence=recurrence,
            history=history,
            updated_at=now,
        )

    def _edit_events(self, draft: TaskDraft, now: datetime) -> list[TaskEvent]:
        """List the events of an edit.

        Args:
            draft: New values (due time to the minute, recurrence anchored).
            now: Change instant.

        Returns:
            One event per changed part, in the order text, due, list, recurrence.
        """
        events: list[TaskEvent] = []
        new_due = due_text(draft.due_date, draft.due_time)
        if draft.text != self.text:
            events.append(TaskEvent.of(now, TaskEventKindEnum.TEXT_EDITED))
        if new_due != self.due_text:
            events.append(_change(TaskEventKindEnum.DUE_CHANGED, now, self.due_text, new_due))
        if draft.list_id != self.list_id:
            events.append(_change(TaskEventKindEnum.MOVED, now, self.list_id, draft.list_id))
        if not _same_rule(self.recurrence, draft.recurrence):
            events.append(TaskEvent.of(now, TaskEventKindEnum.RECURRENCE_CHANGED))
        return events

    def with_due_date(self, due_date: date | None, now: datetime, max_events: int) -> Self:
        """Set or clear the due date (bulk action); the due time is kept with a date, cleared without one.

        Args:
            due_date: New due date, ``None`` to clear it.
            now: Change instant (timezone-aware UTC).
            max_events: Most history events kept.

        Returns:
            The changed task (``DUE_CHANGED`` event, series anchored on the new date), or this task when the
            date is the same. Validate it: a recurring task needs a date.
        """
        if due_date == self.due_date:
            return self
        due_time = self.due_time if due_date is not None else None
        return self.with_draft(replace(self.draft, due_date=due_date, due_time=due_time), now, max_events)

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

    def transitioned(
        self, kind: TaskEventKindEnum, now: datetime, max_events: int, *, source: str = ""
    ) -> DataResult[Self]:
        """Complete, reopen, archive or unarchive the task.

        Args:
            kind: ``COMPLETED``, ``REOPENED``, ``ARCHIVED`` or ``UNARCHIVED``.
            now: Change instant (timezone-aware UTC).
            max_events: Most history events kept.
            source: Where a completion was made (``SOURCE_FOCUS``), ``""`` for zone 1.

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
        event = TaskEvent(at=now, kind=kind, details=_source_details(source))
        history = self.history.with_event(event, max_events)
        return DataResult.ok(replace(self, state=target, completed_at=completed_at, history=history, updated_at=now))

    def with_event(self, event: TaskEvent, max_events: int) -> Self:
        """Record an event that changes nothing else (focus queue additions and removals).

        Args:
            event: New event; its instant becomes ``updated_at``.
            max_events: Most history events kept.

        Returns:
            The task with the event.
        """
        return replace(self, history=self.history.with_event(event, max_events), updated_at=event.at)

    def completed(self, now: datetime, today: date, max_events: int, *, source: str = "") -> DataResult[Self]:
        """Complete the task: the current occurrence of an open recurring task, or the whole task.

        Args:
            now: Change instant (timezone-aware UTC).
            today: Current local date.
            max_events: Most history events kept.
            source: Where the completion was made (``SOURCE_FOCUS``), ``""`` for zone 1.

        Returns:
            The changed task, or ``TASK_STATE_TRANSITION_INVALID`` on ``state``.
        """
        if self.recurrence is None or self.due_date is None or self.state is not TaskStateEnum.OPEN:
            return self.transitioned(TaskEventKindEnum.COMPLETED, now, max_events, source=source)
        return DataResult.ok(
            self.complete_occurrence(self.recurrence, self.due_date, now, today, max_events, source=source)
        )

    def complete_occurrence(
        self, recurrence: Recurrence, due_date: date, now: datetime, today: date, max_events: int, *, source: str = ""
    ) -> Self:
        """Complete the current occurrence of an open recurring task (phase 6 spec, owner decision).

        The count grows by one. If the series ends (count reached, next date after the end date), the task
        becomes done; otherwise it stays open and moves to the first date of the series after its due date
        that is today or later. Past dates passed over are counted in the event, not completed.

        Args:
            recurrence: Recurrence of the task.
            due_date: Due date of the task.
            now: Change instant (timezone-aware UTC).
            today: Current local date.
            max_events: Most history events kept.
            source: Where the completion was made (``SOURCE_FOCUS``), ``""`` for zone 1.

        Returns:
            The changed task.
        """
        occurrence = self.occurrences_done + 1
        following = RecurrenceCalculator.next_from(recurrence, due_date, today)
        if _series_ends(recurrence, occurrence, following.due_date):
            history = self.history.with_event(_occurrence_event(now, occurrence, due_date, None, source), max_events)
            completed = TaskEvent(at=now, kind=TaskEventKindEnum.COMPLETED, details=_source_details(source))
            history = history.with_event(completed, max_events)
            return replace(
                self,
                state=TaskStateEnum.DONE,
                completed_at=now,
                occurrences_done=occurrence,
                history=history,
                updated_at=now,
            )
        event = _occurrence_event(now, occurrence, due_date, following, source)
        return replace(
            self,
            due_date=following.due_date,
            occurrences_done=occurrence,
            history=self.history.with_event(event, max_events),
            updated_at=now,
        )

    def business_copy(self, new_id: str, now: datetime) -> Self:
        """Return an open duplicate with a new identity (``BusinessCopyable``, ADR-012).

        Args:
            new_id: Id of the duplicate.
            now: Creation instant of the duplicate.

        Returns:
            The duplicate: same list, text, due date and recurrence, no occurrence completed; history
            restarted with ``COPIED_FROM``.
        """
        event = TaskEvent(at=now, kind=TaskEventKindEnum.COPIED_FROM, details=((DETAIL_SOURCE, self.id),))
        return replace(
            self,
            id=TaskId(new_id),
            created_at=now,
            updated_at=now,
            state=TaskStateEnum.OPEN,
            completed_at=None,
            occurrences_done=0,
            history=TaskHistory.started(event),
        )
