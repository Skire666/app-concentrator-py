import pytest

from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.domain.timer.duration import Duration
from concentrator.domain.timer.timer_presets_collection import TimerPresetsCollection
from concentrator.domain.timer.timer_state_enum import TimerStateEnum
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from tests.fakes.timer_extras_factory import make_preset, make_presets
from tests.fakes.timer_factory import LIMITS
from tests.fakes.timer_ui_stack import TimerUiStack

MENU = (ActionIdEnum.PRESET_EDIT, ActionIdEnum.PRESET_DELETE)


@pytest.fixture
def stack() -> TimerUiStack:
    return TimerUiStack()


def test_idle_favorites_show_automatic_labels_and_start_tooltips(stack: TimerUiStack) -> None:
    snapshot = stack.presets_snapshot

    assert snapshot.title == "en:presets.title"
    assert [preset.preset_id for preset in snapshot.presets] == ["preset-15", "preset-30", "preset-45"]
    first = snapshot.presets[0].button
    assert first.text == "en:duration.label.minutes(minutes=15)"
    assert first.tooltip == "en:presets.tooltip.start(duration=00:15:00)"
    assert (first.enabled, first.action) == (True, ActionIdEnum.PRESET_APPLY)
    assert not snapshot.empty_text


def test_labels_follow_the_language(stack: TimerUiStack) -> None:
    french = TimerUiStack(language=LanguageEnum.FRENCH)

    assert french.presets_snapshot.presets[0].button.text == "fr:duration.label.minutes(minutes=15)"
    assert stack.presets_snapshot.presets[0].button.text.startswith("en:")


def test_a_typed_label_replaces_the_automatic_one(stack: TimerUiStack) -> None:
    stack.presets.presets = TimerPresetsCollection((make_preset(25, label="Pomodoro"),))

    assert stack.presets_snapshot.presets[0].button.text == "Pomodoro"


@pytest.mark.parametrize("state", [TimerStateEnum.RUNNING, TimerStateEnum.PAUSED, TimerStateEnum.RINGING])
def test_favorites_stay_enabled_and_offer_to_replace_the_countdown(stack: TimerUiStack, state: TimerStateEnum) -> None:
    if state is TimerStateEnum.RINGING:
        stack.run_to_ringing()
    else:
        stack.commands.start()
        if state is TimerStateEnum.PAUSED:
            stack.commands.pause()

    buttons = [preset.button for preset in stack.presets_snapshot.presets]

    assert {button.enabled for button in buttons} == {True}
    assert buttons[0].tooltip == "en:presets.tooltip.replace(duration=00:15:00)"


def test_context_menu_stays_available_while_the_timer_runs(stack: TimerUiStack) -> None:
    stack.commands.start()

    menu = stack.presets_snapshot.presets[1].menu

    assert [item.action for item in menu] == list(MENU)
    assert {item.enabled for item in menu} == {True}


def test_click_on_a_favorite_starts_its_countdown(stack: TimerUiStack) -> None:
    stack.preset_action(ActionIdEnum.PRESET_APPLY, "preset-15")

    assert stack.engine.session.state is TimerStateEnum.RUNNING
    assert stack.snapshot.digits == "00:15:00"
    stack.scheduler.run_pending()
    assert stack.timer_renders[-1].digits == "00:15:00"
    assert stack.preset_renders[-1].presets[0].button.enabled is False
    stack.scheduler.advance(100)
    stack.scheduler.run_pending()
    assert stack.preset_renders[-1].presets[0].button.enabled is True


def test_click_on_a_favorite_replaces_the_running_countdown(stack: TimerUiStack) -> None:
    stack.click(ActionIdEnum.TIMER_START)
    stack.advance(seconds=30)

    stack.preset_action(ActionIdEnum.PRESET_APPLY, "preset-45")

    assert stack.engine.session.state is TimerStateEnum.RUNNING
    assert stack.snapshot.digits == "00:45:00"


def test_favorites_render_on_transitions_not_on_every_second(stack: TimerUiStack) -> None:
    stack.preset_action(ActionIdEnum.PRESET_APPLY, "preset-15")
    stack.scheduler.run_pending()
    renders = len(stack.preset_renders)

    for _second in range(5):
        stack.advance(seconds=1)
        stack.scheduler.run_pending()

    assert len(stack.preset_renders) == renders
    assert len(stack.timer_renders) > renders


