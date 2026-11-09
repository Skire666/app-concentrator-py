"""Events published by the timer engine and the timer, favorite and chime use cases."""

from dataclasses import dataclass

from concentrator.domain.timer.hourly_chime import HourlyChime
from concentrator.domain.timer.timer_config import TimerConfig
from concentrator.domain.timer.timer_presets_collection import TimerPresetsCollection
from concentrator.domain.timer.timer_transition_enum import TimerTransitionEnum


@dataclass(frozen=True, slots=True)
class TimerChangedEvent:
    """What the timer shows changed: state, displayed second or blink phase.

    Attributes:
        transitions: State transitions that happened, empty when only the display changed.
        displayed_seconds: Value of the display.
    """

    transitions: tuple[TimerTransitionEnum, ...]
    displayed_seconds: int


@dataclass(frozen=True, slots=True)
class TimerConfigChangedEvent:
    """The timer configuration changed in memory.

    Attributes:
        config: The new configuration.
    """

    config: TimerConfig


@dataclass(frozen=True, slots=True)
class TimerPresetsChangedEvent:
    """The favorites changed in memory (one event per use case, even when it changed several favorites).

    Attributes:
        presets: The new favorites, in stored order.
    """

    presets: TimerPresetsCollection


@dataclass(frozen=True, slots=True)
class HourlyChimeChangedEvent:
    """The hourly chime changed in memory.

    Attributes:
        chime: The new chime.
    """

    chime: HourlyChime
