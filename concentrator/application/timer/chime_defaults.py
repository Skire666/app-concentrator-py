"""Hourly chime values of ``concentrator.ini`` turned into domain objects."""

from dataclasses import dataclass
from typing import Self

from concentrator.application.common.app_config import ChimeSection
from concentrator.domain.timer.chime_settings import ChimeSettings
from concentrator.domain.timer.sound_ref import SoundRef
from concentrator.domain.timer.volume import Volume


@dataclass(frozen=True, slots=True, kw_only=True)
class ChimeDefaults:
    """Defaults and trigger window of the hourly chime.

    Attributes:
        enabled: Switch of a new data file.
        settings: Sound, volume and hours of a new data file.
        fallback_sound: Built-in sound played when the chosen one cannot be found.
        trigger_window_seconds: How late after ``H:00:00`` the chime of ``H`` still plays.
    """

    enabled: bool
    settings: ChimeSettings
    fallback_sound: SoundRef
    trigger_window_seconds: int

    @classmethod
    def from_section(cls, section: ChimeSection) -> Self:
        """Build the values from the ``[chime]`` section.

        Args:
            section: Loaded section (its ranges are already validated).

        Returns:
            The defaults.
        """
        sound = SoundRef.builtin(section.default_sound)
        settings = ChimeSettings(
            sound=sound,
            volume=Volume(section.default_volume),
            start_hour=section.default_start_hour,
            end_hour=section.default_end_hour,
        )
        return cls(
            enabled=section.default_enabled,
            settings=settings,
            fallback_sound=sound,
            trigger_window_seconds=section.trigger_window_seconds,
        )
