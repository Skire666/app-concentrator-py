"""Priority of a task list."""

from concentrator.domain.common.base_int_enum import BaseIntEnum


class PriorityEnum(BaseIntEnum):
    """Priority of a list: the tabs show the most urgent lists first."""

    UNKNOWN = -1
    UNSET = 0
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
