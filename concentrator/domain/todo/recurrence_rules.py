"""Business rules of the recurrence of a task."""

from datetime import date
from typing import Final

from concentrator.domain.common.base_int_enum import UNSET_VALUE, BaseIntEnum
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.todo.recurrence import Recurrence
from concentrator.domain.todo.recurrence_end_enum import RecurrenceEndEnum
from concentrator.domain.todo.recurrence_frequency_enum import RecurrenceFrequencyEnum
from concentrator.domain.todo.todo_limits import TodoLimits

RECURRENCE_FIELD: Final = "recurrence"
FREQUENCY_FIELD: Final = f"{RECURRENCE_FIELD}.frequency"
INTERVAL_FIELD: Final = f"{RECURRENCE_FIELD}.interval"
WEEKDAYS_FIELD: Final = f"{RECURRENCE_FIELD}.weekdays"
END_KIND_FIELD: Final = f"{RECURRENCE_FIELD}.end_kind"
END_DATE_FIELD: Final = f"{RECURRENCE_FIELD}.end_date"
END_COUNT_FIELD: Final = f"{RECURRENCE_FIELD}.end_count"
MIN_INTERVAL: Final = 1
MIN_COUNT: Final = 1


def _chosen(value: BaseIntEnum, field: str, unset_code: ErrorCodeEnum) -> ValidationResult:
    """Check that an enum holds a real value.

    Args:
        value: Member to check.
        field: Field path.
        unset_code: Code reported for ``UNSET``.

    Returns:
        Success, ``unset_code`` or ``ENUM_VALUE_UNKNOWN``.
    """
    if value.value == UNSET_VALUE:
        return ValidationResult.failure(unset_code, field=field)
    if not value.is_set:
        return ValidationResult.failure(ErrorCodeEnum.ENUM_VALUE_UNKNOWN, field=field)
    return ValidationResult.success()


class RecurrenceRules:
    """Stateless validation of a ``Recurrence``. Field paths are those of a ``[[tasks]]`` element."""

    @staticmethod
    def validate(recurrence: Recurrence | None, due_date: date | None, limits: TodoLimits) -> ValidationResult:
        """Check a recurrence against the due date of its task.

        Args:
            recurrence: Recurrence, ``None`` for a one-off task (always valid).
            due_date: Due date of the task.
            limits: Bounds from ``concentrator.ini``.

        Returns:
            The merged result, one issue per failing field.
        """
        if recurrence is None:
            return ValidationResult.success()
        result = _chosen(recurrence.frequency, FREQUENCY_FIELD, ErrorCodeEnum.RECURRENCE_FREQUENCY_UNSET).merge(
            RecurrenceRules.validate_interval(recurrence.interval, limits),
            RecurrenceRules.validate_weekdays(recurrence),
            RecurrenceRules.validate_end(recurrence, due_date, limits),
        )
        if due_date is None:
            result = result.merge(
                ValidationResult.failure(ErrorCodeEnum.RECURRENCE_REQUIRES_DUE_DATE, field=RECURRENCE_FIELD)
            )
        return result

    @staticmethod
    def validate_interval(interval: int, limits: TodoLimits) -> ValidationResult:
        """Check the interval.

        Args:
            interval: Number of units between two occurrences.
            limits: Bounds from ``concentrator.ini``.

        Returns:
            Success or ``RECURRENCE_INTERVAL_OUT_OF_RANGE`` (``min``, ``max``).
        """
        if MIN_INTERVAL <= interval <= limits.max_recurrence_interval:
            return ValidationResult.success()
        return ValidationResult.failure(
            ErrorCodeEnum.RECURRENCE_INTERVAL_OUT_OF_RANGE,
            field=INTERVAL_FIELD,
            min=MIN_INTERVAL,
            max=limits.max_recurrence_interval,
        )

    @staticmethod
    def validate_weekdays(recurrence: Recurrence) -> ValidationResult:
        """Check the weekdays of a weekly recurrence.

        Args:
            recurrence: Recurrence.

        Returns:
            Success, ``RECURRENCE_WEEKDAYS_EMPTY`` or ``ENUM_VALUE_UNKNOWN`` / ``ENUM_VALUE_UNSET``.
        """
        if recurrence.frequency is not RecurrenceFrequencyEnum.WEEKLY:
            return ValidationResult.success()
        if not recurrence.weekdays:
            return ValidationResult.failure(ErrorCodeEnum.RECURRENCE_WEEKDAYS_EMPTY, field=WEEKDAYS_FIELD)
        return ValidationResult.success().merge(
            *(_chosen(day, WEEKDAYS_FIELD, ErrorCodeEnum.ENUM_VALUE_UNSET) for day in recurrence.weekdays)
        )

    @staticmethod
    def validate_end(recurrence: Recurrence, due_date: date | None, limits: TodoLimits) -> ValidationResult:
        """Check the end condition.

        Args:
            recurrence: Recurrence.
            due_date: Due date of the task.
            limits: Bounds from ``concentrator.ini``.

        Returns:
            Success, ``RECURRENCE_END_KIND_UNSET``, ``ENUM_VALUE_UNKNOWN``, ``RECURRENCE_END_DATE_MISSING``,
            ``RECURRENCE_END_DATE_BEFORE_DUE`` or ``RECURRENCE_COUNT_OUT_OF_RANGE`` (``min``, ``max``).
        """
        kind = _chosen(recurrence.end_kind, END_KIND_FIELD, ErrorCodeEnum.RECURRENCE_END_KIND_UNSET)
        if kind.is_failure:
            return kind
        if recurrence.end_kind is RecurrenceEndEnum.ON_DATE:
            if recurrence.end_date is None:
                return ValidationResult.failure(ErrorCodeEnum.RECURRENCE_END_DATE_MISSING, field=END_DATE_FIELD)
            if due_date is not None and recurrence.end_date < due_date:
                return ValidationResult.failure(ErrorCodeEnum.RECURRENCE_END_DATE_BEFORE_DUE, field=END_DATE_FIELD)
        if recurrence.end_kind is RecurrenceEndEnum.AFTER_COUNT:
            count = recurrence.end_count
            if count is None or not MIN_COUNT <= count <= limits.max_recurrence_count:
                return ValidationResult.failure(
                    ErrorCodeEnum.RECURRENCE_COUNT_OUT_OF_RANGE,
                    field=END_COUNT_FIELD,
                    min=MIN_COUNT,
                    max=limits.max_recurrence_count,
                )
        return ValidationResult.success()
