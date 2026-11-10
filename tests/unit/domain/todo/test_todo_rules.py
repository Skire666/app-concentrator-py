from dataclasses import replace
from datetime import date, datetime, time, timedelta, timezone

import pytest

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.multiline_text import MultilineText
from concentrator.domain.todo.priority_enum import PriorityEnum
from concentrator.domain.todo.task_draft import TaskDraft
from concentrator.domain.todo.task_event import TaskEvent
from concentrator.domain.todo.task_event_kind_enum import TaskEventKindEnum
from concentrator.domain.todo.task_history import TaskHistory
from concentrator.domain.todo.task_list_rules import TaskListRules
from concentrator.domain.todo.task_rules import TaskRules
from concentrator.domain.todo.task_state_enum import TaskStateEnum
from tests.fakes.todo_factory import TODO_LIMITS, WORK_LIST_ID, make_list, make_lists, make_task

PARIS = timezone(timedelta(hours=1))


def _codes_text(text: str) -> tuple[ErrorCodeEnum, ...]:
    return TaskRules.validate_text(MultilineText.from_text(text), TODO_LIMITS).error_codes


@pytest.mark.parametrize(
    ("text", "codes"),
    [
        ("Report", ()),
        ("", (ErrorCodeEnum.TASK_TEXT_EMPTY,)),
        ("   \n  ", (ErrorCodeEnum.TASK_TEXT_EMPTY,)),
        ("x" * 5000, ()),
        ("x" * 5001, (ErrorCodeEnum.TASK_TEXT_TOO_LONG,)),
        ("x" * 2500 + "\n" + "y" * 2500, (ErrorCodeEnum.TASK_TEXT_TOO_LONG,)),
    ],
)
def test_task_text_limits(text: str, codes: tuple[ErrorCodeEnum, ...]) -> None:
    assert _codes_text(text) == codes


def test_task_text_with_blank_first_line_is_empty() -> None:
    text = MultilineText(("  ", "second"))

    assert TaskRules.validate_text(text, TODO_LIMITS).error_codes == (ErrorCodeEnum.TASK_TEXT_EMPTY,)


def test_due_time_requires_a_date() -> None:
    assert TaskRules.validate_due(None, time(9, 0)).issues_for("due_time")[0].code is (
        ErrorCodeEnum.TASK_DUE_TIME_WITHOUT_DATE
    )
    assert TaskRules.validate_due(date(2026, 11, 10), time(9, 0)).is_success
    assert TaskRules.validate_due(None, None).is_success


def test_validate_draft_merges_text_and_due() -> None:
    draft = TaskDraft(list_id=WORK_LIST_ID, text=MultilineText(), due_time=time(9, 0))

    assert set(TaskRules.validate_draft(draft, TODO_LIMITS).error_codes) == {
        ErrorCodeEnum.TASK_TEXT_EMPTY,
        ErrorCodeEnum.TASK_DUE_TIME_WITHOUT_DATE,
    }


@pytest.mark.parametrize(
    ("state", "code"),
    [(TaskStateEnum.UNSET, ErrorCodeEnum.ENUM_VALUE_UNSET), (TaskStateEnum.UNKNOWN, ErrorCodeEnum.ENUM_VALUE_UNKNOWN)],
)
def test_task_state_must_be_real(state: TaskStateEnum, code: ErrorCodeEnum) -> None:
    assert TaskRules.validate(replace(make_task(1), state=state), TODO_LIMITS).error_codes == (code,)


def test_task_timestamps_must_be_utc() -> None:
    local = datetime(2026, 11, 10, 9, 0, tzinfo=PARIS)
    task = replace(
        make_task(1), completed_at=local, history=TaskHistory((TaskEvent.of(local, TaskEventKindEnum.CREATED),))
    )

    result = TaskRules.validate(task, TODO_LIMITS)

    assert [issue.field for issue in result.issues] == ["completed_at", "history.0.at"]
    assert TaskRules.validate(make_task(1), TODO_LIMITS).is_success


def test_tasks_of_a_file_must_reference_an_existing_list() -> None:
    lists = make_lists()
    tasks = [make_task(1), make_task(2, list_id="missing")]

    result = TaskRules.validate_all(tasks, lists, TODO_LIMITS)

    assert [(issue.code, issue.field) for issue in result.issues] == [(ErrorCodeEnum.TASK_LIST_NOT_FOUND, "1.list_id")]


