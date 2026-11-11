from datetime import UTC, datetime

import pytest

from concentrator.domain.focus.focus_removal_reason_enum import FocusRemovalReasonEnum
from concentrator.domain.todo.task_event import (
    DETAIL_DUE,
    DETAIL_NEXT,
    DETAIL_OCCURRENCE,
    DETAIL_REASON,
    DETAIL_SOURCE,
    SOURCE_FOCUS,
    TaskEvent,
)
from concentrator.domain.todo.task_event_kind_enum import TaskEventKindEnum
from concentrator.presentation.common.date_time_formatter import DateTimeFormatter
from concentrator.presentation.todo.task_history_formatter import TaskHistoryFormatter
from tests.fakes.fake_clock import FakeClock
from tests.fakes.fake_translator import FakeTranslator

AT = datetime(2026, 11, 6, 17, 10, tzinfo=UTC)


def _text(kind: TaskEventKindEnum, *details: tuple[str, str]) -> str:
    translator = FakeTranslator()
    formatter = TaskHistoryFormatter(translator, DateTimeFormatter(translator, FakeClock()))
    return formatter.text(TaskEvent(at=AT, kind=kind, details=details), {})


def test_added_to_focus_has_its_text() -> None:
    assert _text(TaskEventKindEnum.ADDED_TO_FOCUS) == "en:todo.history.added_to_focus"


@pytest.mark.parametrize(
    ("reason", "key"),
    [
        ("1", "en:todo.history.removed_from_focus"),
        ("2", "en:todo.history.removed_from_focus.completed"),
        ("3", "en:todo.history.removed_from_focus.occurrence_completed"),
        ("4", "en:todo.history.removed_from_focus.archived"),
        ("99", "en:todo.history.removed_from_focus"),
        ("x", "en:todo.history.removed_from_focus"),
    ],
)
def test_removed_from_focus_names_the_reason(reason: str, key: str) -> None:
    assert _text(TaskEventKindEnum.REMOVED_FROM_FOCUS, (DETAIL_REASON, reason)) == key


def test_completions_made_from_the_queue_say_so() -> None:
    completed = _text(TaskEventKindEnum.COMPLETED, (DETAIL_SOURCE, SOURCE_FOCUS))
    occurrence = _text(
        TaskEventKindEnum.OCCURRENCE_COMPLETED,
        (DETAIL_OCCURRENCE, "1"),
        (DETAIL_DUE, "2026-11-06"),
        (DETAIL_NEXT, "2026-11-13"),
        (DETAIL_SOURCE, SOURCE_FOCUS),
    )

    assert completed == "en:todo.history.from_focus(text=en:todo.history.completed)"
    assert occurrence.startswith("en:todo.history.from_focus(text=en:todo.history.occurrence_completed(")
    assert _text(TaskEventKindEnum.COMPLETED) == "en:todo.history.completed"
    assert str(FocusRemovalReasonEnum.BY_USER.value) == "1"
