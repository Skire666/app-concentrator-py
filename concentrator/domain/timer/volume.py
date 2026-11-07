"""Volume value object: a percentage."""

from dataclasses import dataclass
from typing import Final

MIN_VOLUME_PERCENT: Final = 0
MAX_VOLUME_PERCENT: Final = 100


@dataclass(frozen=True, slots=True, order=True)
class Volume:
    """Playback volume, ``MIN_VOLUME_PERCENT`` to ``MAX_VOLUME_PERCENT``; checked by ``TimerConfigRules``.

    The audio adapter converts it from the perceived (logarithmic) scale to the linear one.

    Attributes:
        percent: Volume in percent.
    """

    percent: int
