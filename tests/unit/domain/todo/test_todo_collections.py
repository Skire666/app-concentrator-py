from datetime import UTC, date, datetime, time

import pytest

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.todo.priority_enum import PriorityEnum
from concentrator.domain.todo.task_lists_collection import TaskListsCollection
from concentrator.domain.todo.task_sort_key_enum import TaskSortKeyEnum
from concentrator.domain.todo.task_state_enum import TaskStateEnum
from concentrator.domain.todo.tasks_collection import TasksCollection
from tests.fakes.todo_factory import HOME_LIST_ID, make_list, make_lists, make_task, make_tasks

NOW = datetime(2026, 11, 10, 9, 30, tzinfo=UTC)


def _names(lists: TaskListsCollection) -> list[str]:
    return [item.name for item in lists]


def _ids(tasks: TasksCollection) -> list[str]:
    return [task.id for task in tasks]


def _spec_lists() -> TaskListsCollection:
    return make_lists(
        make_list("Ideas", priority=PriorityEnum.LOW, position=0),
        make_list("Home", priority=PriorityEnum.NORMAL, position=1),
        make_list("Work", priority=PriorityEnum.HIGH, position=2),
        make_list("Shop", priority=PriorityEnum.NORMAL, position=3),
        make_list("Fire", priority=PriorityEnum.URGENT, position=4),
    )


def test_lists_are_ordered_by_priority_then_position() -> None:
    lists = _spec_lists()

    assert _names(lists.ordered()) == ["Fire", "Work", "Home", "Shop", "Ideas"]
    first = lists.first()
    assert first is not None
    assert first.name == "Fire"
    assert TaskListsCollection().first() is None


def test_next_position_follows_the_highest() -> None:
    assert _spec_lists().next_position() == 5
    assert TaskListsCollection().next_position() == 0


@pytest.mark.parametrize("typed", ["work", "WORK", "  Work  ", "Work"])
def test_name_lookup_ignores_case_and_spaces(typed: str) -> None:
    found = _spec_lists().with_name(typed)

    assert found is not None
    assert found.name == "Work"
    assert _spec_lists().with_name(typed, except_id="list-work") is None


def test_neighbor_stays_within_the_priority_group() -> None:
    lists = _spec_lists()

    after_home = lists.neighbor("list-home", 1)
    assert after_home is not None
    assert after_home.name == "Shop"
    assert lists.neighbor("list-home", -1) is None
    assert lists.neighbor("list-fire", -1) is None
    assert lists.neighbor("missing", 1) is None


def test_moved_swaps_and_renumbers_the_positions() -> None:
    moved = _spec_lists().moved("list-shop", -1, NOW)

    assert moved.data is not None
    ordered = moved.data.ordered()
    assert _names(ordered) == ["Fire", "Work", "Shop", "Home", "Ideas"]
    assert [item.position for item in ordered] == [0, 1, 2, 3, 4]
    assert all(item.updated_at == NOW for item in moved.data)


def test_moved_keeps_updated_at_of_lists_whose_position_does_not_change() -> None:
    lists = make_lists(make_list("A", position=0), make_list("B", position=1), make_list("C", position=2))

    moved = lists.moved("list-c", -1, NOW)

    assert moved.data is not None
    assert {item.name for item in moved.data if item.updated_at == NOW} == {"B", "C"}


def test_moved_at_the_edge_is_skipped_and_unknown_is_not_found() -> None:
    assert _spec_lists().moved("list-home", -1, NOW).validation.is_skipped
    assert _spec_lists().moved("missing", 1, NOW).validation.error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)


def _sortable_tasks() -> TasksCollection:
    return make_tasks(
        make_task(1, text="banana", state=TaskStateEnum.DONE, due_date=date(2026, 11, 12), created_offset_minutes=2),
        make_task(2, text="Apple", due_date=date(2026, 11, 11), due_time=time(9, 0), created_offset_minutes=1),
        make_task(3, text="cherry", state=TaskStateEnum.ARCHIVED),
        make_task(4, text="apple", due_date=date(2026, 11, 11), created_offset_minutes=1),
    )


@pytest.mark.parametrize(
    ("key", "ascending"),
    [
        (TaskSortKeyEnum.STATE, ["task-002", "task-004", "task-001", "task-003"]),
        (TaskSortKeyEnum.TEXT, ["task-002", "task-004", "task-001", "task-003"]),
        (TaskSortKeyEnum.DUE, ["task-002", "task-004", "task-001", "task-003"]),
        (TaskSortKeyEnum.CREATED, ["task-003", "task-002", "task-004", "task-001"]),
        (TaskSortKeyEnum.UPDATED, ["task-003", "task-002", "task-004", "task-001"]),
        (TaskSortKeyEnum.UNKNOWN, ["task-003", "task-002", "task-004", "task-001"]),
    ],
)
def test_tasks_sort_by_each_key_and_break_ties_by_id(key: TaskSortKeyEnum, ascending: list[str]) -> None:
    tasks = _sortable_tasks()

    assert _ids(tasks.ordered_by(key, descending=False)) == ascending
    if key is not TaskSortKeyEnum.DUE:
        assert _ids(tasks.ordered_by(key, descending=True)) == list(reversed(ascending))


def test_tasks_without_due_date_stay_last_in_both_orders() -> None:
    tasks = _sortable_tasks()

    assert _ids(tasks.ordered_by(TaskSortKeyEnum.DUE, descending=True)) == [
        "task-001",
        "task-004",
        "task-002",
        "task-003",
    ]


def test_in_list_with_states_and_open_counts() -> None:
    tasks = make_tasks(make_task(1), make_task(2, state=TaskStateEnum.DONE), make_task(3, list_id=HOME_LIST_ID))

    assert _ids(tasks.in_list(HOME_LIST_ID)) == ["task-003"]
    assert _ids(tasks.with_states({TaskStateEnum.DONE})) == ["task-002"]
    assert tasks.open_counts() == {"list-work": 1, HOME_LIST_ID: 1}


def test_replace_all_is_all_or_nothing() -> None:
    tasks = make_tasks(make_task(1), make_task(2))
    changed = make_task(2, text="changed")

    replaced = tasks.with_replaced_all([changed])
    refused = tasks.with_replaced_all([changed, make_task(9)])

    assert replaced.data is not None
    assert replaced.data.items == (make_task(1), changed)
    assert refused.validation.error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)


def test_without_all_is_all_or_nothing() -> None:
    tasks = make_tasks(make_task(1), make_task(2), make_task(3))

    removed = tasks.without_all(["task-001", "task-003"])

    assert removed.data is not None
    assert _ids(removed.data) == ["task-002"]
    assert tasks.without_all(["task-001", "task-009"]).validation.error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)
