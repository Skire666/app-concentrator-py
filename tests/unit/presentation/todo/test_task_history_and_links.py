from dataclasses import replace
from datetime import UTC, date, datetime

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.multiline_text import MultilineText
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.todo.link_kind_enum import LinkKindEnum
from concentrator.domain.todo.link_target import LinkTarget
from concentrator.domain.todo.recurrence import Recurrence
from concentrator.domain.todo.recurrence_end_enum import RecurrenceEndEnum
from concentrator.domain.todo.recurrence_frequency_enum import RecurrenceFrequencyEnum
from concentrator.domain.todo.task import Task
from concentrator.domain.todo.task_event import TaskEvent
from concentrator.domain.todo.task_event_kind_enum import TaskEventKindEnum
from concentrator.domain.todo.task_history import TaskHistory
from concentrator.presentation.common.date_time_formatter import DateTimeFormatter
from concentrator.presentation.common.table_snapshot import CellLinkSnapshot
from concentrator.presentation.todo.task_details_snapshot import NO_LINK, TextLineSnapshot
from concentrator.presentation.todo.task_menu_snapshot import LinkMenuItemSnapshot
from concentrator.presentation.todo.task_row_formatter import LINK_CACHE_SIZE, TaskRowFormatter
from tests.fakes.todo_factory import HOME_LIST_ID, WORK_LIST_ID, make_task
from tests.fakes.todo_stack import LINKS
from tests.fakes.todo_ui_stack import TodoUiStack

AT = datetime(2026, 11, 6, 16, 45, tzinfo=UTC)
TODAY = date(2026, 11, 6)
LINK_TEXT = MultilineText(
    ("https://example.org/start", "Weekly backup", "  - D:/Projects", "//nas/a", "C:/b", "E:/c", "https://x.org")
)


def _with_events(*events: TaskEvent) -> Task:
    return replace(make_task(1), history=TaskHistory((TaskEvent.of(AT, TaskEventKindEnum.CREATED), *events)))


def _event(kind: TaskEventKindEnum, **details: str) -> TaskEvent:
    return TaskEvent(at=AT, kind=kind, details=tuple(details.items()))


def test_history_lists_the_events_newest_first() -> None:
    task = _with_events(
        _event(TaskEventKindEnum.MOVED, **{"from": WORK_LIST_ID, "to": "gone"}),
        _event(TaskEventKindEnum.DUE_CHANGED, **{"from": "", "to": "2026-11-10T14:30"}),
        _event(TaskEventKindEnum.OCCURRENCE_COMPLETED, occurrence="3", due="2026-11-10", next="2026-11-17"),
        _event(
            TaskEventKindEnum.OCCURRENCE_COMPLETED, occurrence="4", due="2026-11-17", next="2026-12-01", skipped="1"
        ),
        _event(TaskEventKindEnum.OCCURRENCE_COMPLETED, occurrence="5", due="2026-12-01"),
        _event(TaskEventKindEnum.UNKNOWN),
        _event(TaskEventKindEnum.DUE_CHANGED, **{"from": "bad", "to": ""}),
    )
    stack = TodoUiStack(tasks=[task])

    stack.select("task-001")

    snapshot = stack.rendered_history[-1]
    texts = [line.split(",text=", 1)[1] for line in snapshot.lines]
    assert snapshot.title == "en:todo.history.title"
    assert snapshot.lines[0].startswith("en:todo.history.line(time=en:format.datetime(")
    assert texts == [
        "en:todo.history.due_changed(old=bad,new=en:todo.history.no_date))",
        "en:todo.history.unknown)",
        "en:todo.history.occurrence_last(occurrence=5,due=en:format.date(day=01,month=12,year=2026)))",
        (
            "en:todo.history.occurrence_skipped.one(count=1,occurrence=4,due=en:format.date(day=17,month=11,year=2026),"
            "next=en:format.date(day=01,month=12,year=2026)))"
        ),
        (
            "en:todo.history.occurrence_completed(occurrence=3,due=en:format.date(day=10,month=11,year=2026),"
            "next=en:format.date(day=17,month=11,year=2026)))"
        ),
        (
            "en:todo.history.due_changed(old=en:todo.history.no_date,new=en:format.date(day=10,month=11,year=2026) "
            "en:format.time(hour=14,minute=30)))"
        ),
        "en:todo.history.moved(old=Work,new=en:todo.history.deleted_list))",
        "en:todo.history.created)",
    ]


def test_history_shows_the_hint_of_the_details_without_a_single_task() -> None:
    stack = TodoUiStack(tasks=[make_task(1), make_task(2)])

    assert stack.history.build_snapshot().empty_text == "en:todo.details.empty"
    stack.select("task-001", "task-002")
    assert stack.history.build_snapshot().empty_text == "en:todo.details.several.other(count=2)"


