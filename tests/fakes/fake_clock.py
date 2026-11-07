"""Deterministic clock."""

from datetime import UTC, datetime, timedelta, timezone
from typing import Final, override

from concentrator.application.ports.clock_port import ClockPort

DEFAULT_START: Final = datetime(2026, 11, 6, 9, 0, tzinfo=UTC)
LOCAL_ZONE: Final = timezone(timedelta(hours=1))


class FakeClock(ClockPort):
    """Clock that only moves when ``advance`` is called; local time is UTC+1.

    Like ``SystemClock``, wall-clock instants are whole seconds and the monotonic time is not rounded.
    """

    def __init__(self, start: datetime = DEFAULT_START) -> None:
        self._now = start
        self._monotonic = 1000.0

    def advance(self, *, ms: float = 0.0, seconds: float = 0.0) -> None:
        """Move wall-clock and monotonic time forward."""
        delta = seconds + ms / 1000.0
        self._now += timedelta(seconds=delta)
        self._monotonic += delta

    @override
    def now_utc(self) -> datetime:
        return self._now.replace(microsecond=0)

    @override
    def now_local(self) -> datetime:
        return self.to_local(self.now_utc())

    @override
    def to_local(self, moment: datetime) -> datetime:
        return moment.astimezone(LOCAL_ZONE)

    @override
    def monotonic(self) -> float:
        return self._monotonic
