from datetime import date, timedelta
from itertools import combinations

import pytest

from concentrator.domain.todo.recurrence import Recurrence, anchored
from concentrator.domain.todo.recurrence_calculator import NextOccurrence, RecurrenceCalculator
from concentrator.domain.todo.recurrence_end_enum import RecurrenceEndEnum
from concentrator.domain.todo.recurrence_frequency_enum import RecurrenceFrequencyEnum
from concentrator.domain.todo.weekday_enum import WeekdayEnum

REAL_WEEKDAYS = tuple(day for day in WeekdayEnum if day.is_set)


def _recurrence(
    frequency: RecurrenceFrequencyEnum, anchor: date, interval: int = 1, weekdays: tuple[WeekdayEnum, ...] = ()
) -> Recurrence:
    return Recurrence.create(
        frequency=frequency, interval=interval, weekdays=weekdays, anchor_date=anchor, end_kind=RecurrenceEndEnum.NEVER
    )


def test_create_keeps_only_the_values_of_the_frequency_and_end_kind() -> None:
    recurrence = Recurrence.create(
        frequency=RecurrenceFrequencyEnum.DAILY,
        interval=2,
        weekdays=(WeekdayEnum.FRIDAY,),
        anchor_date=date(2026, 11, 6),
        end_kind=RecurrenceEndEnum.ON_DATE,
        end_date=date(2026, 12, 1),
        end_count=4,
    )

    assert (recurrence.weekdays, recurrence.end_date, recurrence.end_count) == ((), date(2026, 12, 1), None)


def test_create_sorts_weekly_days_without_repeats() -> None:
    days = (WeekdayEnum.FRIDAY, WeekdayEnum.MONDAY, WeekdayEnum.FRIDAY)

    recurrence = _recurrence(RecurrenceFrequencyEnum.WEEKLY, date(2026, 11, 6), weekdays=days)

    assert recurrence.weekdays == (WeekdayEnum.MONDAY, WeekdayEnum.FRIDAY)


def test_anchored_moves_the_anchor_only_when_the_due_date_changed() -> None:
    recurrence = _recurrence(RecurrenceFrequencyEnum.DAILY, date(2026, 11, 6))

    moved = anchored(recurrence, date(2026, 11, 9), due_changed=True)

    assert moved is not None
    assert moved.anchor_date == date(2026, 11, 9)
    assert anchored(recurrence, date(2026, 11, 9), due_changed=False) is recurrence
    assert anchored(None, date(2026, 11, 9), due_changed=True) is None
    assert anchored(recurrence, None, due_changed=True) is recurrence
    assert recurrence.with_anchor(date(2026, 11, 6)) is recurrence


def test_daily_every_three_days_follows_the_anchor() -> None:
    recurrence = _recurrence(RecurrenceFrequencyEnum.DAILY, date(2026, 11, 10), interval=3)

    assert RecurrenceCalculator.upcoming(recurrence, date(2026, 11, 10), 3) == (
        date(2026, 11, 13),
        date(2026, 11, 16),
        date(2026, 11, 19),
    )
    assert RecurrenceCalculator.next_after(recurrence, date(2026, 11, 11)) == date(2026, 11, 13)
    assert RecurrenceCalculator.next_after(recurrence, date(2026, 11, 1)) == date(2026, 11, 4)


def test_weekly_monday_and_friday_every_two_weeks_crosses_month_and_year() -> None:
    days = (WeekdayEnum.MONDAY, WeekdayEnum.FRIDAY)
    recurrence = _recurrence(RecurrenceFrequencyEnum.WEEKLY, date(2026, 12, 21), interval=2, weekdays=days)

    assert RecurrenceCalculator.upcoming(recurrence, date(2026, 12, 21), 6) == (
        date(2026, 12, 25),
        date(2027, 1, 4),
        date(2027, 1, 8),
        date(2027, 1, 18),
        date(2027, 1, 22),
        date(2027, 2, 1),
    )


def test_monthly_on_the_31st_is_clamped_over_a_full_year() -> None:
    recurrence = _recurrence(RecurrenceFrequencyEnum.MONTHLY, date(2026, 10, 31))

    assert RecurrenceCalculator.upcoming(recurrence, date(2026, 10, 31), 12) == (
        date(2026, 11, 30),
        date(2026, 12, 31),
        date(2027, 1, 31),
        date(2027, 2, 28),
        date(2027, 3, 31),
        date(2027, 4, 30),
        date(2027, 5, 31),
        date(2027, 6, 30),
        date(2027, 7, 31),
        date(2027, 8, 31),
        date(2027, 9, 30),
        date(2027, 10, 31),
    )


def test_monthly_every_two_months_from_a_date_before_the_anchor() -> None:
    recurrence = _recurrence(RecurrenceFrequencyEnum.MONTHLY, date(2026, 11, 15), interval=2)

    assert RecurrenceCalculator.next_after(recurrence, date(2026, 6, 1)) == date(2026, 7, 15)
    assert RecurrenceCalculator.next_after(recurrence, date(2026, 11, 15)) == date(2027, 1, 15)


