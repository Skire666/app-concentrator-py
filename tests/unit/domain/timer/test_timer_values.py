from datetime import UTC, datetime, timedelta

import pytest

from concentrator.domain.timer.duration import Duration
from concentrator.domain.timer.sound_kind_enum import SoundKindEnum
from concentrator.domain.timer.sound_ref import SoundRef
from concentrator.domain.timer.timer_config import TimerConfig
from tests.fakes.timer_factory import DEFAULT_SETTINGS, SPEC_SETTINGS, TIMER_ID

NOW = datetime(2026, 11, 6, 16, 40, tzinfo=UTC)


def test_duration_from_hms_adds_the_parts() -> None:
    assert Duration.from_hms(1, 2, 3) == Duration(3723)


def test_duration_from_minutes() -> None:
    assert Duration.from_minutes(5) == Duration(300)


def test_duration_hms_splits_the_total() -> None:
    assert Duration(359_999).hms == (99, 59, 59)


def test_duration_milliseconds() -> None:
    assert Duration(2).milliseconds == 2000


@pytest.mark.parametrize(
    ("seconds", "text"), [(0, "00:00:00"), (1500, "00:25:00"), (3723, "01:02:03"), (360_000, "100:00:00")]
)
def test_duration_clock_text_is_zero_padded(seconds: int, text: str) -> None:
    assert Duration(seconds).as_clock_text() == text


def test_durations_are_ordered() -> None:
    assert Duration(1) < Duration(2)


def test_builtin_sound_is_trimmed() -> None:
    assert SoundRef.builtin("  alarm-classic ") == SoundRef(kind=SoundKindEnum.BUILTIN, value="alarm-classic")


def test_file_sound_uses_forward_slashes() -> None:
    sound = SoundRef.file(" E:\\Music\\long alarm.mp3 ")

    assert sound == SoundRef(kind=SoundKindEnum.FILE, value="E:/Music/long alarm.mp3")


def test_unc_file_sound_keeps_its_two_leading_slashes() -> None:
    assert SoundRef.file("\\\\server\\share\\a.mp3").value == "//server/share/a.mp3"


@pytest.mark.parametrize(
    ("kind", "value", "expected"),
    [
        (SoundKindEnum.FILE, "C:\\a.mp3", "C:/a.mp3"),
        (SoundKindEnum.BUILTIN, " chime ", "chime"),
        (SoundKindEnum.UNKNOWN, "x\\y", "x\\y"),
    ],
)
def test_stored_sound_is_normalized_like_the_factories(kind: SoundKindEnum, value: str, expected: str) -> None:
    sound = SoundRef.of(kind, value)

    assert sound.kind is kind
    assert sound.value == expected


def test_timer_config_create_sets_both_timestamps() -> None:
    config = TimerConfig.create(TIMER_ID, NOW, DEFAULT_SETTINGS)

    assert config.id == TIMER_ID
    assert config.created_at == config.updated_at == NOW
    assert config.settings == DEFAULT_SETTINGS


def test_timer_config_with_settings_changes_updated_at_only() -> None:
    config = TimerConfig.create(TIMER_ID, NOW, DEFAULT_SETTINGS)
    later = NOW + timedelta(minutes=3)

    changed = config.with_settings(SPEC_SETTINGS, later)

    assert changed.settings == SPEC_SETTINGS
    assert changed.created_at == NOW
    assert changed.updated_at == later
    assert config.settings == DEFAULT_SETTINGS
