"""Access to the current time."""

from datetime import datetime
from typing import Protocol


class ClockPort(Protocol):
    """Wall-clock and monotonic time. The domain never reads the clock: use cases pass ``now`` in."""

    def now_utc(self) -> datetime:
        """Return the current instant.

        Returns:
            Timezone-aware UTC datetime.
        """
        ...

    def now_local(self) -> datetime:
        """Return the current instant in the local time zone of the machine.

        Returns:
            Timezone-aware local datetime.
        """
        ...

    def monotonic(self) -> float:
        """Return a monotonic time for measuring durations.

        Returns:
            Seconds since an arbitrary origin; never goes backwards.
        """
        ...
