from dataclasses import replace
from datetime import UTC, date, datetime, time
from typing import Final

import pytest

from concentrator.application.storage.user_data import StoredUserData
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.multiline_text import MultilineText
from concentrator.domain.todo.priority_enum import PriorityEnum
from concentrator.domain.todo.task import Task
from concentrator.domain.todo.task_event import DETAIL_FROM, DETAIL_TO, TaskEvent
from concentrator.domain.todo.task_event_kind_enum import TaskEventKindEnum
from concentrator.domain.todo.task_history import TaskHistory
from concentrator.domain.todo.task_lists_collection import TaskListsCollection
from concentrator.domain.todo.task_state_enum import TaskStateEnum
from concentrator.domain.todo.tasks_collection import TasksCollection
from concentrator.infrastructure.persistence.user_data_codec import UserDataCodec
from tests.fakes.todo_factory import SPEC_LIST_ID, SPEC_TASK_ID, make_list, make_spec_list
from tests.fakes.user_data_factory import SPEC_EXAMPLE_TEXT, USER_DATA_LIMITS, make_stored

CODEC: Final = UserDataCodec("0.1.0", USER_DATA_LIMITS)
TASK_CREATED: Final = datetime(2026, 11, 6, 16, 45, tzinfo=UTC)
TASK_DONE: Final = datetime(2026, 11, 7, 9, 0, tzinfo=UTC)

SPEC_TASK_TEXT: Final = """
[[tasks]]
id = '019a5c22-bbbb-7ccc-8ddd-4f5a6b7c8d9e'
created_at = '2026-11-06T16:45:00Z'
updated_at = '2026-11-06T16:45:00Z'
list_id = '019a5c21-aaaa-7bbb-8ccc-3e4f5a6b7c8d'
text = [
  'Prepare the quarterly report',
  '''Sources in D:/Reports/2026/Q4 (the client's folder)''',
]
due_date = '2026-11-10'
state = 1
history = [
  { at = '2026-11-06T16:45:00Z', kind = 1, details = {} },
]
"""

DONE_TASK_TEXT: Final = """
[[tasks]]
id = 'task-done'
created_at = '2026-11-06T16:45:00Z'
updated_at = '2026-11-07T09:00:00Z'
list_id = '019a5c21-aaaa-7bbb-8ccc-3e4f5a6b7c8d'
text = [
  'Call back',
]
due_date = '2026-11-08'
due_time = '14:30'
state = 2
completed_at = '2026-11-07T09:00:00Z'
history = [
  { at = '2026-11-06T16:45:00Z', kind = 1, details = {} },
  { at = '2026-11-07T09:00:00Z', kind = 3, details = { from = '', to = '2026-11-08T14:30' } },
  { at = '2026-11-07T09:00:00Z', kind = 4, details = {} },
]
"""


def _spec_task() -> Task:
    return Task(
        id=SPEC_TASK_ID,
        created_at=TASK_CREATED,
        updated_at=TASK_CREATED,
        list_id=SPEC_LIST_ID,
        text=MultilineText(("Prepare the quarterly report", "Sources in D:/Reports/2026/Q4 (the client's folder)")),
        due_date=date(2026, 11, 10),
        due_time=None,
        state=TaskStateEnum.OPEN,
        completed_at=None,
        history=TaskHistory.started(TaskEvent.of(TASK_CREATED, TaskEventKindEnum.CREATED)),
    )


def _done_task() -> Task:
    due = TaskEvent(
        at=TASK_DONE, kind=TaskEventKindEnum.DUE_CHANGED, details=((DETAIL_FROM, ""), (DETAIL_TO, "2026-11-08T14:30"))
    )
    events = (
        TaskEvent.of(TASK_CREATED, TaskEventKindEnum.CREATED),
        due,
        TaskEvent.of(TASK_DONE, TaskEventKindEnum.COMPLETED),
    )
    return replace(
        _spec_task(),
        id="task-done",
        updated_at=TASK_DONE,
        text=MultilineText(("Call back",)),
        due_date=date(2026, 11, 8),
        due_time=time(14, 30),
        state=TaskStateEnum.DONE,
        completed_at=TASK_DONE,
        history=TaskHistory(events),
    )


def _stored_with_tasks() -> StoredUserData:
    stored = make_stored()
    data = stored.data.with_tasks(TasksCollection((_spec_task(), _done_task())))
    return replace(stored, data=data)


def _file_text() -> str:
    return SPEC_EXAMPLE_TEXT.replace("tasks = []\n", "") + SPEC_TASK_TEXT + DONE_TASK_TEXT


def test_lists_and_tasks_are_written_as_in_the_spec_example() -> None:
    assert CODEC.encode(_stored_with_tasks()) == _file_text()


def test_lists_and_tasks_round_trip() -> None:
    decoded = CODEC.decode(_file_text())

    assert decoded.data == _stored_with_tasks()


