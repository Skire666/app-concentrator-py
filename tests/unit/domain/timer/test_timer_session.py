from collections.abc import Callable
from dataclasses import replace
from typing import Final

import pytest

from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.timer.duration import Duration
from concentrator.domain.timer.timer_session import TimerSession
from concentrator.domain.timer.timer_settings import TimerSettings
from concentrator.domain.timer.timer_state_enum import TimerStateEnum
from concentrator.domain.timer.timer_transition_enum import TimerTransitionEnum
from tests.fakes.timer_factory import DEFAULT_SETTINGS

T0: Final = 1_000_000
DURATION: Final = Duration(1500)
SNOOZE: Final = Duration.from_minutes(5)
NEVER_STOP: Final = replace(DEFAULT_SETTINGS, auto_stop_seconds=0)

type Command = Callable[[TimerSession], DataResult[TimerSession]]

COMMANDS: Final[dict[str, Command]] = {
    "start": lambda session: session.start(T0, DURATION),
    "pause": lambda session: session.pause(T0),
    "resume": lambda session: session.resume(T0),
    "reset": lambda session: session.reset(),
    "acknowledge": lambda session: session.acknowledge(),
    "restart": lambda session: session.restart(T0, DURATION),
    "snooze": lambda session: session.snooze(T0, SNOOZE),
}
ALLOWED: Final = {
    (TimerStateEnum.IDLE, "start"): TimerStateEnum.RUNNING,
    (TimerStateEnum.RUNNING, "pause"): TimerStateEnum.PAUSED,
    (TimerStateEnum.RUNNING, "reset"): TimerStateEnum.IDLE,
    (TimerStateEnum.PAUSED, "resume"): TimerStateEnum.RUNNING,
    (TimerStateEnum.PAUSED, "reset"): TimerStateEnum.IDLE,
    (TimerStateEnum.RINGING, "acknowledge"): TimerStateEnum.IDLE,
    (TimerStateEnum.RINGING, "restart"): TimerStateEnum.RUNNING,
    (TimerStateEnum.RINGING, "snooze"): TimerStateEnum.RUNNING,
}


def _value(result: DataResult[TimerSession]) -> TimerSession:
    assert result.data is not None, result.validation.error_codes
    return result.data


def _running(now: int = T0, duration: Duration = DURATION) -> TimerSession:
    return _value(TimerSession.idle().start(now, duration))


def _ringing(now: int = T0) -> TimerSession:
    tick = _running(now - DURATION.milliseconds).tick(now, DEFAULT_SETTINGS)
    assert tick.transitions == (TimerTransitionEnum.ALARM_STARTED,)
    return tick.session


def _in_state(state: TimerStateEnum) -> TimerSession:
    sessions = {
        TimerStateEnum.IDLE: TimerSession.idle(),
        TimerStateEnum.RUNNING: _running(),
        TimerStateEnum.PAUSED: _value(_running().pause(T0 + 1000)),
        TimerStateEnum.RINGING: _ringing(),
    }
    return sessions[state]


PAIRS: Final = [
    (state, name)
    for state in (TimerStateEnum.IDLE, TimerStateEnum.RUNNING, TimerStateEnum.PAUSED, TimerStateEnum.RINGING)
    for name in COMMANDS
]


@pytest.mark.parametrize(("state", "command"), PAIRS, ids=[f"{state.name}-{name}" for state, name in PAIRS])
def test_every_state_and_command_pair(state: TimerStateEnum, command: str) -> None:
    session = _in_state(state)

    result = COMMANDS[command](session)

    expected = ALLOWED.get((state, command))
    if expected is None:
        assert result.data is None
        assert result.validation.error_codes == (ErrorCodeEnum.TIMER_TRANSITION_INVALID,)
    else:
        assert _value(result).state is expected
    assert session == _in_state(state)


def test_start_sets_the_deadline_from_now() -> None:
    session = _running()

    assert session.deadline_ms == T0 + 1_500_000
    assert session.remaining_ms(T0 + 500) == 1_499_500
    assert not session.snoozed


def test_idle_displays_the_configured_duration() -> None:
    assert TimerSession.idle().displayed_seconds(T0, Duration(42)) == 42


def test_running_display_rounds_the_remaining_time_up() -> None:
    session = _running(duration=Duration(10))

    assert session.displayed_seconds(T0, DURATION) == 10
    assert session.displayed_seconds(T0 + 1, DURATION) == 10
    assert session.displayed_seconds(T0 + 1000, DURATION) == 9
    assert session.displayed_seconds(T0 + 9999, DURATION) == 1


def test_one_millisecond_left_is_still_running_and_shows_one_second() -> None:
    session = _running(duration=Duration(10))
    now = T0 + 9999

    tick = session.tick(now, DEFAULT_SETTINGS)

    assert tick.session.state is TimerStateEnum.RUNNING
    assert tick.transitions == ()
    assert tick.session.displayed_seconds(now, DURATION) == 1


