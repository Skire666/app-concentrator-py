"""What the journal shows: levels, search, cleared entries, pause and follow (pure, no I/O)."""

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from typing import Final, Self

from concentrator.application.journal.journal_queries import JournalRecord
from concentrator.domain.settings.log_level_enum import LogLevelEnum
from concentrator.presentation.common.text_search import TextSearch, fold

ALL_LEVELS: Final = tuple(level for level in LogLevelEnum if level.is_set)
_SEARCHED_SEPARATOR: Final = "\n"


@dataclass(frozen=True, slots=True)
class JournalEntry:
    """A record with its searchable text folded once.

    Attributes:
        record: The record.
        searchable: Folded message and source.
    """

    record: JournalRecord
    searchable: str

    @classmethod
    def of(cls, record: JournalRecord) -> Self:
        """Prepare a record for searching.

        Args:
            record: Record read from the log buffer.

        Returns:
            The entry.
        """
        return cls(record=record, searchable=fold(record.message + _SEARCHED_SEPARATOR + record.source))

    @property
    def sequence(self) -> int:
        """Sequence number of the record."""
        return self.record.sequence

    @property
    def level(self) -> LogLevelEnum:
        """Level of the record."""
        return self.record.level


@dataclass(frozen=True, slots=True, kw_only=True)
class JournalFilter:
    """The view of the journal, changed by the toolbar.

    Attributes:
        levels: Levels shown.
        search: Text every shown entry contains (message or source).
        cleared_through: Entries up to this sequence are hidden ("Clear view").
        paused_at: While paused, entries after this sequence are hidden and counted.
        follow: Whether the table keeps the newest entry in view.
    """

    levels: frozenset[LogLevelEnum] = frozenset(ALL_LEVELS)
    search: TextSearch = field(default_factory=TextSearch)
    cleared_through: int = 0
    paused_at: int | None = None
    follow: bool = True

    @property
    def is_paused(self) -> bool:
        """Whether the view is frozen."""
        return self.paused_at is not None

    def with_level(self, level: LogLevelEnum, *, shown: bool) -> Self:
        """Show or hide one level.

        Args:
            level: Level.
            shown: Whether its entries are shown.

        Returns:
            The changed filter.
        """
        levels = self.levels | {level} if shown else self.levels - {level}
        return replace(self, levels=levels)

    def with_search(self, query: str) -> Self:
        """Search another text.

        Args:
            query: Text typed by the user.

        Returns:
            The changed filter.
        """
        return replace(self, search=TextSearch.parse(query))

    def cleared(self, last_sequence: int) -> Self:
        """Hide every entry received so far.

        Args:
            last_sequence: Sequence of the newest entry received.

        Returns:
            The changed filter.
        """
        return replace(self, cleared_through=max(self.cleared_through, last_sequence))

    def paused(self, last_sequence: int) -> Self:
        """Freeze the view at the newest entry received.

        Args:
            last_sequence: Sequence of the newest entry received.

        Returns:
            The paused filter (unchanged when already paused).
        """
        return self if self.is_paused else replace(self, paused_at=last_sequence)

    def resumed(self) -> Self:
        """Show the entries received while paused again.

        Returns:
            The running filter.
        """
        return replace(self, paused_at=None)

    def with_follow(self, follow: bool) -> Self:
        """Turn following the newest entry on or off.

        Args:
            follow: New state.

        Returns:
            The changed filter.
        """
        return replace(self, follow=follow)

    def in_scope(self, entry: JournalEntry) -> bool:
        """Tell whether an entry is after the cleared ones and matches the search, whatever its level.

        Args:
            entry: Entry to check.

        Returns:
            Whether the level counters include it (when not hidden by the pause).
        """
        return entry.sequence > self.cleared_through and self.search.matches(entry.searchable)

    def shows(self, entry: JournalEntry) -> bool:
        """Tell whether an entry is in the view.

        Args:
            entry: Entry to check.

        Returns:
            Whether the table shows it.
        """
        return entry.level in self.levels and self.in_scope(entry) and not self.held_back(entry)

    def held_back(self, entry: JournalEntry) -> bool:
        """Tell whether the pause hides an entry.

        Args:
            entry: Entry to check.

        Returns:
            Whether it arrived after the view was frozen.
        """
        return self.paused_at is not None and entry.sequence > self.paused_at

    def visible(self, entries: Iterable[JournalEntry]) -> tuple[JournalEntry, ...]:
        """Return the entries of the view, oldest first.

        Args:
            entries: Every entry received, oldest first.

        Returns:
            The shown entries.
        """
        return tuple(entry for entry in entries if self.shows(entry))

    def level_counts(self, entries: Iterable[JournalEntry]) -> Counter[LogLevelEnum]:
        """Count the entries of each level the view would show if every level were checked.

        Args:
            entries: Every entry received.

        Returns:
            The count of each level.
        """
        return Counter(entry.level for entry in entries if self.in_scope(entry) and not self.held_back(entry))

    def hidden_by_pause(self, entries: Iterable[JournalEntry]) -> int:
        """Count the entries received while paused that the view would show.

        Args:
            entries: Every entry received.

        Returns:
            The count, 0 when not paused.
        """
        if self.paused_at is None:
            return 0
        return sum(
            1 for entry in entries if entry.level in self.levels and self.in_scope(entry) and self.held_back(entry)
        )
