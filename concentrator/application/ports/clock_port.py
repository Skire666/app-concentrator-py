"""Access to the current time."""

from datetime import datetime
from typing import Protocol


class ClockPort(Protocol):
    """Wall-clock and monotonic time. The domain never reads the clock: use cases pass ``now`` in.

    Wall-clock instants are whole seconds, as stored in the user data file (ADR-030); the monotonic
    time keeps full precision for durations.
    """

    def now_utc(self) -> datetime:
        """Return the current instant.

        Returns:
            Timezone-aware UTC datetime, microseconds set to zero.
        """
        ...

    def now_local(self) -> datetime:
        """Return the current instant in the local time zone of the machine.

        Returns:
            Timezone-aware local datetime, microseconds set to zero.
        """
        ...

    def to_local(self, moment: datetime) -> datetime:
        """Convert an instant to the local time zone of the machine (for display).

        Args:
            moment: Timezone-aware instant, usually UTC.

        Returns:
            The same instant as a timezone-aware local datetime.
        """
        ...

    def monotonic(self) -> float:
        """Return a monotonic time for measuring durations.

        Returns:
            Seconds since an arbitrary origin, at full precision; never goes backwards.
        """
        ...