def test_zero_left_starts_the_alarm() -> None:
    now = T0 + 10_000

    tick = _running(duration=Duration(10)).tick(now, DEFAULT_SETTINGS)

    assert tick.session.state is TimerStateEnum.RINGING
    assert tick.transitions == (TimerTransitionEnum.ALARM_STARTED,)
    assert tick.session.displayed_seconds(now, DURATION) == 0
    assert tick.session.ringing_ms(now + 250) == 250


def test_a_late_tick_starts_the_alarm_too() -> None:
    tick = _running(duration=Duration(10)).tick(T0 + 60_000, DEFAULT_SETTINGS)

    assert tick.session.state is TimerStateEnum.RINGING
    assert tick.session.remaining_ms(T0 + 60_000) == 0


def test_pause_freezes_the_remaining_time() -> None:
    paused = _value(_running().pause(T0 + 400))

    assert paused.remaining_ms(T0 + 400) == 1_499_600
    assert paused.remaining_ms(T0 + 9_000_000) == 1_499_600
    assert paused.displayed_seconds(T0 + 9_000_000, DURATION) == 1500
    assert paused.tick(T0 + 9_000_000, DEFAULT_SETTINGS).transitions == ()


def test_pause_and_resume_many_times_keeps_the_exact_running_time() -> None:
    session = _running(duration=Duration(100))
    now = T0
    for _cycle in range(200):
        now += 250
        session = _value(session.pause(now))
        now += 7_777
        session = _value(session.resume(now))

    assert session.remaining_ms(now) == 100_000 - 200 * 250


def test_resume_keeps_the_snooze_flag() -> None:
    snoozed = _value(_ringing().snooze(T0, SNOOZE))

    resumed = _value(_value(snoozed.pause(T0 + 1000)).resume(T0 + 5000))

    assert resumed.snoozed
    assert resumed.remaining_ms(T0 + 5000) == 299_000


def test_one_hour_with_100_ms_ticks_rings_exactly_on_time() -> None:
    session = _running(duration=Duration(3600))
    now = T0
    ticks = 0
    while session.state is TimerStateEnum.RUNNING:
        now += 100
        ticks += 1
        session = session.tick(now, DEFAULT_SETTINGS).session

    assert ticks == 36_000
    assert now == T0 + 3_600_000


def test_snooze_runs_for_the_snooze_duration_and_rings_again() -> None:
    snoozed = _value(_ringing().snooze(T0, SNOOZE))

    assert snoozed.state is TimerStateEnum.RUNNING
    assert snoozed.snoozed
    assert snoozed.displayed_seconds(T0, DURATION) == 300
    tick = snoozed.tick(T0 + 300_000, DEFAULT_SETTINGS)
    assert tick.transitions == (TimerTransitionEnum.ALARM_STARTED,)
    assert not tick.session.snoozed


def test_reset_clears_the_snooze_flag() -> None:
    snoozed = _value(_ringing().snooze(T0, SNOOZE))

    assert _value(snoozed.reset()) == TimerSession.idle()


def test_restart_runs_the_full_duration() -> None:
    restarted = _value(_ringing().restart(T0, Duration(60)))

    assert restarted.remaining_ms(T0) == 60_000
    assert not restarted.snoozed


def test_ringing_without_auto_stop_rings_until_acknowledged() -> None:
    ringing = _ringing()

    assert ringing.tick(T0 + 86_400_000, NEVER_STOP).transitions == ()


def test_auto_stop_returns_to_idle_after_the_delay() -> None:
    settings: TimerSettings = replace(DEFAULT_SETTINGS, auto_stop_seconds=10, auto_restart=False)
    ringing = _ringing()

    assert ringing.tick(T0 + 9_999, settings).transitions == ()
    tick = ringing.tick(T0 + 10_000, settings)
    assert tick.transitions == (TimerTransitionEnum.AUTO_STOPPED,)
    assert tick.session == TimerSession.idle()


def test_auto_restart_runs_the_configured_duration_again() -> None:
    settings: TimerSettings = replace(DEFAULT_SETTINGS, auto_stop_seconds=10, auto_restart=True, duration=Duration(60))

    tick = _ringing().tick(T0 + 10_000, settings)

    assert tick.transitions == (TimerTransitionEnum.AUTO_RESTARTED,)
    assert tick.session.state is TimerStateEnum.RUNNING
    assert tick.session.remaining_ms(T0 + 10_000) == 60_000


def test_auto_restart_is_not_applied_without_auto_stop() -> None:
    settings: TimerSettings = replace(DEFAULT_SETTINGS, auto_stop_seconds=0, auto_restart=True)

    assert _ringing().tick(T0 + 86_400_000, settings).transitions == ()


def test_idle_tick_changes_nothing() -> None:
    tick = TimerSession.idle().tick(T0, DEFAULT_SETTINGS)

    assert tick.session == TimerSession.idle()
    assert tick.transitions == ()


def test_ringing_time_is_zero_when_not_ringing() -> None:
    assert _running().ringing_ms(T0 + 5) == 0


def test_remaining_time_is_zero_when_idle_or_ringing() -> None:
    assert TimerSession.idle().remaining_ms(T0) == 0
    assert _ringing().remaining_ms(T0) == 0
