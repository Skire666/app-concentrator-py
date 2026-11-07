from dataclasses import replace

import pytest

from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.domain.timer.duration import Duration
from concentrator.domain.timer.timer_settings import TimerSettings
from concentrator.domain.timer.timer_state_enum import TimerStateEnum
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.duration_formatter import clock_text
from concentrator.presentation.timer.timer_snapshot import TimerSnapshot
from tests.fakes.timer_factory import DEFAULT_SETTINGS
from tests.fakes.timer_ui_stack import TimerUiStack

SETTINGS: TimerSettings = replace(DEFAULT_SETTINGS, duration=Duration(10), auto_stop_seconds=0)
A = ActionIdEnum


def _stack_in(state: TimerStateEnum, language: LanguageEnum = LanguageEnum.ENGLISH) -> TimerUiStack:
    stack = TimerUiStack(SETTINGS, language)
    if state is TimerStateEnum.RUNNING:
        stack.click(A.TIMER_START)
    elif state is TimerStateEnum.PAUSED:
        stack.click(A.TIMER_START)
        stack.click(A.TIMER_PAUSE)
    elif state is TimerStateEnum.RINGING:
        stack.run_to_ringing()
    stack.scheduler.advance(100)
    assert stack.queries.current_view().state is state
    return stack


def _buttons(snapshot: TimerSnapshot) -> list[tuple[ActionIdEnum, str, bool]]:
    return [(button.action, button.text, button.enabled) for button in (snapshot.left, snapshot.middle, snapshot.right)]


MATRIX = {
    TimerStateEnum.IDLE: [(A.TIMER_EDIT, True), (A.TIMER_RESET, False), (A.TIMER_START, True)],
    TimerStateEnum.RUNNING: [(A.TIMER_EDIT, True), (A.TIMER_RESET, True), (A.TIMER_PAUSE, True)],
    TimerStateEnum.PAUSED: [(A.TIMER_EDIT, True), (A.TIMER_RESET, True), (A.TIMER_RESUME, True)],
    TimerStateEnum.RINGING: [(A.TIMER_RESTART, True), (A.TIMER_ACKNOWLEDGE, True), (A.TIMER_SNOOZE, True)],
}


@pytest.mark.parametrize("language", [LanguageEnum.ENGLISH, LanguageEnum.FRENCH])
@pytest.mark.parametrize("state", list(MATRIX))
def test_button_matrix_in_both_languages(state: TimerStateEnum, language: LanguageEnum) -> None:
    snapshot = _stack_in(state, language).snapshot

    iso = language.iso_code
    expected = [
        (action, f"{iso}:action.{action.name.lower()}(minutes=5)", enabled) for action, enabled in MATRIX[state]
    ]
    assert _buttons(snapshot) == expected
    assert all(button.visible for button in (snapshot.left, snapshot.middle, snapshot.right))


def test_snooze_tooltip_names_the_snooze_minutes() -> None:
    assert _stack_in(TimerStateEnum.RINGING).snapshot.right.tooltip == "en:action.timer_snooze.tooltip(minutes=5)"


def test_idle_shows_the_configured_duration_and_no_caption() -> None:
    snapshot = _stack_in(TimerStateEnum.IDLE).snapshot

    assert snapshot.digits == "00:00:10"
    assert not snapshot.caption
    assert not snapshot.alert


def test_running_caption_gives_the_local_end_time() -> None:
    stack = _stack_in(TimerStateEnum.RUNNING)

    assert stack.snapshot.caption == "en:timer.caption.ends_at(time=en:format.time(hour=10,minute=00))"


def test_snoozed_caption_gives_the_ringing_time() -> None:
    stack = _stack_in(TimerStateEnum.RINGING)
    stack.click(A.TIMER_SNOOZE)

    assert stack.snapshot.caption == "en:timer.caption.snoozed(time=en:format.time(hour=10,minute=05))"
    assert stack.snapshot.digits == "00:05:00"


def test_paused_and_ringing_captions() -> None:
    assert _stack_in(TimerStateEnum.PAUSED).snapshot.caption == "en:timer.caption.paused"
    assert _stack_in(TimerStateEnum.RINGING, LanguageEnum.FRENCH).snapshot.caption == "fr:timer.caption.ringing"


def test_ringing_digits_are_zero_and_blink() -> None:
    stack = _stack_in(TimerStateEnum.RINGING)

    phases: list[bool] = []
    for _step in range(4):
        phases.append(stack.snapshot.alert)
        stack.clock.advance(ms=500)

    assert stack.snapshot.digits == "00:00:00"
    assert phases == [True, False, True, False]


def test_running_digits_follow_the_countdown() -> None:
    stack = _stack_in(TimerStateEnum.RUNNING)
    stack.clock.advance(ms=2500)

    assert stack.snapshot.digits == "00:00:08"


def test_a_second_click_within_the_cooldown_is_ignored() -> None:
    stack = _stack_in(TimerStateEnum.IDLE)

    stack.press(A.TIMER_START)
    stack.press(A.TIMER_PAUSE)

    assert stack.queries.current_view().state is TimerStateEnum.RUNNING
    assert stack.events[-1].transitions[0].name == "STARTED"


def test_every_timer_button_is_disabled_during_the_cooldown() -> None:
    stack = _stack_in(TimerStateEnum.IDLE)

    stack.press(A.TIMER_START)

    assert [enabled for _action, _text, enabled in _buttons(stack.snapshot)] == [False, False, False]
    stack.scheduler.advance(100)
    assert [enabled for _action, _text, enabled in _buttons(stack.snapshot)] == [True, True, True]


def test_a_click_on_an_enabled_button_always_counts() -> None:
    stack = _stack_in(TimerStateEnum.IDLE)

    stack.press(A.TIMER_START)
    stack.scheduler.advance(100)
    stack.press(A.TIMER_PAUSE)

    assert stack.queries.current_view().state is TimerStateEnum.PAUSED


def test_edit_opens_the_dialog_interactively(caplog: pytest.LogCaptureFixture) -> None:
    stack = _stack_in(TimerStateEnum.RUNNING)
    stack.window.while_open = lambda: stack.clock.advance(seconds=5)

    stack.click(A.TIMER_EDIT)

    assert stack.window.shows == 1
    assert "Action TIMER_EDIT took" not in caplog.text


def test_a_refused_command_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    stack = _stack_in(TimerStateEnum.IDLE)

    stack.click(A.TIMER_PAUSE)

    assert "Timer action TIMER_PAUSE failed: ['TIMER_TRANSITION_INVALID']" in caplog.text


def test_an_unknown_action_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    _stack_in(TimerStateEnum.IDLE).press(A.SHELL_SHOW_FOCUS)

    assert "Timer action SHELL_SHOW_FOCUS (1) is not handled" in caplog.text


def test_ticks_and_configuration_changes_re_render_the_timer() -> None:
    stack = _stack_in(TimerStateEnum.RUNNING)
    stack.timer_renders.clear()

    stack.advance(seconds=1)
    stack.scheduler.run_pending()
    assert stack.timer_renders[-1].digits == "00:00:09"

    stack.click(A.TIMER_RESET)
    stack.commands.update_config(replace(SETTINGS, duration=Duration(20)))
    stack.scheduler.run_pending()
    assert stack.timer_renders[-1].digits == "00:00:20"


@pytest.mark.parametrize("seconds", [0, 59, 3599, 359_999])
def test_clock_text_never_changes_width(seconds: int) -> None:
    assert len(clock_text(seconds)) == 8


def test_clock_text_clamps_negative_values() -> None:
    assert clock_text(-5) == "00:00:00"
