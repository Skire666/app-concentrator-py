"""Every user action goes through the gate (AGENTS.md section 8.3)."""

import logging
from collections.abc import Callable
from typing import Final

from concentrator.application.ports.clock_port import ClockPort
from concentrator.application.ports.scheduler_port import SchedulerPort
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.action_sections import sections_for
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum

_logger = logging.getLogger(__name__)

_MS_PER_SECOND: Final = 1000.0


class ActionToken:
    """A long action started with ``ActionGate.begin``; call ``finish`` once it is done."""

    def __init__(self, finish: Callable[[], None]) -> None:
        """Wrap the gate's completion callback.

        Args:
            finish: Releases the action.
        """
        self._finish = finish
        self._finished = False

    def finish(self) -> None:
        """Release the action (idempotent)."""
        if not self._finished:
            self._finished = True
            self._finish()


class ActionGate:
    """Prevents re-entrance, disables bound controls while busy, enforces a cooldown, logs slow actions."""

    def __init__(
        self,
        clock: ClockPort,
        scheduler: SchedulerPort,
        renderer: RenderCoordinator,
        *,
        cooldown_ms: int,
        slow_threshold_ms: int,
        sections: Callable[[ActionIdEnum], tuple[RenderSectionEnum, ...]] = sections_for,
    ) -> None:
        """Create a gate.

        Args:
            clock: Measures durations (monotonic).
            scheduler: Schedules the release after the cooldown.
            renderer: Receives the render requests of the bound sections.
            cooldown_ms: ``ui.action_cooldown_ms``.
            slow_threshold_ms: ``ui.slow_action_threshold_ms``.
            sections: Sections displaying the controls of an action.
        """
        self._clock = clock
        self._scheduler = scheduler
        self._renderer = renderer
        self._cooldown_ms = cooldown_ms
        self._slow_threshold_ms = slow_threshold_ms
        self._sections = sections
        self._busy: set[ActionIdEnum] = set()

    def is_busy(self, action: ActionIdEnum) -> bool:
        """Tell whether an action is running or cooling down (its controls are then disabled).

        Args:
            action: Action.

        Returns:
            Whether the action is busy.
        """
        return action in self._busy

    def run(
        self, action: ActionIdEnum, operation: Callable[[], ValidationResult], *, interactive: bool = False
    ) -> ValidationResult:
        """Run a synchronous action.

        Args:
            action: Action identifier.
            operation: The work; its exceptions propagate (to the global hook) after the release is scheduled.
            interactive: True for operations that wait for the user (modal dialogs): never logged as slow.

        Returns:
            The operation's result, or ``ValidationResult.skipped()`` when the action was busy.
        """
        token = self.begin(action, interactive=interactive)
        if token.data is None:
            return token.validation
        try:
            return operation()
        finally:
            token.data.finish()

    def begin(self, action: ActionIdEnum, *, interactive: bool = False) -> DataResult[ActionToken]:
        """Start a long action that finishes later (for example after a background save).

        Args:
            action: Action identifier.
            interactive: True when the duration depends on the user.

        Returns:
            A token to finish, or a skipped result when the action was busy.
        """
        if action in self._busy:
            _logger.debug("Action %s ignored: busy", action.name)
            return DataResult.fail(ValidationResult.skipped())
        self._busy.add(action)
        self._renderer.request(*self._sections(action))
        start = self._clock.monotonic()
        return DataResult.ok(ActionToken(lambda: self._finish(action, start, interactive=interactive)))

    def _finish(self, action: ActionIdEnum, start: float, *, interactive: bool) -> None:
        """Log a slow action and schedule its release after the remaining cooldown.

        Args:
            action: Finished action.
            start: Monotonic start time.
            interactive: Whether the action waited for the user.
        """
        elapsed_ms = (self._clock.monotonic() - start) * _MS_PER_SECOND
        if not interactive and elapsed_ms > self._slow_threshold_ms:
            _logger.info("Action %s took %d ms", action.name, round(elapsed_ms))
        delay_ms = max(0, round(self._cooldown_ms - elapsed_ms))
        self._scheduler.call_later(delay_ms, lambda: self._release(action))

    def _release(self, action: ActionIdEnum) -> None:
        """Make an action available again and re-render its controls.

        Args:
            action: Released action.
        """
        self._busy.discard(action)
        self._renderer.request(*self._sections(action))
