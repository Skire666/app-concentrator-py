"""Independently rendered areas of the window."""

from concentrator.domain.common.base_int_enum import BaseIntEnum


class RenderSectionEnum(BaseIntEnum):
    """One section per registered panel snapshot. Later phases append values.

    7 (notification area icon, removed at the phase 2 review, ADR-038) is never reused.
    """

    UNKNOWN = -1
    UNSET = 0
    SHELL = 1
    STATUS_BAR = 2
    FIRST_RUN = 3
    RECOVERY = 4
    TIMER = 5
    TIMER_EDIT = 6
    PRESETS = 8
    PRESET_EDIT = 9
    SPECIAL_OPTIONS = 10
    CHIME_EDIT = 11
    JOURNAL = 12
