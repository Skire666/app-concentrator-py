from dataclasses import replace
from datetime import date
from typing import Final

import pytest

from concentrator.application.storage.user_data import StoredUserData
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.multiline_text import MultilineText
from concentrator.domain.todo.recurrence import Recurrence
from concentrator.domain.todo.recurrence_end_enum import RecurrenceEndEnum
from concentrator.domain.todo.recurrence_frequency_enum import RecurrenceFrequencyEnum
from concentrator.domain.todo.task import Task
from concentrator.domain.todo.tasks_collection import TasksCollection
from concentrator.domain.todo.weekday_enum import WeekdayEnum
from concentrator.infrastructure.persistence.user_data_codec import UserDataCodec
from tests.fakes.todo_factory import SPEC_LIST_ID, make_task
from tests.fakes.user_data_factory import USER_DATA_LIMITS, make_stored

CODEC: Final = UserDataCodec("0.1.0", USER_DATA_LIMITS)
SPEC_RECURRENCE_LINE: Final = (
    "recurrence = { frequency = 2, interval = 1, weekdays = [5], anchor_date = '2026-11-06', end_kind = 3, "
    "end_count = 10 }\noccurrences_done = 1\n"
)


def _weekly_task() -> Task:
    recurrence = Recurrence.create(
        frequency=RecurrenceFrequencyEnum.WEEKLY,
        interval=1,
        weekdays=(WeekdayEnum.FRIDAY,),
        anchor_date=date(2026, 11, 6),
        end_kind=RecurrenceEndEnum.AFTER_COUNT,
        end_count=10,
    )
    text = MultilineText(
        ("Weekly backup", "Copy D:/Projects/Concentrator to //nas/backup/projects", "https://example.org/backup-guide")
    )
    return replace(
        make_task(1, list_id=SPEC_LIST_ID, due_date=date(2026, 11, 13)),
        text=text,
        recurrence=recurrence,
        occurrences_done=1,
    )


def _stored(*tasks: Task) -> StoredUserData:
    stored = make_stored()
    return replace(stored, data=stored.data.with_tasks(TasksCollection(tasks)))


def test_recurrence_is_written_inline_as_in_the_spec() -> None:
    text = CODEC.encode(_stored(_weekly_task()))

    assert "due_date = '2026-11-13'\n" + SPEC_RECURRENCE_LINE + "state = 1\n" in text


def test_recurrence_round_trips() -> None:
    stored = _stored(_weekly_task(), make_task(2, list_id=SPEC_LIST_ID))

    assert CODEC.decode(CODEC.encode(stored)).data == stored


def test_a_one_off_task_writes_neither_recurrence_nor_count() -> None:
    text = CODEC.encode(_stored(make_task(2, list_id=SPEC_LIST_ID)))

    assert "recurrence" not in text
    assert "occurrences_done" not in text


def test_an_end_date_is_written_and_read() -> None:
    task = _weekly_task()
    assert task.recurrence is not None
    recurrence = replace(task.recurrence, end_kind=RecurrenceEndEnum.ON_DATE, end_date=date(2027, 1, 1), end_count=None)
    stored = _stored(replace(task, recurrence=recurrence))

    text = CODEC.encode(stored)

    assert "end_kind = 2, end_date = '2027-01-01' }" in text
    assert CODEC.decode(text).data == stored


@pytest.mark.parametrize(
    ("old", "new", "code", "field"),
    [
        ("frequency = 2", "frequency = 9", ErrorCodeEnum.ENUM_VALUE_UNKNOWN, "tasks.0.recurrence.frequency"),
        ("weekdays = [5]", "weekdays = []", ErrorCodeEnum.RECURRENCE_WEEKDAYS_EMPTY, "tasks.0.recurrence.weekdays"),
        ("weekdays = [5]", "weekdays = [8]", ErrorCodeEnum.ENUM_VALUE_UNKNOWN, "tasks.0.recurrence.weekdays"),
        (
            "end_count = 10",
            "end_count = 0",
            ErrorCodeEnum.RECURRENCE_COUNT_OUT_OF_RANGE,
            "tasks.0.recurrence.end_count",
        ),
        ("due_date = '2026-11-13'\n", "", ErrorCodeEnum.RECURRENCE_REQUIRES_DUE_DATE, "tasks.0.recurrence"),
        (
            "occurrences_done = 1",
            "occurrences_done = -1",
            ErrorCodeEnum.STORAGE_FIELD_INVALID_VALUE,
            "tasks.0.occurrences_done",
        ),
    ],
)
def test_invalid_recurrence_values_make_the_file_invalid(old: str, new: str, code: ErrorCodeEnum, field: str) -> None:
    text = CODEC.encode(_stored(_weekly_task())).replace(old, new, 1)

    result = CODEC.decode(text)

    assert result.data is None
    assert (code, field) in [(issue.code, issue.field) for issue in result.validation.issues]
