"""Category of an error code, derived from its numeric range."""

from concentrator.domain.common.base_int_enum import BaseIntEnum


class ErrorCategoryEnum(BaseIntEnum):
    """Thousands digit of an ``ErrorCodeEnum`` value.

    6 (focus queue, removed by ADR-046) is never reused.
    """

    UNKNOWN = -1
    UNSET = 0
    COMMON = 1
    STORAGE = 2
    CONFIG = 3
    TIMER = 4
    TODO = 5
    SYSTEM = 7
