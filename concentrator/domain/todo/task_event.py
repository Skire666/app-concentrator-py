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
"""Id of the task a ``COPIED_FROM`` event was copied from; ``SOURCE_FOCUS`` on a completion made from the queue."""
SOURCE_FOCUS: Final = "focus"
"""Value of ``source`` on a ``COMPLETED`` or ``OCCURRENCE_COMPLETED`` event made from the focus queue."""
DETAIL_REASON: Final = "reason"
"""``FocusRemovalReasonEnum`` value (as text) of a ``REMOVED_FROM_FOCUS`` event."""
DETAIL_OCCURRENCE: Final = "occurrence"
"""Number of the occurrence an ``OCCURRENCE_COMPLETED`` event completed (1 for the first)."""
DETAIL_DUE: Final = "due"
"""Due date (ISO) of the occurrence an ``OCCURRENCE_COMPLETED`` event completed."""
DETAIL_NEXT: Final = "next"
"""Next due date (ISO) of an ``OCCURRENCE_COMPLETED`` event; absent when the series ended."""
DETAIL_SKIPPED: Final = "skipped"
"""Past dates passed over by an ``OCCURRENCE_COMPLETED`` event; absent when none was."""


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskEvent:
    """Something that happened to a task. Details never hold the text typed by the user.

    Attributes:
        at: Instant of the event, timezone-aware UTC.
        kind: What happened.
        details: Key-value pairs describing the change, in order (ids, ISO dates, numbers).
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
