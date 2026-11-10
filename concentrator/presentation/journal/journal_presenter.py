"""Journal page (Menu B): live log entries with level filters, search, follow, pause and copy."""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from concentrator.application.journal.journal_queries import JournalQueries
from concentrator.application.ports.clock_port import ClockPort
from concentrator.application.ports.link_opener_port import LinkOpenerPort
from concentrator.application.ports.scheduler_port import ScheduledCallPort, SchedulerPort
from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.settings.log_level_enum import LogLevelEnum
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.layout_state_keeper import LayoutStateKeeper
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.journal.journal_filter import JournalFilter
from concentrator.presentation.journal.journal_snapshot import JournalSnapshot
from concentrator.presentation.journal.journal_snapshot_builder import JournalSnapshotBuilder
from concentrator.presentation.journal.journal_view import JournalView
from concentrator.presentation.ports.clipboard_port import ClipboardPort
from concentrator.presentation.shell.shell_page_enum import ShellPageEnum

_logger = logging.getLogger(__name__)

LINE_BREAK: Final = "\n"


@dataclass(frozen=True, slots=True, kw_only=True)
class JournalPorts:
    """What the journal reads and drives.

    Attributes:
        queries: Log records.
        clock: Local time of the records.
        scheduler: Search debounce.
        clipboard: Copy.
        opener: Opens the log folder.
        layout: Persisted filters (``layout/journal_page/*``).
    """

    queries: JournalQueries
    clock: ClockPort
    scheduler: SchedulerPort
    clipboard: ClipboardPort
    opener: LinkOpenerPort
    layout: LayoutStateKeeper


@dataclass(frozen=True, slots=True, kw_only=True)
class JournalSettings:
    """Values of ``concentrator.ini`` used by the journal.

    Attributes:
        log_dir: ``paths.log_dir``.
        capacity: ``logging.journal_buffer_size``.
        search_debounce_ms: ``journal.search_debounce_ms``.
        copy_max_rows: ``journal.copy_max_rows``.
    """

    log_dir: Path
    capacity: int
    search_debounce_ms: int
    copy_max_rows: int


