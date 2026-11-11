"""Dates of a recurring task."""

import calendar
from dataclasses import dataclass
from datetime import MAXYEAR, MINYEAR, date, timedelta
from typing import Final

from concentrator.domain.todo.recurrence import Recurrence
from concentrator.domain.todo.recurrence_frequency_enum import RecurrenceFrequencyEnum
from concentrator.domain.todo.weekday_enum import WeekdayEnum

DAYS_PER_WEEK: Final = 7
MONTHS_PER_YEAR: Final = 12
_WEEK_STEPS: Final = 3
"""Weeks looked at by the weekly search: the rest of the current week, then a whole valid week."""


@dataclass(frozen=True, slots=True, kw_only=True)
class NextOccurrence:
    """Where a recurring task goes when an occurrence is completed.

    Attributes:
        due_date: Next due date, ``None`` when the series has no later date.
        skipped: Dates of the series passed over because they were already in the past.
    """

    due_date: date | None
    skipped: int


def _monday(day: date) -> date:
    """Monday of the week of a date.

    Args:
        day: Any date.

    Returns:
        The Monday.
    """
    return day - timedelta(days=day.isoweekday() - 1)


def _clamped(year: int, month: int, day: int) -> date | None:
    """Build a date, moving a missing day to the last day of the month (31 -> 30 April, 29 -> 28 February).

    Args:
        year: Year.
        month: Month, 1 to 12.
        day: Wanted day of the month.

    Returns:
        The date, ``None`` beyond the last supported year.
    """
    if year > MAXYEAR:
        return None
    return date(year, month, min(day, calendar.monthrange(year, month)[1]))


def _days_later(day: date, days: int) -> date | None:
    """Add days to a date without overflowing.

    Args:
        day: Start.
        days: Days to add (positive).

    Returns:
        The date, ``None`` beyond the last supported date.
    """
    if (date.max - day).days < days:
        return None
    return day + timedelta(days=days)


class RecurrenceCalculator:
    """Pure date arithmetic of the ``Recurrence`` series (phase 6 spec)."""

    @staticmethod
    def next_after(recurrence: Recurrence, current: date) -> date | None:
        """Return the first date of the series strictly after a date.

        Args:
            recurrence: Valid recurrence (interval >= 1, weekdays for weekly).
            current: Date to move from (usually the current due date).

        Returns:
            The date, or ``None`` when there is none (empty weekdays, end of the calendar).
        """
        match recurrence.frequency:
            case RecurrenceFrequencyEnum.DAILY:
                return RecurrenceCalculator._next_daily(recurrence, current)
            case RecurrenceFrequencyEnum.WEEKLY:
                return RecurrenceCalculator._next_weekly(recurrence, current)
            case RecurrenceFrequencyEnum.MONTHLY:
                return RecurrenceCalculator._next_by_months(recurrence, current, recurrence.interval)
            case RecurrenceFrequencyEnum.YEARLY:
                return RecurrenceCalculator._next_by_months(recurrence, current, recurrence.interval * MONTHS_PER_YEAR)
            case _:
                return None

    @staticmethod
    def next_from(recurrence: Recurrence, current: date, today: date) -> NextOccurrence:
        """Return the next due date of a completed occurrence: the first date after ``current`` that is not past.

        A series late by several dates jumps to today or later (owner decision, phase 6 plan); the dates
        passed over are counted, not completed.

        Args:
            recurrence: Valid recurrence.
            current: Due date of the completed occurrence.
            today: Current local date.

        Returns:
            The next due date and the number of dates skipped.
        """
        following = RecurrenceCalculator.next_after(recurrence, current)
        skipped = 0
        while following is not None and following < today:
            skipped += 1
            following = RecurrenceCalculator.next_after(recurrence, following)
        return NextOccurrence(due_date=following, skipped=skipped)

    @staticmethod
    def upcoming(recurrence: Recurrence, current: date, count: int) -> tuple[date, ...]:
        """Return the dates that follow a due date (preview of the editor).

        Args:
            recurrence: Valid recurrence.
            current: Due date.
            count: Number of dates wanted.

        Returns:
            Up to ``count`` dates, in order.
        """
        dates: list[date] = []
        following = RecurrenceCalculator.next_after(recurrence, current)
        while following is not None and len(dates) < count:
            dates.append(following)
            following = RecurrenceCalculator.next_after(recurrence, following)
        return tuple(dates)

    @staticmethod
    def _next_daily(recurrence: Recurrence, current: date) -> date | None:
        """Every ``interval`` days from the anchor.

        Args:
            recurrence: Daily recurrence.
            current: Date to move from.

        Returns:
            The next date.
        """
        steps = (current - recurrence.anchor_date).days // recurrence.interval + 1
        offset = steps * recurrence.interval - (current - recurrence.anchor_date).days
        return _days_later(current, offset)

    @staticmethod
    def _next_weekly(recurrence: Recurrence, current: date) -> date | None:
        """Chosen weekdays of the weeks that are a multiple of ``interval`` weeks after the anchor week.

        The search is bounded: the rest of the current week, then the next valid week, which holds every
        chosen weekday.

        Args:
            recurrence: Weekly recurrence.
            current: Date to move from.

        Returns:
            The next date, ``None`` without weekdays.
        """
        anchor_monday = _monday(recurrence.anchor_date)
        day = _days_later(current, 1)
        for _ in range(_WEEK_STEPS):
            if day is None:
                return None
            week = (_monday(day) - anchor_monday).days // DAYS_PER_WEEK
            late_weeks = -week % recurrence.interval
            if late_weeks:
                day = _days_later(_monday(day), late_weeks * DAYS_PER_WEEK)
                continue
            found = next(
                (
                    later
                    for later in RecurrenceCalculator._rest_of_week(day)
                    if WeekdayEnum.of(later) in recurrence.weekdays
                ),
                None,
            )
            if found is not None:
                return found
            day = _days_later(_monday(day), DAYS_PER_WEEK)
        return None

    @staticmethod
    def _rest_of_week(day: date) -> tuple[date, ...]:
        """Days from a date to the Sunday of its week.

        Args:
            day: Start.

        Returns:
            The days, in order (stops at the last supported date).
        """
        days = DAYS_PER_WEEK - day.isoweekday() + 1
        return tuple(later for offset in range(days) if (later := _days_later(day, offset)) is not None)

    @staticmethod
    def _next_by_months(recurrence: Recurrence, current: date, months: int) -> date | None:
        """Same day as the anchor every ``months`` months, clamped to the end of shorter months.

        Args:
            recurrence: Monthly or yearly recurrence.
            current: Date to move from.
            months: Months between two dates (12 x interval for yearly).

        Returns:
            The next date.
        """
        anchor = recurrence.anchor_date
        elapsed = (current.year - anchor.year) * MONTHS_PER_YEAR + current.month - anchor.month
        step = elapsed // months
        for candidate_step in (step, step + 1):
            month_index = anchor.year * MONTHS_PER_YEAR + anchor.month - 1 + candidate_step * months
            if month_index // MONTHS_PER_YEAR < MINYEAR:
                continue
            candidate = _clamped(month_index // MONTHS_PER_YEAR, month_index % MONTHS_PER_YEAR + 1, anchor.day)
            if candidate is None or candidate > current:
                return candidate
        return None
