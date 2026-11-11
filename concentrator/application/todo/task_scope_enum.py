"""Lists the task table shows."""

from concentrator.domain.common.base_int_enum import BaseIntEnum


class TaskScopeEnum(BaseIntEnum):
    """The tasks of the current list, or of every list (the table then shows a List column)."""

    UNKNOWN = -1
    UNSET = 0
    THIS_LIST = 1
    ALL_LISTS = 2
