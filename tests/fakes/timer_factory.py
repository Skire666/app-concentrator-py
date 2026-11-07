"""Timer values for tests, mirroring the shipped ``concentrator.ini`` and the phase 2 spec example."""

from datetime import UTC, datetime
from typing import Final

from concentrator.domain.timer.duration import Duration
from concentrator.domain.timer.sound_ref import SoundRef
from concentrator.domain.timer.timer_config import TimerConfig, TimerConfigId
from concentrator.domain.timer.timer_limits import TimerLimits
from concentrator.domain.timer.timer_settings import TimerSettings
from concentrator.domain.timer.volume import Volume

TIMER_ID: Final = TimerConfigId("019a5c1f-0b2e-7d4a-8c61-2a3b4c5d6e7f")
TIMER_CREATED_AT: Final = datetime(2026, 11, 6, 16, 40, tzinfo=UTC)
TIMER_UPDATED_AT: Final = datetime(2026, 11, 6, 16, 50, 12, tzinfo=UTC)
DEFAULT_SOUND: Final = SoundRef.builtin("alarm-classic")
SPEC_SOUND: Final = SoundRef.file("D:/Music/Alarms/long alarm.mp3")

LIMITS: Final = TimerLimits(
    min_duration_seconds=1,
    max_duration_seconds=359_999,
    max_loop_count=99,
    min_auto_stop_seconds=5,
    max_auto_stop_seconds=3600,
)

DEFAULT_SETTINGS: Final = TimerSettings(
    duration=Duration(1500),
    sound=DEFAULT_SOUND,
    volume=Volume(80),
    loop_count=3,
    loop_forever=False,
    auto_stop_seconds=120,
    auto_restart=False,
)

SPEC_SETTINGS: Final = TimerSettings(
    duration=Duration(1500),
    sound=SPEC_SOUND,
    volume=Volume(80),
    loop_count=3,
    loop_forever=False,
    auto_stop_seconds=120,
    auto_restart=False,
)


def make_timer_config(settings: TimerSettings = SPEC_SETTINGS) -> TimerConfig:
    return TimerConfig(id=TIMER_ID, created_at=TIMER_CREATED_AT, updated_at=TIMER_UPDATED_AT, settings=settings)
