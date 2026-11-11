"""One entry of the focus queue: a reference to a task."""

from dataclasses import dataclass, replace
from datetime import datetime
from typing import NewType, Self

from concentrator.domain.todo.task import TaskId

FocusItemId = NewType("FocusItemId", str)


@dataclass(frozen=True, slots=True, kw_only=True)
class FocusItem:
    """A queued task (``[[focus_queue]]``, ADR-013); checked by ``FocusRules``.

    Attributes:
        id: UUIDv7 identifying the item.
        created_at: Instant the task was queued, timezone-aware UTC.
        updated_at: Last change instant (a move), timezone-aware UTC.
        task_id: The queued task.
        position: Order in the queue (lowest first).
    """

    id: FocusItemId
    created_at: datetime
    updated_at: datetime
    task_id: TaskId
    position: int

    @classmethod
    def create(cls, new_id: FocusItemId, now: datetime, *, task_id: TaskId, position: int) -> Self:
        """Queue a task.

        Args:
            new_id: Id from ``IdGeneratorPort``.
            now: Creation instant (timezone-aware UTC).
            task_id: The task to queue.
            position: Order in the queue (``FocusItemsCollection.next_position()`` for the end).

        Returns:
            The item; validate the addition with ``FocusRules``.
        """
        return cls(id=new_id, created_at=now, updated_at=now, task_id=task_id, position=position)

    def with_position(self, position: int, now: datetime) -> Self:
        """Return a copy at another position.

        Args:
            position: New order.
            now: Change instant (timezone-aware UTC).

        Returns:
            The moved item, or this item when the position is the same.
        """
        if position == self.position:
            return self
        return replace(self, position=position, updated_at=now)
