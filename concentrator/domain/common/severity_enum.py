"""Severity of a validation issue."""

from concentrator.domain.common.base_int_enum import BaseIntEnum


class SeverityEnum(BaseIntEnum):
    """Severity of a validation issue or of a whole result. The worst severity is the highest rank."""

    UNKNOWN = -1
    UNSET = 0
    SKIPPED = 1
    SUCCESS = 2
    WARNING = 3
    ERROR = 4
    CRITICAL = 5

    @property
    def rank(self) -> int:
        """Ordering weight: ``UNKNOWN`` and ``UNSET`` are not understood and therefore rank as ``ERROR``."""
        if self.is_set:
            return self.value
        return SeverityEnum.ERROR.value

    @property
    def is_failure(self) -> bool:
        """Whether this severity makes a result a failure (``ERROR``, ``CRITICAL``, not understood)."""
        return self.rank >= SeverityEnum.ERROR.value
