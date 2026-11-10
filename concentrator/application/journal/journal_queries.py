"""Read use cases of the journal page: the recent log records."""

from dataclasses import dataclass
from datetime import datetime
from typing import Self

from concentrator.application.journal.log_levels import log_level_of
from concentrator.application.ports.log_feed_port import LogEntry, LogFeedPort
from concentrator.domain.settings.log_level_enum import LogLevelEnum


@dataclass(frozen=True, slots=True, kw_only=True)
class JournalRecord:
    """One log record as the journal shows it.

    Attributes:
        sequence: Strictly increasing number, starting at 1.
        created_at: Instant of the record, timezone-aware UTC (milliseconds kept).
        level: Severity.
        source: Name of the emitting logger.
        thread: Name of the emitting thread.
        message: Full message, including the traceback when there is one.
    """

    sequence: int
    created_at: datetime
    level: LogLevelEnum
    source: str
    thread: str
    message: str

    @classmethod
    def from_entry(cls, entry: LogEntry) -> Self:
        """Convert a record of the feed.

        Args:
            entry: Record of the in-memory buffer.

        Returns:
            The journal record.
        """
        return cls(
            sequence=entry.sequence,
            created_at=entry.created_at,
            level=log_level_of(entry.level),
            source=entry.logger_name,
            thread=entry.thread_name,
            message=entry.message,
        )


class JournalQueries:
    """Reads the in-memory log buffer (every record since the start, up to ``logging.journal_buffer_size``)."""

    def __init__(self, feed: LogFeedPort) -> None:
        """Create the queries.

        Args:
            feed: The in-memory buffer.
        """
        self._feed = feed

    def records_since(self, sequence: int) -> tuple[JournalRecord, ...]:
        """Return the retained records newer than a sequence number.

        Args:
            sequence: Last sequence already read, 0 for everything retained.

        Returns:
            The records, oldest first.
        """
        return tuple(JournalRecord.from_entry(entry) for entry in self._feed.entries_since(sequence))

    def error_count(self) -> int:
        """Return how many ERROR and CRITICAL records were logged since the start.

        Returns:
            The count; it only grows.
        """
        return self._feed.error_count()
