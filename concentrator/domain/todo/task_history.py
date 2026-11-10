"""The events of one task, oldest first, capped in size."""

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Final, Self

from concentrator.domain.todo.task_event import TaskEvent
from concentrator.domain.todo.task_event_kind_enum import TaskEventKindEnum

ORIGIN_KINDS: Final = frozenset({TaskEventKindEnum.CREATED, TaskEventKindEnum.COPIED_FROM})
"""Kinds of the first event of a task, kept when the history is capped."""


@dataclass(frozen=True, slots=True)
class TaskHistory:
    """Immutable list of events. When it grows past the cap, the origin event stays with the newest ones.

    The origin is the first event when it is ``CREATED`` (or ``COPIED_FROM`` for a duplicate, whose history
    restarts with that event).

    Attributes:
        events: The events, oldest first.
    """

    events: tuple[TaskEvent, ...] = ()

    @classmethod
    def started(cls, event: TaskEvent) -> Self:
        """Start a history.

        Args:
            event: First event (``CREATED`` or ``COPIED_FROM``).

        Returns:
            The history with one event.
        """
        return cls((event,))

    @classmethod
    def capped(cls, events: Iterable[TaskEvent], max_events: int) -> Self:
        """Build a history and drop the oldest events beyond the cap (the origin event is kept).

        Args:
            events: Events, oldest first.
            max_events: Most events kept (``todo.max_history_events``).

        Returns:
            The history.
        """
        items = tuple(events)
        if len(items) <= max_events:
            return cls(items)
        if items[0].kind in ORIGIN_KINDS:
            newest = items[len(items) - max_events + 1 :] if max_events > 1 else ()
            return cls((items[0], *newest))
        return cls(items[len(items) - max_events :])

    def with_event(self, event: TaskEvent, max_events: int) -> Self:
        """Append an event and apply the cap.

        Args:
            event: New event.
            max_events: Most events kept.

        Returns:
            The new history.
        """
        return type(self).capped((*self.events, event), max_events)

    @property
    def last(self) -> TaskEvent | None:
        """Newest event, ``None`` when empty."""
        return self.events[-1] if self.events else None

    def __len__(self) -> int:
        """Number of events.

        Returns:
            The count.
        """
        return len(self.events)

    def __iter__(self) -> Iterator[TaskEvent]:
        """Iterate over the events, oldest first.

        Returns:
            The iterator.
        """
        return iter(self.events)
