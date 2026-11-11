import pytest

from concentrator.application.todo.task_list_commands import ListValues
from concentrator.application.todo.task_query import TaskQuery
from concentrator.application.todo.todo_events import TaskDeletedEvent, TaskListChangedEvent
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.multiline_text import MultilineText
from concentrator.domain.todo.priority_enum import PriorityEnum
from concentrator.domain.todo.task_sort_key_enum import TaskSortKeyEnum
from concentrator.domain.todo.task_state_enum import TaskStateEnum
from tests.fakes.todo_factory import HOME_LIST_ID, WORK_LIST_ID, make_list, make_task
from tests.fakes.todo_stack import WRITE_FAILED, TodoStack


def _values(name: str, priority: PriorityEnum = PriorityEnum.NORMAL, description: str = "") -> ListValues:
    return ListValues(name=name, description=MultilineText.from_text(description), priority=priority)


def _names(stack: TodoStack) -> list[str]:
    return [item.name for item in stack.lists()]


def test_create_adds_the_list_last_in_its_priority() -> None:
    stack = TodoStack()

    created = stack.list_commands.create(_values(" Garden ", description="Seeds\nTools"))

    assert created.data is not None
    assert (created.data.id, created.data.name, created.data.position) == ("new-0001", "Garden", 2)
    assert _names(stack) == ["Work", "Home", "Garden"]
    assert stack.events == [TaskListChangedEvent(list_ids=("new-0001",))]


@pytest.mark.parametrize(
    ("values", "code"),
    [
        (_values("work"), ErrorCodeEnum.LIST_NAME_DUPLICATE),
        (_values(""), ErrorCodeEnum.LIST_NAME_EMPTY),
        (_values("Garden", PriorityEnum.UNSET), ErrorCodeEnum.LIST_PRIORITY_UNSET),
    ],
)
def test_create_refuses_invalid_values(values: ListValues, code: ErrorCodeEnum) -> None:
    stack = TodoStack()

    assert code in stack.list_commands.create(values).validation.error_codes
    assert len(stack.lists()) == 2
    assert stack.events == []


def test_update_changes_the_values_and_keeps_the_position_of_the_same_priority() -> None:
    stack = TodoStack()

    updated = stack.list_commands.update(HOME_LIST_ID, _values("House", description="Chores"))

    assert updated.data is not None
    assert (updated.data.name, updated.data.description.lines, updated.data.position) == ("House", ("Chores",), 1)
    assert stack.events == [TaskListChangedEvent(list_ids=(HOME_LIST_ID,))]


def test_update_with_a_new_priority_puts_the_list_last_of_that_priority() -> None:
    stack = TodoStack(
        lists=[
            make_list("Work", priority=PriorityEnum.HIGH, position=0),
            make_list("Clients", priority=PriorityEnum.HIGH, position=1),
            make_list("Home", priority=PriorityEnum.NORMAL, position=2),
        ]
    )

    stack.list_commands.update(HOME_LIST_ID, _values("Home", PriorityEnum.HIGH))

    assert _names(stack) == ["Work", "Clients", "Home"]


def test_update_without_change_writes_nothing_and_refuses_duplicates() -> None:
    stack = TodoStack()

    assert stack.list_commands.update(HOME_LIST_ID, _values("Home")).is_success
    assert stack.events == []
    assert stack.list_commands.update(HOME_LIST_ID, _values("WORK")).validation.error_codes == (
        ErrorCodeEnum.LIST_NAME_DUPLICATE,
    )
    assert stack.list_commands.update("missing", _values("x")).validation.error_codes == (
        ErrorCodeEnum.ENTITY_NOT_FOUND,
    )


def test_delete_an_empty_list() -> None:
    stack = TodoStack()

    assert stack.list_commands.delete(HOME_LIST_ID, delete_tasks=False).is_success
    assert _names(stack) == ["Work"]
    assert stack.events == [TaskListChangedEvent(list_ids=(HOME_LIST_ID,))]


def test_delete_a_list_with_tasks_needs_the_confirmation_and_deletes_them() -> None:
    stack = TodoStack(tasks=[make_task(1, list_id=HOME_LIST_ID), make_task(2), make_task(3, list_id=HOME_LIST_ID)])

    refused = stack.list_commands.delete(HOME_LIST_ID, delete_tasks=False)
    assert refused.error_codes == (ErrorCodeEnum.LIST_NOT_EMPTY,)
    assert stack.events == []

    assert stack.list_commands.delete(HOME_LIST_ID, delete_tasks=True).is_success

    assert [task.id for task in stack.tasks()] == ["task-002"]
    assert stack.events == [
        TaskDeletedEvent(task_ids=("task-001", "task-003")),
        TaskListChangedEvent(list_ids=(HOME_LIST_ID,)),
    ]


def test_delete_of_the_last_list_is_refused() -> None:
    stack = TodoStack(lists=[make_list("Inbox")])

    assert stack.list_commands.delete("list-inbox", delete_tasks=True).error_codes == (
        ErrorCodeEnum.LIST_LAST_CANNOT_DELETE,
    )


def test_delete_reports_a_failure_to_delete_the_tasks() -> None:
    stack = TodoStack(tasks=[make_task(1, list_id=HOME_LIST_ID)])
    stack.task_writer.fail = True

    assert stack.list_commands.delete(HOME_LIST_ID, delete_tasks=True) == WRITE_FAILED
    assert _names(stack) == ["Work", "Home"]


def test_move_swaps_within_the_priority_group() -> None:
    stack = TodoStack(
        lists=[
            make_list("Work", priority=PriorityEnum.HIGH, position=0),
            make_list("Home", priority=PriorityEnum.NORMAL, position=1),
            make_list("Shop", priority=PriorityEnum.NORMAL, position=2),
        ]
    )

    assert stack.list_commands.move("list-shop", -1).is_success
    assert _names(stack) == ["Work", "Shop", "Home"]
    assert stack.events == [TaskListChangedEvent(list_ids=("list-shop", "list-home"))]
    assert stack.list_commands.move("list-shop", -1).is_skipped
    assert stack.list_commands.move("missing", 1).error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)


def test_queries_give_overviews_and_the_tasks_of_a_query() -> None:
    stack = TodoStack(
        tasks=[
            make_task(1, created_offset_minutes=1),
            make_task(2, state=TaskStateEnum.DONE, created_offset_minutes=2),
            make_task(3, state=TaskStateEnum.ARCHIVED, created_offset_minutes=3),
            make_task(4, list_id=HOME_LIST_ID),
            make_task(5, created_offset_minutes=5),
        ]
    )
    query = TaskQuery(
        list_id=WORK_LIST_ID, show_done=True, show_archived=False, sort_key=TaskSortKeyEnum.CREATED, descending=True
    )

    overviews = stack.queries.overviews()
    tasks = stack.queries.tasks(query, stack.clock.now_local())

    assert [(item.task_list.name, item.open_count) for item in overviews] == [("Work", 2), ("Home", 1)]
    assert [task.id for task in tasks] == ["task-005", "task-002", "task-001"]
    assert stack.queries.task_count(WORK_LIST_ID) == 4
    assert stack.queries.task_list(HOME_LIST_ID).is_success
