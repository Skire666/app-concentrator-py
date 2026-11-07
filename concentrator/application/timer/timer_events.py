"""Events published by the timer engine and the timer use cases."""

from dataclasses import dataclass

from concentrator.domain.timer.timer_config import TimerConfig
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