def test_delete_asks_and_deletes_on_yes(stack: TimerUiStack) -> None:
    stack.preset_action(ActionIdEnum.PRESET_DELETE, "preset-45")

    assert stack.dialogs.texts("confirm") == [
        (
            "en:presets.delete.title",
            "en:presets.delete.message(label=en:duration.label.minutes(minutes=45))",
            "en:presets.delete.accept",
            "en:dialog.button.cancel",
        )
    ]
    assert [preset.preset_id for preset in stack.presets_snapshot.presets] == ["preset-15", "preset-30"]


def test_delete_keeps_the_favorite_on_no(stack: TimerUiStack) -> None:
    stack.dialogs.confirm_answer = False

    stack.preset_action(ActionIdEnum.PRESET_DELETE, "preset-45")

    assert len(stack.presets_snapshot.presets) == 3


def test_actions_on_an_unknown_favorite_change_nothing(stack: TimerUiStack, caplog: pytest.LogCaptureFixture) -> None:
    stack.preset_action(ActionIdEnum.PRESET_DELETE, "gone")

    assert stack.dialogs.calls == []
    assert "Favorite action PRESET_DELETE failed: ['ENTITY_NOT_FOUND']" in caplog.text


def test_add_is_disabled_at_the_limit_with_the_limit_as_tooltip(stack: TimerUiStack) -> None:
    assert stack.presets_snapshot.add.enabled
    stack.presets.presets = make_presets(*range(1, LIMITS.max_presets + 1))

    add = stack.presets_snapshot.add

    assert add.enabled is False
    assert add.tooltip == "en:error.preset_limit_reached(max=12)"


def test_no_favorite_shows_the_empty_text(stack: TimerUiStack) -> None:
    stack.presets.presets = TimerPresetsCollection()

    snapshot = stack.presets_snapshot

    assert (snapshot.presets, snapshot.empty_text) == ((), "en:presets.empty")


def test_add_opens_the_dialog_on_an_empty_favorite(stack: TimerUiStack) -> None:
    stack.preset_action(ActionIdEnum.PRESET_APPLY, "preset-15")
    stack.preset_action(ActionIdEnum.PRESET_ADD)

    assert stack.preset_window.shows == 1
    snapshot = stack.preset_editor.build_snapshot()
    assert snapshot.title == "en:preset.edit.title.new"
    duration = snapshot.duration
    assert (duration.hours, duration.minutes, duration.seconds, snapshot.label.text) == (0, 0, 0, "")
    assert (duration.error, snapshot.label.error, snapshot.label.placeholder) == ("", "", "")
    assert snapshot.save.enabled is False


def test_edit_opens_the_dialog_on_the_favorite(stack: TimerUiStack) -> None:
    stack.preset_action(ActionIdEnum.PRESET_EDIT, "preset-30")

    snapshot = stack.preset_editor.build_snapshot()
    assert snapshot.title == "en:preset.edit.title.edit"
    assert snapshot.duration.minutes == 30
    assert snapshot.save.enabled is False


def test_unhandled_actions_are_logged(stack: TimerUiStack, caplog: pytest.LogCaptureFixture) -> None:
    stack.preset_action(ActionIdEnum.TIMER_START)
    stack.preset_action(ActionIdEnum.PRESET_ADD, "preset-15")

    assert "Favorites action TIMER_START" in caplog.text
    assert "Favorite action PRESET_ADD" in caplog.text


def test_changes_request_a_render(stack: TimerUiStack) -> None:
    stack.scheduler.run_pending()
    before = len(stack.preset_renders)

    stack.preset_commands.update("preset-15", "Tea", Duration(900))
    stack.scheduler.run_pending()

    assert len(stack.preset_renders) == before + 1
    assert stack.preset_renders[-1].presets[0].button.text == "Tea"
    assert RenderSectionEnum.PRESETS.value == 8


def test_failed_apply_is_logged(stack: TimerUiStack, caplog: pytest.LogCaptureFixture) -> None:
    stack.preset_action(ActionIdEnum.PRESET_APPLY, "gone")

    assert "Favorite action PRESET_APPLY failed: ['ENTITY_NOT_FOUND']" in caplog.text
    assert stack.engine.session.state is TimerStateEnum.IDLE
