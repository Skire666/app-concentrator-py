"""Timer panel: digits, caption and the button matrix (phase 2 spec)."""

import logging
from collections.abc import Callable
from types import MappingProxyType
from typing import Final

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.application.timer.timer_commands import TimerCommands
from concentrator.application.timer.timer_events import TimerChangedEvent, TimerConfigChangedEvent
from concentrator.application.timer.timer_queries import TimerQueries
from concentrator.application.timer.timer_view import TimerView, blink_phase
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.timer.duration import SECONDS_PER_MINUTE
from concentrator.domain.timer.timer_state_enum import TimerStateEnum
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.button_snapshot import ButtonSnapshot
from concentrator.presentation.common.date_time_formatter import DateTimeFormatter
from concentrator.presentation.common.duration_formatter import clock_text
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.common.ui_texts import UiTexts
from concentrator.presentation.timer.timer_snapshot import TimerSnapshot

_logger = logging.getLogger(__name__)

type ButtonSlot = tuple[ActionIdEnum, bool]
"""Action shown by a button and whether the state allows it."""

BUTTON_MATRIX: Final = MappingProxyType(
    {
        TimerStateEnum.IDLE: (
            (ActionIdEnum.TIMER_EDIT, True),
            (ActionIdEnum.TIMER_RESET, False),
            (ActionIdEnum.TIMER_START, True),
        ),
        TimerStateEnum.RUNNING: (
            (ActionIdEnum.TIMER_EDIT, True),
            (ActionIdEnum.TIMER_RESET, True),
            (ActionIdEnum.TIMER_PAUSE, True),
        ),
        TimerStateEnum.PAUSED: (
            (ActionIdEnum.TIMER_EDIT, True),
            (ActionIdEnum.TIMER_RESET, True),
            (ActionIdEnum.TIMER_RESUME, True),
        ),
        TimerStateEnum.RINGING: (
            (ActionIdEnum.TIMER_RESTART, True),
            (ActionIdEnum.TIMER_ACKNOWLEDGE, True),
            (ActionIdEnum.TIMER_SNOOZE, True),
        ),
    }
)
"""Left, middle and right button of each state."""


class TimerPresenter:
    """Builds the ``TIMER`` snapshot and runs the timer buttons through the action gate."""

    def __init__(
        self,
        translator: TranslatorPort,
        gate: ActionGate,
        renderer: RenderCoordinator,
        queries: TimerQueries,
        commands: TimerCommands,
        formatter: DateTimeFormatter,
        open_editor: Callable[[], ValidationResult],
        blink_interval_ms: int,
    ) -> None:
        """Create the presenter.

        Args:
            translator: Current-language translator.
            gate: Runs every user action.
            renderer: Receives the render requests.
            queries: Current countdown and snooze length.
            commands: State commands.
            formatter: Formats the end time of a countdown.
            open_editor: Shows the edit dialog modally.
            blink_interval_ms: ``ui.alert_blink_interval_ms``.
        """
        self._translator = translator
        self._texts = UiTexts(translator)
        self._gate = gate
        self._renderer = renderer
        self._queries = queries
        self._formatter = formatter
        self._blink_interval_ms = blink_interval_ms
        self._operations: dict[ActionIdEnum, Callable[[], ValidationResult]] = {
            ActionIdEnum.TIMER_EDIT: open_editor,
            ActionIdEnum.TIMER_START: commands.start,
            ActionIdEnum.TIMER_PAUSE: commands.pause,
            ActionIdEnum.TIMER_RESUME: commands.resume,
            ActionIdEnum.TIMER_RESET: commands.reset,
            ActionIdEnum.TIMER_ACKNOWLEDGE: commands.acknowledge,
            ActionIdEnum.TIMER_RESTART: commands.restart,
            ActionIdEnum.TIMER_SNOOZE: commands.snooze,
        }

    def build_snapshot(self) -> TimerSnapshot:
        """Describe the timer panel now.

        Returns:
            The snapshot.
        """
        view = self._queries.current_view()
        left, middle, right = (self._button(slot) for slot in BUTTON_MATRIX[view.state])
        return TimerSnapshot(
            digits=clock_text(view.displayed_seconds),
            caption=self._caption(view),
            alert=self._alert(view),
            left=left,
            middle=middle,
            right=right,
        )

    def on_timer_changed(self, _event: TimerChangedEvent) -> None:
        """Re-render after a tick or a command.

        Args:
            _event: Published by the timer engine.
        """
        self._renderer.request(RenderSectionEnum.TIMER)

    def on_config_changed(self, _event: TimerConfigChangedEvent) -> None:
        """Re-render after the configuration changed (the idle display shows the new duration).

        Args:
            _event: Published by the timer use cases.
        """
        self._renderer.request(RenderSectionEnum.TIMER)

    def on_action_requested(self, action_value: int) -> None:
        """Handle a click of a timer button.

        Args:
            action_value: ``ActionIdEnum`` value emitted by the panel.
        """
        action = ActionIdEnum.parse(action_value)
        operation = self._operations.get(action)
        if operation is None:
            _logger.warning("Timer action %s (%d) is not handled", action.name, action_value)
            return
        result = self._gate.run(action, operation, interactive=action is ActionIdEnum.TIMER_EDIT)
        if result.is_failure:
            _logger.warning("Timer action %s failed: %s", action.name, [code.name for code in result.error_codes])
        self._renderer.request(RenderSectionEnum.TIMER)

    def _button(self, slot: ButtonSlot) -> ButtonSnapshot:
        """Describe one button.

        Args:
            slot: Action and whether the state allows it.

        Returns:
            The button snapshot.
        """
        action, allowed = slot
        minutes = self._queries.snooze.seconds // SECONDS_PER_MINUTE
        return ButtonSnapshot(
            text=self._texts.action_label(action, minutes=minutes),
            tooltip=self._texts.action_tooltip(action, minutes=minutes),
            enabled=allowed and not self._gate.is_busy(action),
            visible=True,
            action=action,
        )

    def _caption(self, view: TimerView) -> str:
        """Return the line under the digits.

        Args:
            view: Current countdown.

        Returns:
            The caption, ``""`` when idle.
        """
        tr = self._translator.tr
        if view.state is TimerStateEnum.RUNNING and view.ends_at is not None:
            time = self._formatter.time(view.ends_at)
            return tr("timer.caption.snoozed", time=time) if view.snoozed else tr("timer.caption.ends_at", time=time)
        if view.state is TimerStateEnum.PAUSED:
            return tr("timer.caption.paused")
        if view.state is TimerStateEnum.RINGING:
            return tr("timer.caption.ringing")
        return ""

    def _alert(self, view: TimerView) -> bool:
        """Tell whether the digits show the alert style now (ringing timers blink).

        Args:
            view: Current countdown.

        Returns:
            Whether the alert phase is visible.
        """
        if view.state is not TimerStateEnum.RINGING:
            return False
        return blink_phase(view.ringing_ms, self._blink_interval_ms) % 2 == 0
