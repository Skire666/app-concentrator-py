"""Rules on timestamps."""

from datetime import datetime, timedelta
from typing import Final

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult

_UTC_OFFSET: Final = timedelta(0)


class TimeRules:
    """Stateless checks on ``datetime`` values."""

    @staticmethod
    def validate_utc(value: datetime, field: str) -> ValidationResult:
        """Check that a timestamp is timezone-aware with a zero UTC offset.

        Args:
            value: Timestamp to check.
            field: Dotted field path reported in the issue.

        Returns:
            Success, or ``DATETIME_NOT_UTC`` for a naive or non-UTC timestamp.
        """
        if value.utcoffset() != _UTC_OFFSET:
            return ValidationResult.failure(ErrorCodeEnum.DATETIME_NOT_UTC, field=field)
        return ValidationResult.success()
