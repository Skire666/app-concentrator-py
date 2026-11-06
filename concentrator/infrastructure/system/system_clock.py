"""Clock backed by the operating system."""

import time
from datetime import UTC, datetime
from typing import override

from concentrator.application.ports.clock_port import ClockPort


class SystemClock(ClockPort):
    """Real wall-clock and monotonic time."""

    @override
    def now_utc(self) -> datetime:
        return datetime.now(UTC)

    @override
    def now_local(self) -> datetime:
        return datetime.now(UTC).astimezone()

    @override
    def monotonic(self) -> float:
        return time.monotonic()
