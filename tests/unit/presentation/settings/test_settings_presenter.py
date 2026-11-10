from dataclasses import replace

import pytest

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.domain.settings.log_level_enum import LogLevelEnum
from concentrator.domain.timer.volume import Volume
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.shell.shell_page_enum import ShellPageEnum
from tests.fakes.settings_stack import SettingsStack
from tests.fakes.timer_extras_factory import DEFAULT_CHIME_SETTINGS

SAVE = int(ActionIdEnum.SETTINGS_SAVE)
REVERT = int(ActionIdEnum.SETTINGS_REVERT)


@pytest.fixture
def stack() -> SettingsStack:
    return SettingsStack()


def test_form_shows_the_stored_values_with_save_and_revert_disabled(stack: SettingsStack) -> None:
    form = stack.render().form

    assert form.general.title == "en:settings.section.general"
    assert form.general.language.selected == 0
    assert form.general.language.options == ("en:settings.language.en", "en:settings.language.fr")
    assert form.general.log_level.selected == 1
    assert form.general.log_level.options[0] == "en:journal.level.debug"
    assert form.general.notify_when_inactive.checked
    assert not form.chime.enabled.checked
    assert (form.chime.fields.hours.start, form.chime.fields.hours.end) == (8, 20)
    assert not form.status
    assert not form.save.enabled
    assert not form.revert.enabled


def test_a_change_enables_save_and_revert(stack: SettingsStack) -> None:
    stack.presenter.on_log_level_selected(0)

    form = stack.render().form

    assert form.general.log_level.selected == 0
    assert form.status == "en:settings.unsaved"
    assert form.save.enabled
    assert form.revert.enabled
    assert stack.presenter.has_unsaved_edits()


def test_revert_shows_the_stored_values_again(stack: SettingsStack) -> None:
    stack.presenter.on_language_selected(1)
    stack.presenter.on_volume_changed(10)

    stack.click(REVERT)

    assert not stack.presenter.has_unsaved_edits()
    assert stack.last.form.general.language.selected == 0
    assert stack.last.form.chime.fields.volume.value == 60


def test_reversed_chime_hours_show_an_inline_error_and_block_saving(stack: SettingsStack) -> None:
    stack.presenter.on_start_hour_changed(21)

    form = stack.render().form

    assert form.chime.fields.hours.end_error == "en:error.chime_hours_reversed"
    assert not form.save.enabled
    assert form.revert.enabled


def test_save_writes_each_part_once_and_applies_the_language(stack: SettingsStack) -> None:
    stack.presenter.on_language_selected(1)
    stack.presenter.on_log_level_selected(0)
    stack.presenter.on_notify_toggled(False)
    stack.presenter.on_chime_enabled_toggled(True)
    stack.presenter.on_end_hour_changed(22)

    stack.click(SAVE)

    stored = stack.storage.settings.settings
    assert stack.storage.settings.updates == 1
    assert (stored.language, stored.log_level, stored.notify_when_inactive) == (
        LanguageEnum.FRENCH,
        LogLevelEnum.DEBUG,
        False,
    )
    assert len(stack.timer.chime.updates) == 1
    assert stack.timer.chime_queries.enabled()
    assert stack.timer.chime_queries.settings().end_hour == 22
    assert stack.storage.translator.language is LanguageEnum.FRENCH
    assert not stack.presenter.has_unsaved_edits()
    assert stack.last.form.general.title == "fr:settings.section.general"


def test_save_of_the_general_part_only_leaves_the_chime_alone(stack: SettingsStack) -> None:
    stack.presenter.on_log_level_selected(2)

    stack.click(SAVE)

    assert stack.storage.settings.updates == 1
    assert stack.timer.chime.updates == []
    assert stack.storage.translator.language is LanguageEnum.ENGLISH


def test_save_failure_is_shown_and_keeps_the_changes(stack: SettingsStack) -> None:
    stack.storage.settings.write_failure = ValidationResult.failure(ErrorCodeEnum.STORAGE_WRITE_FAILED)
    stack.presenter.on_log_level_selected(0)

    stack.click(SAVE)

    assert stack.dialogs.texts("error")[0][:2] == ("en:settings.error.title", "en:error.storage_write_failed")
    assert stack.presenter.has_unsaved_edits()
    assert stack.timer.chime.updates == []


def test_save_without_change_is_skipped(stack: SettingsStack) -> None:
    assert stack.presenter.save_edits().is_skipped


