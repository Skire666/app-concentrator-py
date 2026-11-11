from dataclasses import replace
from datetime import date

from concentrator.application.focus.focus_events import FocusQueueChangedEvent
from concentrator.application.todo.todo_events import TaskCreatedEvent
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.focus.focus_limits import FocusLimits
from concentrator.domain.focus.focus_removal_reason_enum import FocusRemovalReasonEnum
from concentrator.domain.todo.recurrence import Recurrence
from concentrator.domain.todo.recurrence_end_enum import RecurrenceEndEnum
from concentrator.domain.todo.recurrence_frequency_enum import RecurrenceFrequencyEnum
from concentrator.domain.todo.task import Task
from concentrator.domain.todo.task_event import DETAIL_REASON, DETAIL_SOURCE, SOURCE_FOCUS, TaskEvent
from concentrator.domain.todo.task_event_kind_enum import TaskEventKindEnum
from concentrator.domain.todo.task_list import TaskList
from concentrator.domain.todo.task_state_enum import TaskStateEnum
from concentrator.domain.todo.weekday_enum import WeekdayEnum
from tests.fakes.focus_factory import make_queue
from tests.fakes.focus_stack import FocusStack
from tests.fakes.todo_factory import HOME_LIST_ID, make_list, make_task

TODAY = date(2026, 11, 6)
"""Local date of ``FakeClock`` at its start."""


def _kinds(task: Task) -> list[TaskEventKindEnum]:
    return [event.kind for event in task.history]


def _last(task: Task) -> TaskEvent:
    last = task.history.last
    assert last is not None
    return last


def _weekly(number: int = 1) -> Task:
    recurrence = Recurrence.create(
        frequency=RecurrenceFrequencyEnum.WEEKLY,
        interval=1,
        weekdays=(WeekdayEnum.FRIDAY,),
        anchor_date=TODAY,
        end_kind=RecurrenceEndEnum.NEVER,
    )
    return replace(make_task(number, due_date=TODAY), recurrence=recurrence)


def _name(task_list: TaskList | None) -> str:
    assert task_list is not None
    return task_list.name


def test_add_tasks_queues_at_the_end_records_and_publishes() -> None:
    stack = FocusStack(tasks=[make_task(1), make_task(2), make_task(3)], queue=make_queue(3))

    result = stack.focus_commands.add_tasks(["task-001", "task-002"])

    assert result.is_success
    assert stack.queued() == ["task-003", "task-001", "task-002"]
    assert _kinds(stack.task("task-001")) == [TaskEventKindEnum.CREATED, TaskEventKindEnum.ADDED_TO_FOCUS]
    assert stack.task("task-001").updated_at == stack.clock.now_utc()
    assert stack.focus_events == [FocusQueueChangedEvent(task_ids=("task-001", "task-002"))]


def test_add_tasks_skips_the_tasks_that_cannot_be_queued() -> None:
    tasks = [make_task(1), make_task(2, state=TaskStateEnum.DONE), make_task(3)]
    stack = FocusStack(tasks=tasks, queue=make_queue(3))

    assert stack.focus_commands.add_tasks(["task-001", "task-002", "task-003"]).is_success

    assert stack.queued() == ["task-003", "task-001"]


def test_add_tasks_reports_why_a_single_task_cannot_be_queued() -> None:
    stack = FocusStack(tasks=[make_task(1), make_task(2, state=TaskStateEnum.ARCHIVED)], queue=make_queue(1))

    assert stack.focus_commands.add_tasks(["task-001"]).error_codes == (ErrorCodeEnum.FOCUS_TASK_ALREADY_QUEUED,)
    assert stack.focus_commands.add_tasks(["task-002"]).error_codes == (ErrorCodeEnum.FOCUS_TASK_NOT_OPEN,)
    assert stack.focus_events == []


def test_add_tasks_beyond_the_capacity_queues_nothing() -> None:
    stack = FocusStack(
        tasks=[make_task(1), make_task(2), make_task(3)], queue=make_queue(1), limits=FocusLimits(max_items=2)
    )

    result = stack.focus_commands.add_tasks(["task-002", "task-003"])

    assert result.error_codes == (ErrorCodeEnum.FOCUS_QUEUE_FULL,)
    assert stack.queued() == ["task-001"]
    assert _kinds(stack.task("task-002")) == [TaskEventKindEnum.CREATED]


def test_add_tasks_reports_missing_and_empty_selections() -> None:
    stack = FocusStack(tasks=[make_task(1)])

    assert stack.focus_commands.add_tasks(["task-404"]).error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)
    assert stack.focus_commands.add_tasks([]).is_skipped


def test_toggle_task_queues_then_removes_and_records_the_reason() -> None:
    stack = FocusStack(tasks=[make_task(1)])

    assert stack.focus_commands.toggle_task("task-001").is_success
    assert stack.queued() == ["task-001"]
    assert stack.focus_commands.toggle_task("task-001").is_success

    assert stack.queued() == []
    task = stack.task("task-001")
    assert _kinds(task)[-2:] == [TaskEventKindEnum.ADDED_TO_FOCUS, TaskEventKindEnum.REMOVED_FROM_FOCUS]
    assert _last(task).detail(DETAIL_REASON) == str(FocusRemovalReasonEnum.BY_USER.value)
    assert task.state is TaskStateEnum.OPEN