class JournalPresenter:
    """Builds ``JOURNAL``; reads the log buffer on each tick while the page is shown.

    While the page is hidden, only the number of ERROR and CRITICAL records is read, for the badge of
    the Journal button: errors logged since the journal was last shown, or since the start. Nothing on
    the tick and render path writes to the log: at DEBUG level the journal would otherwise feed on its
    own records.
    """

    def __init__(
        self,
        translator: TranslatorPort,
        gate: ActionGate,
        renderer: RenderCoordinator,
        ports: JournalPorts,
        settings: JournalSettings,
    ) -> None:
        """Create the presenter; the persisted level toggles and Follow are loaded.

        Args:
            translator: Current-language translator.
            gate: Runs every user action.
            renderer: Receives the render requests (``JOURNAL``, and ``SHELL`` for the badge).
            ports: Records, clock, scheduler, clipboard, folder opener and layout store.
            settings: Values of ``concentrator.ini``.
        """
        self._gate = gate
        self._renderer = renderer
        self._ports = ports
        self._settings = settings
        self._view = JournalView(settings.capacity, translator, ports.clock, ports.layout)
        self._builder = JournalSnapshotBuilder(translator, gate, self._view)
        self._visible = False
        self._errors_seen = 0
        self._badge = 0
        self._search_text = ""
        self._search_call: ScheduledCallPort | None = None
        self._actions: dict[ActionIdEnum, Callable[[], ValidationResult]] = {
            ActionIdEnum.JOURNAL_TOGGLE_FOLLOW: self._toggle_follow,
            ActionIdEnum.JOURNAL_TOGGLE_PAUSE: self._toggle_pause,
            ActionIdEnum.JOURNAL_COPY: self._copy,
            ActionIdEnum.JOURNAL_CLEAR_VIEW: self._clear_view,
            ActionIdEnum.JOURNAL_OPEN_LOG_FOLDER: self._open_log_folder,
        }

    def badge_count(self) -> int:
        """Return the number of ERROR and CRITICAL records logged while the page was hidden.

        Returns:
            The count, 0 while the page is shown.
        """
        return self._badge

    def on_tick(self) -> None:
        """Read the new records while the page is shown, else only check for new errors."""
        if self._visible:
            self._read_new_records()
            return
        badge = self._ports.queries.error_count() - self._errors_seen
        if badge != self._badge:
            self._badge = badge
            self._renderer.request(RenderSectionEnum.SHELL)

    def on_page_changed(self, page: ShellPageEnum) -> None:
        """Start or stop reading the log buffer when the journal is shown or hidden.

        Args:
            page: Page now shown.
        """
        self._visible = page is ShellPageEnum.JOURNAL
        if not self._visible:
            return
        if self._badge:
            self._badge = 0
            self._renderer.request(RenderSectionEnum.SHELL)
        self._read_new_records()
        self._renderer.request(RenderSectionEnum.JOURNAL)

    def build_snapshot(self) -> JournalSnapshot:
        """Describe the page.

        Returns:
            The snapshot.
        """
        return self._builder.build(self._search_text)

    def on_action_requested(self, action_value: int) -> None:
        """Handle a toolbar button.

        Args:
            action_value: ``ActionIdEnum`` value emitted by the panel.
        """
        action = ActionIdEnum.parse(action_value)
        operation = self._actions.get(action)
        if operation is None:
            _logger.warning("Journal action %s (%d) is not handled", action.name, action_value)
            return
        result = self._gate.run(action, operation)
        if result.is_failure:
            _logger.warning("Journal action %s: %s", action.name, [code.name for code in result.error_codes])
        self._renderer.request(RenderSectionEnum.JOURNAL)

    def on_level_toggled(self, level_value: int) -> None:
        """Show or hide the entries of a level.

        Args:
            level_value: ``LogLevelEnum`` value of the clicked toggle.
        """
        level = LogLevelEnum.parse(level_value)
        if level.is_set:
            self._gate.run(ActionIdEnum.JOURNAL_TOGGLE_LEVEL, lambda: self._toggle_level(level))
        self._renderer.request(RenderSectionEnum.JOURNAL)

    def on_search_changed(self, text: str) -> None:
        """Apply a search ``journal.search_debounce_ms`` after the last key press.

        Args:
            text: Text of the search field.
        """
        self._search_text = text
        if self._search_call is not None:
            self._search_call.cancel()
        self._search_call = self._ports.scheduler.call_later(self._settings.search_debounce_ms, self._apply_search)

    def on_selection_changed(self, rows: tuple[int, ...], current: int) -> None:
        """Remember the selected entries; the detail pane shows the current one.

        Args:
            rows: Indices of the selected rows in the last rendered table.
            current: Index of the current row, -1 for none.
        """
        self._view.select(rows, current)
        self._renderer.request(RenderSectionEnum.JOURNAL)

    def reset_layout(self) -> None:
        """Show every level and follow the newest entry again ("Reset layout" removed the stored ones)."""
        current = self._view.filter
        self._set_filter(JournalFilter(search=current.search, cleared_through=current.cleared_through))

    def _read_new_records(self) -> None:
        """Append the records logged since the last read and re-render when there are some."""
        records = self._ports.queries.records_since(self._view.entries.last_sequence)
        self._errors_seen = self._ports.queries.error_count()
        if self._view.add(records):
            self._renderer.request(RenderSectionEnum.JOURNAL)

    def _set_filter(self, journal_filter: JournalFilter) -> None:
        """Change the view.

        Args:
            journal_filter: New filter.
        """
        self._view.set_filter(journal_filter)
        self._renderer.request(RenderSectionEnum.JOURNAL)

    def _toggle_level(self, level: LogLevelEnum) -> ValidationResult:
        """Show or hide a level.

        Args:
            level: Clicked level.

        Returns:
            Success.
        """
        current = self._view.filter
        self._set_filter(current.with_level(level, shown=level not in current.levels))
        return ValidationResult.success()

    def _toggle_follow(self) -> ValidationResult:
        """Turn Follow on or off.

        Returns:
            Success.
        """
        self._set_filter(self._view.filter.with_follow(not self._view.filter.follow))
        return ValidationResult.success()

    def _toggle_pause(self) -> ValidationResult:
        """Freeze the view, or show the entries received meanwhile.

        Returns:
            Success.
        """
        current = self._view.filter
        last = self._view.entries.last_sequence
        self._set_filter(current.resumed() if current.is_paused else current.paused(last))
        return ValidationResult.success()

    def _clear_view(self) -> ValidationResult:
        """Hide the entries received so far (the log files are not touched).

        Returns:
            Success.
        """
        self._set_filter(self._view.filter.cleared(self._view.entries.last_sequence))
        return ValidationResult.success()

    def _copy(self) -> ValidationResult:
        """Put the selected entries in the clipboard, at most ``journal.copy_max_rows`` (the newest).

        Returns:
            Success, or skipped without selection.
        """
        entries = self._view.selected_entries()
        if not entries:
            return ValidationResult.skipped()
        kept = entries[-self._settings.copy_max_rows :]
        self._ports.clipboard.set_text(LINE_BREAK.join(self._view.entries.line(entry) for entry in kept))
        return ValidationResult.success()

    def _open_log_folder(self) -> ValidationResult:
        """Open the folder of the log files (created first when missing).

        Returns:
            The opener result (a refusal is a logged warning).
        """
        return self._ports.opener.open_folder(self._settings.log_dir, create_missing=True)

    def _apply_search(self) -> None:
        """Apply the typed search, or try again later while the previous search is cooling down."""
        self._search_call = None
        if self._gate.is_busy(ActionIdEnum.JOURNAL_SEARCH):
            self._search_call = self._ports.scheduler.call_later(self._settings.search_debounce_ms, self._apply_search)
            return
        text = self._search_text
        self._gate.run(ActionIdEnum.JOURNAL_SEARCH, lambda: self._search(text))

    def _search(self, text: str) -> ValidationResult:
        """Filter the entries with a search text.

        Args:
            text: Text typed by the user.

        Returns:
            Success.
        """
        if text != self._view.filter.search.query:
            self._set_filter(self._view.filter.with_search(text))
        return ValidationResult.success()
