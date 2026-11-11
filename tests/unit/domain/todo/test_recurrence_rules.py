from dataclasses import replace
from datetime import date

import pytest

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.todo.recurrence import Recurrence
from concentrator.domain.todo.recurrence_end_enum import RecurrenceEndEnum
from concentrator.domain.todo.recurrence_frequency_enum import RecurrenceFrequencyEnum
from concentrator.domain.todo.recurrence_rules import RecurrenceRules
from concentrator.domain.todo.weekday_enum import WeekdayEnum
from tests.fakes.todo_factory import TODO_LIMITS

DUE = date(2026, 11, 13)
WEEKLY = Recurrence.create(
    frequency=RecurrenceFrequencyEnum.WEEKLY,
    interval=1,
    weekdays=(WeekdayEnum.FRIDAY,),
    anchor_date=DUE,
    end_kind=RecurrenceEndEnum.AFTER_COUNT,
    end_count=10,
)


def _issue(recurrence: Recurrence | None, due: date | None = DUE) -> tuple[ErrorCodeEnum, str] | None:
    failure = RecurrenceRules.validate(recurrence, due, TODO_LIMITS).first_failure
    return None if failure is None else (failure.code, failure.field)


def test_no_recurrence_and_a_valid_one_pass() -> None:
    assert RecurrenceRules.validate(None, None, TODO_LIMITS).is_success
    assert RecurrenceRules.validate(WEEKLY, DUE, TODO_LIMITS).is_success


def test_recurrence_requires_a_due_date() -> None:
    assert _issue(WEEKLY, None) == (ErrorCodeEnum.RECURRENCE_REQUIRES_DUE_DATE, "recurrence")


@pytest.mark.parametrize("interval", [0, 1000])
def test_interval_out_of_range(interval: int) -> None:
    result = RecurrenceRules.validate(replace(WEEKLY, interval=interval), DUE, TODO_LIMITS)

    issue = result.first_failure
    assert issue is not None
    assert (issue.code, issue.field, issue.params) == (
        ErrorCodeEnum.RECURRENCE_INTERVAL_OUT_OF_RANGE,
        "recurrence.interval",
        (("min", "1"), ("max", "999")),
    )


@pytest.mark.parametrize(
    ("frequency", "expected"),
    [
        (RecurrenceFrequencyEnum.UNSET, ErrorCodeEnum.RECURRENCE_FREQUENCY_UNSET),
        (RecurrenceFrequencyEnum.UNKNOWN, ErrorCodeEnum.ENUM_VALUE_UNKNOWN),
    ],
)
def test_frequency_must_be_chosen(frequency: RecurrenceFrequencyEnum, expected: ErrorCodeEnum) -> None:
    assert _issue(replace(WEEKLY, frequency=frequency)) == (expected, "recurrence.frequency")


def test_weekly_needs_days() -> None:
    assert _issue(replace(WEEKLY, weekdays=())) == (ErrorCodeEnum.RECURRENCE_WEEKDAYS_EMPTY, "recurrence.weekdays")


@pytest.mark.parametrize(
    ("day", "expected"),
    [(WeekdayEnum.UNKNOWN, ErrorCodeEnum.ENUM_VALUE_UNKNOWN), (WeekdayEnum.UNSET, ErrorCodeEnum.ENUM_VALUE_UNSET)],
)
def test_weekdays_must_be_real_days(day: WeekdayEnum, expected: ErrorCodeEnum) -> None:
    assert _issue(replace(WEEKLY, weekdays=(WeekdayEnum.MONDAY, day))) == (expected, "recurrence.weekdays")


@pytest.mark.parametrize(
    ("end_kind", "expected"),
    [
        (RecurrenceEndEnum.UNSET, ErrorCodeEnum.RECURRENCE_END_KIND_UNSET),
        (RecurrenceEndEnum.UNKNOWN, ErrorCodeEnum.ENUM_VALUE_UNKNOWN),
    ],
)
def test_end_kind_must_be_chosen(end_kind: RecurrenceEndEnum, expected: ErrorCodeEnum) -> None:
    assert _issue(replace(WEEKLY, end_kind=end_kind)) == (expected, "recurrence.end_kind")


def test_end_date_is_required_and_not_before_the_due_date() -> None:
    on_date = replace(WEEKLY, end_kind=RecurrenceEndEnum.ON_DATE, end_count=None)

    assert _issue(on_date) == (ErrorCodeEnum.RECURRENCE_END_DATE_MISSING, "recurrence.end_date")
    assert _issue(replace(on_date, end_date=date(2026, 11, 12))) == (
        ErrorCodeEnum.RECURRENCE_END_DATE_BEFORE_DUE,
        "recurrence.end_date",
    )
    assert _issue(replace(on_date, end_date=DUE)) is None


@pytest.mark.parametrize("count", [None, 0, 10_000])
def test_count_out_of_range(count: int | None) -> None:
    assert _issue(replace(WEEKLY, end_count=count)) == (
        ErrorCodeEnum.RECURRENCE_COUNT_OUT_OF_RANGE,
        "recurrence.end_count",
    )


def test_never_ending_daily_needs_no_days_nor_end() -> None:
    daily = Recurrence.create(
        frequency=RecurrenceFrequencyEnum.DAILY, interval=1, anchor_date=DUE, end_kind=RecurrenceEndEnum.NEVER
    )

    assert _issue(daily) is None
