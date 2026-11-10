import logging

import pytest
from PySide6.QtWidgets import QSplitter
from pytestqt.qtbot import QtBot

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.layout_keys import (
    LAYOUT_FOCUS_PAGE_SPLITTER,
    LAYOUT_JOURNAL_HEADER,
    LAYOUT_JOURNAL_SPLITTER,
    LAYOUT_MAIN_WINDOW_GEOMETRY,
    LAYOUT_TODO_HEADER,
    LAYOUT_TODO_LIST,
    LAYOUT_TODO_SPLITTER,
)
from tests.fakes.in_memory_view_preferences import InMemoryViewPreferences
from tests.fakes.storage_stack import DATA_PATH
from tests.fakes.user_data_factory import SAVED_AT, make_user_data
from tests.ui.shell_harness import ShellHarness

pytestmark = pytest.mark.ui
WINDOW_LOGGER = "concentrator.ui.windows.main_window"


@pytest.fixture
def harness(qtbot: QtBot) -> ShellHarness:
    built = ShellHarness()
    qtbot.addWidget(built.window)
    return built


def test_main_window_builds_with_the_first_render(harness: ShellHarness) -> None:
    window = harness.window

    assert window.windowTitle() == "en:app.title"
    assert window.current_page_index == 0
    assert window.focus_page.toolbar_panel.buttons[ActionIdEnum.TASK_NEW].text() == "en:action.task_new"
    assert window.timer_panel.digits.text() == "00:25:00"
    assert window.status_bar.language_button.text() == "en:shell.language.button.en"
    assert window.status_bar.save_state_text == "en:status.save.no_file"
    assert window.status_bar.instance_warning.isHidden()
    assert window.module_bar.button(ActionIdEnum.SHELL_SHOW_FOCUS).isChecked()
    assert not window.module_bar.button(ActionIdEnum.SHELL_SHOW_FOCUS).icon().isNull()


def test_module_bar_has_the_ini_width_and_the_full_window_height(qtbot: QtBot) -> None:
    harness = ShellHarness(module_bar_width_px=140)
    qtbot.addWidget(harness.window)
    harness.window.restore_layout()
    harness.window.show()
    qtbot.waitExposed(harness.window)

    assert harness.window.module_bar.width() == 140
    assert harness.window.module_bar.height() == harness.window.height()
    assert harness.window.status_bar.geometry().left() == 140


def test_clicking_a_module_button_switches_the_page(harness: ShellHarness) -> None:
    journal = harness.window.module_bar.button(ActionIdEnum.SHELL_SHOW_JOURNAL)

    journal.click()
    assert not journal.isChecked()
    harness.turn()

    assert harness.window.current_page_index == 1
    assert journal.isChecked()
    assert not harness.window.module_bar.button(ActionIdEnum.SHELL_SHOW_FOCUS).isChecked()


def test_clicking_the_active_module_button_keeps_it_checked(harness: ShellHarness) -> None:
    focus = harness.window.module_bar.button(ActionIdEnum.SHELL_SHOW_FOCUS)

    focus.click()
    harness.turn()
    harness.scheduler.advance(100)

    assert focus.isChecked()


def test_language_button_switches_every_text(harness: ShellHarness) -> None:
    harness.window.status_bar.language_button.click()
    harness.turn()

    window = harness.window
    assert window.status_bar.language_button.text() == "fr:shell.language.button.fr"
    assert window.windowTitle() == "fr:app.title"
    assert window.module_bar.button(ActionIdEnum.SHELL_SHOW_SETTINGS).text() == "fr:action.shell_show_settings"
    assert window.focus_page.toolbar_panel.buttons[ActionIdEnum.TASK_NEW].text() == "fr:action.task_new"
    assert window.timer_panel.buttons[2].text() == "fr:action.timer_start(minutes=5)"
    assert not window.status_bar.language_button.isEnabled()


