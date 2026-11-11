"""How often a recurring task comes back."""

from concentrator.domain.common.base_int_enum import BaseIntEnum


class RecurrenceFrequencyEnum(BaseIntEnum):
    """Unit of the interval of a ``Recurrence``."""

    UNKNOWN = -1
    UNSET = 0
    DAILY = 1
    WEEKLY = 2
    MONTHLY = 3
    YEARLY = 4
