"""One problem found while validating a value or performing an operation."""

from dataclasses import dataclass

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.severity_enum import SeverityEnum


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """A coded problem; the UI turns ``code`` and ``params`` into a translated message.

    Attributes:
        code: What went wrong.
        severity: How bad it is.
        field: Dotted path of the field concerned, ``""`` for a global issue.
        params: Message interpolation values as ``(name, value)`` pairs.
    """

    code: ErrorCodeEnum
    severity: SeverityEnum
    field: str = ""
    params: tuple[tuple[str, str], ...] = ()

    @property
    def is_failure(self) -> bool:
        """Whether this issue makes its result a failure."""
        return self.severity.is_failure
