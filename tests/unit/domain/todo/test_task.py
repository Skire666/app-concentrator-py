from dataclasses import replace
from datetime import UTC, date, datetime, time, timedelta

import pytest

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.multiline_text import MultilineText
from concentrator.domain.todo.task import Task, TaskId
from concentrator.domain.todo.task_draft import TaskDraft, due_text
from concentrator.domain.todo.task_event import DETAIL_FROM, DETAIL_SOURCE, DETAIL_TO, TaskEvent
from concentrator.domain.todo.task_event_kind_enum import TaskEventKindEnum
from concentrator.domain.todo.task_history import TaskHistory
from concentrator.domain.todo.task_list import TaskListId
from concentrator.domain.todo.task_state_enum import TaskStateEnum
from tests.fakes.todo_factory import HOME_LIST_ID, WORK_LIST_ID, make_task

NOW = datetime(2026, 11, 10, 9, 30, tzinfo=UTC)
MAX_EVENTS = 10


def _kinds(task: Task) -> list[TaskEventKindEnum]:
    return [event.kind for event in task.history]


def test_create_opens_the_task_with_a_created_event_and_minutes_only() -> None:
    draft = TaskDraft(
        list_id=WORK_LIST_ID,
        text=MultilineText.from_text("Report\nwith sources"),
        due_date=date(2026, 11, 12),
        due_time=time(14, 30, 45),
    )

    task = Task.create(TaskId("t"), NOW, draft)

    assert (task.state, task.completed_at, task.created_at, task.updated_at) == (TaskStateEnum.OPEN, None, NOW, NOW)
    assert task.due_time == time(14, 30)
    assert _kinds(task) == [TaskEventKindEnum.CREATED]
    assert task.draft == TaskDraft(
        list_id=WORK_LIST_ID, text=draft.text, due_date=date(2026, 11, 12), due_time=time(14, 30)
    )


@pytest.mark.parametrize(
    ("due_date", "due_time", "expected"),
    [(None, None, ""), (date(2026, 11, 10), None, "2026-11-10"), (date(2026, 11, 10), time(8, 5), "2026-11-10T08:05")],
)
def test_due_text_is_iso(due_date: date | None, due_time: time | None, expected: str) -> None:
    assert due_text(due_date, due_time) == expected


def test_with_draft_adds_one_event_per_changed_part() -> None:
    task = make_task(1)
    draft = TaskDraft(list_id=HOME_LIST_ID, text=MultilineText.from_text("Other"), due_date=date(2026, 11, 20))

    edited = task.with_draft(draft, NOW, MAX_EVENTS)

    assert _kinds(edited) == [
        TaskEventKindEnum.CREATED,
        TaskEventKindEnum.TEXT_EDITED,
        TaskEventKindEnum.DUE_CHANGED,
        TaskEventKindEnum.MOVED,
    ]
    due_event, moved_event = edited.history.events[2], edited.history.events[3]
    assert (due_event.detail(DETAIL_FROM), due_event.detail(DETAIL_TO)) == ("", "2026-11-20")
    assert (moved_event.detail(DETAIL_FROM), moved_event.detail(DETAIL_TO)) == (WORK_LIST_ID, HOME_LIST_ID)
    assert edited.updated_at == NOW
    assert edited.list_id == HOME_LIST_ID


def test_with_draft_without_change_returns_the_same_task() -> None:
    task = make_task(1)

    assert task.with_draft(task.draft, NOW, MAX_EVENTS) is task


def test_moved_to_records_the_move_and_ignores_the_same_list() -> None:
    task = make_task(1)

    moved = task.moved_to(TaskListId(HOME_LIST_ID), NOW, MAX_EVENTS)

    assert moved.list_id == HOME_LIST_ID
    assert _kinds(moved)[-1] is TaskEventKindEnum.MOVED
    assert task.moved_to(TaskListId(WORK_LIST_ID), NOW, MAX_EVENTS) is task


