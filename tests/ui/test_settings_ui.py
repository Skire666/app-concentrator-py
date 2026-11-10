import pytest
from pytestqt.qtbot import QtBot

from concentrator.domain.settings.log_level_enum import LogLevelEnum
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.layout_keys import LAYOUT_MAIN_WINDOW_GEOMETRY
from concentrator.presentation.settings.settings_folder_enum import SettingsFolderEnum
from tests.fakes.settings_stack import ABOUT
from tests.ui.shell_harness import ShellHarness

pytestmark = pytest.mark.ui


@pytest.fixture
def harness(qtbot: QtBot) -> ShellHarness:
    built = ShellHarness()
    qtbot.addWidget(built.window)
    built.window.module_bar.button(ActionIdEnum.SHELL_SHOW_SETTINGS).click()
    built.turn()
    return built


def test_settings_page_shows_the_stored_values_and_the_paths(harness: ShellHarness) -> None:
    page = harness.window.settings_page

    assert harness.window.current_page_index == 2
    assert page.form.language.count() == 2
    assert page.form.language.currentIndex() == 0
    assert page.form.log_level.currentIndex() == 1
    assert page.form.notify.isChecked()
    assert not page.form.chime_enabled.isChecked()
    assert page.form.chime_fields.start_hour.currentIndex() == 8
    assert not page.footer.save_button.isEnabled()
    assert not page.footer.status
    assert [row.path for row in page.files.about_paths] == [
        ABOUT.app_config_file.as_posix(),
        ABOUT.ui_state_file.as_posix(),
        ABOUT.log_dir.as_posix(),
        ABOUT.backup_dir.as_posix(),
    ]
    assert not page.files.data_path.path


def test_a_change_enables_save_and_save_stores_it(harness: ShellHarness) -> None:
    page = harness.window.settings_page

    page.form.log_level.setCurrentIndex(0)
    page.form.chime_enabled.click()
    harness.turn()
    assert page.footer.status == "en:settings.unsaved"
    assert page.footer.save_button.isEnabled()

    page.footer.save_button.click()
    harness.turn()

    assert harness.stack.settings.settings.log_level is LogLevelEnum.DEBUG
    assert harness.timer.chime_queries.enabled()
    assert not page.footer.save_button.isEnabled()


def test_revert_restores_the_fields(harness: ShellHarness) -> None:
    page = harness.window.settings_page
    page.form.notify.click()
    harness.turn()

    page.footer.revert_button.click()
    harness.turn()

    assert page.form.notify.isChecked()
    assert not page.footer.revert_button.isEnabled()


def test_leaving_with_changes_can_be_cancelled(harness: ShellHarness) -> None:
    harness.window.settings_page.form.language.setCurrentIndex(1)
    harness.turn()
    harness.scheduler.advance(100)
    harness.stack.dialogs.choice = 2

    harness.window.module_bar.button(ActionIdEnum.SHELL_SHOW_FOCUS).click()
    harness.turn()

    assert harness.window.current_page_index == 2
    assert harness.stack.dialogs.texts("choose")[0][0] == "en:settings.leave.title"


def test_open_folder_and_reset_layout_buttons(harness: ShellHarness) -> None:
    page = harness.window.settings_page
    harness.preferences.values[LAYOUT_MAIN_WINDOW_GEOMETRY] = "AA=="

    page.files.about_paths[2].open_button.click()
    harness.turn()
    page.files.buttons()[2].click()
    harness.turn()

    assert harness.settings.opener.opened == [(ABOUT.log_dir, True)]
    assert LAYOUT_MAIN_WINDOW_GEOMETRY not in harness.preferences.values
    assert harness.settings.layout_resets == 1
    assert int(SettingsFolderEnum.LOG) == 4


def test_chime_fields_of_the_page_edit_the_draft(harness: ShellHarness) -> None:
    fields = harness.window.settings_page.form.chime_fields

    fields.start_hour.setCurrentIndex(22)
    harness.turn()

    assert fields.end_hour_error.text() == "en:error.chime_hours_reversed"
    assert not harness.window.settings_page.footer.save_button.isEnabled()
