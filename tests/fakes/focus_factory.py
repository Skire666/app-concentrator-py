"""Focus queue items for tests."""

from datetime import UTC, datetime, timedelta
from typing import Final

from concentrator.domain.focus.focus_item import FocusItem, FocusItemId
from concentrator.domain.focus.focus_items_collection import FocusItemsCollection
from concentrator.domain.focus.focus_limits import FocusLimits
from concentrator.domain.todo.task import TaskId

FOCUS_CREATED_AT: Final = datetime(2026, 11, 6, 17, 10, tzinfo=UTC)
FOCUS_LIMITS: Final = FocusLimits(max_items=20)


def make_item(number: int, task_number: int | None = None, *, position: int | None = None) -> FocusItem:
    """An item ``item-<number:03d>`` queuing ``task-<task_number:03d>`` (same number by default)."""
    created = FOCUS_CREATED_AT + timedelta(minutes=number)
    return FocusItem(
        id=FocusItemId(f"item-{number:03d}"),
        created_at=created,
        updated_at=created,
        task_id=TaskId(f"task-{(task_number if task_number is not None else number):03d}"),
        position=number if position is None else position,
    )


def make_queue(*task_numbers: int) -> FocusItemsCollection:
    """A queue of the given tasks, in that order (item number = task number)."""
    return FocusItemsCollection(make_item(number, position=position) for position, number in enumerate(task_numbers))
