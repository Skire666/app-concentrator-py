"""Outcome of an operation that produces a value."""

from dataclasses import dataclass
from typing import Final

from concentrator.domain.common.validation_result import ValidationResult

_SUCCESS: Final = ValidationResult.success()
_OK_NEEDS_SUCCESS: Final = "DataResult.ok() needs a successful validation"
_FAIL_NEEDS_FAILURE: Final = "DataResult.fail() needs a failed or skipped validation"


@dataclass(frozen=True, slots=True)
class DataResult[T]:
    """A value together with its validation. ``data`` is ``None`` unless the operation succeeded.

    Attributes:
        data: The produced value, ``None`` on failure or when skipped.
        validation: Issues found while producing the value (warnings are allowed on success).
    """

    data: T | None
    validation: ValidationResult

    @staticmethod
    def ok[U](data: U, validation: ValidationResult = _SUCCESS) -> DataResult[U]:
        """Wrap a produced value.

        Args:
            data: The value.
            validation: Successful validation, possibly with warnings.

        Returns:
            A successful data result.

        Raises:
            ValueError: If ``validation`` is not successful (programming error).
        """
        if not validation.is_success:
            raise ValueError(_OK_NEEDS_SUCCESS)
        return DataResult(data=data, validation=validation)

    @staticmethod
    def fail[U](validation: ValidationResult) -> DataResult[U]:
        """Wrap a failed or skipped operation.

        Args:
            validation: Failed or skipped validation.

        Returns:
            A data result without data.

        Raises:
            ValueError: If ``validation`` is successful (programming error).
        """
        if validation.is_success:
            raise ValueError(_FAIL_NEEDS_FAILURE)
        return DataResult[U](data=None, validation=validation)

    @property
    def is_success(self) -> bool:
        """Whether the operation succeeded and produced ``data``."""
        return self.validation.is_success and self.data is not None

    def value_or(self, default: T) -> T:
        """Return the produced value, or a fallback when the operation did not succeed.

        Args:
            default: Value returned on failure.

        Returns:
            ``data`` on success, ``default`` otherwise.
        """
        if self.validation.is_success and self.data is not None:
            return self.data
        return default
