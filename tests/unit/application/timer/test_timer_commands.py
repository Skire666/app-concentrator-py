from dataclasses import replace

import pytest

from concentrator.application.ports.sound_player_port import SoundPlayback
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.timer.duration import Duration
from concentrator.domain.timer.sound_ref import SoundRef
from concentrator.domain.timer.timer_settings import TimerSettings
from concentrator.domain.timer.timer_state_enum import TimerStateEnum
from concentrator.domain.timer.volume import Volume
from tests.fakes.fake_sound import SOUNDS_DIR
from tests.fakes.timer_factory import DEFAULT_SETTINGS
from tests.fakes.timer_stack import TimerStack

SHORT: TimerSettings = replace(DEFAULT_SETTINGS, duration=Duration(10), auto_stop_seconds=0)


@pytest.fixture
def stack() -> TimerStack:
    return TimerStack(SHORT)


def test_snooze_runs_for_the_snooze_minutes_and_is_flagged(stack: TimerStack) -> None:
    stack.run_to_ringing()

    assert stack.commands.snooze().is_success

    view = stack.queries.current_view()
    assert view.state is TimerStateEnum.RUNNING
    assert view.snoozed
    assert view.displayed_seconds == 300


def test_restart_runs_the_full_configured_duration(stack: TimerStack) -> None:
    stack.run_to_ringing()

    stack.commands.restart()

    assert stack.queries.current_view().displayed_seconds == 10
    assert not stack.queries.current_view().snoozed


def test_acknowledge_returns_to_idle(stack: TimerStack) -> None:
    stack.run_to_ringing()

    stack.commands.acknowledge()

    assert stack.queries.current_view().state is TimerStateEnum.IDLE


def test_resume_after_pause(stack: TimerStack) -> None:
    stack.commands.start()
    stack.commands.pause()

    assert stack.commands.resume().is_success
    assert stack.queries.current_view().state is TimerStateEnum.RUNNING


def test_update_config_stores_and_publishes(stack: TimerStack) -> None:
    changed = replace(SHORT, volume=Volume(30))

    assert stack.commands.update_config(changed).is_success

    assert stack.config.config is not None
    assert stack.config.config.settings == changed
    assert stack.config.config.updated_at == stack.clock.now_utc()
    assert [event.config.settings for event in stack.config_events] == [changed]


def test_update_config_without_change_writes_nothing(stack: TimerStack) -> None:
    assert stack.commands.update_config(SHORT).is_success

    assert stack.config.updates == []
    assert stack.config_events == []


def test_update_config_refuses_invalid_settings(stack: TimerStack) -> None:
    result = stack.commands.update_config(replace(SHORT, loop_count=0))

    assert result.error_codes == (ErrorCodeEnum.TIMER_LOOP_COUNT_OUT_OF_RANGE,)
    assert stack.config.updates == []


def test_update_config_reports_a_missing_configuration(stack: TimerStack) -> None:
    stack.config.config = None

    assert stack.commands.update_config(SHORT).error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)


def test_update_config_reports_a_write_failure(stack: TimerStack) -> None:
    stack.config.write_failure = ValidationResult.failure(ErrorCodeEnum.ENTITY_NOT_FOUND)

    result = stack.commands.update_config(replace(SHORT, volume=Volume(1)))

    assert result.error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)
    assert stack.config_events == []


def test_queries_return_the_configuration_and_the_builtin_sounds(stack: TimerStack) -> None:
    assert stack.queries.config().data == stack.config.config
    assert stack.queries.builtin_sounds() == (SoundRef.builtin("alarm-classic"), SoundRef.builtin("alarm-soft"))


def test_check_sound_needs_an_existing_playable_file(stack: TimerStack) -> None:
    missing = stack.queries.check_sound(SoundRef.file("E:/nope.mp3"))
    stack.catalog.existing_files.add("E:/song.flac")
    stack.preview_player.check_results["E:/song.flac"] = ValidationResult.failure(
        ErrorCodeEnum.AUDIO_FORMAT_UNSUPPORTED
    )

    unsupported = stack.queries.check_sound(SoundRef.file("E:/song.flac"))

    assert missing.error_codes == (ErrorCodeEnum.AUDIO_FILE_NOT_FOUND,)
    assert unsupported.error_codes == (ErrorCodeEnum.AUDIO_FORMAT_UNSUPPORTED,)
    assert stack.queries.check_sound(SoundRef.builtin("alarm-soft")).is_success


def test_preview_plays_once_at_the_chosen_volume(stack: TimerStack) -> None:
    assert stack.preview.play(SoundRef.builtin("alarm-soft"), Volume(42)).is_success

    assert stack.preview_player.played == [
        SoundPlayback(paths=(f"{SOUNDS_DIR}/alarm-soft.mp3",), volume=Volume(42), loops=1)
    ]
    assert stack.alarm_player.played == []


def test_preview_of_a_missing_file_fails_without_playing(stack: TimerStack) -> None:
    result = stack.preview.play(SoundRef.file("E:/nope.mp3"), Volume(42))

    assert result.error_codes == (ErrorCodeEnum.AUDIO_FILE_NOT_FOUND,)
    assert stack.preview_player.played == []


def test_preview_stop_stops_the_preview_player(stack: TimerStack) -> None:
    stack.preview.stop()

    assert stack.preview_player.stops == 1
    assert stack.alarm_player.stops == 0


def test_apply_config_with_a_new_duration_replaces_a_running_countdown(stack: TimerStack) -> None:
    assert stack.commands.start().is_success
    stack.advance(seconds=4)

    assert stack.commands.apply_config(replace(SHORT, duration=Duration(60))).is_success

    view = stack.queries.current_view()
    assert view.state is TimerStateEnum.RUNNING
    assert view.displayed_seconds == 60


def test_apply_config_without_a_new_duration_keeps_the_countdown(stack: TimerStack) -> None:
    assert stack.commands.start().is_success
    stack.advance(seconds=4)

    assert stack.commands.apply_config(replace(SHORT, volume=Volume(10))).is_success

    assert stack.queries.current_view().displayed_seconds == 6


def test_apply_config_while_idle_only_stores(stack: TimerStack) -> None:
    assert stack.commands.apply_config(replace(SHORT, duration=Duration(60))).is_success

    assert stack.queries.current_view().state is TimerStateEnum.IDLE
    assert stack.queries.settings().duration == Duration(60)


def test_apply_config_refused_by_the_rules_keeps_the_countdown(stack: TimerStack) -> None:
    assert stack.commands.start().is_success

    result = stack.commands.apply_config(replace(SHORT, duration=Duration(0)))

    assert result.is_failure
    assert stack.queries.current_view().displayed_seconds == 10
