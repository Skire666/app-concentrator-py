import logging
from dataclasses import replace

import pytest

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.multiline_text import MultilineText
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.todo.link_kind_enum import LinkKindEnum
from concentrator.domain.todo.link_target import LinkTarget
from tests.fakes.todo_factory import make_task
from tests.fakes.todo_stack import TodoStack

TEXT = MultilineText(
    (
        "Weekly backup",
        "D:/Projects/Concentrator",
        "//nas/backup/projects",
        "https://example.org/backup-guide",
        "Z:/This/Folder/Does/Not/Exist",
    )
)


def _stack() -> TodoStack:
    return TodoStack(tasks=[replace(make_task(1), text=TEXT)])


@pytest.mark.parametrize(
    ("index", "target"),
    [
        (0, LinkTarget(LinkKindEnum.LOCAL_PATH, "D:/Projects/Concentrator")),
        (1, LinkTarget(LinkKindEnum.UNC_PATH, "//nas/backup/projects")),
        (2, LinkTarget(LinkKindEnum.URL, "https://example.org/backup-guide")),
        (3, LinkTarget(LinkKindEnum.LOCAL_PATH, "Z:/This/Folder/Does/Not/Exist")),
    ],
)
def test_the_normalized_target_reaches_the_opener_unchanged(index: int, target: LinkTarget) -> None:
    stack = _stack()

    assert stack.link_commands.open_link("task-001", index).is_success

    assert stack.opener.links == [target]
    assert stack.opener.opened == []


def test_a_refusal_is_returned_and_logged_without_the_link(caplog: pytest.LogCaptureFixture) -> None:
    stack = _stack()
    stack.opener.result = ValidationResult.warning(ErrorCodeEnum.LINK_OPEN_FAILED, kind="URL")

    with caplog.at_level(logging.DEBUG):
        result = stack.link_commands.open_link("task-001", 2)

    assert result.has_warnings
    assert result.issues[0].code is ErrorCodeEnum.LINK_OPEN_FAILED
    assert "example.org" not in caplog.text


def test_an_opened_link_is_logged_by_kind_only(caplog: pytest.LogCaptureFixture) -> None:
    stack = _stack()

    with caplog.at_level(logging.INFO):
        stack.link_commands.open_link("task-001", 0)

    assert "Link opened (LOCAL_PATH)" in caplog.text
    assert "Projects" not in caplog.text


@pytest.mark.parametrize(("task_id", "index"), [("task-001", 4), ("task-001", -1), ("missing", 0)])
def test_a_link_or_task_gone_is_not_found(task_id: str, index: int) -> None:
    stack = _stack()

    result = stack.link_commands.open_link(task_id, index)

    assert result.error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)
    assert stack.opener.links == []
