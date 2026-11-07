"""Independently rendered areas of the window."""

from concentrator.domain.common.base_int_enum import BaseIntEnum


class RenderSectionEnum(BaseIntEnum):
    """One section per registered panel snapshot. Later phases append values."""

    UNKNOWN = -1
    UNSET = 0
    SHELL = 1
    STATUS_BAR = 2
    FIRST_RUN = 3
    RECOVERY = 4
    TIMER = 5
    TIMER_EDIT = 6
    TRAY = 7
