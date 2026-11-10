import logging

import pytest

from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.shell.shell_page_enum import ShellPageEnum
from concentrator.presentation.shell.shell_presenter import ShellPresenter
from concentrator.presentation.shell.shell_snapshot import ShellSnapshot
from tests.fakes.fake_clock import FakeClock
from tests.fakes.fake_translator import FakeTranslator
from tests.fakes.manual_scheduler import ManualScheduler

PRESENTER_LOGGER = "concentrator.presentation.shell.shell_presenter"


class _Harness:
    def __init__(self) -> None:
        self.translator = FakeTranslator()
        self.scheduler = ManualScheduler()
        self.coordinator = RenderCoordinator(self.scheduler)
        self.gate = ActionGate(FakeClock(), self.scheduler, self.coordinator, cooldown_ms=100, slow_threshold_ms=200)
        self.presenter = ShellPresenter(self.translator, self.gate, self.coordinator)
        self.shell: list[ShellSnapshot] = []
        self.status: list[object] = []
        self.coordinator.register(RenderSectionEnum.SHELL, self.presenter.build_shell_snapshot, self.shell.append)
        self.coordinator.register(RenderSectionEnum.STATUS_BAR, lambda: len(self.status), self.status.append)

    def click(self, action: ActionIdEnum) -> None:
        self.presenter.on_action_requested(int(action))
        self.scheduler.run_pending()


@pytest.fixture
def harness() -> _Harness:
    return _Harness()


def test_initial_shell_snapshot_shows_the_focus_page(harness: _Harness) -> None:
    snapshot = harness.presenter.build_shell_snapshot()

    assert snapshot.window_title == "en:app.title"
    assert snapshot.active_page_index == 0
    assert [button.text for button in snapshot.module_buttons] == [
        "en:action.shell_show_focus",
        "en:action.shell_show_journal",
        "en:action.shell_show_settings",
    ]
    assert [button.checked for button in snapshot.module_buttons] == [True, False, False]
    assert all(button.enabled and not button.highlighted for button in snapshot.module_buttons)
    assert snapshot.module_buttons[0].tooltip == "en:action.shell_show_focus.tooltip"
    assert snapshot.focus_zone1_placeholder == "en:placeholder.focus.zone1"


def test_module_action_switches_page_and_renders_the_shell_only(harness: _Harness) -> None:
    harness.click(ActionIdEnum.SHELL_SHOW_JOURNAL)

    assert harness.presenter.active_page is ShellPageEnum.JOURNAL
    assert harness.status == []
    last = harness.shell[-1]
    assert last.active_page_index == 1
    assert [button.checked for button in last.module_buttons] == [False, True, False]
    assert not last.module_buttons[1].enabled


def test_busy_module_button_is_enabled_again_after_the_cooldown(harness: _Harness) -> None:
    harness.click(ActionIdEnum.SHELL_SHOW_SETTINGS)

    harness.scheduler.advance(100)

    assert harness.shell[-1].active_page_index == 2
    assert all(button.enabled for button in harness.shell[-1].module_buttons)


def test_showing_the_active_page_again_changes_nothing(harness: _Harness) -> None:
    harness.click(ActionIdEnum.SHELL_SHOW_FOCUS)

    assert harness.presenter.active_page is ShellPageEnum.FOCUS
    assert harness.shell[-1].active_page_index == 0


def test_language_toggle_is_not_a_shell_action(harness: _Harness, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger=PRESENTER_LOGGER):
        harness.click(ActionIdEnum.SHELL_TOGGLE_LANGUAGE)

    assert harness.translator.language is LanguageEnum.ENGLISH
    assert "not handled" in caplog.records[0].getMessage()


def test_unknown_action_value_is_logged_and_ignored(harness: _Harness, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger=PRESENTER_LOGGER):
        harness.presenter.on_action_requested(999)

    assert "UNKNOWN" in caplog.records[0].getMessage()
    assert harness.scheduler.pending_count == 0


class _Badge:
    def __init__(self) -> None:
        self.count = 0

    def __call__(self) -> int:
        return self.count


def _badged(count: int) -> tuple[_Harness, _Badge]:
    harness = _Harness()
    badge = _Badge()
    badge.count = count
    harness.presenter = ShellPresenter(harness.translator, harness.gate, harness.coordinator, journal_badge=badge)
    return harness, badge


@pytest.mark.parametrize(("count", "text"), [(0, ""), (1, "1"), (99, "99"), (100, "en:shell.badge.overflow(max=99)")])
def test_journal_button_shows_the_number_of_new_errors(count: int, text: str) -> None:
    harness, _badge = _badged(count)

    journal = harness.presenter.build_shell_snapshot().module_buttons[1]

    assert journal.badge == text
    assert ("en:shell.journal.badge.tooltip" in journal.tooltip) is (count > 0)
    assert journal.tooltip.startswith("en:action.shell_show_journal.tooltip")


def test_journal_page_itself_shows_no_badge() -> None:
    harness, _badge = _badged(3)

    harness.presenter.show_page(ShellPageEnum.JOURNAL)

    assert not harness.presenter.build_shell_snapshot().module_buttons[1].badge


def test_page_listeners_learn_the_page_shown(harness: _Harness) -> None:
    pages: list[ShellPageEnum] = []
    harness.presenter.add_page_listener(pages.append)

    harness.click(ActionIdEnum.SHELL_SHOW_SETTINGS)
    harness.scheduler.advance(100)
    harness.click(ActionIdEnum.SHELL_SHOW_SETTINGS)

    assert pages == [ShellPageEnum.SETTINGS]


def test_leave_guard_can_keep_the_page(harness: _Harness) -> None:
    answers = [False, True]
    pages: list[ShellPageEnum] = []
    harness.presenter.add_page_listener(pages.append)
    harness.presenter.show_page(ShellPageEnum.SETTINGS)
    harness.presenter.set_leave_guard(ShellPageEnum.SETTINGS, lambda: answers.pop(0))

    assert harness.presenter.show_page(ShellPageEnum.FOCUS).is_skipped
    assert harness.presenter.active_page is ShellPageEnum.SETTINGS
    assert harness.presenter.show_page(ShellPageEnum.FOCUS).is_success
    assert pages == [ShellPageEnum.SETTINGS, ShellPageEnum.FOCUS]
