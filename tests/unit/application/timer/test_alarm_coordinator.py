import logging
from dataclasses import replace

import pytest

from concentrator.application.ports.sound_player_port import LOOP_FOREVER, SoundPlayback
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.timer.duration import Duration
from concentrator.domain.timer.sound_ref import SoundRef
from concentrator.domain.timer.timer_settings import TimerSettings
from concentrator.domain.timer.volume import Volume
from tests.fakes.fake_sound import SOUNDS_DIR
from tests.fakes.timer_factory import DEFAULT_SETTINGS
from tests.fakes.timer_stack import TimerStack

CUSTOM = "E:/Music/long alarm.mp3"
SETTINGS: TimerSettings = replace(
    DEFAULT_SETTINGS,
    duration=Duration(10),
    sound=SoundRef.file(CUSTOM),
    volume=Volume(65),
    loop_count=4,
    auto_stop_seconds=30,
)
CLASSIC = f"{SOUNDS_DIR}/alarm-classic.mp3"


@pytest.fixture
def stack() -> TimerStack:
    stack = TimerStack(SETTINGS)
    stack.catalog.existing_files.add(CUSTOM)
    return stack


def test_alarm_plays_once_with_the_chosen_sound_volume_and_loops(stack: TimerStack) -> None:
    stack.run_to_ringing()
    for _tick in range(20):
        stack.advance(ms=100)

    assert stack.alarm_player.played == [SoundPlayback(paths=(CUSTOM, CLASSIC), volume=Volume(65), loops=4)]


def test_repeat_until_stopped_loops_forever() -> None:
    stack = TimerStack(replace(SETTINGS, sound=DEFAULT_SETTINGS.sound, loop_forever=True))

    stack.run_to_ringing()

    assert stack.alarm_player.last == SoundPlayback(paths=(CLASSIC,), volume=Volume(65), loops=LOOP_FOREVER)


def test_missing_custom_sound_falls_back_to_the_default_with_an_error(
    stack: TimerStack, caplog: pytest.LogCaptureFixture
) -> None:
    stack.catalog.existing_files.clear()

    stack.run_to_ringing()

    assert stack.alarm_player.last.paths == (CLASSIC,)
    errors = [record.getMessage() for record in caplog.records if record.levelno == logging.ERROR]
    assert errors == ["Alarm sound (FILE) not found; falling back"]
    assert CUSTOM not in caplog.text


def test_no_sound_file_at_all_leaves_the_beep_to_the_player(stack: TimerStack) -> None:
    stack.catalog.existing_files.clear()
    stack.catalog.builtin = ()

    stack.run_to_ringing()

    assert stack.alarm_player.last.paths == ()


def test_player_failure_is_logged(stack: TimerStack, caplog: pytest.LogCaptureFixture) -> None:
    stack.alarm_player.play_failure = ValidationResult.failure(ErrorCodeEnum.AUDIO_DEVICE_UNAVAILABLE)

    stack.run_to_ringing()

    assert "AUDIO_DEVICE_UNAVAILABLE" in caplog.text


@pytest.mark.parametrize("command", ["acknowledge", "restart", "snooze"])
def test_leaving_ringing_by_a_command_stops_the_alarm(stack: TimerStack, command: str) -> None:
    stack.run_to_ringing()

    assert getattr(stack.commands, command)().is_success

    assert stack.alarm_player.stops == 1


@pytest.mark.parametrize("auto_restart", [False, True])
def test_auto_stop_stops_the_alarm(auto_restart: bool) -> None:
    stack = TimerStack(replace(SETTINGS, auto_stop_seconds=5, auto_restart=auto_restart))
    stack.run_to_ringing()

    stack.advance(seconds=5)

    assert stack.alarm_player.stops == 1


def test_pause_and_reset_do_not_touch_the_alarm(stack: TimerStack) -> None:
    stack.commands.start()
    stack.commands.pause()
    stack.commands.reset()

    assert stack.alarm_player.stops == 0
    assert stack.alarm_player.played == []


def test_inactive_application_gets_a_flashing_taskbar_button(stack: TimerStack) -> None:
    stack.attention.active = False

    stack.run_to_ringing()

    assert stack.attention.attention_requests == 1


def test_inactive_application_without_the_setting_gets_only_the_sound(stack: TimerStack) -> None:
    stack.attention.active = False
    stack.notify_when_inactive = False

    stack.run_to_ringing()

    assert stack.attention.attention_requests == 0
    assert len(stack.alarm_player.played) == 1


def test_active_application_gets_only_the_sound(stack: TimerStack) -> None:
    stack.attention.active = True

    stack.run_to_ringing()

    assert stack.attention.attention_requests == 0
    assert len(stack.alarm_player.played) == 1


def test_sound_changed_while_running_applies_to_the_ringing(stack: TimerStack) -> None:
    stack.commands.start()
    stack.commands.update_config(replace(SETTINGS, sound=SoundRef.builtin("alarm-soft"), volume=Volume(10)))

    stack.advance(seconds=10)

    assert stack.alarm_player.last.paths == (f"{SOUNDS_DIR}/alarm-soft.mp3", CLASSIC)
    assert stack.alarm_player.last.volume == Volume(10)
