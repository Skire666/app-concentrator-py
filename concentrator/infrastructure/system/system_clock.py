"""Clock backed by the operating system."""

import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import override

from concentrator.application.ports.clock_port import ClockPort


def _utc_now() -> datetime:
    """Read the operating system wall clock.

    Returns:
        Timezone-aware UTC datetime at full precision.
    """
    return datetime.now(UTC)


class SystemClock(ClockPort):
    """Real wall-clock time in whole seconds (ADR-030) and real monotonic time at full precision."""

    def __init__(
        self, *, wall_clock: Callable[[], datetime] = _utc_now, monotonic_clock: Callable[[], float] = time.monotonic
    ) -> None:
        """Create the clock.

        Args:
            wall_clock: Source of the UTC wall-clock time (replaced in tests).
            monotonic_clock: Source of the monotonic time (replaced in tests).
        """
        self._wall_clock = wall_clock
        self._monotonic_clock = monotonic_clock

    @override
    def now_utc(self) -> datetime:
        return self._wall_clock().replace(microsecond=0)

    @override
    def now_local(self) -> datetime:
        return self.to_local(self.now_utc())

    @override
    def to_local(self, moment: datetime) -> datetime:
        return moment.astimezone()

    @override
    def monotonic(self) -> float:
        return self._monotonic_clock()
