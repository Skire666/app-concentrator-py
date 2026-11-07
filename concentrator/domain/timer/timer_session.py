"""The countdown state machine (runtime only, never persisted)."""

from dataclasses import dataclass, replace
from typing import Final, Self

from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.timer.duration import MS_PER_SECOND, Duration
from concentrator.domain.timer.timer_settings import TimerSettings
from concentrator.domain.timer.timer_state_enum import TimerStateEnum
from concentrator.domain.timer.timer_transition_enum import TimerTransitionEnum

_COUNTING: Final = frozenset({TimerStateEnum.RUNNING, TimerStateEnum.PAUSED})


@dataclass(frozen=True, slots=True, kw_only=True)
class TimerTickResult:
    """Outcome of ``TimerSession.tick``.

    Attributes:
        session: The session after the tick (the same one when nothing happened).
        transitions: What happened, in order; empty when the state did not change.
    """

    session: TimerSession
    transitions: tuple[TimerTransitionEnum, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class TimerSession:
    """State, deadline and alarm start of the countdown.

    Times are integer milliseconds of a monotonic clock, passed in by the caller: the remaining time is
    always ``deadline - now``, never a decremented counter, and integers keep long runs exact. Each
    command returns a new session, or ``TIMER_TRANSITION_INVALID`` when the current state does not
    allow it.

    Attributes:
        state: Current state.
        deadline_ms: When the countdown reaches zero (``RUNNING``).
        paused_remaining_ms: Remaining time frozen by a pause (``PAUSED``).
        ringing_since_ms: When the alarm started (``RINGING``).
        snoozed: The running countdown is a snooze.
    """

    state: TimerStateEnum = TimerStateEnum.IDLE
    deadline_ms: int = 0
    paused_remaining_ms: int = 0
    ringing_since_ms: int = 0
    snoozed: bool = False

    @classmethod
    def idle(cls) -> Self:
        """Return a session waiting to start.

        Returns:
            An ``IDLE`` session.
        """
        return cls()

    def start(self, now_ms: int, duration: Duration) -> DataResult[TimerSession]:
        """``IDLE`` -> ``RUNNING`` for the configured duration.

        Args:
            now_ms: Monotonic time.
            duration: Configured duration.

        Returns:
            The running session, or ``TIMER_TRANSITION_INVALID``.
        """
        if self.state is not TimerStateEnum.IDLE:
            return _invalid()
        return DataResult.ok(_running(now_ms, duration.milliseconds, snoozed=False))

    def pause(self, now_ms: int) -> DataResult[TimerSession]:
        """``RUNNING`` -> ``PAUSED``, freezing the remaining time.

        Args:
            now_ms: Monotonic time.

        Returns:
            The paused session, or ``TIMER_TRANSITION_INVALID``.
        """
        if self.state is not TimerStateEnum.RUNNING:
            return _invalid()
        paused = replace(self, state=TimerStateEnum.PAUSED, paused_remaining_ms=self.remaining_ms(now_ms))
        return DataResult.ok(paused)

    def resume(self, now_ms: int) -> DataResult[TimerSession]:
        """``PAUSED`` -> ``RUNNING`` with the frozen remaining time.

        Args:
            now_ms: Monotonic time.

        Returns:
            The running session (still snoozed if it was), or ``TIMER_TRANSITION_INVALID``.
        """
        if self.state is not TimerStateEnum.PAUSED:
            return _invalid()
        return DataResult.ok(_running(now_ms, self.paused_remaining_ms, snoozed=self.snoozed))

    def reset(self) -> DataResult[TimerSession]:
        """``RUNNING`` or ``PAUSED`` -> ``IDLE`` (the snooze flag is cleared).

        Returns:
            The idle session, or ``TIMER_TRANSITION_INVALID``.
        """
        if self.state not in _COUNTING:
            return _invalid()
        return DataResult.ok(self.idle())

    def acknowledge(self) -> DataResult[TimerSession]:
        """``RINGING`` -> ``IDLE`` (OK button).

        Returns:
            The idle session, or ``TIMER_TRANSITION_INVALID``.
        """
        if self.state is not TimerStateEnum.RINGING:
            return _invalid()
        return DataResult.ok(self.idle())

    def restart(self, now_ms: int, duration: Duration) -> DataResult[TimerSession]:
        """``RINGING`` -> ``RUNNING`` for the full configured duration.

        Args:
            now_ms: Monotonic time.
            duration: Configured duration.

        Returns:
            The running session, or ``TIMER_TRANSITION_INVALID``.
        """
        if self.state is not TimerStateEnum.RINGING:
            return _invalid()
        return DataResult.ok(_running(now_ms, duration.milliseconds, snoozed=False))

    def snooze(self, now_ms: int, snooze: Duration) -> DataResult[TimerSession]:
        """``RINGING`` -> ``RUNNING`` (snoozed) for the snooze duration.

        Args:
            now_ms: Monotonic time.
            snooze: ``timer.snooze_minutes``.

        Returns:
            The snoozed session, or ``TIMER_TRANSITION_INVALID``.
        """
        if self.state is not TimerStateEnum.RINGING:
            return _invalid()
        return DataResult.ok(_running(now_ms, snooze.milliseconds, snoozed=True))

    def tick(self, now_ms: int, settings: TimerSettings) -> TimerTickResult:
        """Start the alarm at zero; stop it (and restart the countdown) after the automatic stop delay.

        Args:
            now_ms: Monotonic time.
            settings: Current configuration (automatic stop, restart and duration).

        Returns:
            The new session and its transitions.
        """
        if self.state is TimerStateEnum.RUNNING and self.remaining_ms(now_ms) <= 0:
            ringing = replace(self, state=TimerStateEnum.RINGING, ringing_since_ms=now_ms, snoozed=False)
            return TimerTickResult(session=ringing, transitions=(TimerTransitionEnum.ALARM_STARTED,))
        if self.state is TimerStateEnum.RINGING:
            return self._tick_ringing(now_ms, settings)
        return TimerTickResult(session=self)

    def remaining_ms(self, now_ms: int) -> int:
        """Return the time left.

        Args:
            now_ms: Monotonic time.

        Returns:
            Milliseconds left while running or paused, ``0`` otherwise.
        """
        if self.state is TimerStateEnum.RUNNING:
            return max(0, self.deadline_ms - now_ms)
        if self.state is TimerStateEnum.PAUSED:
            return self.paused_remaining_ms
        return 0

    def displayed_seconds(self, now_ms: int, configured: Duration) -> int:
        """Return the value of the display.

        Args:
            now_ms: Monotonic time.
            configured: Configured duration, shown while ``IDLE``.

        Returns:
            The configured duration (``IDLE``), the remaining time rounded up (``RUNNING``, ``PAUSED``)
            or ``0`` (``RINGING``), in seconds.
        """
        if self.state is TimerStateEnum.IDLE:
            return configured.seconds
        return -(-self.remaining_ms(now_ms) // MS_PER_SECOND)

    def ringing_ms(self, now_ms: int) -> int:
        """Return how long the alarm has been ringing.

        Args:
            now_ms: Monotonic time.

        Returns:
            Milliseconds since the alarm started, ``0`` when not ringing.
        """
        if self.state is not TimerStateEnum.RINGING:
            return 0
        return max(0, now_ms - self.ringing_since_ms)

    def _tick_ringing(self, now_ms: int, settings: TimerSettings) -> TimerTickResult:
        """Apply the automatic stop of a ringing alarm.

        Args:
            now_ms: Monotonic time.
            settings: Current configuration.

        Returns:
            The session after the automatic stop or restart, or unchanged.
        """
        auto_stop_ms = settings.auto_stop_seconds * MS_PER_SECOND
        if auto_stop_ms <= 0 or self.ringing_ms(now_ms) < auto_stop_ms:
            return TimerTickResult(session=self)
        if settings.auto_restart:
            running = _running(now_ms, settings.duration.milliseconds, snoozed=False)
            return TimerTickResult(session=running, transitions=(TimerTransitionEnum.AUTO_RESTARTED,))
        return TimerTickResult(session=self.idle(), transitions=(TimerTransitionEnum.AUTO_STOPPED,))


def _invalid() -> DataResult[TimerSession]:
    """Refuse a command that the current state does not allow.

    Returns:
        ``TIMER_TRANSITION_INVALID``.
    """
    return DataResult.fail(ValidationResult.failure(ErrorCodeEnum.TIMER_TRANSITION_INVALID))


def _running(now_ms: int, remaining_ms: int, *, snoozed: bool) -> TimerSession:
    """Build a running session.

    Args:
        now_ms: Monotonic time.
        remaining_ms: Time to count down.
        snoozed: Whether this countdown is a snooze.

    Returns:
        The session.
    """
    return TimerSession(state=TimerStateEnum.RUNNING, deadline_ms=now_ms + remaining_ms, snoozed=snoozed)
