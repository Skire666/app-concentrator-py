"""State of the journal page: entries received, filter, selection, and the view they give."""

from concentrator.application.journal.journal_queries import JournalRecord
from concentrator.application.ports.clock_port import ClockPort
from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.presentation.common.layout_state_keeper import LayoutStateKeeper
from concentrator.presentation.journal.journal_entries import JournalEntries
from concentrator.presentation.journal.journal_filter import JournalEntry, JournalFilter
from concentrator.presentation.journal.journal_filter_store import JournalFilterStore


class JournalView:
    """Filters the entries once per change; the selection is kept by sequence number."""

    def __init__(self, capacity: int, translator: TranslatorPort, clock: ClockPort, layout: LayoutStateKeeper) -> None:
        """Create the view with the persisted level toggles and Follow.

        Args:
            capacity: ``logging.journal_buffer_size``.
            translator: Texts of the rows.
            clock: Local time of the rows.
            layout: ``layout/journal_page/*`` keys.
        """
        self.entries = JournalEntries(capacity, translator, clock)
        self._store = JournalFilterStore(layout)
        self._filter = self._store.load()
        self._visible: tuple[JournalEntry, ...] | None = None
        self._shown: tuple[JournalEntry, ...] = ()
        self._selected: tuple[int, ...] = ()
        self._current = 0

    @property
    def filter(self) -> JournalFilter:
        """Current filter."""
        return self._filter

    @property
    def selected(self) -> tuple[int, ...]:
        """Sequences of the selected entries."""
        return self._selected

    def add(self, records: tuple[JournalRecord, ...]) -> bool:
        """Append new records.

        Args:
            records: Records newer than the last one received.

        Returns:
            Whether there were any.
        """
        if not records:
            return False
        self.entries.add(records)
        self._visible = None
        return True

    def set_filter(self, journal_filter: JournalFilter) -> None:
        """Change the filter and store its persisted part.

        Args:
            journal_filter: New filter.
        """
        self._filter = journal_filter
        self._visible = None
        self._store.save(journal_filter)

    def visible(self) -> tuple[JournalEntry, ...]:
        """Return the entries of the view, filtered once per change.

        Returns:
            The shown entries, oldest first.
        """
        if self._visible is None:
            self._visible = self._filter.visible(self.entries)
        return self._visible

    def mark_shown(self) -> tuple[JournalEntry, ...]:
        """Return the view and remember it as the table being rendered (selection indices refer to it).

        Returns:
            The shown entries.
        """
        self._shown = self.visible()
        return self._shown

    def select(self, rows: tuple[int, ...], current: int) -> None:
        """Remember a selection made in the rendered table.

        Args:
            rows: Indices of the selected rows.
            current: Index of the current row, -1 for none.
        """
        shown = self._shown
        self._selected = tuple(shown[index].sequence for index in rows if 0 <= index < len(shown))
        self._current = shown[current].sequence if 0 <= current < len(shown) else 0

    def selected_entries(self) -> list[JournalEntry]:
        """Return the selected entries of the view, oldest first.

        Returns:
            The entries.
        """
        selected = set(self._selected)
        return [entry for entry in self.visible() if entry.sequence in selected]

    def current_entry(self) -> JournalEntry | None:
        """Return the entry shown in the detail pane.

        Returns:
            The current entry, ``None`` without one.
        """
        return self.entries.find(self._current)
