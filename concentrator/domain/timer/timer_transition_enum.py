"""Transitions of the countdown, published with each timer change."""

from concentrator.domain.common.base_int_enum import BaseIntEnum


class TimerTransitionEnum(BaseIntEnum):
    """What made the timer change state."""

    UNKNOWN = -1
    UNSET = 0
    STARTED = 1
    PAUSED = 2
    RESUMED = 3
    RESET = 4
    ALARM_STARTED = 5
    ACKNOWLEDGED = 6
    RESTARTED = 7
    SNOOZED = 8
    AUTO_STOPPED = 9
    AUTO_RESTARTED = 10
