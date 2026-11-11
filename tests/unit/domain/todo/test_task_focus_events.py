from dataclasses import replace
from datetime import UTC, date, datetime

from concentrator.domain.todo.recurrence import Recurrence
from concentrator.domain.todo.recurrence_end_enum import RecurrenceEndEnum
from concentrator.domain.todo.recurrence_frequency_enum import RecurrenceFrequencyEnum
from concentrator.domain.todo.task import Task, TaskId
from concentrator.domain.todo.task_draft import TaskDraft
from concentrator.domain.todo.task_event import DETAIL_SOURCE, SOURCE_FOCUS, TaskEvent
from concentrator.domain.todo.task_event_kind_enum import TaskEventKindEnum
from tests.fakes.todo_factory import WORK_LIST_ID, make_task

NOW = datetime(2026, 11, 6, 18, 0, tzinfo=UTC)
DUE = date(2026, 11, 6)
MAX_EVENTS = 10


def _recurring(end_count: int) -> Task:
    recurrence = Recurrence.create(
        frequency=RecurrenceFrequencyEnum.DAILY,
        interval=1,
        weekdays=(),
        anchor_date=DUE,
        end_kind=RecurrenceEndEnum.AFTER_COUNT,
        end_date=None,
        end_count=end_count,
    )
    draft = TaskDraft(list_id=WORK_LIST_ID, text=make_task(1).text, due_date=DUE, due_time=None)
    return Task.create(TaskId("t"), NOW, replace(draft, recurrence=recurrence))


def _last(task: Task) -> TaskEvent:
    last = task.history.last
    assert last is not None
    return last


def test_completed_from_focus_adds_the_source_to_the_event() -> None:
    result = make_task(1).completed(NOW, DUE, MAX_EVENTS, source=SOURCE_FOCUS)

    assert result.data is not None
    event = _last(result.data)
    assert event.kind is TaskEventKindEnum.COMPLETED
    assert event.detail(DETAIL_SOURCE) == SOURCE_FOCUS


def test_completed_from_zone_one_has_no_source() -> None:
    result = make_task(1).completed(NOW, DUE, MAX_EVENTS)

    assert result.data is not None
    assert _last(result.data).details == ()


def test_occurrence_completed_from_focus_adds_the_source() -> None:
    result = _recurring(5).completed(NOW, DUE, MAX_EVENTS, source=SOURCE_FOCUS)

    assert result.data is not None
    event = _last(result.data)
    assert event.kind is TaskEventKindEnum.OCCURRENCE_COMPLETED
    assert event.detail(DETAIL_SOURCE) == SOURCE_FOCUS


def test_last_occurrence_from_focus_marks_both_events() -> None:
    result = _recurring(1).completed(NOW, DUE, MAX_EVENTS, source=SOURCE_FOCUS)

    assert result.data is not None
    occurrence, completed = result.data.history.events[-2:]
    assert occurrence.kind is TaskEventKindEnum.OCCURRENCE_COMPLETED
    assert completed.kind is TaskEventKindEnum.COMPLETED
    assert occurrence.detail(DETAIL_SOURCE) == SOURCE_FOCUS
    assert completed.detail(DETAIL_SOURCE) == SOURCE_FOCUS


def test_with_event_appends_and_sets_updated_at() -> None:
    later = datetime(2026, 11, 7, 8, 0, tzinfo=UTC)
    event = TaskEvent.of(later, TaskEventKindEnum.ADDED_TO_FOCUS)

    task = make_task(1).with_event(event, MAX_EVENTS)

    assert _last(task) == event
    assert task.updated_at == later
