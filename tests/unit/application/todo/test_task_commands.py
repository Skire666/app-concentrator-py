from datetime import date, time

import pytest

from concentrator.application.todo.todo_events import (
    TaskChangedEvent,
    TaskCreatedEvent,
    TaskDeletedEvent,
    TaskStateChangedEvent,
)
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.multiline_text import MultilineText
from concentrator.domain.todo.task_draft import TaskDraft
from concentrator.domain.todo.task_event import DETAIL_SOURCE
from concentrator.domain.todo.task_event_kind_enum import TaskEventKindEnum
from concentrator.domain.todo.task_list import TaskListId
from concentrator.domain.todo.task_state_enum import TaskStateEnum
from tests.fakes.fake_clock import DEFAULT_START
from tests.fakes.todo_factory import HOME_LIST_ID, WORK_LIST_ID, make_task
from tests.fakes.todo_stack import WRITE_FAILED, TodoStack


def _draft(text: str = "Report", list_id: str = WORK_LIST_ID) -> TaskDraft:
    return TaskDraft(list_id=TaskListId(list_id), text=MultilineText.from_text(text), due_date=date(2026, 11, 12))


def test_quick_add_creates_an_open_task_and_publishes_once() -> None:
    stack = TodoStack()

    created = stack.task_commands.quick_add(WORK_LIST_ID, "  Call the bank  ")

    assert created.data is not None
    task = stack.task(created.data.id)
    assert (task.id, task.text.lines, task.state, task.created_at) == (
        "new-0001",
        ("Call the bank",),
        TaskStateEnum.OPEN,
        DEFAULT_START,
    )
    assert stack.events == [TaskCreatedEvent(task_id="new-0001")]


@pytest.mark.parametrize(
    ("list_id", "text", "code"),
    [
        (WORK_LIST_ID, "   ", ErrorCodeEnum.TASK_TEXT_EMPTY),
        ("missing", "Call", ErrorCodeEnum.TASK_LIST_NOT_FOUND),
        (WORK_LIST_ID, "x" * 5001, ErrorCodeEnum.TASK_TEXT_TOO_LONG),
    ],
)
def test_quick_add_refuses_invalid_values(list_id: str, text: str, code: ErrorCodeEnum) -> None:
    stack = TodoStack()

    result = stack.task_commands.quick_add(list_id, text)

    assert result.validation.error_codes == (code,)
    assert len(stack.tasks()) == 0
    assert stack.events == []


def test_create_stores_the_due_date_and_time() -> None:
    stack = TodoStack()
    draft = TaskDraft(
        list_id=WORK_LIST_ID, text=MultilineText.from_text("a\nb"), due_date=date(2026, 11, 12), due_time=time(9, 30)
    )

    created = stack.task_commands.create(draft)

    assert created.data is not None
    assert (created.data.due_date, created.data.due_time, created.data.text.line_count) == (
        date(2026, 11, 12),
        time(9, 30),
        2,
    )


def test_create_reports_a_write_failure_without_event() -> None:
    stack = TodoStack()
    stack.task_writer.fail = True

    assert stack.task_commands.create(_draft()).validation == WRITE_FAILED
    assert stack.events == []


def test_update_records_the_changes_and_publishes_task_changed() -> None:
    stack = TodoStack(tasks=[make_task(1)])
    stack.clock.advance(seconds=60)

    updated = stack.task_commands.update("task-001", _draft("Report v2", HOME_LIST_ID))

    assert updated.data is not None
    assert [event.kind for event in updated.data.history][1:] == [
        TaskEventKindEnum.TEXT_EDITED,
        TaskEventKindEnum.DUE_CHANGED,
        TaskEventKindEnum.MOVED,
    ]
    assert stack.task("task-001").list_id == HOME_LIST_ID
    assert stack.events == [TaskChangedEvent(task_ids=("task-001",))]


def test_update_without_change_writes_nothing() -> None:
    stack = TodoStack(tasks=[make_task(1)])

    result = stack.task_commands.update("task-001", make_task(1).draft)

    assert result.data == make_task(1)
    assert stack.events == []


@pytest.mark.parametrize(
    ("task_id", "draft", "code"),
    [
        ("missing", _draft(), ErrorCodeEnum.ENTITY_NOT_FOUND),
        ("task-001", _draft(""), ErrorCodeEnum.TASK_TEXT_EMPTY),
        ("task-001", _draft("x", "missing"), ErrorCodeEnum.TASK_LIST_NOT_FOUND),
    ],
)
def test_update_refuses_invalid_values(task_id: str, draft: TaskDraft, code: ErrorCodeEnum) -> None:
    stack = TodoStack(tasks=[make_task(1)])

    assert stack.task_commands.update(task_id, draft).validation.error_codes == (code,)
    assert stack.task("task-001") == make_task(1)


def test_update_reports_a_write_failure_without_event() -> None:
    stack = TodoStack(tasks=[make_task(1)])
    stack.task_writer.fail = True

    assert stack.task_commands.update("task-001", _draft("Other")).validation == WRITE_FAILED
    assert stack.events == []


