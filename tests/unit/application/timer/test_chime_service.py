from dataclasses import replace
from datetime import datetime, time, timedelta, timezone

import pytest

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.timer.chime_settings import ChimeSettings
from concentrator.domain.timer.duration import Duration
from concentrator.domain.timer.sound_ref import SoundRef
from concentrator.domain.timer.timer_state_enum import TimerStateEnum
from concentrator.domain.timer.volume import Volume
from tests.fakes.fake_sound import SOUNDS_DIR
from tests.fakes.timer_extras_factory import DEFAULT_CHIME_SETTINGS, make_chime
from tests.fakes.timer_stack import TimerStack

CHIME_FILE = f"{SOUNDS_DIR}/chime.mp3"
ALL_DAY = replace(DEFAULT_CHIME_SETTINGS, start_hour=0, end_hour=23)
SUMMER = timezone(timedelta(hours=2))
WINTER = timezone(timedelta(hours=1))


@pytest.fixture
def stack() -> TimerStack:
    stack = TimerStack()
    stack.catalog.builtin = (*stack.catalog.builtin, "chime")
    stack.chime.chime = make_chime(enabled=True)
    return stack


def _go(stack: TimerStack, local: str, *, tick_timer: bool = False) -> None:
    """Move the clock forward to a local time of the next day (or later today), then tick."""
    now = stack.clock.now_local()
    target = datetime.combine(now.date(), time.fromisoformat(local), tzinfo=now.tzinfo)
    if target <= now:
        target += timedelta(days=1)
    stack.clock.advance(seconds=(target - now).total_seconds())
    if tick_timer:
        stack.engine.tick()
    stack.chime_service.tick()


def _tick_after(stack: TimerStack, seconds: float) -> None:
    stack.clock.advance(seconds=seconds)
    stack.chime_service.tick()


def test_chimes_once_at_the_full_hour(stack: TimerStack) -> None:
    _go(stack, "08:59:59")
    assert stack.chime_player.played == []

    _tick_after(stack, 1)
    _tick_after(stack, 0.1)
    _tick_after(stack, 30)

    assert len(stack.chime_player.played) == 1
    playback = stack.chime_player.last
    assert (playback.paths, playback.volume, playback.loops) == ((CHIME_FILE,), Volume(60), 1)


def test_chimes_on_a_late_tick_within_the_window(stack: TimerStack) -> None:
    _go(stack, "09:00:40")

    assert len(stack.chime_player.played) == 1


def test_does_not_chime_after_the_window(stack: TimerStack) -> None:
    _go(stack, "09:01:00")

    assert stack.chime_player.played == []


def test_does_not_chime_before_the_hour(stack: TimerStack) -> None:
    _go(stack, "08:59:30")

    assert stack.chime_player.played == []


@pytest.mark.parametrize(
    ("local", "chimes"), [("07:00:00", False), ("08:00:00", True), ("20:00:00", True), ("21:00:00", False)]
)
def test_chimes_only_within_the_active_hours(stack: TimerStack, local: str, chimes: bool) -> None:
    _go(stack, local)

    assert bool(stack.chime_player.played) is chimes


def test_all_day_hours_chime_at_midnight(stack: TimerStack) -> None:
    stack.chime.chime = make_chime(enabled=True, settings=ALL_DAY)

    _go(stack, "00:00:00")

    assert len(stack.chime_player.played) == 1


def test_does_not_chime_when_disabled(stack: TimerStack) -> None:
    stack.chime.chime = make_chime(enabled=False)

    _go(stack, "09:00:00")

    assert stack.chime_player.played == []


def test_enabling_during_the_window_still_chimes_that_hour(stack: TimerStack) -> None:
    stack.chime.chime = make_chime(enabled=False)
    _go(stack, "09:00:05")

    stack.chime_commands.set_enabled(True)
    _tick_after(stack, 5)

    assert len(stack.chime_player.played) == 1


def test_missed_hour_after_a_jump_is_not_chimed_late(stack: TimerStack) -> None:
    _go(stack, "09:58:00")
    _go(stack, "10:03:00")
    assert stack.chime_player.played == []

    _go(stack, "11:00:00")

    assert len(stack.chime_player.played) == 1


def test_skips_the_hour_while_the_timer_rings(stack: TimerStack, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level("INFO")
    _go(stack, "08:59:50")
    stack.commands.start_with_duration(Duration(10))

    _go(stack, "09:00:00", tick_timer=True)
    assert stack.engine.session.state is TimerStateEnum.RINGING
    stack.commands.acknowledge()
    _tick_after(stack, 5)

    assert stack.chime_player.played == []
    assert stack.alarm_player.played
    assert "Hourly chime of 09:00 skipped: the timer is ringing" in caplog.text


def test_clocks_going_back_do_not_chime_the_repeated_hour_twice(stack: TimerStack) -> None:
    stack.chime.chime = make_chime(enabled=True, settings=ALL_DAY)
    stack.clock.local_zone = SUMMER
    _go(stack, "02:00:00")

    _tick_after(stack, 3600 - 5)
    stack.clock.local_zone = WINTER
    _tick_after(stack, 5)
    assert stack.clock.now_local().hour == 2
    assert len(stack.chime_player.played) == 1

    _tick_after(stack, 3600)
    assert stack.clock.now_local().hour == 3
    assert len(stack.chime_player.played) == 2


def test_clocks_going_forward_chime_the_next_existing_hour(stack: TimerStack) -> None:
    stack.chime.chime = make_chime(enabled=True, settings=ALL_DAY)
    stack.clock.local_zone = WINTER
    _go(stack, "01:00:00")

    _tick_after(stack, 3600 - 5)
    stack.clock.local_zone = SUMMER
    _tick_after(stack, 5)

    assert stack.clock.now_local().hour == 3
    assert len(stack.chime_player.played) == 2


def test_missing_sound_falls_back_to_the_default_chime(stack: TimerStack, caplog: pytest.LogCaptureFixture) -> None:
    custom = ChimeSettings(sound=SoundRef.file("D:/gone.mp3"), volume=Volume(30), start_hour=8, end_hour=20)
    stack.chime.chime = make_chime(enabled=True, settings=custom)

    _go(stack, "09:00:00")

    assert stack.chime_player.last.paths == (CHIME_FILE,)
    assert "Chime sound (FILE) not found" in caplog.text
    assert "gone.mp3" not in caplog.text


def test_player_failure_is_logged(stack: TimerStack, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level("INFO")
    stack.chime_player.play_failure = ValidationResult.failure(ErrorCodeEnum.AUDIO_DEVICE_UNAVAILABLE)

    _go(stack, "09:00:00")

    assert "Hourly chime not played: ['AUDIO_DEVICE_UNAVAILABLE']" in caplog.text
    assert "played" not in caplog.text.replace("not played", "")


def test_unreadable_chime_falls_back_to_the_ini_switch(stack: TimerStack, caplog: pytest.LogCaptureFixture) -> None:
    stack.chime.chime = None

    _go(stack, "09:00:00")

    assert stack.chime_player.played == []
    assert stack.chime_queries.settings() == stack.chime_defaults.settings
    assert "Hourly chime unavailable: ['ENTITY_NOT_FOUND']" in caplog.text
