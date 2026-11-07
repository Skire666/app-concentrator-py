from dataclasses import replace
from datetime import timedelta

import pytest

from concentrator.application.timer.timer_events import TimerChangedEvent
from concentrator.application.timer.timer_view import blink_phase
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.timer.duration import Duration
from concentrator.domain.timer.timer_settings import TimerSettings
from concentrator.domain.timer.timer_state_enum import TimerStateEnum
from concentrator.domain.timer.timer_transition_enum import TimerTransitionEnum
from tests.fakes.timer_factory import DEFAULT_SETTINGS
from tests.fakes.timer_stack import TimerStack

TEN_SECONDS: TimerSettings = replace(DEFAULT_SETTINGS, duration=Duration(10), auto_stop_seconds=0)


@pytest.fixture
def stack() -> TimerStack:
    return TimerStack(TEN_SECONDS)


def test_idle_view_shows_the_configured_duration(stack: TimerStack) -> None:
    view = stack.queries.current_view()

    assert view.state is TimerStateEnum.IDLE
    assert view.displayed_seconds == 10
    assert view.ends_at is None
    assert view.ringing_ms == 0


def test_start_publishes_the_transition_and_the_wall_clock_end(stack: TimerStack) -> None:
    assert stack.commands.start().is_success

    assert stack.events == [TimerChangedEvent(transitions=(TimerTransitionEnum.STARTED,), displayed_seconds=10)]
    assert stack.queries.current_view().ends_at == stack.clock.now_utc() + timedelta(seconds=10)


def test_ticks_publish_only_when_the_displayed_second_changes(stack: TimerStack) -> None:
    stack.commands.start()
    stack.events.clear()

    for _tick in range(10):
        stack.advance(ms=100)

    assert stack.events == [TimerChangedEvent(transitions=(), displayed_seconds=9)]


def test_idle_ticks_publish_nothing(stack: TimerStack) -> None:
    for _tick in range(30):
        stack.advance(ms=100)

    assert stack.events == []


def test_reaching_zero_starts_ringing(stack: TimerStack) -> None:
    stack.run_to_ringing()

    assert stack.events[-1] == TimerChangedEvent(transitions=(TimerTransitionEnum.ALARM_STARTED,), displayed_seconds=0)
    assert stack.queries.current_view().state is TimerStateEnum.RINGING
    assert stack.queries.current_view().ends_at is None


def test_ringing_publishes_each_blink_phase_change(stack: TimerStack) -> None:
    stack.run_to_ringing()
    stack.events.clear()

    for _tick in range(10):
        stack.advance(ms=100)

    assert len(stack.events) == 2
    assert all(event.transitions == () for event in stack.events)


def test_refused_command_changes_nothing_and_publishes_nothing(stack: TimerStack) -> None:
    result = stack.commands.pause()

    assert result.error_codes == (ErrorCodeEnum.TIMER_TRANSITION_INVALID,)
    assert stack.events == []
    assert stack.engine.session.state is TimerStateEnum.IDLE


def test_paused_view_keeps_the_frozen_value_and_has_no_end(stack: TimerStack) -> None:
    stack.commands.start()
    stack.clock.advance(ms=3_500)
    stack.commands.pause()
    stack.clock.advance(seconds=60)

    view = stack.queries.current_view()

    assert view.displayed_seconds == 7
    assert view.ends_at is None


def test_resume_recomputes_the_wall_clock_end(stack: TimerStack) -> None:
    stack.commands.start()
    stack.clock.advance(seconds=4)
    stack.commands.pause()
    stack.clock.advance(seconds=60)

    stack.commands.resume()

    assert stack.queries.current_view().ends_at == stack.clock.now_utc() + timedelta(seconds=6)


def test_duration_change_while_running_does_not_alter_the_remaining_time(stack: TimerStack) -> None:
    stack.commands.start()
    stack.clock.advance(seconds=2)

    assert stack.commands.update_config(replace(TEN_SECONDS, duration=Duration(600))).is_success

    assert stack.queries.current_view().displayed_seconds == 8
    stack.commands.reset()
    assert stack.queries.current_view().displayed_seconds == 600


def test_missing_configuration_falls_back_to_the_defaults(stack: TimerStack) -> None:
    stack.config.config = None

    assert stack.engine.settings() == DEFAULT_SETTINGS
    assert stack.queries.current_view().displayed_seconds == DEFAULT_SETTINGS.duration.seconds


def test_auto_stop_and_auto_restart_through_the_engine() -> None:
    stack = TimerStack(replace(TEN_SECONDS, auto_stop_seconds=5, auto_restart=True))
    stack.run_to_ringing()

    stack.advance(seconds=5)

    assert stack.events[-1].transitions == (TimerTransitionEnum.AUTO_RESTARTED,)
    assert stack.queries.current_view().state is TimerStateEnum.RUNNING
    assert stack.queries.current_view().ends_at == stack.clock.now_utc() + timedelta(seconds=10)


@pytest.mark.parametrize(("ringing_ms", "phase"), [(0, 0), (499, 0), (500, 1), (1499, 2)])
def test_blink_phase(ringing_ms: int, phase: int) -> None:
    assert blink_phase(ringing_ms, 500) == phase
