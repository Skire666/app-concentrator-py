"""Repeat section of the task dialog: builds its snapshot and applies its edits to the open form."""

from collections.abc import Callable
from dataclasses import replace
from datetime import date
from types import MappingProxyType
from typing import Final

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.domain.todo.recurrence_calculator import RecurrenceCalculator
from concentrator.domain.todo.recurrence_end_enum import RecurrenceEndEnum
from concentrator.domain.todo.recurrence_frequency_enum import RecurrenceFrequencyEnum
from concentrator.domain.todo.recurrence_rules import RECURRENCE_FIELD
from concentrator.domain.todo.todo_limits import TodoLimits
from concentrator.domain.todo.weekday_enum import WeekdayEnum
from concentrator.presentation.common.date_time_formatter import DateTimeFormatter
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.common.ui_texts import UiTexts
from concentrator.presentation.settings.settings_snapshot import ChoiceFieldSnapshot
from concentrator.presentation.todo.recurrence_form import END_KINDS, FREQUENCIES, WEEK, RecurrenceDraft
from concentrator.presentation.todo.recurrence_summary_formatter import (
    WEEKDAY_KEYS,
    WEEKDAY_SHORT_KEYS,
    RecurrenceSummaryFormatter,
)
from concentrator.presentation.todo.task_edit_form import TaskEditForm
from concentrator.presentation.todo.task_edit_snapshot import (
    DateValueSnapshot,
    RecurrenceEndSnapshot,
    RecurrenceFieldSnapshot,
    RecurrenceRuleSnapshot,
    WeekdayToggleSnapshot,
)

UNIT_KEYS: Final = MappingProxyType(
    {
        RecurrenceFrequencyEnum.DAILY: "todo.task_edit.unit.daily",
        RecurrenceFrequencyEnum.WEEKLY: "todo.task_edit.unit.weekly",
        RecurrenceFrequencyEnum.MONTHLY: "todo.task_edit.unit.monthly",
        RecurrenceFrequencyEnum.YEARLY: "todo.task_edit.unit.yearly",
    }
)
"""Plural base key of the unit of each frequency, as the interval list shows it."""

END_KEYS: Final = MappingProxyType(
    {
        RecurrenceEndEnum.NEVER: "todo.task_edit.end.never",
        RecurrenceEndEnum.ON_DATE: "todo.task_edit.end.on_date",
        RecurrenceEndEnum.AFTER_COUNT: "todo.task_edit.end.after_count",
    }
)
"""Label of each end condition."""


