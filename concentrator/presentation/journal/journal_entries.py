"""Entries received by the journal page, with their table rows built once per entry and language."""

from collections import deque
from collections.abc import Iterator
from datetime import datetime
from types import MappingProxyType
from typing import Final

from concentrator.application.journal.journal_queries import JournalRecord
from concentrator.application.ports.clock_port import ClockPort
from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.domain.settings.log_level_enum import LogLevelEnum
from concentrator.presentation.common.date_time_formatter import DateTimeFormatter
from concentrator.presentation.common.row_tone_enum import RowToneEnum
from concentrator.presentation.common.table_snapshot import TableRowSnapshot
from concentrator.presentation.journal.journal_filter import JournalEntry

LEVEL_KEYS: Final = MappingProxyType(
    {
        LogLevelEnum.DEBUG: "journal.level.debug",
        LogLevelEnum.INFO: "journal.level.info",
        LogLevelEnum.WARNING: "journal.level.warning",
        LogLevelEnum.ERROR: "journal.level.error",
        LogLevelEnum.CRITICAL: "journal.level.critical",
    }
)
_TONES: Final = MappingProxyType(
    {
        LogLevelEnum.DEBUG: RowToneEnum.MUTED,
        LogLevelEnum.WARNING: RowToneEnum.WARNING,
        LogLevelEnum.ERROR: RowToneEnum.ERROR,
        LogLevelEnum.CRITICAL: RowToneEnum.ERROR,
    }
)
LINE_TEMPLATE: Final = "{timestamp}.{milliseconds:03d} | {level:<8} | {thread} | {source} | {message}"
TIMESTAMP_FORMAT: Final = "%Y-%m-%d %H:%M:%S"
_MICROSECONDS_PER_MILLISECOND: Final = 1000
_LINE_BREAK: Final = "\n"


def entry_line(record: JournalRecord, local: datetime) -> str:
    """Write a record as a line of the log file (technical, English, language independent).

    Args:
        record: Record to write.
        local: Its instant in local time.

    Returns:
        The text; a multi-line message keeps its lines (traceback).
    """
    return LINE_TEMPLATE.format(
        timestamp=local.strftime(TIMESTAMP_FORMAT),
        milliseconds=local.microsecond // _MICROSECONDS_PER_MILLISECOND,
        level=record.level.name,
        thread=record.thread,
        source=record.source,
        message=record.message,
    )


class JournalEntries:
    """Keeps at most ``capacity`` entries, oldest first, like the log buffer it reads."""

    def __init__(self, capacity: int, translator: TranslatorPort, clock: ClockPort) -> None:
        """Create an empty store.

        Args:
            capacity: ``logging.journal_buffer_size``.
            translator: Level names and time template of the rows.
            clock: Local time of the records.
        """
        self._entries: deque[JournalEntry] = deque()
        self._by_sequence: dict[int, JournalEntry] = {}
        self._rows: dict[int, TableRowSnapshot] = {}
        self._rows_language = LanguageEnum.UNSET
        self._capacity = capacity
        self._translator = translator
        self._clock = clock
        self._formatter = DateTimeFormatter(translator, clock)

    def __iter__(self) -> Iterator[JournalEntry]:
        """Iterate over the entries, oldest first.

        Returns:
            The iterator.
        """
        return iter(self._entries)

    @property
    def last_sequence(self) -> int:
        """Sequence of the newest entry, 0 before the first one."""
        return self._entries[-1].sequence if self._entries else 0

    def add(self, records: tuple[JournalRecord, ...]) -> None:
        """Append new records; the oldest entries go when the capacity is reached.

        Args:
            records: Records newer than ``last_sequence``, oldest first.
        """
        for record in records:
            entry = JournalEntry.of(record)
            self._entries.append(entry)
            self._by_sequence[entry.sequence] = entry
        while len(self._entries) > self._capacity:
            dropped = self._entries.popleft()
            del self._by_sequence[dropped.sequence]
            self._rows.pop(dropped.sequence, None)

    def find(self, sequence: int) -> JournalEntry | None:
        """Return the entry of a sequence.

        Args:
            sequence: Sequence number.

        Returns:
            The entry, ``None`` when it is gone or never came.
        """
        return self._by_sequence.get(sequence)

    def row(self, entry: JournalEntry) -> TableRowSnapshot:
        """Return the table row of an entry, the same object while the language does not change.

        Args:
            entry: An entry of this store.

        Returns:
            The row: time, level, source, thread and first line of the message.
        """
        language = self._translator.language
        if language is not self._rows_language:
            self._rows.clear()
            self._rows_language = language
        row = self._rows.get(entry.sequence)
        if row is None:
            row = self._build_row(entry.record)
            self._rows[entry.sequence] = row
        return row

    def line(self, entry: JournalEntry) -> str:
        """Return the full text of an entry, as in the log file.

        Args:
            entry: An entry of this store.

        Returns:
            The text.
        """
        return entry_line(entry.record, self._clock.to_local(entry.record.created_at))

    def _build_row(self, record: JournalRecord) -> TableRowSnapshot:
        """Build the row of a record.

        Args:
            record: Record.

        Returns:
            The row.
        """
        lines = record.message.split(_LINE_BREAK)
        message = lines[0] if len(lines) == 1 else self._translator.tr("journal.message.more_lines", text=lines[0])
        level = self._translator.tr(LEVEL_KEYS.get(record.level, "journal.level.info"))
        return TableRowSnapshot(
            key=record.sequence,
            cells=(
                self._formatter.time_with_milliseconds(record.created_at),
                level,
                record.source,
                record.thread,
                message,
            ),
            tone=_TONES.get(record.level, RowToneEnum.NORMAL),
        )