@pytest.mark.parametrize(
    ("state", "completed", "kind", "target"),
    [
        (TaskStateEnum.OPEN, False, TaskEventKindEnum.COMPLETED, TaskStateEnum.DONE),
        (TaskStateEnum.DONE, True, TaskEventKindEnum.REOPENED, TaskStateEnum.OPEN),
        (TaskStateEnum.OPEN, False, TaskEventKindEnum.ARCHIVED, TaskStateEnum.ARCHIVED),
        (TaskStateEnum.DONE, True, TaskEventKindEnum.ARCHIVED, TaskStateEnum.ARCHIVED),
        (TaskStateEnum.ARCHIVED, True, TaskEventKindEnum.UNARCHIVED, TaskStateEnum.DONE),
        (TaskStateEnum.ARCHIVED, False, TaskEventKindEnum.UNARCHIVED, TaskStateEnum.OPEN),
    ],
)
def test_allowed_transitions(
    state: TaskStateEnum, completed: bool, kind: TaskEventKindEnum, target: TaskStateEnum
) -> None:
    task = replace(make_task(1, state=state), completed_at=NOW if completed else None)

    result = task.transitioned(kind, NOW + timedelta(minutes=1), MAX_EVENTS)

    assert result.data is not None
    assert result.data.state is target
    assert _kinds(result.data)[-1] is kind
    assert result.data.updated_at == NOW + timedelta(minutes=1)


@pytest.mark.parametrize(
    ("state", "kind"),
    [
        (TaskStateEnum.DONE, TaskEventKindEnum.COMPLETED),
        (TaskStateEnum.OPEN, TaskEventKindEnum.REOPENED),
        (TaskStateEnum.ARCHIVED, TaskEventKindEnum.ARCHIVED),
        (TaskStateEnum.ARCHIVED, TaskEventKindEnum.COMPLETED),
        (TaskStateEnum.ARCHIVED, TaskEventKindEnum.REOPENED),
        (TaskStateEnum.OPEN, TaskEventKindEnum.UNARCHIVED),
        (TaskStateEnum.DONE, TaskEventKindEnum.UNARCHIVED),
        (TaskStateEnum.OPEN, TaskEventKindEnum.TEXT_EDITED),
    ],
)
def test_refused_transitions(state: TaskStateEnum, kind: TaskEventKindEnum) -> None:
    result = make_task(1, state=state).transitioned(kind, NOW, MAX_EVENTS)

    assert result.validation.error_codes == (ErrorCodeEnum.TASK_STATE_TRANSITION_INVALID,)


def test_complete_sets_and_reopen_clears_the_completion_instant() -> None:
    done = make_task(1).transitioned(TaskEventKindEnum.COMPLETED, NOW, MAX_EVENTS).data
    assert done is not None
    assert done.completed_at == NOW

    reopened = done.transitioned(TaskEventKindEnum.REOPENED, NOW, MAX_EVENTS).data

    assert reopened is not None
    assert reopened.completed_at is None


def test_business_copy_restarts_the_history_with_copied_from_and_reopens() -> None:
    task = make_task(1, state=TaskStateEnum.DONE, due_date=date(2026, 11, 12))

    copy = task.business_copy("copy", NOW)

    assert (copy.id, copy.created_at, copy.updated_at, copy.state, copy.completed_at) == (
        "copy",
        NOW,
        NOW,
        TaskStateEnum.OPEN,
        None,
    )
    assert (copy.text, copy.due_date, copy.list_id) == (task.text, task.due_date, task.list_id)
    assert _kinds(copy) == [TaskEventKindEnum.COPIED_FROM]
    assert copy.history.events[0].detail(DETAIL_SOURCE) == task.id


def _event(minute: int, kind: TaskEventKindEnum = TaskEventKindEnum.TEXT_EDITED) -> TaskEvent:
    return TaskEvent.of(NOW + timedelta(minutes=minute), kind)


def test_history_cap_keeps_the_created_event_and_the_newest_ones() -> None:
    history = TaskHistory.started(_event(0, TaskEventKindEnum.CREATED))
    for minute in range(1, 15):
        history = history.with_event(_event(minute), 5)

    assert len(history) == 5
    assert history.events[0].kind is TaskEventKindEnum.CREATED
    assert [event.at.minute - NOW.minute for event in history.events[1:]] == [11, 12, 13, 14]
    assert history.last == _event(14)


def test_history_cap_without_origin_keeps_the_newest_events() -> None:
    history = TaskHistory.capped([_event(minute) for minute in range(6)], 3)

    assert history.events == (_event(3), _event(4), _event(5))


def test_history_cap_of_one_keeps_the_origin_only() -> None:
    history = TaskHistory.capped([_event(0, TaskEventKindEnum.CREATED), _event(1), _event(2)], 1)

    assert [event.kind for event in history] == [TaskEventKindEnum.CREATED]


def test_empty_history_has_no_last_event_and_details_default_to_empty() -> None:
    assert TaskHistory().last is None
    assert not _event(0).detail("missing")
