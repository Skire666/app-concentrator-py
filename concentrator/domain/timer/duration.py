"""Duration value object in whole seconds."""

from dataclasses import dataclass
from typing import Final, Self

SECONDS_PER_MINUTE: Final = 60
SECONDS_PER_HOUR: Final = 3600
MS_PER_SECOND: Final = 1000


@dataclass(frozen=True, slots=True, order=True)
class Duration:
    """A duration in whole seconds; ``TimerConfigRules`` checks its limits.

    Attributes:
        seconds: Total number of seconds.
    """

    seconds: int

    @classmethod
    def from_hms(cls, hours: int, minutes: int, seconds: int) -> Self:
        """Build a duration from hours, minutes and seconds.

        Args:
            hours: Hours.
            minutes: Minutes.
            seconds: Seconds.

        Returns:
            The total duration.
        """
        return cls(hours * SECONDS_PER_HOUR + minutes * SECONDS_PER_MINUTE + seconds)

    @classmethod
    def from_minutes(cls, minutes: int) -> Self:
        """Build a duration from whole minutes.

        Args:
            minutes: Minutes.

        Returns:
            The duration.
        """
        return cls(minutes * SECONDS_PER_MINUTE)

    @property
    def hms(self) -> tuple[int, int, int]:
        """Hours, minutes (0-59) and seconds (0-59) of a non-negative duration."""
        hours, rest = divmod(self.seconds, SECONDS_PER_HOUR)
        minutes, seconds = divmod(rest, SECONDS_PER_MINUTE)
        return hours, minutes, seconds

    @property
    def milliseconds(self) -> int:
        """The duration in milliseconds."""
        return self.seconds * MS_PER_SECOND

    def as_clock_text(self) -> str:
        """Return ``HH:MM:SS`` (at least two digits per part), the neutral form of the timer display.

        Returns:
            The text, for example ``00:25:00``.
        """
        hours, minutes, seconds = self.hms
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
