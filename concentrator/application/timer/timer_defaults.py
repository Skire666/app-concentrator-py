"""Timer values of ``concentrator.ini`` turned into domain objects."""

from dataclasses import dataclass
from typing import Self

from concentrator.application.common.app_config import TimerSection
from concentrator.domain.timer.duration import Duration
from concentrator.domain.timer.sound_ref import SoundRef
from concentrator.domain.timer.timer_limits import TimerLimits
from concentrator.domain.timer.timer_settings import TimerSettings
from concentrator.domain.timer.volume import Volume


@dataclass(frozen=True, slots=True, kw_only=True)
class TimerDefaults:
    """Defaults, limits and snooze of the timer.

    Attributes:
        settings: Configuration of a new data file.
        limits: Bounds checked by ``TimerConfigRules`` and ``TimerPresetRules``.
        snooze: Length of a snooze.
        fallback_sound: Built-in sound played when the chosen one cannot be found.
        presets: Favorites of a data file that has none yet, in order.
    """

    settings: TimerSettings
    limits: TimerLimits
    snooze: Duration
    fallback_sound: SoundRef
    presets: tuple[Duration, ...]

    @classmethod
    def from_section(cls, section: TimerSection) -> Self:
        """Build the values from the ``[timer]`` section.

        Args:
            section: Loaded section (its ranges are already validated).

        Returns:
            The defaults.
        """
        sound = SoundRef.builtin(section.default_sound)
        settings = TimerSettings(
            duration=Duration(section.default_duration_seconds),
            sound=sound,
            volume=Volume(section.default_volume),
            loop_count=section.default_loop_count,
            loop_forever=False,
            auto_stop_seconds=section.default_auto_stop_seconds,
            auto_restart=False,
        )
        limits = TimerLimits(
            min_duration_seconds=section.min_duration_seconds,
            max_duration_seconds=section.max_duration_seconds,
            max_loop_count=section.max_loop_count,
            min_auto_stop_seconds=section.min_auto_stop_seconds,
            max_auto_stop_seconds=section.max_auto_stop_seconds,
            max_presets=section.max_presets,
            max_preset_label_length=section.max_preset_label_length,
        )
        return cls(
            settings=settings,
            limits=limits,
            snooze=Duration.from_minutes(section.snooze_minutes),
            fallback_sound=sound,
            presets=tuple(Duration.from_minutes(minutes) for minutes in section.default_presets_minutes),
        )
