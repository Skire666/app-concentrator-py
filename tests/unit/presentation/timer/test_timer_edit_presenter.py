from dataclasses import replace

import pytest

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.domain.timer.duration import Duration
from concentrator.domain.timer.sound_ref import SoundRef
from concentrator.domain.timer.timer_settings import TimerSettings
from concentrator.domain.timer.timer_state_enum import TimerStateEnum
from concentrator.domain.timer.volume import Volume
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.timer.timer_edit_presenter import TimerEditPresenter
from tests.fakes.fake_sound import SOUNDS_DIR
from tests.fakes.timer_factory import DEFAULT_SETTINGS, LIMITS
from tests.fakes.timer_ui_stack import FakeEditorDialog, TimerUiStack

A = ActionIdEnum
SETTINGS: TimerSettings = replace(DEFAULT_SETTINGS, duration=Duration(1500), auto_stop_seconds=120)
CUSTOM = "E:/Music/long alarm.mp3"


@pytest.fixture
def stack() -> TimerUiStack:
    return TimerUiStack(SETTINGS)


def _open(stack: TimerUiStack, *steps: object) -> None:
    """Open the dialog; ``steps`` are callables run while it is open."""

    def act() -> None:
        for step in steps:
            assert callable(step)
            step()

    stack.window.while_open = act
    stack.click(A.TIMER_EDIT)


def test_the_snapshot_shows_the_stored_settings(stack: TimerUiStack) -> None:
    snapshot = stack.edit_snapshot

    assert snapshot.title == "en:timer.edit.title"
    assert (snapshot.duration.hours, snapshot.duration.minutes, snapshot.duration.seconds) == (0, 25, 0)
    assert snapshot.duration.max_hours == 99
    assert snapshot.sound.options == ("en:sound.builtin.alarm-classic", "en:sound.builtin.alarm-soft")
    assert snapshot.sound.selected == 0
    assert snapshot.volume.value == 80
    assert snapshot.volume.value_text == "en:timer.edit.volume_value(percent=80)"
    assert (snapshot.loops.count, snapshot.loops.maximum, snapshot.loops.count_enabled) == (3, 99, True)
    assert (snapshot.auto_stop.seconds, snapshot.auto_stop.maximum) == (120, 3600)
    assert snapshot.auto_stop.restart_enabled
    assert not snapshot.note
    assert not snapshot.save.enabled
    assert snapshot.cancel.enabled


def test_french_labels() -> None:
    stack = TimerUiStack(SETTINGS, LanguageEnum.FRENCH)

    assert stack.edit_snapshot.duration.label == "fr:timer.edit.duration"
    assert stack.edit_snapshot.save.text == "fr:action.timer_edit_save"


def test_changes_update_the_draft_and_enable_save(stack: TimerUiStack) -> None:
    editor = stack.editor

    editor.on_duration_changed(1, 2, 3)
    editor.on_sound_selected(1)
    editor.on_volume_changed(40)
    editor.on_loop_count_changed(5)
    editor.on_loop_forever_changed(True)
    editor.on_auto_stop_changed(0)
    editor.on_auto_restart_changed(True)
    snapshot = stack.edit_snapshot

    assert (snapshot.duration.hours, snapshot.duration.minutes, snapshot.duration.seconds) == (1, 2, 3)
    assert snapshot.sound.selected == 1
    assert snapshot.volume.value == 40
    assert not snapshot.loops.count_enabled
    assert snapshot.loops.forever
    assert not snapshot.auto_stop.restart_enabled
    assert snapshot.save.enabled


def test_inline_errors_appear_while_typing(stack: TimerUiStack) -> None:
    stack.editor.on_duration_changed(0, 0, 0)
    stack.editor.on_auto_stop_changed(3)

    snapshot = stack.edit_snapshot

    assert snapshot.duration.error == "en:error.timer_duration_too_short(min=00:00:01)"
    assert snapshot.auto_stop.error == "en:error.timer_auto_stop_out_of_range(min=5,max=3600)"
    assert not snapshot.sound.error
    assert not snapshot.save.enabled


def test_changes_request_a_render_of_the_dialog(stack: TimerUiStack) -> None:
    stack.editor.on_volume_changed(10)
    stack.scheduler.run_pending()

    assert stack.edit_renders[-1].volume.value == 10


