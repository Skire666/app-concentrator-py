"""The journal presenter wired with fakes, like bootstrap does."""

from pathlib import Path
from typing import Final

from concentrator.application.journal.journal_queries import JournalQueries
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.layout_state_keeper import LayoutStateKeeper
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.journal.journal_presenter import JournalPorts, JournalPresenter, JournalSettings
from concentrator.presentation.journal.journal_snapshot import JournalSnapshot
from concentrator.presentation.shell.shell_page_enum import ShellPageEnum
from tests.fakes.fake_clock import FakeClock
from tests.fakes.fake_desktop import FakeClipboard, FakeLinkOpener
from tests.fakes.fake_log_feed import FakeLogFeed
from tests.fakes.fake_translator import FakeTranslator
from tests.fakes.in_memory_view_preferences import InMemoryViewPreferences
from tests.fakes.manual_scheduler import ManualScheduler

LOG_DIR: Final = Path("C:/Users/me/AppData/Local/Concentrator/logs")
DEBOUNCE_MS: Final = 150
COOLDOWN_MS: Final = 100


class JournalStack:
    """Renders ``JOURNAL`` into ``journal`` and ``SHELL`` (a counter) into ``shell``."""

    def __init__(
        self,
        *,
        capacity: int = 1000,
        copy_max_rows: int = 2000,
        preferences: dict[str, str] | None = None,
        feed: FakeLogFeed | None = None,
    ) -> None:
        self.feed = feed or FakeLogFeed(capacity)
        self.clock = FakeClock()
        self.scheduler = ManualScheduler()
        self.translator = FakeTranslator(LanguageEnum.ENGLISH)
        self.renderer = RenderCoordinator(self.scheduler)
        self.gate = ActionGate(
            self.clock, self.scheduler, self.renderer, cooldown_ms=COOLDOWN_MS, slow_threshold_ms=200
        )
        self.preferences = InMemoryViewPreferences(preferences)
        self.clipboard = FakeClipboard()
        self.opener = FakeLinkOpener()
        self.presenter = JournalPresenter(
            self.translator,
            self.gate,
            self.renderer,
            JournalPorts(
                queries=JournalQueries(self.feed),
                clock=self.clock,
                scheduler=self.scheduler,
                clipboard=self.clipboard,
                opener=self.opener,
                layout=LayoutStateKeeper(self.preferences),
            ),
            JournalSettings(
                log_dir=LOG_DIR, capacity=capacity, search_debounce_ms=DEBOUNCE_MS, copy_max_rows=copy_max_rows
            ),
        )
        self.journal: list[JournalSnapshot] = []
        self.shell: list[int] = []
        self.renderer.register(RenderSectionEnum.JOURNAL, self.presenter.build_snapshot, self.journal.append)
        self.renderer.register(RenderSectionEnum.SHELL, self.presenter.badge_count, self.shell.append)

    @property
    def last(self) -> JournalSnapshot:
        return self.journal[-1]

    def show(self, page: ShellPageEnum = ShellPageEnum.JOURNAL) -> None:
        self.presenter.on_page_changed(page)
        self.scheduler.run_pending()

    def tick(self) -> None:
        self.presenter.on_tick()
        self.scheduler.run_pending()

    def settle(self) -> None:
        """Let the gate cooldown and the search debounce pass."""
        self.scheduler.advance(max(COOLDOWN_MS, DEBOUNCE_MS) * 3)

    def messages(self) -> list[str]:
        return [row.cells[4] for row in self.last.table.rows]
