"""Favorites and hourly chime for tests, mirroring the phase 3 spec example and the shipped ini."""

from datetime import UTC, datetime
from typing import Final

from concentrator.application.settings.settings_defaults import SettingsDefaults
from concentrator.application.storage.user_data_defaults import SectionDefaults
from concentrator.domain.settings.log_level_enum import LogLevelEnum
from concentrator.domain.timer.chime_settings import ChimeSettings
from concentrator.domain.timer.duration import Duration
from concentrator.domain.timer.hourly_chime import HourlyChime, HourlyChimeId
from concentrator.domain.timer.sound_ref import SoundRef
from concentrator.domain.timer.timer_preset import TimerPreset, TimerPresetId
from concentrator.domain.timer.timer_presets_collection import TimerPresetsCollection
from concentrator.domain.timer.volume import Volume
from tests.fakes.timer_factory import DEFAULT_SETTINGS

EXTRAS_CREATED_AT: Final = datetime(2026, 11, 6, 16, 40, tzinfo=UTC)
SPEC_PRESET_ID: Final = TimerPresetId("019a5c20-1111-7aaa-8bbb-1c2d3e4f5a6b")
CHIME_ID: Final = HourlyChimeId("019a5c20-2222-7ccc-8ddd-2d3e4f5a6b7c")
CHIME_SOUND: Final = SoundRef.builtin("chime")
DEFAULT_PRESET_MINUTES: Final = (15, 30, 45)

DEFAULT_CHIME_SETTINGS: Final = ChimeSettings(sound=CHIME_SOUND, volume=Volume(60), start_hour=8, end_hour=20)
DEFAULT_SECTIONS: Final = SectionDefaults(
    timer=DEFAULT_SETTINGS,
    presets=tuple(Duration.from_minutes(minutes) for minutes in DEFAULT_PRESET_MINUTES),
    chime_enabled=False,
    chime=DEFAULT_CHIME_SETTINGS,
    settings=SettingsDefaults(log_level=LogLevelEnum.INFO, notify_when_inactive=True),
)


def make_preset(
    minutes: int, position: int = 0, label: str = "", preset_id: str = "", seconds: int | None = None
) -> TimerPreset:
    """A favorite; the id defaults to ``preset-<minutes>``."""
    return TimerPreset(
        id=TimerPresetId(preset_id or f"preset-{minutes}"),
        created_at=EXTRAS_CREATED_AT,
        updated_at=EXTRAS_CREATED_AT,
        label=label,
        duration=Duration(minutes * 60 if seconds is None else seconds),
        position=position,
    )


def make_presets(*minutes: int) -> TimerPresetsCollection:
    """Favorites at positions 0, 1, 2... (15, 30 and 45 minutes by default)."""
    values = minutes or DEFAULT_PRESET_MINUTES
    return TimerPresetsCollection(make_preset(value, position) for position, value in enumerate(values))


def make_spec_presets() -> TimerPresetsCollection:
    """The ``[[timer_presets]]`` element of the spec example."""
    return TimerPresetsCollection((make_preset(15, preset_id=SPEC_PRESET_ID),))


def make_chime(*, enabled: bool = False, settings: ChimeSettings = DEFAULT_CHIME_SETTINGS) -> HourlyChime:
    """The ``[hourly_chime]`` section of the spec example."""
    return HourlyChime(
        id=CHIME_ID, created_at=EXTRAS_CREATED_AT, updated_at=EXTRAS_CREATED_AT, enabled=enabled, settings=settings
    )