@pytest.mark.parametrize(
    ("name", "codes"),
    [
        ("Work", ()),
        ("   ", (ErrorCodeEnum.LIST_NAME_EMPTY,)),
        ("x" * 80, ()),
        ("x" * 81, (ErrorCodeEnum.LIST_NAME_TOO_LONG,)),
    ],
)
def test_list_name_limits(name: str, codes: tuple[ErrorCodeEnum, ...]) -> None:
    assert TaskListRules.validate_name(name, TODO_LIMITS).error_codes == codes


def test_list_description_limit() -> None:
    assert TaskListRules.validate_description(MultilineText.from_text("x" * 2000), TODO_LIMITS).is_success
    assert TaskListRules.validate_description(MultilineText.from_text("x" * 2001), TODO_LIMITS).error_codes == (
        ErrorCodeEnum.LIST_DESCRIPTION_TOO_LONG,
    )


@pytest.mark.parametrize(
    ("priority", "codes"),
    [
        (PriorityEnum.LOW, ()),
        (PriorityEnum.UNSET, (ErrorCodeEnum.LIST_PRIORITY_UNSET,)),
        (PriorityEnum.UNKNOWN, (ErrorCodeEnum.ENUM_VALUE_UNKNOWN,)),
    ],
)
def test_list_priority_must_be_chosen(priority: PriorityEnum, codes: tuple[ErrorCodeEnum, ...]) -> None:
    assert TaskListRules.validate_priority(priority).error_codes == codes


def test_list_position_must_not_be_negative() -> None:
    result = TaskListRules.validate(make_list("Work", position=-1), TODO_LIMITS)

    assert result.error_codes == (ErrorCodeEnum.VALUE_OUT_OF_RANGE,)
    assert TaskListRules.validate(make_list("Work"), TODO_LIMITS).is_success


def test_list_names_are_unique_without_regard_to_case() -> None:
    lists = make_lists()

    assert TaskListRules.validate_unique_name(lists, "work").error_codes == (ErrorCodeEnum.LIST_NAME_DUPLICATE,)
    assert TaskListRules.validate_unique_name(lists, "work", except_id="list-work").is_success
    assert TaskListRules.validate_unique_name(lists, "Garden").is_success


def test_lists_of_a_file_must_have_unique_names() -> None:
    result = TaskListRules.validate_all([make_list("Work"), make_list("work", list_id="other")], TODO_LIMITS)

    assert [(issue.code, issue.field) for issue in result.issues] == [(ErrorCodeEnum.LIST_NAME_DUPLICATE, "1.name")]


def test_list_deletion_rules() -> None:
    lists = make_lists()
    single = make_lists(make_list("Inbox"))

    assert TaskListRules.validate_deletion(lists, "list-home", 0, delete_tasks=False).is_success
    assert TaskListRules.validate_deletion(lists, "list-home", 3, delete_tasks=True).is_success
    assert TaskListRules.validate_deletion(lists, "list-home", 3, delete_tasks=False).error_codes == (
        ErrorCodeEnum.LIST_NOT_EMPTY,
    )
    assert TaskListRules.validate_deletion(single, "list-inbox", 0, delete_tasks=True).error_codes == (
        ErrorCodeEnum.LIST_LAST_CANNOT_DELETE,
    )
    assert TaskListRules.validate_deletion(lists, "missing", 0, delete_tasks=True).error_codes == (
        ErrorCodeEnum.ENTITY_NOT_FOUND,
    )


def test_list_business_copy_and_with_values() -> None:
    now = datetime(2026, 11, 10, 9, 0, tzinfo=PARIS).astimezone(make_list("A").created_at.tzinfo)
    work = make_list("Work")

    copy = work.business_copy("copy", now)
    edited = work.with_values("  Big   work ", MultilineText.from_text("notes"), PriorityEnum.URGENT, now)

    assert (copy.id, copy.created_at, copy.name) == ("copy", now, "Work")
    assert (edited.name, edited.priority, edited.updated_at) == ("Big work", PriorityEnum.URGENT, now)
