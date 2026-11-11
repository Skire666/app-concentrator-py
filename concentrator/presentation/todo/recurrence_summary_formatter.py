"""Texts of a recurrence: "Every 2 weeks" in the table, "Every 2 weeks on Monday and Friday, 10 times" in full."""

from collections.abc import Sequence
from types import MappingProxyType
from typing import Final

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.domain.todo.recurrence import Recurrence
from concentrator.domain.todo.recurrence_end_enum import RecurrenceEndEnum
from concentrator.domain.todo.recurrence_frequency_enum import RecurrenceFrequencyEnum
from concentrator.domain.todo.weekday_enum import WeekdayEnum
from concentrator.presentation.common.date_time_formatter import DateTimeFormatter
from concentrator.presentation.todo.todo_texts import UNKNOWN_KEY

FREQUENCY_KEYS: Final = MappingProxyType(
    {
        RecurrenceFrequencyEnum.DAILY: "todo.recurrence.every.daily",
        RecurrenceFrequencyEnum.WEEKLY: "todo.recurrence.every.weekly",
        RecurrenceFrequencyEnum.MONTHLY: "todo.recurrence.every.monthly",
        RecurrenceFrequencyEnum.YEARLY: "todo.recurrence.every.yearly",
    }
)
"""Plural base key of "every N units", per frequency."""

WEEKDAY_KEYS: Final = MappingProxyType(
    {
        WeekdayEnum.MONDAY: "format.weekday.monday",
        WeekdayEnum.TUESDAY: "format.weekday.tuesday",
        WeekdayEnum.WEDNESDAY: "format.weekday.wednesday",
        WeekdayEnum.THURSDAY: "format.weekday.thursday",
        WeekdayEnum.FRIDAY: "format.weekday.friday",
        WeekdayEnum.SATURDAY: "format.weekday.saturday",
        WeekdayEnum.SUNDAY: "format.weekday.sunday",
    }
)
"""Full name of each weekday."""

WEEKDAY_SHORT_KEYS: Final = MappingProxyType(
    {
        WeekdayEnum.MONDAY: "format.weekday.short.monday",
        WeekdayEnum.TUESDAY: "format.weekday.short.tuesday",
        WeekdayEnum.WEDNESDAY: "format.weekday.short.wednesday",
        WeekdayEnum.THURSDAY: "format.weekday.short.thursday",
        WeekdayEnum.FRIDAY: "format.weekday.short.friday",
        WeekdayEnum.SATURDAY: "format.weekday.short.saturday",
        WeekdayEnum.SUNDAY: "format.weekday.short.sunday",
    }
)
"""Short name of each weekday (toggles of the task dialog)."""

_TWO_DIGITS: Final = "02d"


class RecurrenceSummaryFormatter:
    """Builds the texts of a recurrence from catalog templates, so each language orders its words."""

    def __init__(self, translator: TranslatorPort, dates: DateTimeFormatter) -> None:
        """Create the formatter.

        Args:
            translator: Current-language translator.
            dates: Date templates (end date).
        """
        self._translator = translator
        self._dates = dates

    def short(self, recurrence: Recurrence) -> str:
        """Frequency and interval only (Repeat column).

        Args:
            recurrence: Recurrence.

        Returns:
            ``Every 2 weeks``, or the "unknown value" text for a frequency a newer version wrote.
        """
        key = FREQUENCY_KEYS.get(recurrence.frequency)
        if key is None:
            return self._translator.tr(UNKNOWN_KEY)
        return self._translator.tr_plural(key, recurrence.interval)

    def full(self, recurrence: Recurrence) -> str:
        """Frequency, days and end (details pane, task dialog).

        Args:
            recurrence: Recurrence.

        Returns:
            ``Every 2 weeks on Monday and Friday, 10 times``.
        """
        tr = self._translator.tr
        rule = self.short(recurrence)
        anchor = recurrence.anchor_date
        match recurrence.frequency:
            case RecurrenceFrequencyEnum.WEEKLY if recurrence.weekdays:
                rule = tr("todo.recurrence.on_days", rule=rule, days=self.day_list(recurrence.weekdays))
            case RecurrenceFrequencyEnum.MONTHLY:
                rule = tr("todo.recurrence.on_month_day", rule=rule, day=anchor.day)
            case RecurrenceFrequencyEnum.YEARLY:
                day_month = tr(
                    "format.day_month", day=format(anchor.day, _TWO_DIGITS), month=format(anchor.month, _TWO_DIGITS)
                )
                rule = tr("todo.recurrence.on_year_day", rule=rule, date=day_month)
            case _:
                pass
        return self._with_end(rule, recurrence)

    def day_list(self, days: Sequence[WeekdayEnum]) -> str:
        """Names of weekdays joined as a sentence.

        Args:
            days: Weekdays, Monday first.

        Returns:
            ``Monday``, ``Monday and Friday`` or ``Monday, Wednesday and Friday``.
        """
        names = [self._translator.tr(WEEKDAY_KEYS.get(day, UNKNOWN_KEY)) for day in days]
        if len(names) <= 1:
            return "".join(names)
        head = self._translator.tr("format.list.separator").join(names[:-1])
        return head + self._translator.tr("format.list.last") + names[-1]

    def _with_end(self, rule: str, recurrence: Recurrence) -> str:
        """Add the end condition.

        Args:
            rule: Text of the frequency and days.
            recurrence: Recurrence.

        Returns:
            The text with ``, until ...`` or ``, N times`` (nothing for a series without end).
        """
        if recurrence.end_kind is RecurrenceEndEnum.ON_DATE and recurrence.end_date is not None:
            return self._translator.tr(
                "todo.recurrence.until", rule=rule, date=self._dates.calendar_date(recurrence.end_date)
            )
        if recurrence.end_kind is RecurrenceEndEnum.AFTER_COUNT and recurrence.end_count is not None:
            return self._translator.tr_plural("todo.recurrence.times", recurrence.end_count, rule=rule)
        return rule
