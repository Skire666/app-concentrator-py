"""When a recurring task stops coming back."""

from concentrator.domain.common.base_int_enum import BaseIntEnum


class RecurrenceEndEnum(BaseIntEnum):
    """End condition of a ``Recurrence``."""

    UNKNOWN = -1
    UNSET = 0
    NEVER = 1
    ON_DATE = 2
    AFTER_COUNT = 3