def test_save_stores_the_draft_and_closes(stack: TimerUiStack) -> None:
    _open(stack, lambda: stack.editor.on_volume_changed(30), lambda: stack.edit(A.TIMER_EDIT_SAVE))

    assert stack.config.config is not None
    assert stack.config.config.settings.volume == Volume(30)
    assert stack.window.closes == 1
    assert stack.preview_player.stops >= 1


def test_save_without_a_valid_change_does_nothing(stack: TimerUiStack) -> None:
    stack.editor.on_duration_changed(0, 0, 0)

    stack.edit(A.TIMER_EDIT_SAVE)

    assert stack.config.updates == []
    assert stack.window.closes == 0


def test_save_failure_keeps_the_dialog_open(stack: TimerUiStack, caplog: pytest.LogCaptureFixture) -> None:
    stack.config.write_failure = ValidationResult.failure(ErrorCodeEnum.ENTITY_NOT_FOUND)
    stack.editor.on_volume_changed(30)

    stack.edit(A.TIMER_EDIT_SAVE)

    assert stack.window.closes == 0
    assert "TIMER_EDIT_SAVE: ['ENTITY_NOT_FOUND']" in caplog.text


def test_cancel_of_a_clean_form_closes_without_question(stack: TimerUiStack) -> None:
    _open(stack, lambda: stack.edit(A.TIMER_EDIT_CANCEL))

    assert stack.window.closes == 1
    assert stack.dialogs.calls == []


def test_cancel_of_a_changed_form_closes_without_question_and_discards(stack: TimerUiStack) -> None:
    stack.editor.on_volume_changed(30)
    stack.edit(A.TIMER_SOUND_PREVIEW)

    stack.edit(A.TIMER_EDIT_CANCEL)

    assert stack.window.closes == 1
    assert stack.dialogs.calls == []
    assert stack.config.updates == []
    assert stack.preview_player.stops == 1


def test_reopening_starts_from_the_stored_settings(stack: TimerUiStack) -> None:
    _open(stack, lambda: stack.editor.on_volume_changed(30))
    _open(stack)

    assert stack.edit_snapshot.volume.value == 80
    assert not stack.edit_snapshot.save.enabled


def test_preview_plays_the_draft_sound_and_volume(stack: TimerUiStack) -> None:
    stack.editor.on_sound_selected(1)
    stack.editor.on_volume_changed(35)

    stack.edit(A.TIMER_SOUND_PREVIEW)

    assert stack.preview_player.last.paths == (f"{SOUNDS_DIR}/alarm-soft.mp3",)
    assert stack.preview_player.last.volume == Volume(35)
    assert stack.preview_player.last.loops == 1


def test_closing_the_dialog_stops_the_preview(stack: TimerUiStack) -> None:
    _open(stack, lambda: stack.edit(A.TIMER_SOUND_PREVIEW))

    assert stack.preview_player.stops == 1


def test_choose_file_sets_a_normalized_path(stack: TimerUiStack) -> None:
    stack.catalog.existing_files.add(CUSTOM)
    stack.dialogs.chosen_path = "E:\\Music\\long alarm.mp3"

    stack.edit(A.TIMER_SOUND_CHOOSE_FILE)
    snapshot = stack.edit_snapshot

    assert snapshot.sound.options[-1] == "en:sound.file.label(name=long alarm.mp3)"
    assert snapshot.sound.tooltips[-1] == CUSTOM
    assert snapshot.sound.selected == 2
    assert snapshot.save.enabled
    title, directory, name_filter = stack.dialogs.texts("choose_open_file")[0]
    assert (title, directory, name_filter) == ("en:sound.file_dialog.title", "", "en:sound.file_dialog.filter")


def test_choose_file_starts_in_the_folder_of_the_current_file() -> None:
    stack = TimerUiStack(replace(SETTINGS, sound=SoundRef.file(CUSTOM)))
    stack.catalog.existing_files.add(CUSTOM)

    stack.edit(A.TIMER_SOUND_CHOOSE_FILE)

    assert stack.dialogs.texts("choose_open_file")[0][1] == "E:/Music"


def test_cancelled_file_picker_changes_nothing(stack: TimerUiStack) -> None:
    stack.dialogs.chosen_path = None

    stack.edit(A.TIMER_SOUND_CHOOSE_FILE)

    assert not stack.edit_snapshot.save.enabled


