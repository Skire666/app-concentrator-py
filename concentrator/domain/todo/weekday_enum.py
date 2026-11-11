"""Days of the week, Monday first (ISO 8601)."""

from datetime import date
from typing import Self

from concentrator.domain.common.base_int_enum import BaseIntEnum


class WeekdayEnum(BaseIntEnum):
    """Day of the week; the value is the ISO weekday number (``date.isoweekday``)."""

    UNKNOWN = -1
    UNSET = 0
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6
    SUNDAY = 7

    @classmethod
    def of(cls, day: date) -> Self:
        """Return the weekday of a date.

        Args:
            day: Any date.

        Returns:
            Its weekday.
        """
        return cls(day.isoweekday())
