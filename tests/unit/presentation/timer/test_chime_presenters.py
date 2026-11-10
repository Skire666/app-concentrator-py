from dataclasses import replace

import pytest

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.timer.sound_ref import SoundRef
from concentrator.domain.timer.volume import Volume
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from tests.fakes.timer_extras_factory import DEFAULT_CHIME_SETTINGS, make_chime
from tests.fakes.timer_ui_stack import TimerUiStack


@pytest.fixture
def stack() -> TimerUiStack:
    stack = TimerUiStack()
    stack.catalog.builtin = (*stack.catalog.builtin, "chime")
    return stack


def test_special_options_show_the_switch_and_the_hours(stack: TimerUiStack) -> None:
    snapshot = stack.chime_presenter.build_snapshot()

    assert snapshot.title == "en:special_options.title"
    assert (snapshot.chime.text, snapshot.chime.checked, snapshot.chime.action) == (
        "en:action.chime_toggle",
        False,
        ActionIdEnum.CHIME_TOGGLE,
    )
    assert snapshot.chime_hours == (
        "en:chime.hours(start=en:format.time(hour=08,minute=00),end=en:format.time(hour=20,minute=00))"
    )
    assert snapshot.chime_edit.action is ActionIdEnum.CHIME_EDIT


def test_toggle_switches_the_chime_and_renders(stack: TimerUiStack) -> None:
    stack.options_action(ActionIdEnum.CHIME_TOGGLE)
    stack.scheduler.run_pending()

    assert stack.chime_queries.enabled() is True
    assert stack.options_renders[-1].chime.checked is True

    stack.options_action(ActionIdEnum.CHIME_TOGGLE)
    assert stack.chime_queries.enabled() is False


def test_toggle_failure_is_logged_and_the_box_shows_the_stored_value(
    stack: TimerUiStack, caplog: pytest.LogCaptureFixture
) -> None:
    stack.chime.write_failure = ValidationResult.failure(ErrorCodeEnum.ENTITY_NOT_FOUND)

    stack.options_action(ActionIdEnum.CHIME_TOGGLE)

    assert "Special options action CHIME_TOGGLE: ['ENTITY_NOT_FOUND']" in caplog.text
    assert stack.chime_presenter.build_snapshot().chime.checked is False


def test_unhandled_special_option_is_logged(stack: TimerUiStack, caplog: pytest.LogCaptureFixture) -> None:
    stack.options_action(ActionIdEnum.TIMER_START)

    assert "Special options action TIMER_START" in caplog.text


def test_dots_open_the_chime_dialog_on_the_stored_settings(stack: TimerUiStack) -> None:
    stack.options_action(ActionIdEnum.CHIME_EDIT)

    assert stack.chime_window.shows == 1
    snapshot = stack.chime_editor.build_snapshot()
    assert snapshot.title == "en:chime.edit.title"
    assert snapshot.fields.sound.options[snapshot.fields.sound.selected] == "en:sound.builtin.chime"
    assert (snapshot.fields.volume.value, snapshot.fields.hours.start, snapshot.fields.hours.end) == (60, 8, 20)
    assert snapshot.fields.hours.options[0] == "en:format.time(hour=00,minute=00)"
    assert len(snapshot.fields.hours.options) == 24
    assert snapshot.save.enabled is False
    assert stack.preview_player.stops == 1


def test_editing_and_saving_stores_the_settings(stack: TimerUiStack) -> None:
    def edit() -> None:
        stack.chime_editor.on_volume_changed(35)
        stack.chime_editor.on_start_hour_changed(0)
        stack.chime_editor.on_end_hour_changed(23)
        stack.chime_editor.on_sound_selected(0)
        stack.chime_edit(ActionIdEnum.CHIME_EDIT_SAVE)

    stack.chime_window.while_open = edit
    stack.options_action(ActionIdEnum.CHIME_EDIT)

    assert stack.chime_queries.settings() == replace(
        DEFAULT_CHIME_SETTINGS, sound=SoundRef.builtin("alarm-classic"), volume=Volume(35), start_hour=0, end_hour=23
    )
    assert stack.chime_window.closes == 1
    stack.scheduler.run_pending()
    assert stack.options_renders[-1].chime_hours.endswith("end=en:format.time(hour=23,minute=00))")