def test_language_changed_from_the_status_bar_keeps_the_other_edits(stack: SettingsStack) -> None:
    stack.render()
    stack.presenter.on_log_level_selected(3)

    stack.storage.switcher.toggle()
    form = stack.render().form

    assert form.general.language.selected == 1
    assert form.general.log_level.selected == 3
    assert stack.presenter.has_unsaved_edits()


def test_chime_changed_in_its_dialog_is_followed(stack: SettingsStack) -> None:
    stack.render()

    stack.timer.chime_commands.update_settings(replace(DEFAULT_CHIME_SETTINGS, volume=Volume(15)))

    assert stack.render().form.chime.fields.volume.value == 15
    assert not stack.presenter.has_unsaved_edits()


@pytest.mark.parametrize(("choice", "leaves", "saved"), [(0, True, 1), (1, True, 0), (2, False, 0)])
def test_leaving_with_changes_asks_save_discard_or_cancel(
    stack: SettingsStack, choice: int, leaves: bool, saved: int
) -> None:
    stack.presenter.on_log_level_selected(0)
    stack.dialogs.choice = choice

    assert stack.presenter.may_leave() is leaves

    assert stack.dialogs.texts("choose")[0] == (
        "en:settings.leave.title",
        "en:settings.leave.message",
        "en:dialog.button.save",
        "en:dialog.button.discard",
        "en:dialog.button.cancel",
    )
    assert stack.storage.settings.updates == saved
    assert stack.presenter.has_unsaved_edits() is (choice == 2)


def test_leaving_without_changes_asks_nothing(stack: SettingsStack) -> None:
    assert stack.presenter.may_leave()
    assert stack.dialogs.calls == []


def test_preview_plays_the_draft_and_stops_when_the_page_is_left(stack: SettingsStack) -> None:
    stack.presenter.on_volume_changed(42)

    stack.click(int(ActionIdEnum.SETTINGS_CHIME_PREVIEW))
    stack.presenter.on_page_changed(ShellPageEnum.SETTINGS)
    stops = stack.timer.preview_player.stops
    stack.presenter.on_page_changed(ShellPageEnum.FOCUS)

    assert stack.timer.preview_player.last.volume == Volume(42)
    assert stack.timer.preview_player.stops == stops + 1


def test_choose_file_makes_the_file_the_chime_sound(stack: SettingsStack) -> None:
    stack.dialogs.chosen_path = "D:/Music/bell.mp3"

    stack.click(int(ActionIdEnum.SETTINGS_CHIME_SOUND_CHOOSE_FILE))

    sound = stack.last.form.chime.fields.sound
    assert sound.options[sound.selected] == "en:sound.file.label(name=bell.mp3)"
    assert stack.presenter.has_unsaved_edits()


def test_choosing_no_file_changes_nothing(stack: SettingsStack) -> None:
    stack.click(int(ActionIdEnum.SETTINGS_CHIME_SOUND_CHOOSE_FILE))

    assert not stack.presenter.has_unsaved_edits()


def test_sound_selected_in_the_list_and_out_of_range_indices(stack: SettingsStack) -> None:
    options = stack.render().form.chime.fields.sound.options

    stack.presenter.on_sound_selected(len(options))
    stack.presenter.on_language_selected(5)
    stack.presenter.on_log_level_selected(-1)
    assert not stack.presenter.has_unsaved_edits()

    stack.presenter.on_sound_selected(0)
    assert stack.render().form.chime.fields.sound.selected == 0
    assert options[0] == "en:sound.builtin.alarm-classic"
    assert stack.presenter.has_unsaved_edits()


def test_unknown_action_is_logged(stack: SettingsStack, caplog: pytest.LogCaptureFixture) -> None:
    stack.presenter.on_action_requested(int(ActionIdEnum.TIMER_START))

    assert "not handled" in caplog.text


def test_unreadable_settings_use_the_ini_defaults_in_the_current_language(stack: SettingsStack) -> None:
    stack.storage.settings.read_failure = ValidationResult.failure(ErrorCodeEnum.ENTITY_NOT_FOUND)

    form = stack.render().form

    assert form.general.language.selected == 0
    assert form.general.log_level.selected == 1


def test_detached_presenter_reports_a_wiring_error(stack: SettingsStack) -> None:
    stack.presenter._dialogs = None  # pyright: ignore[reportPrivateUsage]  # simulate a missing attach
    stack.presenter.on_log_level_selected(0)

    with pytest.raises(RuntimeError, match="attach"):
        stack.presenter.may_leave()
