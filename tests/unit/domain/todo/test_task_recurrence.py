from dataclasses import replace
from datetime import UTC, date, datetime, time

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.todo.recurrence import Recurrence
from concentrator.domain.todo.recurrence_end_enum import RecurrenceEndEnum
from concentrator.domain.todo.recurrence_frequency_enum import RecurrenceFrequencyEnum
from concentrator.domain.todo.task import Task, TaskId
from concentrator.domain.todo.task_draft import TaskDraft
from concentrator.domain.todo.task_event import DETAIL_DUE, DETAIL_NEXT, DETAIL_OCCURRENCE, DETAIL_SKIPPED, TaskEvent
from concentrator.domain.todo.task_event_kind_enum import TaskEventKindEnum
from concentrator.domain.todo.task_rules import TaskRules
from concentrator.domain.todo.task_state_enum import TaskStateEnum
from concentrator.domain.todo.weekday_enum import WeekdayEnum
from tests.fakes.todo_factory import TODO_LIMITS, WORK_LIST_ID, make_task

NOW = datetime(2026, 11, 6, 18, 0, tzinfo=UTC)
MAX_EVENTS = 10
FIRST_DUE = date(2026, 11, 6)


def _weekly(
    end_kind: RecurrenceEndEnum = RecurrenceEndEnum.AFTER_COUNT, end_date: date | None = None, end_count: int = 4
) -> Recurrence:
    return Recurrence.create(
        frequency=RecurrenceFrequencyEnum.WEEKLY,
        interval=2,
        weekdays=(WeekdayEnum.MONDAY, WeekdayEnum.FRIDAY),
        anchor_date=date(2000, 1, 1),
        end_kind=end_kind,
        end_date=end_date,
        end_count=end_count,
    )


def _recurring(recurrence: Recurrence, due: date = FIRST_DUE, due_time: time | None = None) -> Task:
    draft = TaskDraft(list_id=WORK_LIST_ID, text=make_task(1).text, due_date=due, due_time=due_time)
    return Task.create(TaskId("t"), NOW, replace(draft, recurrence=recurrence))


def _complete(task: Task, today: date) -> Task:
    result = task.completed(NOW, today, MAX_EVENTS)
    assert result.data is not None
    return result.data


def _last(task: Task, kind: TaskEventKindEnum) -> TaskEvent:
    return next(event for event in reversed(task.history.events) if event.kind is kind)


def test_create_anchors_the_series_on_the_due_date() -> None:
    task = _recurring(_weekly())

    assert task.recurrence is not None
    assert task.recurrence.anchor_date == FIRST_DUE
    assert task.occurrences_done == 0


def test_weekly_four_times_moves_to_the_right_dates_then_is_done() -> None:
    task = _recurring(_weekly())
    dues: list[date | None] = []
    for _ in range(3):
        task = _complete(task, task.due_date or FIRST_DUE)
        dues.append(task.due_date)

    assert dues == [date(2026, 11, 16), date(2026, 11, 20), date(2026, 11, 30)]
    assert (task.state, task.occurrences_done, task.completed_at) == (TaskStateEnum.OPEN, 3, None)

    task = _complete(task, date(2026, 11, 30))

    assert (task.state, task.occurrences_done, task.completed_at) == (TaskStateEnum.DONE, 4, NOW)
    assert task.due_date == date(2026, 11, 30)
    kinds = [event.kind for event in task.history]
    assert kinds.count(TaskEventKindEnum.OCCURRENCE_COMPLETED) == 4
    assert kinds[-1] is TaskEventKindEnum.COMPLETED
    assert _last(task, TaskEventKindEnum.OCCURRENCE_COMPLETED).details == (
        (DETAIL_OCCURRENCE, "4"),
        (DETAIL_DUE, "2026-11-30"),
    )


def test_occurrence_event_names_the_due_and_next_dates() -> None:
    task = _complete(_recurring(_weekly()), FIRST_DUE)

    assert _last(task, TaskEventKindEnum.OCCURRENCE_COMPLETED).details == (
        (DETAIL_OCCURRENCE, "1"),
        (DETAIL_DUE, "2026-11-06"),
        (DETAIL_NEXT, "2026-11-16"),
    )


def test_on_date_stops_when_the_next_date_passes_the_end() -> None:
    task = _recurring(_weekly(RecurrenceEndEnum.ON_DATE, end_date=date(2026, 11, 18)))

    task = _complete(task, FIRST_DUE)
    assert (task.state, task.due_date) == (TaskStateEnum.OPEN, date(2026, 11, 16))

    task = _complete(task, date(2026, 11, 16))
    assert (task.state, task.due_date, task.occurrences_done) == (TaskStateEnum.DONE, date(2026, 11, 16), 2)


def test_never_ending_series_keeps_going_and_keeps_the_due_time() -> None:
    task = _recurring(_weekly(RecurrenceEndEnum.NEVER), due_time=time(9, 0))

    for _ in range(10):
        task = _complete(task, task.due_date or FIRST_DUE)

    assert (task.state, task.occurrences_done, task.due_time) == (TaskStateEnum.OPEN, 10, time(9, 0))


