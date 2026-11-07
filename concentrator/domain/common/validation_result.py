"""Outcome of a validation or of an operation: a tuple of coded issues, never an error string."""

from dataclasses import dataclass, replace
from typing import Final, Self

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.severity_enum import SeverityEnum
from concentrator.domain.common.validation_issue import ValidationIssue

_BASELINES: Final = frozenset({SeverityEnum.SUCCESS, SeverityEnum.SKIPPED})
_BASELINE_INVALID: Final = "baseline must be SUCCESS or SKIPPED"


def _severity_order(severity: SeverityEnum) -> tuple[int, int]:
    """Sort key: rank first, then the raw value so that ``ERROR`` beats ``UNKNOWN`` on equal rank.

    Args:
        severity: Severity to order.

    Returns:
        The sort key.
    """
    return severity.rank, severity.value


def _issue(code: ErrorCodeEnum, severity: SeverityEnum, field: str, params: dict[str, object]) -> ValidationIssue:
    """Build an issue, converting interpolation values to text.

    Args:
        code: Error code.
        severity: Issue severity.
        field: Dotted field path, ``""`` for a global issue.
        params: Interpolation values.

    Returns:
        The issue.
    """
    pairs = tuple((name, str(value)) for name, value in params.items())
    return ValidationIssue(code=code, severity=severity, field=field, params=pairs)


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Immutable, always-present result. Use the factories rather than the constructor.

    Attributes:
        issues: Every issue found, in the order they were found.
        baseline: Severity reported when there is no issue: ``SUCCESS``, or ``SKIPPED`` when the
            operation did not run.
    """

    issues: tuple[ValidationIssue, ...] = ()
    baseline: SeverityEnum = SeverityEnum.SUCCESS

    def __post_init__(self) -> None:
        """Reject an impossible baseline (programming error).

        Raises:
            ValueError: If ``baseline`` is neither ``SUCCESS`` nor ``SKIPPED``.
        """
        if self.baseline not in _BASELINES:
            raise ValueError(_BASELINE_INVALID)

    @classmethod
    def success(cls) -> Self:
        """Return a result without any issue.

        Returns:
            A successful result.
        """
        return cls()

    @classmethod
    def skipped(cls) -> Self:
        """Return the result of an operation that deliberately did not run (for example a busy action).

        Returns:
            A skipped result.
        """
        return cls(baseline=SeverityEnum.SKIPPED)

    @classmethod
    def failure(cls, code: ErrorCodeEnum, *, field: str = "", **params: object) -> Self:
        """Return a result holding one ``ERROR`` issue.

        Args:
            code: Error code.
            field: Dotted field path, ``""`` for a global issue.
            **params: Message interpolation values, converted to text.

        Returns:
            A failed result.
        """
        return cls(issues=(_issue(code, SeverityEnum.ERROR, field, params),))

    @classmethod
    def warning(cls, code: ErrorCodeEnum, *, field: str = "", **params: object) -> Self:
        """Return a successful result holding one ``WARNING`` issue.

        Args:
            code: Error code.
            field: Dotted field path, ``""`` for a global issue.
            **params: Message interpolation values, converted to text.

        Returns:
            A successful result with a warning.
        """
        return cls(issues=(_issue(code, SeverityEnum.WARNING, field, params),))

    @classmethod
    def of(cls, *issues: ValidationIssue) -> Self:
        """Return a result holding the given issues.

        Args:
            *issues: Issues, in order.

        Returns:
            The result; successful when ``issues`` is empty.
        """
        return cls(issues=issues)

    @property
    def severity(self) -> SeverityEnum:
        """Worst severity among the issues, or the baseline when there is none."""
        if not self.issues:
            return self.baseline
        return max((issue.severity for issue in self.issues), key=_severity_order)

    @property
    def is_failure(self) -> bool:
        """Whether any issue is an error, critical, or of a severity that is not understood."""
        return self.severity.is_failure

    @property
    def is_success(self) -> bool:
        """Whether the operation ran and nothing failed (warnings allowed)."""
        return self.severity in {SeverityEnum.SUCCESS, SeverityEnum.WARNING}

    @property
    def is_skipped(self) -> bool:
        """Whether the operation deliberately did not run."""
        return self.severity == SeverityEnum.SKIPPED

    @property
    def has_warnings(self) -> bool:
        """Whether at least one issue is a warning."""
        return any(issue.severity == SeverityEnum.WARNING for issue in self.issues)

    @property
    def is_success_with_warnings(self) -> bool:
        """Whether the operation succeeded but reported warnings."""
        return self.is_success and self.has_warnings

    @property
    def error_codes(self) -> tuple[ErrorCodeEnum, ...]:
        """Codes of every issue, in order."""
        return tuple(issue.code for issue in self.issues)

    @property
    def first_failure(self) -> ValidationIssue | None:
        """First failing issue, or ``None`` when nothing failed."""
        return next((issue for issue in self.issues if issue.is_failure), None)

    def issues_for(self, field: str) -> tuple[ValidationIssue, ...]:
        """Return the issues attached to one field.

        Args:
            field: Dotted field path, ``""`` for global issues.

        Returns:
            The matching issues, in order.
        """
        return tuple(issue for issue in self.issues if issue.field == field)

    def prefixed(self, prefix: str) -> ValidationResult:
        """Place every issue under a parent field (rules of a nested object).

        Args:
            prefix: Dotted path of the parent, for example ``settings``.

        Returns:
            The same result with ``field`` turned into ``<prefix>.<field>`` (``<prefix>`` for a global issue).
        """
        if not prefix:
            return self
        issues = tuple(
            replace(issue, field=f"{prefix}.{issue.field}" if issue.field else prefix) for issue in self.issues
        )
        return ValidationResult(issues=issues, baseline=self.baseline)

    def merge(self, *others: ValidationResult) -> ValidationResult:
        """Combine results: issues are concatenated, the worst baseline wins.

        Args:
            *others: Results to append after this one.

        Returns:
            The combined result; skipped only if every merged result was skipped.
        """
        results = (self, *others)
        issues = tuple(issue for result in results for issue in result.issues)
        baseline = max((result.baseline for result in results), key=_severity_order)
        return ValidationResult(issues=issues, baseline=baseline)
