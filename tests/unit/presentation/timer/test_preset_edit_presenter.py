import pytest

from concentrator.domain.timer.duration import Duration
from concentrator.domain.timer.timer_presets_collection import TimerPresetsCollection
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.timer.preset_edit_form import PresetDraft, PresetEditForm
from tests.fakes.timer_extras_factory import make_presets
from tests.fakes.timer_factory import LIMITS
from tests.fakes.timer_ui_stack import TimerUiStack


@pytest.fixture
def stack() -> TimerUiStack:
    return TimerUiStack()


def test_new_favorite_form_can_be_saved_when_valid_without_change() -> None:
    form = PresetEditForm(
        PresetDraft(label="", duration=Duration(1500)), limits=LIMITS, presets=make_presets(), preset_id=""
    )

    assert form.is_new
    assert form.can_submit


def test_existing_favorite_form_needs_a_change() -> None:
    form = PresetEditForm(
        PresetDraft(label="", duration=Duration(900)), limits=LIMITS, presets=make_presets(), preset_id="preset-15"
    )

    assert not form.can_submit
    form.set_label("Tea")
    assert form.can_submit


def test_form_reports_a_duplicate_duration_and_a_long_label() -> None:
    form = PresetEditForm(
        PresetDraft(label="", duration=Duration(1500)), limits=LIMITS, presets=make_presets(), preset_id=""
    )

    form.set_duration(0, 30, 0)
    form.set_label("x" * 41)

    assert [issue.field for issue in form.errors.issues] == ["label", "duration_seconds"]
    assert not form.can_submit


def test_label_length_is_checked_after_trimming() -> None:
    form = PresetEditForm(
        PresetDraft(label="", duration=Duration(60)), limits=LIMITS, presets=TimerPresetsCollection(), preset_id=""
    )

    form.set_label("  " + "x" * 40 + "  ")

    assert form.can_submit


def test_saving_a_new_favorite_adds_it_and_closes(stack: TimerUiStack) -> None:
    def edit() -> None:
        stack.preset_editor.on_label_changed(" Pomodoro ")
        stack.preset_edit(ActionIdEnum.PRESET_EDIT_SAVE)

    stack.preset_window.while_open = edit
    stack.preset_action(ActionIdEnum.PRESET_ADD)

    labels = [preset.button.text for preset in stack.presets_snapshot.presets]
    assert labels[-1] == "Pomodoro"
    assert stack.preset_window.closes == 1


def test_snapshot_shows_inline_errors_and_the_automatic_placeholder(stack: TimerUiStack) -> None:
    stack.preset_window.while_open = lambda: stack.preset_editor.on_duration_changed(0, 15, 0)
    stack.preset_action(ActionIdEnum.PRESET_ADD)

    snapshot = stack.preset_editor.build_snapshot()

    assert snapshot.duration.error == "en:error.preset_duration_duplicate(duration=00:15:00)"
    assert snapshot.label.placeholder == "en:preset.edit.label_placeholder(label=en:duration.label.minutes(minutes=15))"
    assert not snapshot.label.error
    assert snapshot.save.enabled is False
    assert snapshot.duration.max_hours == 99


def test_saving_an_invalid_draft_is_skipped(stack: TimerUiStack) -> None:
    def edit() -> None:
        stack.preset_editor.on_duration_changed(0, 15, 0)
        stack.preset_edit(ActionIdEnum.PRESET_EDIT_SAVE)

    stack.preset_window.while_open = edit
    stack.preset_action(ActionIdEnum.PRESET_ADD)

    assert stack.preset_window.closes == 0
    assert len(stack.presets_snapshot.presets) == 3


def test_editing_updates_the_favorite(stack: TimerUiStack) -> None:
    def edit() -> None:
        stack.preset_editor.on_duration_changed(0, 20, 0)
        stack.preset_edit(ActionIdEnum.PRESET_EDIT_SAVE)

    stack.preset_window.while_open = edit
    stack.preset_action(ActionIdEnum.PRESET_EDIT, "preset-15")

    assert stack.presets.presets.get("preset-15").data is not None
    assert stack.presets_snapshot.presets[0].button.text == "en:duration.label.minutes(minutes=20)"
    assert stack.preset_window.closes == 1


def test_cancel_closes_without_saving_or_asking(stack: TimerUiStack) -> None:
    def edit() -> None:
        stack.preset_editor.on_label_changed("Changed")
        stack.preset_edit(ActionIdEnum.PRESET_EDIT_CANCEL)

    stack.preset_window.while_open = edit
    stack.preset_action(ActionIdEnum.PRESET_EDIT, "preset-15")

    assert stack.preset_window.closes == 1
    assert stack.dialogs.calls == []
    assert stack.presets_snapshot.presets[0].button.text != "Changed"


def test_save_failure_keeps_the_dialog_open(stack: TimerUiStack, caplog: pytest.LogCaptureFixture) -> None:
    def edit() -> None:
        stack.presets.presets = make_presets(*range(1, LIMITS.max_presets + 1))
        stack.preset_edit(ActionIdEnum.PRESET_EDIT_SAVE)

    stack.preset_window.while_open = edit
    stack.preset_action(ActionIdEnum.PRESET_ADD)

    assert stack.preset_window.closes == 0
    assert "PRESET_LIMIT_REACHED" in caplog.text


def test_editing_an_unknown_favorite_opens_nothing(stack: TimerUiStack) -> None:
    assert stack.preset_editor.open_edit("gone").is_failure
    assert stack.preset_window.shows == 0


def test_snapshot_before_any_opening_describes_a_new_favorite(stack: TimerUiStack) -> None:
    assert stack.preset_editor.build_snapshot().title == "en:preset.edit.title.new"


def test_unhandled_dialog_action_is_logged(stack: TimerUiStack, caplog: pytest.LogCaptureFixture) -> None:
    stack.preset_edit(ActionIdEnum.TIMER_START)

    assert "Favorite dialog action TIMER_START" in caplog.text
