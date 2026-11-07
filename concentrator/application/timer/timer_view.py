"""What the timer shows at one instant."""

from dataclasses import dataclass
from datetime import datetime

from concentrator.domain.timer.timer_state_enum import TimerStateEnum


@dataclass(frozen=True, slots=True, kw_only=True)
class TimerView:
    """Read model of the countdown for the presenters.

    Attributes:
        state: Current state.
        displayed_seconds: Value of the display.
        snoozed: The running or paused countdown is a snooze.
        ends_at: Wall-clock end of a running countdown (UTC, computed once when it started running),
            ``None`` otherwise.
        ringing_ms: How long the alarm has been ringing, ``0`` when not ringing.
    """

    state: TimerStateEnum
    displayed_seconds: int
    snoozed: bool
    ends_at: datetime | None
    ringing_ms: int


def blink_phase(ringing_ms: int, interval_ms: int) -> int:
    """Return the blink phase of a ringing display: even phases show the alert, odd ones do not.

    Args:
        ringing_ms: How long the alarm has been ringing.
        interval_ms: ``ui.alert_blink_interval_ms``.

    Returns:
        The phase number.
    """
    return ringing_ms // interval_ms
