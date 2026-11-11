"""The focus queue, ordered by position."""

from collections.abc import Iterable
from datetime import datetime
from typing import Final, Self

from concentrator.domain.common.entity_collection import EntityCollection
from concentrator.domain.focus.focus_item import FocusItem

FIRST_POSITION: Final = 0


class FocusItemsCollection(EntityCollection[FocusItem]):
    """Group logic of the queue: order, task lookup, moves.

    Every change renumbers the positions ``0, 1, 2...`` in queue order, so the stored positions stay
    dense. ``FocusRules`` checks the capacity, the duplicates and the task state before an addition.
    """

    def ordered(self) -> Self:
        """Sort by position (stable: equal positions keep the stored order).

        Returns:
            The items in queue order.
        """
        return self.sorted_by(lambda item: item.position)

    def next_position(self) -> int:
        """Return the position of an item added at the end.

        Returns:
            One more than the highest position, ``0`` when empty.
        """
        return max((item.position for item in self), default=FIRST_POSITION - 1) + 1

    def task_ids(self) -> frozenset[str]:
        """Ids of the queued tasks.

        Returns:
            The ids.
        """
        return frozenset(item.task_id for item in self)

    def contains_task(self, task_id: str) -> bool:
        """Tell whether a task is queued.

        Args:
            task_id: Task id.

        Returns:
            Whether an item references it.
        """
        return any(item.task_id == task_id for item in self)

    def item_of_task(self, task_id: str) -> FocusItem | None:
        """Find the item of a task.

        Args:
            task_id: Task id.

        Returns:
            The item, ``None`` when the task is not queued.
        """
        return next((item for item in self if item.task_id == task_id), None)

    def without_tasks(self, task_ids: Iterable[str], now: datetime) -> Self:
        """Remove the items of some tasks and renumber the others.

        Args:
            task_ids: Tasks to remove (tasks not queued are ignored).
            now: Change instant of the renumbered items.

        Returns:
            The new queue.
        """
        removed = set(task_ids)
        kept = self.ordered().filtered(lambda item: item.task_id not in removed)
        return kept.renumbered(now)

    def moved(self, item_id: str, offset: int, now: datetime) -> Self:
        """Move an item up (negative offset) or down, stopping at both ends.

        Args:
            item_id: Item to move (an unknown id changes nothing).
            offset: Number of places, negative to move up.
            now: Change instant of the items that change position.

        Returns:
            The new queue, renumbered.
        """
        items = list(self.ordered())
        index = next((position for position, item in enumerate(items) if item.id == item_id), None)
        if index is None:
            return self
        target = max(FIRST_POSITION, min(len(items) - 1, index + offset))
        items.insert(target, items.pop(index))
        return type(self)(items).renumbered(now)

    def renumbered(self, now: datetime) -> Self:
        """Number the positions ``0, 1, 2...`` in the current order.

        Args:
            now: Change instant of the items whose position changes.

        Returns:
            The renumbered queue.
        """
        return self._with_items(item.with_position(position, now) for position, item in enumerate(self))

    def can_move(self, item_id: str, offset: int) -> bool:
        """Tell whether a move would change the order.

        Args:
            item_id: Item to move.
            offset: Number of places, negative to move up.

        Returns:
            Whether the item exists and is not already at that end.
        """
        ids: list[str] = [item.id for item in self.ordered()]
        if item_id not in ids:
            return False
        index = ids.index(item_id)
        return FIRST_POSITION <= index + offset < len(ids) and offset != 0
