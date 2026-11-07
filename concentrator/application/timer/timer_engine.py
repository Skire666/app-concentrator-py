"""Runtime owner of the countdown, driven by ``AppTicker``."""

import logging
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Final

from concentrator.application.common.event_bus import EventBus
from concentrator.application.ports.clock_port import ClockPort
from concentrator.application.ports.timer_config_reader_port import TimerConfigReaderPort
from concentrator.application.timer.timer_events import TimerChangedEvent
from concentrator.application.timer.timer_view import TimerView, blink_phase
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.timer.timer_session import TimerSession
from concentrator.domain.timer.timer_settings import TimerSettings
from concentrator.domain.timer.timer_state_enum import TimerStateEnum
from concentrator.domain.timer.timer_transition_enum import TimerTransitionEnum

_logger = logging.getLogger(__name__)

MS_PER_SECOND: Final = 1000
_NO_BLINK: Final = -1

type TimerStep = Callable[[TimerSession, int], DataResult[TimerSession]]
"""A session command applied at a monotonic time in milliseconds."""


class TimerEngine:
    """Holds the ``TimerSession``, applies commands and ticks, and publishes ``TimerChangedEvent``.

    The remaining time comes from ``ClockPort.monotonic()`` at each tick. An event is published for
    every transition and otherwise only when the state, the displayed second or the blink phase changes;
    the first tick only records what the startup render already shows.
    """

    def __init__(
        self,
        *,
        clock: ClockPort,
        config: TimerConfigReaderPort,
        event_bus: EventBus,
        fallback: TimerSettings,
        blink_interval_ms: int,
    ) -> None:
        """Create an idle engine.

        Args:
            clock: Monotonic time and wall-clock end of a countdown.
            config: Current timer configuration.
            event_bus: Receives ``TimerChangedEvent``.
            fallback: Settings used if no configuration can be read (never after startup).
            blink_interval_ms: ``ui.alert_blink_interval_ms``.
        """
        self._clock = clock
        self._config = config
        self._event_bus = event_bus
        self._fallback = fallback
        self._blink_interval_ms = blink_interval_ms
        self._session = TimerSession.idle()
        self._ends_at: datetime | None = None
        self._last_visible: tuple[object, ...] | None = None

    @property
    def session(self) -> TimerSession:
        """Current session."""
        return self._session

    def settings(self) -> TimerSettings:
        """Return the current timer settings.

        Returns:
            The stored settings, or the ini defaults when none can be read (logged at WARNING).
        """
        config = self._config.read()
        if config.data is None:
            _logger.warning(
                "Timer configuration unavailable: %s", [code.name for code in config.validation.error_codes]
            )
            return self._fallback
        return config.data.settings

    def view(self) -> TimerView:
        """Describe the countdown now.

        Returns:
            The read model.
        """
        return self._view(self._now_ms())

    def change(self, step: TimerStep, transition: TimerTransitionEnum) -> ValidationResult:
        """Apply a command to the session and publish the change.

        Args:
            step: The session command.
            transition: Transition it performs.

        Returns:
            Success, or ``TIMER_TRANSITION_INVALID`` when the state does not allow it (nothing changes).
        """
        now_ms = self._now_ms()
        result = step(self._session, now_ms)
        if result.data is None:
            _logger.info("Timer command %s refused in state %s", transition.name, self._session.state.name)
            return result.validation
        self._enter(result.data, (transition,), now_ms)
        return result.validation

    def tick(self) -> None:
        """Advance the countdown (called every ``timer.tick_interval_ms``)."""
        now_ms = self._now_ms()
        result = self._session.tick(now_ms, self.settings())
        self._enter(result.session, result.transitions, now_ms)

    def _enter(self, session: TimerSession, transitions: tuple[TimerTransitionEnum, ...], now_ms: int) -> None:
        """Make a session the current one and publish what is visible.

        Args:
            session: New session.
            transitions: What happened.
            now_ms: Monotonic time of the change.
        """
        self._session = session
        if transitions:
            self._ends_at = self._wall_clock_end(now_ms)
            _logger.info("Timer %s", ", ".join(transition.name for transition in transitions))
        view = self._view(now_ms)
        visible = (view.state, view.displayed_seconds, view.snoozed, self._blink(view))
        first = self._last_visible is None
        changed = visible != self._last_visible
        self._last_visible = visible
        if transitions or (changed and not first):
            self._event_bus.publish(
                TimerChangedEvent(transitions=transitions, displayed_seconds=view.displayed_seconds)
            )

    def _wall_clock_end(self, now_ms: int) -> datetime | None:
        """Compute the wall-clock end of a running countdown once, so its caption stays steady.

        Args:
            now_ms: Monotonic time of the transition.

        Returns:
            The end instant (UTC), ``None`` when not running.
        """
        if self._session.state is not TimerStateEnum.RUNNING:
            return None
        seconds = -(-self._session.remaining_ms(now_ms) // MS_PER_SECOND)
        return self._clock.now_utc() + timedelta(seconds=seconds)

    def _view(self, now_ms: int) -> TimerView:
        """Describe the countdown at a monotonic time.

        Args:
            now_ms: Monotonic time.

        Returns:
            The read model.
        """
        session = self._session
        return TimerView(
            state=session.state,
            displayed_seconds=session.displayed_seconds(now_ms, self.settings().duration),
            snoozed=session.snoozed,
            ends_at=self._ends_at,
            ringing_ms=session.ringing_ms(now_ms),
        )

    def _blink(self, view: TimerView) -> int:
        """Return the blink phase of a ringing timer.

        Args:
            view: Current read model.

        Returns:
            The phase, or a constant when not ringing.
        """
        if view.state is not TimerStateEnum.RINGING:
            return _NO_BLINK
        return blink_phase(view.ringing_ms, self._blink_interval_ms)

    def _now_ms(self) -> int:
        """Return the monotonic time in whole milliseconds.

        Returns:
            Milliseconds.
        """
        return round(self._clock.monotonic() * MS_PER_SECOND)