def test_a_missing_chosen_file_shows_an_error(stack: TimerUiStack) -> None:
    stack.dialogs.chosen_path = "E:/deleted.mp3"

    stack.edit(A.TIMER_SOUND_CHOOSE_FILE)

    assert stack.edit_snapshot.sound.error == "en:error.audio_file_not_found"
    assert not stack.edit_snapshot.save.enabled


def test_a_chosen_file_stays_in_the_list_after_picking_a_builtin_sound(stack: TimerUiStack) -> None:
    stack.catalog.existing_files.add(CUSTOM)
    stack.dialogs.chosen_path = CUSTOM
    stack.edit(A.TIMER_SOUND_CHOOSE_FILE)

    stack.editor.on_sound_selected(0)
    stack.editor.on_sound_selected(2)

    assert stack.edit_snapshot.sound.selected == 2
    assert len(stack.edit_snapshot.sound.options) == 3


def test_an_out_of_range_sound_index_is_ignored(stack: TimerUiStack) -> None:
    stack.editor.on_sound_selected(9)
    stack.editor.on_sound_selected(-1)

    assert stack.edit_snapshot.sound.selected == 0


def test_an_unlabelled_or_missing_builtin_sound_shows_its_name() -> None:
    stack = TimerUiStack(replace(SETTINGS, sound=SoundRef.builtin("alarm-old")))
    stack.translator.missing = frozenset({"sound.builtin.alarm-old"})

    snapshot = stack.edit_snapshot

    assert snapshot.sound.options[-1] == "alarm-old"
    assert snapshot.sound.selected == 2
    assert snapshot.sound.error == "en:error.audio_file_not_found"


def test_the_note_explains_changes_while_running(stack: TimerUiStack) -> None:
    stack.click(A.TIMER_START)

    assert stack.edit_snapshot.note == "en:timer.edit.running_note"


def test_a_duration_saved_while_running_replaces_the_countdown(stack: TimerUiStack) -> None:
    stack.click(A.TIMER_START)
    stack.clock.advance(seconds=100)

    _open(stack, lambda: stack.editor.on_duration_changed(0, 5, 0), lambda: stack.edit(A.TIMER_EDIT_SAVE))

    view = stack.queries.current_view()
    assert view.state is TimerStateEnum.RUNNING
    assert view.displayed_seconds == 300
    assert stack.snapshot.right.action is A.TIMER_PAUSE


def test_a_duration_saved_while_paused_starts_the_new_countdown(stack: TimerUiStack) -> None:
    stack.click(A.TIMER_START)
    stack.click(A.TIMER_PAUSE)

    _open(stack, lambda: stack.editor.on_duration_changed(0, 5, 0), lambda: stack.edit(A.TIMER_EDIT_SAVE))

    assert stack.queries.current_view().state is TimerStateEnum.RUNNING
    assert stack.queries.current_view().displayed_seconds == 300


def test_a_sound_saved_while_running_keeps_the_countdown(stack: TimerUiStack) -> None:
    stack.click(A.TIMER_START)
    stack.clock.advance(seconds=100)

    _open(stack, lambda: stack.editor.on_volume_changed(20), lambda: stack.edit(A.TIMER_EDIT_SAVE))

    assert stack.queries.current_view().state is TimerStateEnum.RUNNING
    assert stack.queries.current_view().displayed_seconds == 1400


def test_an_unknown_edit_action_is_logged(stack: TimerUiStack, caplog: pytest.LogCaptureFixture) -> None:
    stack.editor.on_action_requested(int(A.TIMER_START))

    assert "Timer edit action TIMER_START (16) is not handled" in caplog.text


def test_using_the_presenter_before_attach_is_a_wiring_error(stack: TimerUiStack) -> None:
    editor = TimerEditPresenter(
        stack.translator, stack.gate, stack.renderer, stack.queries, stack.commands, stack.preview, LIMITS
    )
    with pytest.raises(RuntimeError, match="attach"):
        editor.open()
    with pytest.raises(RuntimeError, match="attach"):
        editor.on_action_requested(int(A.TIMER_SOUND_CHOOSE_FILE))


def test_fake_dialog_counts_shows() -> None:
    window = FakeEditorDialog()
    window.show_editor()

    assert window.shows == 1
