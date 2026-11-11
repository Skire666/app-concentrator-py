from dataclasses import replace
from datetime import date

from concentrator.domain.todo.recurrence import Recurrence
from concentrator.domain.todo.recurrence_end_enum import RecurrenceEndEnum
from concentrator.domain.todo.recurrence_frequency_enum import RecurrenceFrequencyEnum
from concentrator.domain.todo.task_event_kind_enum import TaskEventKindEnum
from concentrator.domain.todo.weekday_enum import WeekdayEnum
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from tests.fakes.todo_factory import WORK_LIST_ID, make_task
from tests.fakes.todo_ui_stack import TodoUiStack

SAVE_TASK = int(ActionIdEnum.TASK_EDIT_SAVE)
TODAY = date(2026, 11, 6)
"""Local date of the fake clock: a Friday."""


def _open_new() -> TodoUiStack:
    stack = TodoUiStack()
    stack.task_editor.open_new(WORK_LIST_ID)
    stack.task_editor.on_text_changed("Backup")
    return stack


def test_repeat_is_off_for_a_new_task() -> None:
    stack = _open_new()

    snapshot = stack.task_editor.build_snapshot().recurrence

    assert not snapshot.enabled
    assert (snapshot.summary, snapshot.preview, snapshot.error) == ("", "", "")
    assert len(snapshot.rule.weekdays) == 7
    assert snapshot.rule.weekdays[0].text == "en:format.weekday.short.monday"


def test_ticking_repeat_proposes_weekly_on_the_weekday_of_the_due_date() -> None:
    stack = _open_new()
    editor = stack.task_editor
    editor.on_due_date_changed(True, 2026, 11, 10)

    editor.recurrence.on_repeat_toggled(True)

    snapshot = editor.build_snapshot().recurrence
    assert snapshot.enabled
    assert snapshot.rule.weekdays_visible
    assert [day.checked for day in snapshot.rule.weekdays] == [False, True, False, False, False, False, False]
    assert snapshot.rule.frequency.selected == 1
    assert snapshot.summary.startswith("en:todo.recurrence.on_days(rule=en:todo.recurrence.every.weekly.one")
    assert snapshot.preview.startswith("en:todo.task_edit.repeat_preview(dates=en:format.date(day=17")


def test_repeat_without_due_date_shows_the_rule_error() -> None:
    stack = _open_new()

    stack.task_editor.recurrence.on_repeat_toggled(True)

    snapshot = stack.task_editor.build_snapshot()
    assert snapshot.recurrence.error == "en:error.recurrence_requires_due_date"
    assert not snapshot.recurrence.preview
    assert not snapshot.save.enabled


def test_weekly_mon_fri_every_two_weeks_four_times_is_saved() -> None:
    stack = TodoUiStack()

    def act() -> None:
        editor = stack.task_editor
        section = editor.recurrence
        editor.on_text_changed("Backup")
        editor.on_due_date_changed(True, 2026, 11, 6)
        section.on_repeat_toggled(True)
        section.on_weekday_toggled(int(WeekdayEnum.MONDAY), True)
        section.on_interval_changed(2)
        section.on_end_selected(2)
        section.on_end_count_changed(4)
        snapshot = editor.build_snapshot().recurrence
        assert snapshot.ending.end_count_visible
        assert not snapshot.ending.end_date_visible
        editor.on_action_requested(SAVE_TASK)

    stack.task_window.while_open = act
    stack.task_editor.open_new(WORK_LIST_ID)

    task = stack.tasks().items[0]
    assert task.recurrence == Recurrence.create(
        frequency=RecurrenceFrequencyEnum.WEEKLY,
        interval=2,
        weekdays=(WeekdayEnum.MONDAY, WeekdayEnum.FRIDAY),
        anchor_date=TODAY,
        end_kind=RecurrenceEndEnum.AFTER_COUNT,
        end_count=4,
    )


def test_monthly_on_the_31st_previews_the_clamped_dates() -> None:
    stack = _open_new()
    editor = stack.task_editor
    editor.on_due_date_changed(True, 2026, 10, 31)
    editor.recurrence.on_repeat_toggled(True)

    editor.recurrence.on_frequency_selected(2)

    preview = editor.build_snapshot().recurrence.preview
    assert preview == (
        "en:todo.task_edit.repeat_preview(dates="
        "en:format.date(day=30,month=11,year=2026)en:format.list.separator"
        "en:format.date(day=31,month=12,year=2026)en:format.list.separator"
        "en:format.date(day=31,month=01,year=2027)en:format.list.separator"
        "en:format.date(day=28,month=02,year=2027))"
    )


