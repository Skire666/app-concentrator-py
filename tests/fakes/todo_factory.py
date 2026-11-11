"""Lists and tasks for tests, mirroring the phase 5 spec example and the shipped ini."""

from datetime import UTC, date, datetime, time, timedelta
from typing import Final

from concentrator.domain.common.multiline_text import MultilineText
from concentrator.domain.todo.priority_enum import PriorityEnum
from concentrator.domain.todo.task import Task, TaskId
from concentrator.domain.todo.task_event import TaskEvent
from concentrator.domain.todo.task_event_kind_enum import TaskEventKindEnum
from concentrator.domain.todo.task_history import TaskHistory
from concentrator.domain.todo.task_list import TaskList, TaskListId
from concentrator.domain.todo.task_lists_collection import TaskListsCollection
from concentrator.domain.todo.task_state_enum import TaskStateEnum
from concentrator.domain.todo.tasks_collection import TasksCollection
from concentrator.domain.todo.todo_limits import TodoLimits

TODO_CREATED_AT: Final = datetime(2026, 11, 6, 16, 41, tzinfo=UTC)
SPEC_LIST_ID: Final = TaskListId("019a5c21-aaaa-7bbb-8ccc-3e4f5a6b7c8d")
SPEC_TASK_ID: Final = TaskId("019a5c22-bbbb-7ccc-8ddd-4f5a6b7c8d9e")
WORK_LIST_ID: Final = TaskListId("list-work")
HOME_LIST_ID: Final = TaskListId("list-home")

TODO_LIMITS: Final = TodoLimits(
    max_task_text_length=5000,
    max_list_name_length=80,
    max_list_description_length=2000,
    max_history_events=10,
    max_recurrence_interval=999,
    max_recurrence_count=9999,
)


def make_spec_list() -> TaskList:
    """The list of the phase 5 spec example (Work, HIGH, two-line description)."""
    return TaskList(
        id=SPEC_LIST_ID,
        created_at=TODO_CREATED_AT,
        updated_at=TODO_CREATED_AT,
        name="Work",
        description=MultilineText(("Client projects", "and admin")),
        priority=PriorityEnum.HIGH,
        position=0,
    )


def make_list(
    name: str, list_id: str = "", priority: PriorityEnum = PriorityEnum.NORMAL, position: int = 0, description: str = ""
) -> TaskList:
    """A list; the id defaults to ``list-<name lowercase>``."""
    return TaskList(
        id=TaskListId(list_id or f"list-{name.lower()}"),
        created_at=TODO_CREATED_AT,
        updated_at=TODO_CREATED_AT,
        name=name,
        description=MultilineText.from_text(description),
        priority=priority,
        position=position,
    )


def make_lists(*lists: TaskList) -> TaskListsCollection:
    """Wrap lists in a collection; Work (HIGH) and Home (NORMAL) by default."""
    if not lists:
        lists = (
            make_list("Work", priority=PriorityEnum.HIGH, position=0),
            make_list("Home", priority=PriorityEnum.NORMAL, position=1),
        )
    return TaskListsCollection(lists)


def make_task(
    number: int,
    *,
    list_id: str = WORK_LIST_ID,
    text: str = "",
    state: TaskStateEnum = TaskStateEnum.OPEN,
    due_date: date | None = None,
    due_time: time | None = None,
    created_offset_minutes: int = 0,
) -> Task:
    """A task with id ``task-<number:03d>``, created ``created_offset_minutes`` after the reference instant."""
    created = TODO_CREATED_AT + timedelta(minutes=created_offset_minutes)
    completed = created if state is TaskStateEnum.DONE else None
    return Task(
        id=TaskId(f"task-{number:03d}"),
        created_at=created,
        updated_at=created,
        list_id=TaskListId(list_id),
        text=MultilineText.from_text(text or f"Task {number}"),
        due_date=due_date,
        due_time=due_time,
        state=state,
        completed_at=completed,
        history=TaskHistory.started(TaskEvent.of(created, TaskEventKindEnum.CREATED)),
    )


def make_tasks(*tasks: Task) -> TasksCollection:
    """Wrap tasks in a collection."""
    return TasksCollection(tasks)
