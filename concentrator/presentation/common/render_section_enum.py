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
    SETTINGS = 13
    TODO_TABS = 14
    TODO_TOOLBAR = 15
    TODO_TABLE = 16
    TODO_DETAILS = 17
    TASK_EDIT = 18
    LIST_EDIT = 19
    QUICK_ADD = 20
    TODO_FILTERS = 21
    TODO_HISTORY = 22