def test_overdue_occurrence_jumps_to_today_or_later_and_counts_the_skipped_dates() -> None:
    task = _recurring(_weekly(RecurrenceEndEnum.NEVER))

    task = _complete(task, date(2026, 11, 25))

    assert (task.due_date, task.occurrences_done) == (date(2026, 11, 30), 1)
    assert _last(task, TaskEventKindEnum.OCCURRENCE_COMPLETED).details == (
        (DETAIL_OCCURRENCE, "1"),
        (DETAIL_DUE, "2026-11-06"),
        (DETAIL_NEXT, "2026-11-30"),
        (DETAIL_SKIPPED, "2"),
    )


def test_count_is_reached_by_completions_not_by_skipped_dates() -> None:
    task = _recurring(_weekly(end_count=2))

    task = _complete(task, date(2026, 12, 20))

    assert (task.state, task.occurrences_done) == (TaskStateEnum.OPEN, 1)


def test_completing_a_one_off_or_a_done_task_uses_the_normal_transition() -> None:
    one_off = _complete(make_task(1), FIRST_DUE)
    done = _recurring(_weekly()).transitioned(TaskEventKindEnum.COMPLETED, NOW, MAX_EVENTS).data
    assert done is not None

    assert (one_off.state, one_off.occurrences_done) == (TaskStateEnum.DONE, 0)
    assert done.completed(NOW, FIRST_DUE, MAX_EVENTS).validation.error_codes == (
        ErrorCodeEnum.TASK_STATE_TRANSITION_INVALID,
    )


def test_editing_the_due_date_moves_the_anchor_without_a_recurrence_event() -> None:
    task = _recurring(_weekly())

    edited = task.with_draft(replace(task.draft, due_date=date(2026, 11, 9)), NOW, MAX_EVENTS)

    assert edited.recurrence is not None
    assert edited.recurrence.anchor_date == date(2026, 11, 9)
    assert edited.history.last is not None
    assert edited.history.last.kind is TaskEventKindEnum.DUE_CHANGED


def test_changing_the_repetition_keeps_the_anchor_and_adds_an_event() -> None:
    task = _complete(_recurring(_weekly()), FIRST_DUE)
    other = replace(_weekly(), interval=3, anchor_date=date(2000, 1, 1))

    edited = task.with_draft(replace(task.draft, recurrence=other), NOW, MAX_EVENTS)

    assert edited.recurrence is not None
    assert (edited.recurrence.interval, edited.recurrence.anchor_date) == (3, date(2000, 1, 1))
    assert edited.history.last is not None
    assert edited.history.last.kind is TaskEventKindEnum.RECURRENCE_CHANGED


def test_adding_and_removing_a_repetition() -> None:
    task = make_task(1, due_date=date(2026, 11, 12))

    added = task.with_draft(replace(task.draft, recurrence=_weekly()), NOW, MAX_EVENTS)
    removed = added.with_draft(replace(added.draft, recurrence=None), NOW, MAX_EVENTS)

    assert added.recurrence is not None
    assert added.recurrence.anchor_date == date(2026, 11, 12)
    assert removed.recurrence is None
    assert [event.kind for event in removed.history][-2:] == [
        TaskEventKindEnum.RECURRENCE_CHANGED,
        TaskEventKindEnum.RECURRENCE_CHANGED,
    ]
    assert removed.with_draft(removed.draft, NOW, MAX_EVENTS) is removed


def test_with_due_date_keeps_the_time_and_clearing_drops_it() -> None:
    task = make_task(1, due_date=date(2026, 11, 12), due_time=time(14, 30))

    moved = task.with_due_date(date(2026, 11, 20), NOW, MAX_EVENTS)
    cleared = task.with_due_date(None, NOW, MAX_EVENTS)

    assert (moved.due_date, moved.due_time) == (date(2026, 11, 20), time(14, 30))
    assert (cleared.due_date, cleared.due_time) == (None, None)
    assert task.with_due_date(date(2026, 11, 12), NOW, MAX_EVENTS) is task


def test_clearing_the_due_date_of_a_recurring_task_breaks_the_rules() -> None:
    task = _recurring(_weekly()).with_due_date(None, NOW, MAX_EVENTS)

    assert TaskRules.validate(task, TODO_LIMITS).error_codes == (ErrorCodeEnum.RECURRENCE_REQUIRES_DUE_DATE,)


def test_business_copy_keeps_the_repetition_and_restarts_the_count() -> None:
    task = _complete(_recurring(_weekly()), FIRST_DUE)

    copy = task.business_copy("copy", NOW)

    assert (copy.recurrence, copy.occurrences_done) == (task.recurrence, 0)


def test_draft_rules_check_the_repetition() -> None:
    draft = TaskDraft(list_id=WORK_LIST_ID, text=make_task(1).text, recurrence=_weekly())

    assert TaskRules.validate_draft(draft, TODO_LIMITS).error_codes == (ErrorCodeEnum.RECURRENCE_REQUIRES_DUE_DATE,)
