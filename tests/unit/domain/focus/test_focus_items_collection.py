from datetime import UTC, datetime

from concentrator.domain.focus.focus_items_collection import FocusItemsCollection
from tests.fakes.focus_factory import make_item, make_queue

NOW = datetime(2026, 11, 11, 9, 0, tzinfo=UTC)


def _tasks(queue: FocusItemsCollection) -> list[str]:
    return [item.task_id for item in queue.ordered()]


def test_ordered_sorts_by_position() -> None:
    queue = FocusItemsCollection((make_item(1, position=2), make_item(2, position=0), make_item(3, position=1)))

    assert _tasks(queue) == ["task-002", "task-003", "task-001"]


def test_next_position_is_zero_when_empty_and_after_the_last_otherwise() -> None:
    assert FocusItemsCollection().next_position() == 0
    assert make_queue(4, 5).next_position() == 2


def test_task_lookup_finds_the_item_of_a_task() -> None:
    queue = make_queue(1, 2)

    assert queue.task_ids() == {"task-001", "task-002"}
    assert queue.contains_task("task-002")
    assert not queue.contains_task("task-003")
    found = queue.item_of_task("task-002")
    assert found is not None
    assert found.id == "item-002"
    assert queue.item_of_task("task-009") is None


def test_without_tasks_removes_and_renumbers() -> None:
    queue = make_queue(1, 2, 3)

    changed = queue.without_tasks(["task-001", "task-404"], NOW)

    assert _tasks(changed) == ["task-002", "task-003"]
    assert [item.position for item in changed.ordered()] == [0, 1]
    assert all(item.updated_at == NOW for item in changed)


def test_moved_down_and_up_swaps_with_the_neighbour() -> None:
    queue = make_queue(1, 2, 3)

    assert _tasks(queue.moved("item-001", 1, NOW)) == ["task-002", "task-001", "task-003"]
    assert _tasks(queue.moved("item-003", -1, NOW)) == ["task-001", "task-003", "task-002"]


def test_moved_at_both_ends_changes_nothing() -> None:
    queue = make_queue(1, 2, 3)

    top = queue.moved("item-001", -1, NOW)
    bottom = queue.moved("item-003", 1, NOW)

    assert _tasks(top) == ["task-001", "task-002", "task-003"]
    assert _tasks(bottom) == ["task-001", "task-002", "task-003"]
    assert all(item.updated_at != NOW for item in top)


def test_moved_unknown_item_returns_the_same_queue() -> None:
    queue = make_queue(1, 2)

    assert queue.moved("item-404", 1, NOW) is queue


def test_can_move_is_false_at_the_ends_and_for_unknown_items() -> None:
    queue = make_queue(1, 2, 3)

    assert queue.can_move("item-002", -1)
    assert queue.can_move("item-002", 1)
    assert not queue.can_move("item-001", -1)
    assert not queue.can_move("item-003", 1)
    assert not queue.can_move("item-404", 1)
    assert not queue.can_move("item-002", 0)
