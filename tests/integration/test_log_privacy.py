"""Logs at INFO and above never hold what the user typed in tasks and lists (phase 8 audit, AGENTS.md 7.5).

The data file path and the application paths stay in the logs (owner decision, ADR-044); the texts, list
names and the paths and URLs written in tasks do not.
"""

import logging
from dataclasses import replace
from typing import Final

import pytest

from concentrator.application.storage.user_data import StoredUserData
from concentrator.application.todo.task_list_commands import ListValues
from concentrator.domain.common.multiline_text import MultilineText
from concentrator.domain.todo.priority_enum import PriorityEnum
from concentrator.domain.todo.tasks_collection import TasksCollection
from concentrator.infrastructure.persistence.user_data_codec import UserDataCodec
from tests.fakes.todo_factory import HOME_LIST_ID, WORK_LIST_ID
from tests.fakes.todo_stack import TodoStack
from tests.fakes.user_data_factory import USER_DATA_LIMITS, make_stored

SECRET: Final = "Zq7secret"
SECRET_PATH: Final = f"D:/Clients/{SECRET}/contract.pdf"
SECRET_URL: Final = f"https://example.org/{SECRET}?token=1"
TASK_TEXT: Final = f"Call {SECRET} about the offer\n{SECRET_PATH}\n{SECRET_URL}"
CODEC: Final = UserDataCodec("1.0.0", USER_DATA_LIMITS)


def _visible_records(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [record.getMessage() for record in caplog.records if record.levelno >= logging.INFO]


def _run_every_task_use_case(stack: TodoStack) -> None:
    listed = stack.list_commands.create(
        ListValues(name=f"List {SECRET}", description=MultilineText((SECRET,)), priority=PriorityEnum.HIGH)
    )
    assert listed.data is not None
    task = stack.task_commands.quick_add(WORK_LIST_ID, TASK_TEXT).data
    assert task is not None
    other = stack.task_commands.quick_add(WORK_LIST_ID, f"Quick {SECRET}").data
    assert other is not None
    for index in range(2):
        stack.link_commands.open_link(task.id, index)
    stack.link_commands.open_link(task.id, 7)
    stack.task_commands.move_to_list((task.id,), HOME_LIST_ID)
    stack.task_commands.duplicate(task.id)
    stack.task_commands.complete((task.id, other.id))
    stack.task_commands.reopen((task.id,))
    stack.task_commands.archive((task.id,))
    stack.list_commands.update(
        listed.data.id, ListValues(name=SECRET, description=MultilineText(()), priority=PriorityEnum.LOW)
    )
    stack.list_commands.delete(listed.data.id, delete_tasks=True)
    stack.task_commands.delete((task.id, other.id))


def test_task_and_list_use_cases_never_log_user_text(caplog: pytest.LogCaptureFixture) -> None:
    stack = TodoStack()

    with caplog.at_level(logging.DEBUG):
        _run_every_task_use_case(stack)

    assert len(_visible_records(caplog)) > 0
    assert [message for message in _visible_records(caplog) if SECRET in message] == []


def _stored_with_secret() -> StoredUserData:
    stack = TodoStack()
    stack.task_commands.quick_add(WORK_LIST_ID, TASK_TEXT)
    stored = make_stored()
    return replace(stored, data=stored.data.with_tasks(TasksCollection(stack.tasks())))


def test_reading_a_damaged_file_never_logs_user_text(caplog: pytest.LogCaptureFixture) -> None:
    text = CODEC.encode(_stored_with_secret())
    damaged = text.replace("state = 1\n", f"state = 1\nnote = '{SECRET}'\n", 1).replace("  'Call", "  42,\n  'Call", 1)

    with caplog.at_level(logging.DEBUG):
        result = CODEC.decode(damaged)

    assert result.validation.is_failure
    assert len(_visible_records(caplog)) > 0
    assert [message for message in _visible_records(caplog) if SECRET in message] == []