def test_details_lines_carry_their_links() -> None:
    stack = TodoUiStack(tasks=[replace(make_task(1), text=LINK_TEXT)])

    stack.select("task-001")

    lines = stack.rendered_details[-1].lines
    assert lines[0] == TextLineSnapshot(text="https://example.org/start", link_start=0, link_end=25, link_index=0)
    assert lines[1] == TextLineSnapshot(text="Weekly backup", link_index=NO_LINK)
    assert lines[2] == TextLineSnapshot(text="  - D:/Projects", link_start=4, link_end=15, link_index=1)


def test_details_show_the_repetition_of_a_recurring_task() -> None:
    recurrence = Recurrence.create(
        frequency=RecurrenceFrequencyEnum.DAILY,
        interval=1,
        anchor_date=TODAY,
        end_kind=RecurrenceEndEnum.AFTER_COUNT,
        end_count=5,
    )
    task = replace(make_task(1, due_date=TODAY), recurrence=recurrence, occurrences_done=2)
    stack = TodoUiStack(tasks=[task])

    stack.select("task-001")

    rows = {row.label: row.value for row in stack.rendered_details[-1].rows}
    assert rows["en:todo.details.repeat"].startswith("en:todo.recurrence.times.other(count=5,rule=")
    assert rows["en:todo.details.occurrences"] == "en:todo.table.occurrences_of(done=2,count=5)"


def test_table_rows_mark_the_links_of_every_line() -> None:
    stack = TodoUiStack(tasks=[replace(make_task(1), text=LINK_TEXT), make_task(2, created_offset_minutes=1)])

    rows = {row.key: row for row in stack.table.build_snapshot().table.rows}

    separator = len("en:todo.table.line_separator")
    third_line = 25 + separator + len("Weekly backup") + separator
    assert rows["task-001"].links[:2] == (
        CellLinkSnapshot(column=2, start=0, end=25, index=0),
        CellLinkSnapshot(column=2, start=third_line + 4, end=third_line + 15, index=1),
    )
    assert len(rows["task-001"].links) == 6
    assert rows["task-001"].overflow == "en:todo.table.overflow.other(count=7)"
    assert rows["task-001"].cells[7] == "6"
    assert rows["task-002"].links == ()


def test_menu_lists_the_links_of_the_only_selected_task_up_to_the_limit() -> None:
    stack = TodoUiStack(tasks=[replace(make_task(1), text=LINK_TEXT), make_task(2)])

    assert stack.table.build_snapshot().menu.links == ()
    stack.select("task-001")
    menu = stack.table.build_snapshot().menu

    assert menu.open_link is not None
    assert menu.open_link.enabled
    assert menu.links == (
        LinkMenuItemSnapshot(index=0, text="https://example.org/start"),
        LinkMenuItemSnapshot(index=1, text="D:/Projects"),
        LinkMenuItemSnapshot(index=2, text="//nas/a"),
    )
    stack.select("task-001", "task-002")
    menu = stack.table.build_snapshot().menu
    assert menu.open_link is not None
    assert not menu.open_link.enabled


def test_a_link_click_hands_the_target_to_the_opener() -> None:
    stack = TodoUiStack(tasks=[replace(make_task(1), text=LINK_TEXT)])

    stack.links.on_table_link("task-001", 1)
    stack.settle()
    stack.select("task-001")
    stack.links.on_selected_link(3)

    assert stack.opener.links == [
        LinkTarget(LinkKindEnum.LOCAL_PATH, "D:/Projects"),
        LinkTarget(LinkKindEnum.LOCAL_PATH, "C:/b"),
    ]


def test_a_refused_link_shows_no_dialog() -> None:
    stack = TodoUiStack(tasks=[replace(make_task(1), text=LINK_TEXT)])
    stack.opener.result = ValidationResult.warning(ErrorCodeEnum.LINK_OPEN_FAILED, kind="URL")

    stack.links.on_table_link("task-001", 0)

    assert stack.dialogs.calls == []


def test_a_link_chosen_without_a_single_task_or_gone_is_ignored() -> None:
    stack = TodoUiStack(tasks=[replace(make_task(1), text=LINK_TEXT), make_task(2, list_id=HOME_LIST_ID)])

    stack.links.on_selected_link(0)
    stack.links.on_table_link("task-001", 99)

    assert stack.opener.links == []


def test_links_are_found_once_per_text_and_the_cache_empties_when_full() -> None:
    stack = TodoUiStack()
    formatter = TaskRowFormatter(stack.translator, DateTimeFormatter(stack.translator, stack.clock), LINKS)
    first = MultilineText(("C:/a",))

    found = formatter.links(first)
    assert formatter.links(MultilineText(("C:/a",))) is found
    for number in range(LINK_CACHE_SIZE):
        formatter.links(MultilineText((f"text {number}",)))

    assert formatter.links(first) is not found
    assert formatter.links(first) == found
