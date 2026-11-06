import logging

import pytest

from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.shell.shell_page_enum import ShellPageEnum
from concentrator.presentation.shell.shell_presenter import ShellPresenter
from concentrator.presentation.shell.shell_snapshot import ShellSnapshot, StatusBarSnapshot
from tests.fakes.fake_clock import FakeClock
from tests.fakes.fake_translator import FakeTranslator
from tests.fakes.manual_scheduler import ManualScheduler

PRESENTER_LOGGER = "concentrator.presentation.shell.shell_presenter"


class _Harness:
    def __init__(self) -> None:
        self.translator = FakeTranslator()
        self.scheduler = ManualScheduler()
        self.coordinator = RenderCoordinator(self.scheduler)
        gate = ActionGate(FakeClock(), self.scheduler, self.coordinator, cooldown_ms=100, slow_threshold_ms=200)
        self.presenter = ShellPresenter(self.translator, gate, self.coordinator)
        self.shell: list[ShellSnapshot] = []
        self.status: list[StatusBarSnapshot] = []
        self.coordinator.register(RenderSectionEnum.SHELL, self.presenter.build_shell_snapshot, self.shell.append)
        self.coordinator.register(
            RenderSectionEnum.STATUS_BAR, self.presenter.build_status_bar_snapshot, self.status.append
        )

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


def test_initial_status_bar_shows_the_current_language(harness: _Harness) -> None:
    snapshot = harness.presenter.build_status_bar_snapshot()

    assert snapshot.save_state_text == "en:status.save.none"
    assert snapshot.language_button.text == "en:shell.language.button.en"
    assert snapshot.language_button.tooltip == "en:shell.language.tooltip.en"
    assert snapshot.language_button.action is ActionIdEnum.SHELL_TOGGLE_LANGUAGE
    assert snapshot.language_button.enabled


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


def test_language_toggle_switches_language_and_renders_every_section(harness: _Harness) -> None:
    harness.click(ActionIdEnum.SHELL_TOGGLE_LANGUAGE)

    assert harness.translator.language is LanguageEnum.FRENCH
    assert harness.shell[-1].window_title == "fr:app.title"
    assert harness.status[-1].language_button.text == "fr:shell.language.button.fr"
    assert not harness.status[-1].language_button.enabled

    harness.scheduler.advance(100)
    harness.click(ActionIdEnum.SHELL_TOGGLE_LANGUAGE)
    assert harness.translator.language is LanguageEnum.ENGLISH


def test_language_toggle_failure_is_logged_and_changes_nothing(
    harness: _Harness, caplog: pytest.LogCaptureFixture
) -> None:
    harness.translator.refused = frozenset({LanguageEnum.FRENCH})

    with caplog.at_level(logging.WARNING, logger=PRESENTER_LOGGER):
        harness.click(ActionIdEnum.SHELL_TOGGLE_LANGUAGE)

    assert harness.translator.language is LanguageEnum.ENGLISH
    assert "SHELL_TOGGLE_LANGUAGE failed" in caplog.records[0].getMessage()
    assert harness.shell == []


def test_unknown_action_value_is_logged_and_ignored(harness: _Harness, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger=PRESENTER_LOGGER):
        harness.presenter.on_action_requested(999)

    assert "UNKNOWN" in caplog.records[0].getMessage()
    assert harness.scheduler.pending_count == 0
