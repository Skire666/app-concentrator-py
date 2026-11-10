"""Builds the ``JOURNAL`` snapshot from the journal view."""

from typing import Final

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.presentation.common.action_button import action_button
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.button_snapshot import ButtonSnapshot
from concentrator.presentation.common.table_snapshot import TableSnapshot
from concentrator.presentation.common.ui_texts import UiTexts
from concentrator.presentation.journal.journal_entries import LEVEL_KEYS
from concentrator.presentation.journal.journal_filter import ALL_LEVELS, JournalEntry
from concentrator.presentation.journal.journal_snapshot import (
    JournalDetailSnapshot,
    JournalSnapshot,
    JournalToolbarSnapshot,
    LevelToggleSnapshot,
    SearchBoxSnapshot,
)
from concentrator.presentation.journal.journal_view import JournalView

COLUMN_KEYS: Final = (
    "journal.column.time",
    "journal.column.level",
    "journal.column.source",
    "journal.column.thread",
    "journal.column.message",
)


class JournalSnapshotBuilder:
    """Translates the view into the toolbar, table and detail snapshots."""

    def __init__(self, translator: TranslatorPort, gate: ActionGate, view: JournalView) -> None:
        """Create the builder.

        Args:
            translator: Current-language translator.
            gate: Busy state of the actions.
            view: Entries, filter and selection.
        """
        self._translator = translator
        self._texts = UiTexts(translator)
        self._gate = gate
        self._view = view

    def build(self, search_text: str) -> JournalSnapshot:
        """Describe the page.

        Args:
            search_text: Text of the search field, possibly not applied yet.

        Returns:
            The snapshot; rows are reused objects, so an unchanged table compares fast.
        """
        shown = self._view.mark_shown()
        return JournalSnapshot(toolbar=self._toolbar(search_text), table=self._table(shown), detail=self._detail())

    def _toolbar(self, search_text: str) -> JournalToolbarSnapshot:
        """Describe the toolbar.

        Args:
            search_text: Text of the search field.

        Returns:
            The toolbar snapshot.
        """
        journal_filter = self._view.filter
        paused = journal_filter.is_paused
        hidden = journal_filter.hidden_by_pause(self._view.entries)
        button = self._button
        return JournalToolbarSnapshot(
            levels=self._level_toggles(),
            search=SearchBoxSnapshot(
                text=search_text,
                placeholder=self._translator.tr("journal.search.placeholder"),
                tooltip=self._texts.action_tooltip(ActionIdEnum.JOURNAL_SEARCH),
            ),
            follow=button(ActionIdEnum.JOURNAL_TOGGLE_FOLLOW, checked=journal_filter.follow),
            pause=button(ActionIdEnum.JOURNAL_TOGGLE_PAUSE, checked=paused),
            paused_caption=self._translator.tr_plural("journal.paused", hidden) if paused else "",
            copy=button(ActionIdEnum.JOURNAL_COPY, enabled=bool(self._view.selected)),
            clear_view=button(ActionIdEnum.JOURNAL_CLEAR_VIEW),
            open_log_folder=button(ActionIdEnum.JOURNAL_OPEN_LOG_FOLDER),
        )

    def _button(self, action: ActionIdEnum, *, enabled: bool = True, checked: bool = False) -> ButtonSnapshot:
        """Describe a toolbar button.

        Args:
            action: Its action.
            enabled: Whether the current state allows it.
            checked: State of a checkable button.

        Returns:
            The button snapshot.
        """
        return action_button(self._texts, self._gate, action, enabled=enabled, checked=checked)

    def _level_toggles(self) -> tuple[LevelToggleSnapshot, ...]:
        """Describe the five level toggles with their counts.

        Returns:
            The toggles, from Debug to Critical.
        """
        journal_filter = self._view.filter
        counts = journal_filter.level_counts(self._view.entries)
        tr = self._translator.tr
        enabled = not self._gate.is_busy(ActionIdEnum.JOURNAL_TOGGLE_LEVEL)
        tooltip = self._texts.action_tooltip(ActionIdEnum.JOURNAL_TOGGLE_LEVEL)
        return tuple(
            LevelToggleSnapshot(
                level=int(level),
                text=tr("journal.level.count", level=tr(LEVEL_KEYS[level]), count=counts[level]),
                tooltip=tooltip,
                checked=level in journal_filter.levels,
                enabled=enabled,
            )
            for level in ALL_LEVELS
        )

    def _table(self, shown: tuple[JournalEntry, ...]) -> TableSnapshot:
        """Describe the table.

        Args:
            shown: Entries of the view.

        Returns:
            The table snapshot.
        """
        positions = {entry.sequence: index for index, entry in enumerate(shown)}
        journal_filter = self._view.filter
        return TableSnapshot(
            columns=tuple(self._translator.tr(key) for key in COLUMN_KEYS),
            rows=tuple(self._view.entries.row(entry) for entry in shown),
            selection=tuple(positions[sequence] for sequence in self._view.selected if sequence in positions),
            scroll_to_end=journal_filter.follow and not journal_filter.is_paused,
            empty_text=self._translator.tr("journal.empty"),
        )

    def _detail(self) -> JournalDetailSnapshot:
        """Describe the detail pane.

        Returns:
            The full text of the current entry.
        """
        entry = self._view.current_entry()
        text = "" if entry is None else self._view.entries.line(entry)
        return JournalDetailSnapshot(text=text, placeholder=self._translator.tr("journal.detail.placeholder"))