def test_complete_changes_every_task_and_publishes_one_event_per_task() -> None:
    stack = TodoStack(tasks=[make_task(1), make_task(2), make_task(3)])

    result = stack.task_commands.complete(["task-001", "task-003"])

    assert result.is_success
    assert [task.state for task in stack.tasks()] == [TaskStateEnum.DONE, TaskStateEnum.OPEN, TaskStateEnum.DONE]
    assert stack.events == [
        TaskStateChangedEvent(task_id="task-001", old_state=TaskStateEnum.OPEN, new_state=TaskStateEnum.DONE),
        TaskStateChangedEvent(task_id="task-003", old_state=TaskStateEnum.OPEN, new_state=TaskStateEnum.DONE),
    ]


def test_bulk_change_with_one_unknown_id_changes_nothing() -> None:
    stack = TodoStack(tasks=[make_task(1), make_task(2)])

    result = stack.task_commands.complete(["task-001", "missing"])

    assert result.error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)
    assert {task.state for task in stack.tasks()} == {TaskStateEnum.OPEN}
    assert stack.events == []


def test_bulk_change_with_one_refused_transition_changes_nothing() -> None:
    stack = TodoStack(tasks=[make_task(1), make_task(2, state=TaskStateEnum.DONE)])

    result = stack.task_commands.complete(["task-001", "task-002"])

    assert result.error_codes == (ErrorCodeEnum.TASK_STATE_TRANSITION_INVALID,)
    assert stack.task("task-001").state is TaskStateEnum.OPEN
    assert stack.events == []


def test_bulk_change_reports_a_write_failure_without_event() -> None:
    stack = TodoStack(tasks=[make_task(1)])
    stack.task_writer.fail = True

    assert stack.task_commands.archive(["task-001"]) == WRITE_FAILED
    assert stack.events == []


def test_reopen_archive_and_unarchive_follow_the_transition_table() -> None:
    stack = TodoStack(tasks=[make_task(1, state=TaskStateEnum.DONE), make_task(2)])
    commands = stack.task_commands

    assert commands.reopen(["task-001"]).is_success
    assert commands.archive(["task-001", "task-002"]).is_success
    assert commands.unarchive(["task-002"]).is_success

    assert [task.state for task in stack.tasks()] == [TaskStateEnum.ARCHIVED, TaskStateEnum.OPEN]


def test_no_selected_task_is_skipped() -> None:
    commands = TodoStack().task_commands

    assert commands.complete([]).is_skipped
    assert commands.delete([]).is_skipped
    assert commands.move_to_list([], HOME_LIST_ID).is_skipped


def test_delete_removes_the_tasks_in_one_write() -> None:
    stack = TodoStack(tasks=[make_task(1), make_task(2), make_task(3)])

    assert stack.task_commands.delete(["task-001", "task-002"]).is_success
    assert [task.id for task in stack.tasks()] == ["task-003"]
    assert stack.events == [TaskDeletedEvent(task_ids=("task-001", "task-002"))]
    assert stack.task_commands.delete(["missing"]).error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)


def test_move_to_list_moves_only_the_tasks_of_other_lists() -> None:
    stack = TodoStack(tasks=[make_task(1), make_task(2, list_id=HOME_LIST_ID)])

    result = stack.task_commands.move_to_list(["task-001", "task-002"], HOME_LIST_ID)

    assert result.is_success
    assert {task.list_id for task in stack.tasks()} == {HOME_LIST_ID}
    assert stack.events == [TaskChangedEvent(task_ids=("task-001",))]
    assert stack.task_commands.move_to_list(["task-001"], HOME_LIST_ID).is_skipped


def test_move_to_list_refuses_a_missing_list_or_task() -> None:
    stack = TodoStack(tasks=[make_task(1)])

    assert stack.task_commands.move_to_list(["task-001"], "missing").error_codes == (ErrorCodeEnum.TASK_LIST_NOT_FOUND,)
    assert stack.task_commands.move_to_list(["missing"], HOME_LIST_ID).error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)


def test_move_to_list_reports_a_write_failure() -> None:
    stack = TodoStack(tasks=[make_task(1)])
    stack.task_writer.fail = True

    assert stack.task_commands.move_to_list(["task-001"], HOME_LIST_ID) == WRITE_FAILED


def test_duplicate_creates_a_new_open_task_with_copied_from() -> None:
    stack = TodoStack(tasks=[make_task(1, state=TaskStateEnum.DONE)])
    stack.clock.advance(seconds=30)

    copy = stack.task_commands.duplicate("task-001")

    assert copy.data is not None
    assert (copy.data.id, copy.data.state, copy.data.created_at) == (
        "new-0001",
        TaskStateEnum.OPEN,
        stack.clock.now_utc(),
    )
    assert [event.kind for event in copy.data.history] == [TaskEventKindEnum.COPIED_FROM]
    assert copy.data.history.events[0].detail(DETAIL_SOURCE) == "task-001"
    assert stack.events == [TaskCreatedEvent(task_id="new-0001")]
    assert stack.task_commands.duplicate("missing").validation.error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)
