"""Due date filter of the task table."""

from concentrator.domain.common.base_int_enum import BaseIntEnum


class DueFilterEnum(BaseIntEnum):
    """Which due dates the task table shows (weeks start on Monday)."""

    UNKNOWN = -1
    UNSET = 0
    ALL = 1
    OVERDUE = 2
    TODAY = 3
    THIS_WEEK = 4
    NEXT_7_DAYS = 5
    WITH_DATE = 6
    NO_DATE = 7
