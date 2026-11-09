from dataclasses import replace
from datetime import UTC, datetime

import pytest

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.timer.hourly_chime import HourlyChime, HourlyChimeId
from concentrator.domain.timer.hourly_chime_rules import HourlyChimeRules
from concentrator.domain.timer.sound_ref import SoundRef
from concentrator.domain.timer.volume import Volume
from tests.fakes.timer_extras_factory import DEFAULT_CHIME_SETTINGS, make_chime

NOW = datetime(2026, 11, 9, 10, 0, tzinfo=UTC)


def _codes(**changes: object) -> tuple[ErrorCodeEnum, ...]:
    return HourlyChimeRules.validate_settings(replace(DEFAULT_CHIME_SETTINGS, **changes)).error_codes


def test_create_and_changes_set_updated_at() -> None:
    chime = HourlyChime.create(HourlyChimeId("c"), NOW, enabled=False, settings=DEFAULT_CHIME_SETTINGS)
    later = datetime(2026, 11, 9, 11, 0, tzinfo=UTC)
    quiet = replace(DEFAULT_CHIME_SETTINGS, volume=Volume(10))

    switched = chime.with_enabled(True, later)
    edited = chime.with_settings(quiet, later)

    assert (chime.created_at, chime.updated_at, chime.enabled) == (NOW, NOW, False)
    assert (switched.enabled, switched.updated_at, switched.settings) == (True, later, DEFAULT_CHIME_SETTINGS)
    assert (edited.settings, edited.updated_at, edited.enabled) == (quiet, later, False)


@pytest.mark.parametrize(("hour", "covered"), [(7, False), (8, True), (14, True), (20, True), (21, False)])
def test_covers_the_active_hours_inclusively(hour: int, covered: bool) -> None:
    assert DEFAULT_CHIME_SETTINGS.covers(hour) is covered


def test_spec_example_is_valid() -> None:
    assert HourlyChimeRules.validate(make_chime()).is_success


def test_validate_includes_identity_checks() -> None:
    chime = replace(make_chime(), id=HourlyChimeId(""), updated_at=NOW.replace(tzinfo=None))

    assert HourlyChimeRules.validate(chime).error_codes == (
        ErrorCodeEnum.REQUIRED_VALUE_MISSING,
        ErrorCodeEnum.DATETIME_NOT_UTC,
    )


def test_all_day_is_valid() -> None:
    assert _codes(start_hour=0, end_hour=23) == ()


def test_same_start_and_end_hour_is_valid() -> None:
    assert _codes(start_hour=12, end_hour=12) == ()


@pytest.mark.parametrize(("start", "end", "field"), [(-1, 20, "start_hour"), (8, 24, "end_hour")])
def test_hour_out_of_range_names_its_field(start: int, end: int, field: str) -> None:
    result = HourlyChimeRules.validate_settings(replace(DEFAULT_CHIME_SETTINGS, start_hour=start, end_hour=end))

    assert result.error_codes == (ErrorCodeEnum.CHIME_HOUR_OUT_OF_RANGE,)
    assert result.issues[0].field == field
    assert result.issues[0].params == (("min", "0"), ("max", "23"))


def test_reversed_hours_are_reported_on_the_end_hour() -> None:
    result = HourlyChimeRules.validate_settings(replace(DEFAULT_CHIME_SETTINGS, start_hour=21, end_hour=8))

    assert result.error_codes == (ErrorCodeEnum.CHIME_HOURS_REVERSED,)
    assert result.issues[0].field == "end_hour"


def test_sound_and_volume_use_the_alarm_rules() -> None:
    assert _codes(sound=SoundRef.builtin(" "), volume=Volume(101)) == (
        ErrorCodeEnum.TIMER_SOUND_UNSET,
        ErrorCodeEnum.TIMER_VOLUME_OUT_OF_RANGE,
    )
