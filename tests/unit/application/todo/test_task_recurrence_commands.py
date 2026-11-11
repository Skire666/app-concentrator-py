from dataclasses import replace
from datetime import date

from concentrator.application.todo.todo_events import TaskOccurrenceCompletedEvent, TaskStateChangedEvent
from concentrator.domain.common.multiline_text import MultilineText
from concentrator.domain.todo.recurrence import Recurrence
from concentrator.domain.todo.recurrence_end_enum import RecurrenceEndEnum
from concentrator.domain.todo.recurrence_frequency_enum import RecurrenceFrequencyEnum
from concentrator.domain.todo.task import Task
from concentrator.domain.todo.task_draft import TaskDraft
from concentrator.domain.todo.task_event_kind_enum import TaskEventKindEnum
from concentrator.domain.todo.task_list import TaskListId
from concentrator.domain.todo.task_state_enum import TaskStateEnum
from tests.fakes.todo_factory import WORK_LIST_ID, make_task
from tests.fakes.todo_stack import TodoStack

TODAY = date(2026, 11, 6)
"""Local date of ``FakeClock`` at its start (a Friday)."""


def _daily(end_count: int = 2) -> Recurrence:
    return Recurrence.create(
        frequency=RecurrenceFrequencyEnum.DAILY,
        interval=1,
        anchor_date=TODAY,
        end_kind=RecurrenceEndEnum.AFTER_COUNT,
        end_count=end_count,
    )


def _recurring(number: int = 1, due: date = TODAY) -> Task:
    return replace(make_task(number, due_date=due), recurrence=_daily().with_anchor(due))


def test_completing_a_recurring_task_moves_it_to_its_next_date() -> None:
    stack = TodoStack(tasks=[_recurring()])

    assert stack.task_commands.complete(["task-001"]).is_success

    task = stack.task("task-001")
    assert (task.state, task.due_date, task.occurrences_done) == (TaskStateEnum.OPEN, date(2026, 11, 7), 1)
    assert stack.events == [TaskOccurrenceCompletedEvent(task_id="task-001", occurrence=1)]


def test_completing_the_last_occurrence_marks_the_task_done() -> None:
    stack = TodoStack(tasks=[replace(_recurring(), occurrences_done=1)])

    assert stack.task_commands.complete(["task-001"]).is_success

    assert stack.task("task-001").state is TaskStateEnum.DONE
    assert stack.events == [
        TaskOccurrenceCompletedEvent(task_id="task-001", occurrence=2),
        TaskStateChangedEvent(task_id="task-001", old_state=TaskStateEnum.OPEN, new_state=TaskStateEnum.DONE),
    ]


def test_an_overdue_occurrence_jumps_to_today() -> None:
    stack = TodoStack(tasks=[_recurring(due=date(2026, 11, 1))])

    stack.task_commands.complete(["task-001"])

    task = stack.task("task-001")
    assert task.due_date == TODAY
    assert task.history.last is not None
    assert task.history.last.kind is TaskEventKindEnum.OCCURRENCE_COMPLETED


def test_a_mixed_selection_completes_one_off_tasks_and_occurrences_in_one_write() -> None:
    stack = TodoStack(tasks=[_recurring(1), make_task(2)])

    assert stack.task_commands.complete(["task-001", "task-002"]).is_success

    assert stack.task("task-001").state is TaskStateEnum.OPEN
    assert stack.task("task-002").state is TaskStateEnum.DONE


def test_created_and_edited_texts_get_flat_paths() -> None:
    stack = TodoStack()
    draft = TaskDraft(list_id=TaskListId(WORK_LIST_ID), text=MultilineText(("Docs", "C:\\Users\\me\\My folder")))

    created = stack.task_commands.create(draft)
    assert created.data is not None
    edited = stack.task_commands.update(
        created.data.id, replace(draft, text=MultilineText(("Docs", "\\\\nas\\share", "See C:\\inline")))
    )

    assert created.data.text.lines == ("Docs", "C:/Users/me/My folder")
    assert edited.data is not None
    assert edited.data.text.lines == ("Docs", "//nas/share", "See C:\\inline")


def test_quick_add_flattens_a_pasted_path() -> None:
    stack = TodoStack()

    created = stack.task_commands.quick_add(WORK_LIST_ID, "D:\\Projects\\Concentrator")

    assert created.data is not None
    assert created.data.text.lines == ("D:/Projects/Concentrator",)


def test_typing_the_stored_path_with_backslashes_changes_nothing() -> None:
    stored = replace(make_task(1), text=MultilineText(("C:/Docs",)))
    stack = TodoStack(tasks=[stored])

    result = stack.task_commands.update("task-001", replace(stored.draft, text=MultilineText(("C:\\Docs",))))

    assert result.data is stored
    assert stack.events == []
