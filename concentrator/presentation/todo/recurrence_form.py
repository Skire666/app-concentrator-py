"""Repeat section of the task dialog: the draft of a recurrence (phase 6 spec)."""

from dataclasses import dataclass, replace
from datetime import date
from typing import Final, Self

from concentrator.domain.todo.recurrence import Recurrence
from concentrator.domain.todo.recurrence_end_enum import RecurrenceEndEnum
from concentrator.domain.todo.recurrence_frequency_enum import RecurrenceFrequencyEnum
from concentrator.domain.todo.weekday_enum import WeekdayEnum

FREQUENCIES: Final = (
    RecurrenceFrequencyEnum.DAILY,
    RecurrenceFrequencyEnum.WEEKLY,
    RecurrenceFrequencyEnum.MONTHLY,
    RecurrenceFrequencyEnum.YEARLY,
)
"""Frequencies offered, in order."""

END_KINDS: Final = (RecurrenceEndEnum.NEVER, RecurrenceEndEnum.ON_DATE, RecurrenceEndEnum.AFTER_COUNT)
"""End conditions offered, in order."""

WEEK: Final = tuple(day for day in WeekdayEnum if day.is_set)
"""Weekdays, Monday first."""

INITIAL_END_COUNT: Final = 10
"""Count shown when "After N times" is chosen for a new series."""


@dataclass(frozen=True, slots=True, kw_only=True)
class RecurrenceDraft:
    """Values of the Repeat section; the fields are kept while the section is off.

    Attributes:
        enabled: Whether the task repeats.
        frequency: Unit of the interval.
        interval: Every N units.
        weekdays: Days of a weekly series, Monday first.
        anchor_date: Anchor of the stored series, ``None`` for a new one (the due date anchors it).
        end_kind: When the series stops.
        end_date: Last possible due date (``ON_DATE``).
        end_count: Occurrences to complete (``AFTER_COUNT``).
    """

    enabled: bool = False
    frequency: RecurrenceFrequencyEnum = RecurrenceFrequencyEnum.WEEKLY
    interval: int = 1
    weekdays: tuple[WeekdayEnum, ...] = ()
    anchor_date: date | None = None
    end_kind: RecurrenceEndEnum = RecurrenceEndEnum.NEVER
    end_date: date | None = None
    end_count: int = INITIAL_END_COUNT

    @classmethod
    def of(cls, recurrence: Recurrence | None) -> Self:
        """Values of a stored recurrence.

        Args:
            recurrence: Recurrence of the task, ``None`` for a one-off task.

        Returns:
            The draft (off for a one-off task).
        """
        if recurrence is None:
            return cls()
        return cls(
            enabled=True,
            frequency=recurrence.frequency,
            interval=recurrence.interval,
            weekdays=recurrence.weekdays,
            anchor_date=recurrence.anchor_date,
            end_kind=recurrence.end_kind,
            end_date=recurrence.end_date,
            end_count=recurrence.end_count or INITIAL_END_COUNT,
        )

    @classmethod
    def started(cls, first_date: date) -> Self:
        """A new series, as the section shows it when Repeat is ticked: weekly on the weekday of the date.

        Args:
            first_date: Due date of the task, or today without one.

        Returns:
            The draft, on.
        """
        return cls(enabled=True, weekdays=(WeekdayEnum.of(first_date),), end_date=first_date)

    def with_weekday(self, day: WeekdayEnum, *, checked: bool) -> Self:
        """Add or remove a weekday.

        Args:
            day: Weekday toggled.
            checked: Whether it is now chosen.

        Returns:
            The draft with the days in week order.
        """
        days = set(self.weekdays)
        if checked:
            days.add(day)
        else:
            days.discard(day)
        return replace(self, weekdays=tuple(sorted(days)))

    def to_recurrence(self, due_date: date | None, today: date) -> Recurrence | None:
        """Build the recurrence the use cases take.

        Args:
            due_date: Due date of the draft.
            today: Anchor used while there is no due date (the rules then report the missing date).

        Returns:
            The recurrence, ``None`` when the section is off.
        """
        if not self.enabled:
            return None
        return Recurrence.create(
            frequency=self.frequency,
            interval=self.interval,
            weekdays=self.weekdays,
            anchor_date=self.anchor_date or due_date or today,
            end_kind=self.end_kind,
            end_date=self.end_date,
            end_count=self.end_count,
        )