def test_remove_by_item_and_unknown_items() -> None:
    stack = FocusStack(tasks=[make_task(1), make_task(2)], queue=make_queue(1, 2))

    assert stack.focus_commands.remove("item-002").is_success
    assert stack.queued() == ["task-001"]
    assert stack.focus_commands.remove("item-404").error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)
    assert stack.focus_commands.remove_tasks(["task-002"]).is_skipped


def test_move_reorders_and_stops_at_the_ends() -> None:
    stack = FocusStack(tasks=[make_task(1), make_task(2), make_task(3)], queue=make_queue(1, 2, 3))

    assert stack.focus_commands.move("item-003", -1).is_success
    assert stack.queued() == ["task-001", "task-003", "task-002"]
    assert stack.focus_commands.move("item-001", -1).is_skipped
    assert stack.focus_commands.move("item-404", 1).error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)
    assert stack.focus_events == [FocusQueueChangedEvent(task_ids=("task-003",))]


def test_complete_from_the_queue_completes_the_task_with_the_focus_source() -> None:
    stack = FocusStack(tasks=[make_task(1)], queue=make_queue(1))

    assert stack.focus_commands.complete("item-001").is_success

    task = stack.task("task-001")
    assert task.state is TaskStateEnum.DONE
    assert _last(task).kind is TaskEventKindEnum.COMPLETED
    assert _last(task).detail(DETAIL_SOURCE) == SOURCE_FOCUS
    assert stack.queued() == []
    assert stack.focus_events == [FocusQueueChangedEvent(task_ids=("task-001",))]


def test_complete_a_recurring_task_from_the_queue_keeps_it_open_and_unqueues_it() -> None:
    stack = FocusStack(tasks=[_weekly()], queue=make_queue(1))

    assert stack.focus_commands.complete("item-001").is_success

    task = stack.task("task-001")
    assert (task.state, task.due_date, task.occurrences_done) == (TaskStateEnum.OPEN, date(2026, 11, 13), 1)
    assert _last(task).kind is TaskEventKindEnum.OCCURRENCE_COMPLETED
    assert _last(task).detail(DETAIL_SOURCE) == SOURCE_FOCUS
    assert stack.queued() == []


def test_complete_an_unknown_item_is_reported() -> None:
    stack = FocusStack(tasks=[make_task(1)])

    assert stack.focus_commands.complete("item-404").error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)


def test_quick_add_creates_the_task_in_the_chosen_list_and_queues_it() -> None:
    stack = FocusStack()

    result = stack.focus_commands.quick_add("  Call the bank  ", HOME_LIST_ID)

    task = result.data
    assert task is not None
    assert (task.list_id, task.text.as_text()) == (HOME_LIST_ID, "Call the bank")
    assert _kinds(stack.task(task.id)) == [TaskEventKindEnum.CREATED, TaskEventKindEnum.ADDED_TO_FOCUS]
    assert stack.queued() == [task.id]
    assert TaskCreatedEvent(task_id=task.id) in stack.events


def test_quick_add_uses_the_list_named_like_the_inbox_when_the_chosen_one_is_gone() -> None:
    inbox = make_list("en:todo.default_list_name", list_id="list-inbox", position=2)
    stack = FocusStack(lists=[make_list("Work"), inbox])

    task = stack.focus_commands.quick_add("Pay", "list-gone").data

    assert task is not None
    assert task.list_id == "list-inbox"
    assert _name(stack.focus_queries.quick_add_list("")) == "en:todo.default_list_name"


def test_quick_add_creates_an_inbox_when_no_list_is_named_so() -> None:
    stack = FocusStack()

    task = stack.focus_commands.quick_add("Pay", "").data

    assert task is not None
    names = {item.id: item.name for item in stack.lists()}
    assert names[task.list_id] == "en:todo.default_list_name"
    assert _name(stack.focus_queries.quick_add_list("")) == "en:todo.default_list_name"


def test_quick_add_on_a_full_queue_or_without_text_creates_nothing() -> None:
    stack = FocusStack(tasks=[make_task(1)], queue=make_queue(1), limits=FocusLimits(max_items=1))
    count = len(stack.tasks())

    full = stack.focus_commands.quick_add("Pay", HOME_LIST_ID)
    stack.focus_commands.remove("item-001")
    empty = stack.focus_commands.quick_add("   ", HOME_LIST_ID)

    assert full.validation.error_codes == (ErrorCodeEnum.FOCUS_QUEUE_FULL,)
    assert empty.validation.error_codes == (ErrorCodeEnum.TASK_TEXT_EMPTY,)
    assert len(stack.tasks()) == count


def test_quick_add_reports_a_failed_creation() -> None:
    stack = FocusStack()
    stack.task_writer.fail = True

    result = stack.focus_commands.quick_add("Pay", HOME_LIST_ID)

    assert result.validation.error_codes == (ErrorCodeEnum.STORAGE_WRITE_FAILED,)
    assert stack.queued() == []


def test_history_write_failure_is_reported_after_the_queue_changed() -> None:
    stack = FocusStack(tasks=[make_task(1)])
    stack.task_writer.fail = True

    result = stack.focus_commands.add_tasks(["task-001"])

    assert result.error_codes == (ErrorCodeEnum.STORAGE_WRITE_FAILED,)
    assert stack.queued() == ["task-001"]
