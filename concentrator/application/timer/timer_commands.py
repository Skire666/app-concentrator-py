"""Write use cases of the timer: state commands and configuration changes."""

import logging
from dataclasses import replace

from concentrator.application.common.event_bus import EventBus
from concentrator.application.ports.clock_port import ClockPort
from concentrator.application.ports.timer_config_reader_port import TimerConfigReaderPort
from concentrator.application.ports.timer_config_writer_port import TimerConfigWriterPort
from concentrator.application.timer.timer_engine import TimerEngine
from concentrator.application.timer.timer_events import TimerConfigChangedEvent
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.timer.duration import Duration
from concentrator.domain.timer.timer_config_rules import TimerConfigRules
from concentrator.domain.timer.timer_limits import TimerLimits
from concentrator.domain.timer.timer_settings import TimerSettings
from concentrator.domain.timer.timer_state_enum import TimerStateEnum
from concentrator.domain.timer.timer_transition_enum import TimerTransitionEnum

_logger = logging.getLogger(__name__)


class TimerCommands:
    """Start (also with a favorite's duration), pause, resume, reset, acknowledge, restart, snooze, store.

    State commands return ``TIMER_TRANSITION_INVALID`` when the current state does not allow them. A
    duration stored while the timer runs applies at the next start or reset.
    """

    def __init__(
        self,
        *,
        engine: TimerEngine,
        reader: TimerConfigReaderPort,
        writer: TimerConfigWriterPort,
        clock: ClockPort,
        event_bus: EventBus,
        limits: TimerLimits,
        snooze: Duration,
    ) -> None:
        """Create the use cases.

        Args:
            engine: Runtime countdown.
            reader: Timer configuration reader.
            writer: Timer configuration writer.
            clock: Change instants.
            event_bus: Receives ``TimerConfigChangedEvent``.
            limits: Bounds from ``concentrator.ini``.
            snooze: ``timer.snooze_minutes``.
        """
        self._engine = engine
        self._reader = reader
        self._writer = writer
        self._clock = clock
        self._event_bus = event_bus
        self._limits = limits
        self._snooze = snooze

    def start(self) -> ValidationResult:
        """``IDLE`` -> ``RUNNING`` for the configured duration.

        Returns:
            Success or ``TIMER_TRANSITION_INVALID``.
        """
        duration = self._engine.settings().duration
        return self._engine.change(lambda session, now: session.start(now, duration), TimerTransitionEnum.STARTED)

    def start_with_duration(self, duration: Duration) -> ValidationResult:
        """Store a new countdown duration and start it, in one action (a favorite).

        Args:
            duration: Duration of the favorite.

        Returns:
            Success, ``TIMER_TRANSITION_INVALID`` when the timer is not ``IDLE`` (the configuration is
            then unchanged), or the rule or write failure of the new duration.
        """
        state = self._engine.session.state
        if state is not TimerStateEnum.IDLE:
            _logger.info("Timer command STARTED with a favorite refused in state %s", state.name)
            return ValidationResult.failure(ErrorCodeEnum.TIMER_TRANSITION_INVALID)
        stored = self.update_config(replace(self._engine.settings(), duration=duration))
        if stored.is_failure:
            return stored
        return self.start()

    def pause(self) -> ValidationResult:
        """``RUNNING`` -> ``PAUSED``.

        Returns:
            Success or ``TIMER_TRANSITION_INVALID``.
        """
        return self._engine.change(lambda session, now: session.pause(now), TimerTransitionEnum.PAUSED)

    def resume(self) -> ValidationResult:
        """``PAUSED`` -> ``RUNNING``.

        Returns:
            Success or ``TIMER_TRANSITION_INVALID``.
        """
        return self._engine.change(lambda session, now: session.resume(now), TimerTransitionEnum.RESUMED)

    def reset(self) -> ValidationResult:
        """``RUNNING`` or ``PAUSED`` -> ``IDLE``.

        Returns:
            Success or ``TIMER_TRANSITION_INVALID``.
        """
        return self._engine.change(lambda session, _now: session.reset(), TimerTransitionEnum.RESET)

    def acknowledge(self) -> ValidationResult:
        """``RINGING`` -> ``IDLE`` (OK).

        Returns:
            Success or ``TIMER_TRANSITION_INVALID``.
        """
        return self._engine.change(lambda session, _now: session.acknowledge(), TimerTransitionEnum.ACKNOWLEDGED)

    def restart(self) -> ValidationResult:
        """``RINGING`` -> ``RUNNING`` for the full configured duration.

        Returns:
            Success or ``TIMER_TRANSITION_INVALID``.
        """
        duration = self._engine.settings().duration
        return self._engine.change(lambda session, now: session.restart(now, duration), TimerTransitionEnum.RESTARTED)

    def snooze(self) -> ValidationResult:
        """``RINGING`` -> ``RUNNING`` (snoozed) for ``timer.snooze_minutes``.

        Returns:
            Success or ``TIMER_TRANSITION_INVALID``.
        """
        snooze = self._snooze
        return self._engine.change(lambda session, now: session.snooze(now, snooze), TimerTransitionEnum.SNOOZED)

    def update_config(self, settings: TimerSettings) -> ValidationResult:
        """Store new timer settings (edit dialog).

        Args:
            settings: Edited values.

        Returns:
            Success (also when nothing changed), or the rule or write failure.
        """
        current = self._reader.read()
        if current.data is None:
            return current.validation
        if current.data.settings == settings:
            return ValidationResult.success()
        validation = TimerConfigRules.validate_settings(settings, self._limits)
        if validation.is_failure:
            return validation
        written = self._writer.update(current.data.with_settings(settings, self._clock.now_utc()))
        if written.data is None:
            return written.validation
        _logger.info("Timer configuration stored")
        self._event_bus.publish(TimerConfigChangedEvent(config=written.data))
        return written.validation
