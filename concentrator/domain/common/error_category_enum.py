"""Category of an error code, derived from its numeric range."""

from concentrator.domain.common.base_int_enum import BaseIntEnum


class ErrorCategoryEnum(BaseIntEnum):
    """Thousands digit of an ``ErrorCodeEnum`` value."""

    UNKNOWN = -1
    UNSET = 0
    COMMON = 1
    STORAGE = 2
    CONFIG = 3
    TIMER = 4
    TODO = 5
    FOCUS = 6
    SYSTEM = 7
