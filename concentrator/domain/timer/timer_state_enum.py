"""States of the countdown."""

from concentrator.domain.common.base_int_enum import BaseIntEnum


class TimerStateEnum(BaseIntEnum):
    """State of ``TimerSession`` (phase 2 spec, "State machine")."""

    UNKNOWN = -1
    UNSET = 0
    IDLE = 1
    RUNNING = 2
    PAUSED = 3
    RINGING = 4