def test_lists_are_written_in_display_order() -> None:
    stored = make_stored()
    lists = TaskListsCollection((make_list("Later", priority=PriorityEnum.LOW, position=0), make_spec_list()))
    text = CODEC.encode(replace(stored, data=stored.data.with_task_lists(lists)))

    assert text.index("name = 'Work'") < text.index("name = 'Later'")


def test_a_task_of_a_missing_list_makes_the_file_invalid() -> None:
    text = _file_text().replace(
        "list_id = '019a5c21-aaaa-7bbb-8ccc-3e4f5a6b7c8d'\ntext = [\n  'Call", "list_id = 'missing'\ntext = [\n  'Call"
    )

    result = CODEC.decode(text)

    assert [(issue.code, issue.field) for issue in result.validation.issues] == [
        (ErrorCodeEnum.TASK_LIST_NOT_FOUND, "tasks.1.list_id")
    ]


def test_native_toml_dates_and_times_are_read() -> None:
    text = _file_text().replace(
        "due_date = '2026-11-08'\ndue_time = '14:30'", "due_date = 2026-11-08\ndue_time = 14:30:59"
    )

    decoded = CODEC.decode(text)

    assert decoded.data == _stored_with_tasks()


def test_a_history_longer_than_the_cap_keeps_the_creation_and_the_newest_events() -> None:
    events = "".join(
        f"  {{ at = '2026-11-07T09:00:{second:02d}Z', kind = 2, details = {{}} }},\n" for second in range(15)
    )
    text = _file_text().replace(
        "history = [\n  { at = '2026-11-06T16:45:00Z', kind = 1, details = {} },\n]\n",
        "history = [\n  { at = '2026-11-06T16:45:00Z', kind = 1, details = {} },\n" + events + "]\n",
        1,
    )

    decoded = CODEC.decode(text)

    assert decoded.data is not None
    tasks = decoded.data.data.tasks
    assert tasks is not None
    history = tasks.items[0].history
    assert len(history) == USER_DATA_LIMITS.todo.max_history_events
    assert history.events[0].kind is TaskEventKindEnum.CREATED
    assert history.events[-1].at == datetime(2026, 11, 7, 9, 0, 14, tzinfo=UTC)


@pytest.mark.parametrize(
    ("old", "new", "code", "field"),
    [
        ("priority = 3", "priority = 9", ErrorCodeEnum.ENUM_VALUE_UNKNOWN, "task_lists.0.priority"),
        ("priority = 3", "priority = 0", ErrorCodeEnum.LIST_PRIORITY_UNSET, "task_lists.0.priority"),
        ("name = 'Work'", "name = ' '", ErrorCodeEnum.LIST_NAME_EMPTY, "task_lists.0.name"),
        ("state = 1", "state = 0", ErrorCodeEnum.ENUM_VALUE_UNSET, "tasks.0.state"),
        (
            "due_date = '2026-11-10'\n",
            "due_time = '08:00'\n",
            ErrorCodeEnum.TASK_DUE_TIME_WITHOUT_DATE,
            "tasks.0.due_time",
        ),
        (
            "due_date = '2026-11-10'",
            "due_date = '2026-13-10'",
            ErrorCodeEnum.STORAGE_FIELD_INVALID_TYPE,
            "tasks.0.due_date",
        ),
    ],
)
def test_invalid_todo_values_are_reported_with_their_field(old: str, new: str, code: ErrorCodeEnum, field: str) -> None:
    result = CODEC.decode(_file_text().replace(old, new, 1))

    assert (code, field) in [(issue.code, issue.field) for issue in result.validation.issues]


def test_duplicate_list_names_are_reported() -> None:
    second = SPEC_EXAMPLE_TEXT[SPEC_EXAMPLE_TEXT.index("\n[[task_lists]]") :].replace("name = 'Work'", "name = 'WORK'")

    result = CODEC.decode(_file_text() + second)

    codes = [(issue.code, issue.field) for issue in result.validation.issues]
    assert (ErrorCodeEnum.LIST_NAME_DUPLICATE, "task_lists.1.name") in codes


def test_a_task_without_text_makes_the_file_invalid() -> None:
    text = _file_text().replace(
        "text = [\n  'Prepare the quarterly report',\n  '''Sources in D:/Reports/2026/Q4 (the client's folder)''',\n]",
        "text = [\n  '   ',\n]",
    )

    result = CODEC.decode(text)

    assert [(issue.code, issue.field) for issue in result.validation.issues] == [
        (ErrorCodeEnum.TASK_TEXT_EMPTY, "tasks.0.text")
    ]


def test_unknown_event_kinds_are_kept_for_newer_versions() -> None:
    text = _file_text().replace("kind = 4, details = {}", "kind = 99, details = {}")

    decoded = CODEC.decode(text)

    assert decoded.data is not None
    tasks = decoded.data.data.tasks
    assert tasks is not None
    assert tasks.items[1].history.events[-1].kind is TaskEventKindEnum.UNKNOWN
