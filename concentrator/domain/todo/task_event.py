"""One event of the history of a task."""

from dataclasses import dataclass
from datetime import datetime
from typing import Final, Self

from concentrator.domain.todo.task_event_kind_enum import TaskEventKindEnum

DETAIL_FROM: Final = "from"
"""Previous value (list id, due date) of a ``MOVED`` or ``DUE_CHANGED`` event."""
DETAIL_TO: Final = "to"
"""New value (list id, due date) of a ``MOVED`` or ``DUE_CHANGED`` event."""
DETAIL_SOURCE: Final = "source"
"""Id of the task a ``COPIED_FROM`` event was copied from."""


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskEvent:
    """Something that happened to a task. Details never hold the text typed by the user.

    Attributes:
        at: Instant of the event, timezone-aware UTC.
        kind: What happened.
        details: Key-value pairs describing the change, in order (ids, ISO dates).
    """

    at: datetime
    kind: TaskEventKindEnum
    details: tuple[tuple[str, str], ...] = ()

    @classmethod
    def of(cls, at: datetime, kind: TaskEventKindEnum) -> Self:
        """Create an event without details.

        Args:
            at: Instant of the event (timezone-aware UTC).
            kind: What happened.

        Returns:
            The event.
        """
        return cls(at=at, kind=kind)

    def detail(self, key: str) -> str:
        """Read one detail.

        Args:
            key: Detail name.

        Returns:
            Its value, ``""`` when absent.
        """
        return next((value for name, value in self.details if name == key), "")