def test_reversed_hours_show_an_inline_error_and_block_saving(stack: TimerUiStack) -> None:
    stack.chime_editor.on_start_hour_changed(21)

    snapshot = stack.chime_editor.build_snapshot()

    assert snapshot.fields.hours.end_error == "en:error.chime_hours_reversed"
    assert not snapshot.fields.hours.start_error
    assert snapshot.save.enabled is False


def test_cancel_closes_without_saving(stack: TimerUiStack) -> None:
    def edit() -> None:
        stack.chime_editor.on_volume_changed(5)
        stack.chime_edit(ActionIdEnum.CHIME_EDIT_CANCEL)

    stack.chime_window.while_open = edit
    stack.options_action(ActionIdEnum.CHIME_EDIT)

    assert stack.chime_queries.settings() == DEFAULT_CHIME_SETTINGS
    assert stack.chime_window.closes == 1
    assert stack.dialogs.calls == []


def test_preview_plays_the_draft_on_the_preview_player(stack: TimerUiStack) -> None:
    stack.chime_editor.on_volume_changed(42)

    stack.chime_edit(ActionIdEnum.CHIME_PREVIEW)

    assert stack.preview_player.last.volume == Volume(42)
    assert stack.preview_player.last.loops == 1
    assert stack.chime_player.played == []


def test_choose_file_makes_the_file_the_draft_sound(stack: TimerUiStack) -> None:
    stack.dialogs.chosen_path = "E:\\Music\\bell.mp3"
    stack.catalog.existing_files.add("E:/Music/bell.mp3")

    stack.chime_edit(ActionIdEnum.CHIME_SOUND_CHOOSE_FILE)

    snapshot = stack.chime_editor.build_snapshot()
    assert stack.dialogs.texts("choose_open_file")[0][0] == "en:sound.file_dialog.chime_title"
    assert snapshot.fields.sound.options[snapshot.fields.sound.selected] == "en:sound.file.label(name=bell.mp3)"
    assert snapshot.save.enabled is True


def test_a_missing_stored_file_is_a_warning(stack: TimerUiStack) -> None:
    stored = replace(DEFAULT_CHIME_SETTINGS, sound=SoundRef.file("D:/gone.mp3"))
    stack.chime.chime = make_chime(settings=stored)

    stack.options_action(ActionIdEnum.CHIME_EDIT)
    stack.chime_editor.on_volume_changed(10)
    snapshot = stack.chime_editor.build_snapshot()

    assert snapshot.fields.sound.error == "en:error.audio_file_not_found"
    assert snapshot.save.enabled is True


def test_save_without_change_is_skipped(stack: TimerUiStack) -> None:
    stack.chime_edit(ActionIdEnum.CHIME_EDIT_SAVE)

    assert stack.chime.updates == []


def test_save_failure_keeps_the_dialog_open(stack: TimerUiStack, caplog: pytest.LogCaptureFixture) -> None:
    def edit() -> None:
        stack.chime.write_failure = ValidationResult.failure(ErrorCodeEnum.ENTITY_NOT_FOUND)
        stack.chime_editor.on_volume_changed(5)
        stack.chime_edit(ActionIdEnum.CHIME_EDIT_SAVE)

    stack.chime_window.while_open = edit
    stack.options_action(ActionIdEnum.CHIME_EDIT)

    assert stack.chime_window.closes == 0
    assert "Chime dialog action CHIME_EDIT_SAVE: ['ENTITY_NOT_FOUND']" in caplog.text


def test_out_of_list_sound_index_is_ignored(stack: TimerUiStack) -> None:
    stack.chime_editor.on_sound_selected(99)

    assert stack.chime_editor.build_snapshot().fields.sound.options[0] == "en:sound.builtin.alarm-classic"
    assert stack.chime_editor.build_snapshot().save.enabled is False


def test_unhandled_dialog_action_is_logged(stack: TimerUiStack, caplog: pytest.LogCaptureFixture) -> None:
    stack.chime_edit(ActionIdEnum.TIMER_START)

    assert "Chime dialog action TIMER_START" in caplog.text
