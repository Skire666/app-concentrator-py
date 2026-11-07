"""Limits of the timer configuration, built from ``concentrator.ini`` by the application layer."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class TimerLimits:
    """Bounds used by ``TimerConfigRules`` (the volume bounds are fixed by ``Volume``).

    Attributes:
        min_duration_seconds: Shortest countdown.
        max_duration_seconds: Longest countdown.
        max_loop_count: Highest play count (the lowest is 1).
        min_auto_stop_seconds: Shortest automatic stop (0 means never).
        max_auto_stop_seconds: Longest automatic stop.
    """

    min_duration_seconds: int
    max_duration_seconds: int
    max_loop_count: int
    min_auto_stop_seconds: int
    max_auto_stop_seconds: int