def test_end_date_before_the_due_date_is_an_inline_error() -> None:
    stack = _open_new()
    editor = stack.task_editor
    editor.on_due_date_changed(True, 2026, 11, 10)
    editor.recurrence.on_repeat_toggled(True)

    editor.recurrence.on_end_selected(1)
    editor.recurrence.on_end_date_changed(2026, 11, 9)

    snapshot = editor.build_snapshot().recurrence
    assert snapshot.ending.end_date_visible
    assert (snapshot.ending.end_date.year, snapshot.ending.end_date.month, snapshot.ending.end_date.day) == (
        2026,
        11,
        9,
    )
    assert snapshot.error == "en:error.recurrence_end_date_before_due"


def test_removing_the_last_weekday_is_an_inline_error() -> None:
    stack = _open_new()
    editor = stack.task_editor
    editor.on_due_date_changed(True, 2026, 11, 6)
    editor.recurrence.on_repeat_toggled(True)

    editor.recurrence.on_weekday_toggled(int(WeekdayEnum.FRIDAY), False)
    editor.recurrence.on_weekday_toggled(99, True)

    assert editor.build_snapshot().recurrence.error == "en:error.recurrence_weekdays_empty"


def test_bad_indices_change_nothing() -> None:
    stack = _open_new()
    editor = stack.task_editor
    editor.recurrence.on_repeat_toggled(True)
    before = editor.build_snapshot().recurrence

    editor.recurrence.on_frequency_selected(9)
    editor.recurrence.on_end_selected(-1)

    assert editor.build_snapshot().recurrence == before


def test_unticking_and_ticking_again_brings_back_the_stored_series() -> None:
    recurrence = Recurrence.create(
        frequency=RecurrenceFrequencyEnum.DAILY, interval=3, anchor_date=TODAY, end_kind=RecurrenceEndEnum.NEVER
    )
    stack = TodoUiStack(tasks=[replace(make_task(1, due_date=TODAY), recurrence=recurrence)])
    editor = stack.task_editor
    editor.open_edit("task-001")

    editor.recurrence.on_repeat_toggled(False)
    assert editor.build_snapshot().save.enabled
    editor.recurrence.on_repeat_toggled(False)
    editor.recurrence.on_repeat_toggled(True)

    snapshot = editor.build_snapshot()
    assert (snapshot.recurrence.rule.interval, snapshot.recurrence.rule.frequency.selected) == (3, 0)
    assert not snapshot.save.enabled


def test_unticking_a_new_series_is_not_a_change() -> None:
    stack = TodoUiStack(tasks=[make_task(1, due_date=TODAY)])
    editor = stack.task_editor
    editor.open_edit("task-001")

    editor.recurrence.on_repeat_toggled(True)
    editor.recurrence.on_interval_changed(5)
    editor.recurrence.on_repeat_toggled(False)

    assert not editor.build_snapshot().save.enabled


def test_removing_a_repetition_is_saved_with_an_event() -> None:
    recurrence = Recurrence.create(
        frequency=RecurrenceFrequencyEnum.DAILY, interval=1, anchor_date=TODAY, end_kind=RecurrenceEndEnum.NEVER
    )
    stack = TodoUiStack(tasks=[replace(make_task(1, due_date=TODAY), recurrence=recurrence)])

    def act() -> None:
        stack.task_editor.recurrence.on_repeat_toggled(False)
        stack.task_editor.on_action_requested(SAVE_TASK)

    stack.task_window.while_open = act
    stack.task_editor.open_edit("task-001")

    task = stack.task("task-001")
    assert task.recurrence is None
    assert task.history.last is not None
    assert task.history.last.kind is TaskEventKindEnum.RECURRENCE_CHANGED


def test_errors_of_a_new_task_wait_for_a_change() -> None:
    stack = TodoUiStack()
    stack.task_editor.open_new(WORK_LIST_ID)
    assert not stack.task_editor.build_snapshot().recurrence.error

    stack.task_editor.recurrence.on_repeat_toggled(True)

    assert stack.task_editor.build_snapshot().recurrence.error == "en:error.recurrence_requires_due_date"
