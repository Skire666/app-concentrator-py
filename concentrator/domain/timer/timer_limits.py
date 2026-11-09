"""Limits of the timer feature, built from ``concentrator.ini`` by the application layer."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class TimerLimits:
    """Bounds used by ``TimerConfigRules`` and ``TimerPresetRules`` (the volume bounds are fixed by ``Volume``).

    Attributes:
        min_duration_seconds: Shortest countdown (also the shortest favorite).
        max_duration_seconds: Longest countdown (also the longest favorite).
        max_loop_count: Highest play count (the lowest is 1).
        min_auto_stop_seconds: Shortest automatic stop (0 means never).
        max_auto_stop_seconds: Longest automatic stop.
        max_presets: Highest number of favorites.
        max_preset_label_length: Longest favorite label, in characters.
    """

    min_duration_seconds: int
    max_duration_seconds: int
    max_loop_count: int
    min_auto_stop_seconds: int
    max_auto_stop_seconds: int
    max_presets: int
    max_preset_label_length: int