class RecurrenceFieldPresenter:
    """The Repeat section of the form the task dialog shows (``TaskEditPresenter.form``)."""

    def __init__(
        self,
        translator: TranslatorPort,
        renderer: RenderCoordinator,
        *,
        form: Callable[[], TaskEditForm],
        dates: DateTimeFormatter,
        limits: TodoLimits,
        preview_count: int,
    ) -> None:
        """Create the presenter.

        Args:
            translator: Current-language translator.
            renderer: Receives the render requests.
            form: Returns the form of the open dialog.
            dates: Date templates (preview, end date).
            limits: Bounds from ``concentrator.ini``.
            preview_count: Dates shown after the due date (``todo.recurrence_preview_count``).
        """
        self._translator = translator
        self._texts = UiTexts(translator)
        self._renderer = renderer
        self._form = form
        self._dates = dates
        self._summaries = RecurrenceSummaryFormatter(translator, dates)
        self._limits = limits
        self._preview_count = preview_count

    def build(self) -> RecurrenceFieldSnapshot:
        """Describe the section.

        Returns:
            The snapshot.
        """
        form = self._form()
        draft = form.draft.recurrence
        return RecurrenceFieldSnapshot(
            repeat_label=self._translator.tr("todo.task_edit.repeat"),
            enabled=draft.enabled,
            rule=self._rule(draft),
            ending=self._ending(draft, draft.end_date or form.draft.due_date or form.today),
            summary=self._summary(form),
            preview=self._preview(form),
            error=self._error(form),
        )

    def _rule(self, draft: RecurrenceDraft) -> RecurrenceRuleSnapshot:
        """Describe the interval, the unit and the weekdays.

        Args:
            draft: Section values.

        Returns:
            The rule fields.
        """
        units = tuple(self._translator.tr_plural(UNIT_KEYS[item], draft.interval) for item in FREQUENCIES)
        return RecurrenceRuleSnapshot(
            every_label=self._translator.tr("todo.task_edit.repeat_every"),
            interval=draft.interval,
            interval_max=self._limits.max_recurrence_interval,
            frequency=self._choice("", units, _index(FREQUENCIES, draft.frequency)),
            weekdays_visible=draft.frequency is RecurrenceFrequencyEnum.WEEKLY,
            weekdays=tuple(self._weekday(day, draft) for day in WEEK),
        )

    def _ending(self, draft: RecurrenceDraft, end_date: date) -> RecurrenceEndSnapshot:
        """Describe the end condition.

        Args:
            draft: Section values.
            end_date: Date shown by the end date field.

        Returns:
            The end fields.
        """
        tr = self._translator.tr
        kinds = tuple(tr(END_KEYS[item]) for item in END_KINDS)
        return RecurrenceEndSnapshot(
            end=self._choice(tr("todo.task_edit.repeat_ends"), kinds, _index(END_KINDS, draft.end_kind)),
            end_date_visible=draft.end_kind is RecurrenceEndEnum.ON_DATE,
            end_date=DateValueSnapshot(year=end_date.year, month=end_date.month, day=end_date.day),
            date_format=tr("todo.task_edit.date_format"),
            end_count_visible=draft.end_kind is RecurrenceEndEnum.AFTER_COUNT,
            end_count=draft.end_count,
            end_count_max=self._limits.max_recurrence_count,
            end_count_suffix=self._translator.tr_plural("todo.task_edit.end_count_suffix", draft.end_count),
        )

    def on_repeat_toggled(self, enabled: bool) -> None:
        """Tick or untick Repeat.

        Args:
            enabled: Whether the task repeats.
        """
        self._form().set_repeat(enabled=enabled)
        self._renderer.request(RenderSectionEnum.TASK_EDIT)

    def on_interval_changed(self, interval: int) -> None:
        """Change the interval.

        Args:
            interval: Every N units.
        """
        self._change(lambda draft: replace(draft, interval=interval))

    def on_frequency_selected(self, index: int) -> None:
        """Choose the unit of the interval.

        Args:
            index: Index in days, weeks, months, years.
        """
        if 0 <= index < len(FREQUENCIES):
            frequency = FREQUENCIES[index]
            self._change(lambda draft: replace(draft, frequency=frequency))

    def on_weekday_toggled(self, day_value: int, checked: bool) -> None:
        """Choose or remove a weekday of a weekly series.

        Args:
            day_value: ``WeekdayEnum`` value.
            checked: Whether the day is now chosen.
        """
        day = WeekdayEnum.parse(day_value)
        if day.is_set:
            self._change(lambda draft: draft.with_weekday(day, checked=checked))

    def on_end_selected(self, index: int) -> None:
        """Choose when the series ends.

        Args:
            index: Index in never, on a date, after a count.
        """
        if not 0 <= index < len(END_KINDS):
            return
        end_kind = END_KINDS[index]
        form = self._form()
        first = form.draft.due_date or form.today
        self._change(lambda draft: replace(draft, end_kind=end_kind, end_date=draft.end_date or first))

    def on_end_date_changed(self, year: int, month: int, day: int) -> None:
        """Change the end date.

        Args:
            year: Year of the date field.
            month: Month of the date field.
            day: Day of the date field.
        """
        self._change(lambda draft: replace(draft, end_date=date(year, month, day)))

    def on_end_count_changed(self, count: int) -> None:
        """Change the number of occurrences.

        Args:
            count: Occurrences to complete.
        """
        self._change(lambda draft: replace(draft, end_count=count))

    def _change(self, change: Callable[[RecurrenceDraft], RecurrenceDraft]) -> None:
        """Apply an edit of the section and render the dialog.

        Args:
            change: New values from the current ones.
        """
        self._form().change_recurrence(change)
        self._renderer.request(RenderSectionEnum.TASK_EDIT)

    def _weekday(self, day: WeekdayEnum, draft: RecurrenceDraft) -> WeekdayToggleSnapshot:
        """Describe a weekday button.

        Args:
            day: Weekday.
            draft: Section values.

        Returns:
            The button.
        """
        return WeekdayToggleSnapshot(
            value=int(day),
            text=self._translator.tr(WEEKDAY_SHORT_KEYS[day]),
            tooltip=self._translator.tr(WEEKDAY_KEYS[day]),
            checked=day in draft.weekdays,
        )

    def _summary(self, form: TaskEditForm) -> str:
        """Full text of the series.

        Args:
            form: Open form.

        Returns:
            The text, ``""`` when Repeat is off.
        """
        recurrence = form.effective_recurrence()
        return "" if recurrence is None else self._summaries.full(recurrence)

    def _preview(self, form: TaskEditForm) -> str:
        """Next dates after the due date.

        Args:
            form: Open form.

        Returns:
            ``Next dates: 30/11/2026, 31/12/2026...``, ``""`` when off, without due date or invalid.
        """
        recurrence = form.effective_recurrence()
        due = form.draft.due_date
        if recurrence is None or due is None or self._has_error(form):
            return ""
        upcoming = RecurrenceCalculator.upcoming(recurrence, due, self._preview_count)
        separator = self._translator.tr("format.list.separator")
        dates = separator.join(self._dates.calendar_date(item) for item in upcoming)
        return self._translator.tr("todo.task_edit.repeat_preview", dates=dates)

    def _error(self, form: TaskEditForm) -> str:
        """First message of the section.

        Args:
            form: Open form.

        Returns:
            The message, ``""`` when valid or while the errors of a new task are not shown yet.
        """
        return self._texts.field_message(form.errors, RECURRENCE_FIELD) if form.shows_errors else ""

    @staticmethod
    def _has_error(form: TaskEditForm) -> bool:
        """Tell whether the section breaks a rule.

        Args:
            form: Open form.

        Returns:
            Whether a ``recurrence.*`` issue is a failure.
        """
        return any(item.field.startswith(RECURRENCE_FIELD) for item in form.errors.issues)

    @staticmethod
    def _choice(label: str, options: tuple[str, ...], selected: int) -> ChoiceFieldSnapshot:
        """Describe a list.

        Args:
            label: Caption, ``""`` for none.
            options: Texts of the choices.
            selected: Index of the chosen one.

        Returns:
            The field.
        """
        return ChoiceFieldSnapshot(label=label, tooltip="", options=options, selected=selected, error="")


def _index[T](values: tuple[T, ...], value: T) -> int:
    """Position of a value.

    Args:
        values: Options.
        value: Current value.

    Returns:
        Its index, ``0`` when it is not offered.
    """
    return values.index(value) if value in values else 0
