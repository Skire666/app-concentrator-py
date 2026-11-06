"""Thread-safe bounded buffer of recent log records, read by the journal page."""

import logging
import threading
from collections import deque
from datetime import UTC, datetime
from typing import Final, override

from concentrator.application.ports.log_feed_port import LogEntry, LogFeedPort

_MESSAGE_ONLY: Final = "%(message)s"


class RingBufferHandler(logging.Handler, LogFeedPort):
    """Keeps the last ``capacity`` records with strictly increasing sequence numbers."""

    def __init__(self, capacity: int) -> None:
        """Create an empty buffer.

        Args:
            capacity: Maximum number of records kept (``logging.journal_buffer_size``).
        """
        super().__init__()
        self.setFormatter(logging.Formatter(_MESSAGE_ONLY))
        self._entries: deque[LogEntry] = deque(maxlen=capacity)
        self._sequence = 0
        self._buffer_lock = threading.Lock()

    @override
    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
        except (TypeError, ValueError, KeyError) as error:  # malformed %-arguments in a log call
            message = f"<unformattable log message {record.msg!r}: {error}>"
        with self._buffer_lock:
            self._sequence += 1
            self._entries.append(
                LogEntry(
                    sequence=self._sequence,
                    created_at=datetime.fromtimestamp(record.created, UTC),
                    level=record.levelno,
                    level_name=record.levelname,
                    logger_name=record.name,
                    thread_name=record.threadName or "",
                    message=message,
                )
            )

    @override
    def entries_since(self, sequence: int) -> tuple[LogEntry, ...]:
        with self._buffer_lock:
            return tuple(entry for entry in self._entries if entry.sequence > sequence)
