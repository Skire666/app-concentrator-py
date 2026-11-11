"""Repetition of a task: frequency, interval, weekdays, anchor and end condition."""

from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import date
from typing import Self

from concentrator.domain.todo.recurrence_end_enum import RecurrenceEndEnum
from concentrator.domain.todo.recurrence_frequency_enum import RecurrenceFrequencyEnum
from concentrator.domain.todo.weekday_enum import WeekdayEnum


@dataclass(frozen=True, slots=True, kw_only=True)
class Recurrence:
    """Value object stored in ``Task.recurrence``; checked by ``RecurrenceRules``.

    Build it with ``create``, which drops the values that do not apply to the frequency and end kind, so
    two recurrences that behave the same compare equal.

    Attributes:
        frequency: Unit of the interval.
        interval: Every ``interval`` days, weeks, months or years.
        weekdays: Days of a weekly recurrence, Monday first, without repeats; ``()`` otherwise.
        anchor_date: First due date of the series; drives the week parity, the day of the month and the
            day of the year.
        end_kind: When the series stops.
        end_date: Last possible due date (``ON_DATE`` only).
        end_count: Number of occurrences to complete (``AFTER_COUNT`` only).
    """

    frequency: RecurrenceFrequencyEnum
    interval: int
    weekdays: tuple[WeekdayEnum, ...] = ()
    anchor_date: date
    end_kind: RecurrenceEndEnum
    end_date: date | None = None
    end_count: int | None = None

    @classmethod
    def create(
        cls,
        *,
        frequency: RecurrenceFrequencyEnum,
        interval: int,
        anchor_date: date,
        end_kind: RecurrenceEndEnum,
        weekdays: Iterable[WeekdayEnum] = (),
        end_date: date | None = None,
        end_count: int | None = None,
    ) -> Self:
        """Build a normalized recurrence.

        Args:
            frequency: Unit of the interval.
            interval: Number of units between two occurrences.
            anchor_date: First due date of the series.
            end_kind: When the series stops.
            weekdays: Days of a weekly recurrence (ignored for the other frequencies).
            end_date: Last possible due date (ignored unless ``ON_DATE``).
            end_count: Occurrences to complete (ignored unless ``AFTER_COUNT``).

        Returns:
            The recurrence; validate it with ``RecurrenceRules``.
        """
        days = tuple(sorted(set(weekdays))) if frequency is RecurrenceFrequencyEnum.WEEKLY else ()
        return cls(
            frequency=frequency,
            interval=interval,
            weekdays=days,
            anchor_date=anchor_date,
            end_kind=end_kind,
            end_date=end_date if end_kind is RecurrenceEndEnum.ON_DATE else None,
            end_count=end_count if end_kind is RecurrenceEndEnum.AFTER_COUNT else None,
        )

    def with_anchor(self, anchor_date: date) -> Self:
        """Start the series again on another date.

        Args:
            anchor_date: New first due date.

        Returns:
            The recurrence, or this one when the anchor is the same.
        """
        if anchor_date == self.anchor_date:
            return self
        return replace(self, anchor_date=anchor_date)


def anchored(recurrence: Recurrence | None, due_date: date | None, *, due_changed: bool) -> Recurrence | None:
    """Anchor a recurrence chosen or kept by the user (owner decision, phase 6 plan).

    A due date changed by hand starts the series again on that date; completing an occurrence never
    moves the anchor.

    Args:
        recurrence: Recurrence entered, ``None`` for a one-off task.
        due_date: Due date entered.
        due_changed: Whether the due date differs from the stored one, or the task had no recurrence.

    Returns:
        The recurrence to store.
    """
    if recurrence is None or due_date is None or not due_changed:
        return recurrence
    return recurrence.with_anchor(due_date)
