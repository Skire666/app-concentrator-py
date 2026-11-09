"""The editable values of the hourly chime, apart from the on/off switch."""

from dataclasses import dataclass

from concentrator.domain.timer.sound_ref import SoundRef
from concentrator.domain.timer.volume import Volume


@dataclass(frozen=True, slots=True, kw_only=True)
class ChimeSettings:
    """Sound, volume and active hours, as edited in the chime dialog; checked by ``HourlyChimeRules``.

    Attributes:
        sound: Chime sound.
        volume: Chime volume.
        start_hour: First full hour that chimes (0-23, local time).
        end_hour: Last full hour that chimes (0-23, not before ``start_hour``).
    """

    sound: SoundRef
    volume: Volume
    start_hour: int
    end_hour: int

    def covers(self, hour: int) -> bool:
        """Tell whether a full hour is within the active hours.

        Args:
            hour: Local hour (0-23).

        Returns:
            Whether ``start_hour <= hour <= end_hour``.
        """
        return self.start_hour <= hour <= self.end_hour
