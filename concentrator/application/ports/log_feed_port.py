"""Read access to recent application log records (journal page)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True, kw_only=True)
class LogEntry:
    """One formatted log record.

    Attributes:
        sequence: Strictly increasing number, starting at 1.
        created_at: Instant of the record, timezone-aware UTC.
        level: Numeric ``logging`` level.
        level_name: Level name such as ``INFO``.
        logger_name: Name of the emitting logger.
        thread_name: Name of the emitting thread.
        message: Formatted message, including the traceback when there is one.
    """

    sequence: int
    created_at: datetime
    level: int
    level_name: str
    logger_name: str
    thread_name: str
    message: str


class LogFeedPort(Protocol):
    """Bounded in-memory feed of the most recent log records."""

    def entries_since(self, sequence: int) -> tuple[LogEntry, ...]:
        """Return the retained records newer than a sequence number.

        Args:
            sequence: Last sequence already seen, 0 for everything retained.

        Returns:
            Records with ``entry.sequence > sequence``, oldest first.
        """
        ...

    def error_count(self) -> int:
        """Return how many ERROR and CRITICAL records were emitted since the start, retained or not.

        Returns:
            The count; it only grows, so comparing two values tells whether errors arrived.
        """
        ...