def test_close_exports_the_layout_and_restore_reapplies_it(qtbot: QtBot, caplog: pytest.LogCaptureFixture) -> None:
    preferences = InMemoryViewPreferences()
    first = ShellHarness(preferences)
    qtbot.addWidget(first.window)
    first.window.restore_layout()
    first.window.resize(1000, 640)
    first.window.show()
    qtbot.waitExposed(first.window)
    splitter = first.window.findChild(QSplitter)
    assert splitter is not None
    splitter.setSizes([500, 400])
    moved_sizes = first.window.focus_page.splitter_sizes()

    first.window.close()

    assert set(preferences.values) == {
        LAYOUT_MAIN_WINDOW_GEOMETRY,
        LAYOUT_FOCUS_PAGE_SPLITTER,
        LAYOUT_JOURNAL_SPLITTER,
        LAYOUT_JOURNAL_HEADER,
        LAYOUT_TODO_SPLITTER,
        LAYOUT_TODO_HEADER,
        LAYOUT_TODO_LIST,
    }
    second = ShellHarness(preferences)
    qtbot.addWidget(second.window)
    with caplog.at_level(logging.WARNING, logger=WINDOW_LOGGER):
        second.window.restore_layout()
    second.window.show()
    qtbot.waitExposed(second.window)
    assert caplog.records == []
    assert second.window.size().toTuple() == (1000, 640)
    assert second.window.focus_page.splitter_sizes() == moved_sizes
    assert moved_sizes[0] / sum(moved_sizes) < 0.6  # not the 70 % default ratio


def test_first_run_uses_the_default_size_and_ratio(harness: ShellHarness) -> None:
    harness.window.restore_layout()

    assert harness.window.size().toTuple() == (1400, 860)


def test_invalid_saved_layout_falls_back_to_defaults_with_a_warning(
    qtbot: QtBot, caplog: pytest.LogCaptureFixture
) -> None:
    preferences = InMemoryViewPreferences(
        {LAYOUT_MAIN_WINDOW_GEOMETRY: "not base64!", LAYOUT_FOCUS_PAGE_SPLITTER: "AAAA"}
    )
    harness = ShellHarness(preferences)
    qtbot.addWidget(harness.window)

    with caplog.at_level(logging.WARNING, logger=WINDOW_LOGGER):
        harness.window.restore_layout()

    assert harness.window.size().toTuple() == (1400, 860)
    assert len(caplog.records) == 2


def test_bring_to_front_shows_a_minimized_window(qtbot: QtBot, harness: ShellHarness) -> None:
    harness.window.showMinimized()

    harness.window.bring_to_front()
    qtbot.waitExposed(harness.window)

    assert harness.window.isVisible()
    assert not harness.window.isMinimized()


def test_close_with_unsaved_changes_that_fail_keeps_the_window_open(qtbot: QtBot, harness: ShellHarness) -> None:
    stack = harness.stack
    stack.session.reset(make_user_data())
    stack.coordinator.attach(DATA_PATH, SAVED_AT)
    stack.session.change()
    stack.file.blocking_validation = ValidationResult.failure(ErrorCodeEnum.STORAGE_REPLACE_FAILED)
    stack.dialogs.confirm_answers = [True, False]
    harness.window.show()
    qtbot.waitExposed(harness.window)

    harness.window.close()

    assert harness.window.isVisible()
    titles = [texts[0] for texts in stack.dialogs.texts("confirm")]
    assert titles == ["en:shutdown.confirm.title", "en:shutdown.failed.title"]
    stack.dialogs.confirm_answer = True
    harness.window.close()
    assert not harness.window.isVisible()


def test_declining_the_quit_question_keeps_the_window_open(qtbot: QtBot, harness: ShellHarness) -> None:
    harness.stack.dialogs.confirm_answer = False
    harness.window.show()
    qtbot.waitExposed(harness.window)

    harness.window.close()

    assert harness.window.isVisible()
    assert harness.stack.dialogs.texts("confirm")[0][1] == "en:shutdown.confirm.message"
    harness.stack.dialogs.confirm_answer = True


def test_unguarded_mode_shows_the_indicator(qtbot: QtBot) -> None:
    harness = ShellHarness(protected=False)
    qtbot.addWidget(harness.window)

    assert harness.window.status_bar.instance_warning.text() == "en:status.instance.unguarded"
    assert not harness.window.status_bar.instance_warning.isHidden()