def test_yearly_on_29_february_over_eight_years() -> None:
    recurrence = _recurrence(RecurrenceFrequencyEnum.YEARLY, date(2028, 2, 29))

    assert RecurrenceCalculator.upcoming(recurrence, date(2028, 2, 29), 8) == (
        date(2029, 2, 28),
        date(2030, 2, 28),
        date(2031, 2, 28),
        date(2032, 2, 29),
        date(2033, 2, 28),
        date(2034, 2, 28),
        date(2035, 2, 28),
        date(2036, 2, 29),
    )


def test_yearly_every_two_years() -> None:
    recurrence = _recurrence(RecurrenceFrequencyEnum.YEARLY, date(2026, 3, 10), interval=2)

    assert RecurrenceCalculator.next_after(recurrence, date(2026, 3, 10)) == date(2028, 3, 10)
    assert RecurrenceCalculator.next_after(recurrence, date(2027, 1, 1)) == date(2028, 3, 10)


@pytest.mark.parametrize("interval", [1, 2, 5])
def test_weekly_search_ends_on_a_chosen_day_for_every_weekday_set(interval: int) -> None:
    anchor = date(2026, 11, 4)
    sets = [days for size in range(1, 8) for days in combinations(REAL_WEEKDAYS, size)]
    for days in sets:
        recurrence = _recurrence(RecurrenceFrequencyEnum.WEEKLY, anchor, interval=interval, weekdays=days)
        for offset in range(-3, 14):
            current = anchor + timedelta(days=offset)
            found = RecurrenceCalculator.next_after(recurrence, current)
            assert found is not None
            assert found > current
            assert WeekdayEnum.of(found) in days
            assert (found - anchor + timedelta(days=anchor.weekday())).days // 7 % interval == 0


def test_weekly_without_days_has_no_next_date() -> None:
    recurrence = Recurrence(
        frequency=RecurrenceFrequencyEnum.WEEKLY,
        interval=1,
        anchor_date=date(2026, 11, 4),
        end_kind=RecurrenceEndEnum.NEVER,
    )

    assert RecurrenceCalculator.next_after(recurrence, date(2026, 11, 4)) is None
    assert RecurrenceCalculator.upcoming(recurrence, date(2026, 11, 4), 3) == ()


@pytest.mark.parametrize(
    "frequency", [RecurrenceFrequencyEnum.DAILY, RecurrenceFrequencyEnum.MONTHLY, RecurrenceFrequencyEnum.YEARLY]
)
def test_no_next_date_after_the_end_of_the_calendar(frequency: RecurrenceFrequencyEnum) -> None:
    recurrence = _recurrence(frequency, date(9999, 12, 31))

    assert RecurrenceCalculator.next_after(recurrence, date(9999, 12, 31)) is None


def test_weekly_at_the_end_of_the_calendar_has_no_next_date() -> None:
    recurrence = _recurrence(RecurrenceFrequencyEnum.WEEKLY, date(9999, 12, 27), weekdays=(WeekdayEnum.MONDAY,))

    assert RecurrenceCalculator.next_after(recurrence, date(9999, 12, 27)) is None


def test_monthly_far_before_an_early_anchor_skips_years_before_the_first() -> None:
    recurrence = _recurrence(RecurrenceFrequencyEnum.YEARLY, date(500, 6, 1), interval=999)

    assert RecurrenceCalculator.next_after(recurrence, date(400, 1, 1)) == date(500, 6, 1)


@pytest.mark.parametrize("frequency", [RecurrenceFrequencyEnum.UNSET, RecurrenceFrequencyEnum.UNKNOWN])
def test_frequency_not_set_has_no_next_date(frequency: RecurrenceFrequencyEnum) -> None:
    recurrence = _recurrence(frequency, date(2026, 11, 4))

    assert RecurrenceCalculator.next_after(recurrence, date(2026, 11, 4)) is None


def test_next_from_jumps_over_past_dates_to_today_or_later() -> None:
    recurrence = _recurrence(
        RecurrenceFrequencyEnum.WEEKLY, date(2026, 10, 7), interval=3, weekdays=(WeekdayEnum.WEDNESDAY,)
    )

    assert RecurrenceCalculator.next_from(recurrence, date(2026, 10, 7), date(2026, 11, 11)) == NextOccurrence(
        due_date=date(2026, 11, 18), skipped=1
    )
    assert RecurrenceCalculator.next_from(recurrence, date(2026, 10, 7), date(2026, 10, 8)) == NextOccurrence(
        due_date=date(2026, 10, 28), skipped=0
    )


def test_next_from_keeps_a_date_that_is_today() -> None:
    recurrence = _recurrence(RecurrenceFrequencyEnum.DAILY, date(2026, 11, 1))

    assert RecurrenceCalculator.next_from(recurrence, date(2026, 11, 8), date(2026, 11, 11)) == NextOccurrence(
        due_date=date(2026, 11, 11), skipped=2
    )
    assert RecurrenceCalculator.next_from(recurrence, date(2026, 11, 11), date(2026, 11, 11)) == NextOccurrence(
        due_date=date(2026, 11, 12), skipped=0
    )
