from dataclasses import replace
from datetime import UTC, datetime

import pytest

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.timer.duration import Duration
from concentrator.domain.timer.sound_kind_enum import SoundKindEnum
from concentrator.domain.timer.sound_ref import SoundRef
from concentrator.domain.timer.timer_config import TimerConfig, TimerConfigId
from concentrator.domain.timer.timer_config_rules import TimerConfigRules
from concentrator.domain.timer.timer_settings import TimerSettings
from concentrator.domain.timer.volume import Volume
from tests.fakes.timer_factory import DEFAULT_SETTINGS, LIMITS, make_timer_config

NOW = datetime(2026, 11, 6, 16, 40, tzinfo=UTC)


def _validate(**changes: object) -> tuple[ErrorCodeEnum, ...]:
    settings: TimerSettings = replace(DEFAULT_SETTINGS, **changes)
    return TimerConfigRules.validate_settings(settings, LIMITS).error_codes


def test_default_settings_are_valid() -> None:
    assert TimerConfigRules.validate_settings(DEFAULT_SETTINGS, LIMITS).is_success


def test_spec_example_is_valid() -> None:
    assert TimerConfigRules.validate(make_timer_config(), LIMITS).is_success


def test_validate_includes_identity_checks() -> None:
    config = TimerConfig(
        id=TimerConfigId(" "), created_at=NOW.replace(tzinfo=None), updated_at=NOW, settings=DEFAULT_SETTINGS
    )

    codes = TimerConfigRules.validate(config, LIMITS).error_codes

    assert codes == (ErrorCodeEnum.REQUIRED_VALUE_MISSING, ErrorCodeEnum.DATETIME_NOT_UTC)


@pytest.mark.parametrize(("seconds", "valid"), [(0, False), (1, True), (359_999, True), (360_000, False)])
def test_duration_limits(seconds: int, valid: bool) -> None:
    assert (_validate(duration=Duration(seconds)) == ()) is valid


def test_too_short_duration_names_the_minimum() -> None:
    result = TimerConfigRules.validate_duration(Duration(0), LIMITS)

    assert result.error_codes == (ErrorCodeEnum.TIMER_DURATION_TOO_SHORT,)
    assert result.issues[0].field == "duration_seconds"
    assert result.issues[0].params == (("min", "00:00:01"),)


def test_too_long_duration_names_the_maximum() -> None:
    result = TimerConfigRules.validate_duration(Duration(360_000), LIMITS)

    assert result.error_codes == (ErrorCodeEnum.TIMER_DURATION_TOO_LONG,)
    assert result.issues[0].params == (("max", "99:59:59"),)


@pytest.mark.parametrize(("percent", "valid"), [(-1, False), (0, True), (100, True), (101, False)])
def test_volume_limits(percent: int, valid: bool) -> None:
    expected = () if valid else (ErrorCodeEnum.TIMER_VOLUME_OUT_OF_RANGE,)

    assert _validate(volume=Volume(percent)) == expected


def test_volume_issue_uses_the_given_field() -> None:
    result = TimerConfigRules.validate_volume(Volume(101), "hourly_chime.volume")

    assert result.issues[0].field == "hourly_chime.volume"
    assert result.issues[0].params == (("min", "0"), ("max", "100"))


@pytest.mark.parametrize(("count", "valid"), [(0, False), (1, True), (99, True), (100, False)])
def test_loop_count_limits(count: int, valid: bool) -> None:
    expected = () if valid else (ErrorCodeEnum.TIMER_LOOP_COUNT_OUT_OF_RANGE,)

    assert _validate(loop_count=count) == expected


def test_loop_count_is_checked_even_when_repeating_forever() -> None:
    assert _validate(loop_count=0, loop_forever=True) == (ErrorCodeEnum.TIMER_LOOP_COUNT_OUT_OF_RANGE,)


@pytest.mark.parametrize(
    ("seconds", "valid"), [(-1, False), (0, True), (1, False), (4, False), (5, True), (3600, True), (3601, False)]
)
def test_auto_stop_limits(seconds: int, valid: bool) -> None:
    expected = () if valid else (ErrorCodeEnum.TIMER_AUTO_STOP_OUT_OF_RANGE,)

    assert _validate(auto_stop_seconds=seconds) == expected


def test_auto_stop_issue_names_both_bounds() -> None:
    result = TimerConfigRules.validate_auto_stop(4, LIMITS)

    assert result.issues[0].field == "auto_stop_seconds"
    assert result.issues[0].params == (("min", "5"), ("max", "3600"))


@pytest.mark.parametrize(
    ("sound", "code", "field"),
    [
        (SoundRef(kind=SoundKindEnum.UNSET, value="x"), ErrorCodeEnum.TIMER_SOUND_UNSET, "sound"),
        (SoundRef.builtin("  "), ErrorCodeEnum.TIMER_SOUND_UNSET, "sound"),
        (SoundRef.file(""), ErrorCodeEnum.TIMER_SOUND_UNSET, "sound"),
        (SoundRef.of(SoundKindEnum.UNKNOWN, "x"), ErrorCodeEnum.ENUM_VALUE_UNKNOWN, "sound.kind"),
    ],
)
def test_sound_must_be_chosen(sound: SoundRef, code: ErrorCodeEnum, field: str) -> None:
    result = TimerConfigRules.validate_sound(sound)

    assert result.error_codes == (code,)
    assert result.issues[0].field == field


def test_every_failing_field_is_reported() -> None:
    codes = _validate(duration=Duration(0), volume=Volume(200), loop_count=0, auto_stop_seconds=2)

    assert codes == (
        ErrorCodeEnum.TIMER_DURATION_TOO_SHORT,
        ErrorCodeEnum.TIMER_VOLUME_OUT_OF_RANGE,
        ErrorCodeEnum.TIMER_LOOP_COUNT_OUT_OF_RANGE,
        ErrorCodeEnum.TIMER_AUTO_STOP_OUT_OF_RANGE,
    )
