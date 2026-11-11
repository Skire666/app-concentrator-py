"""Inline message of the focus queue: why the last action was refused (queue full, task not open...)."""

from collections.abc import Collection

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_issue import ValidationIssue
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum


class FocusFeedback:
    """Keeps the last refusal of a focus action until the next action or key press.

    Zone 1 ("Add to focus", the star) and zone 2 report here, so the message always shows under the queue.
    """

    def __init__(self, renderer: RenderCoordinator) -> None:
        """Create the feedback.

        Args:
            renderer: Receives the render requests of the queue.
        """
        self._renderer = renderer
        self._error = ValidationResult.success()

    @property
    def issue(self) -> ValidationIssue | None:
        """First failure of the last refused action, ``None`` when there is nothing to say."""
        return self._error.first_failure

    def report(self, result: ValidationResult, silent: Collection[ErrorCodeEnum] = ()) -> ValidationResult:
        """Remember the outcome of an action.

        Args:
            result: Result of the action.
            silent: Codes that show no message (Enter on an empty field).

        Returns:
            The result.
        """
        refused = result.is_failure and not set(result.error_codes) <= set(silent)
        self._error = result if refused else ValidationResult.success()
        self._renderer.request(RenderSectionEnum.FOCUS_QUEUE)
        return result

    def clear(self) -> None:
        """Forget the message (the user typed again)."""
        if self._error.is_failure:
            self._error = ValidationResult.success()
            self._renderer.request(RenderSectionEnum.FOCUS_QUEUE)
