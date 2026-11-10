"""Log feed fake: ``log`` adds a record like ``RingBufferHandler`` does, bounded by ``capacity``."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Final, override

from concentrator.application.ports.log_feed_port import LogEntry, LogFeedPort

FIRST_RECORD_AT: Final = datetime(2026, 11, 6, 9, 0, 0, 250_000, tzinfo=UTC)


class FakeLogFeed(LogFeedPort):
    """Counts ``reads`` (calls of ``entries_since``) and ``error_reads``."""

    def __init__(self, capacity: int = 1000) -> None:
        self.capacity = capacity
        self.entries: list[LogEntry] = []
        self.sequence = 0
        self.errors = 0
        self.reads = 0
        self.error_reads = 0

    def log(
        self,
        message: str = "message",
        level: int = logging.INFO,
        *,
        source: str = "concentrator.test",
        thread: str = "MainThread",
    ) -> LogEntry:
        self.sequence += 1
        entry = LogEntry(
            sequence=self.sequence,
            created_at=FIRST_RECORD_AT + timedelta(seconds=self.sequence),
            level=level,
            level_name=logging.getLevelName(level),
            logger_name=source,
            thread_name=thread,
            message=message,
        )
        self.entries.append(entry)
        del self.entries[: -self.capacity]
        if level >= logging.ERROR:
            self.errors += 1
        return entry

    def log_many(self, count: int, level: int = logging.INFO) -> None:
        for index in range(count):
            self.log(f"message {index}", level)

    @override
    def entries_since(self, sequence: int) -> tuple[LogEntry, ...]:
        self.reads += 1
        return tuple(entry for entry in self.entries if entry.sequence > sequence)

    @override
    def error_count(self) -> int:
        self.error_reads += 1
        return self.errors
