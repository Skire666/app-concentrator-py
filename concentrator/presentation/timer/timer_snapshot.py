"""Snapshot of the timer panel (``TIMER``)."""

from dataclasses import dataclass

from concentrator.presentation.common.button_snapshot import ButtonSnapshot


@dataclass(frozen=True, slots=True, kw_only=True)
class TimerSnapshot:
    """Digits, caption and the three buttons of the timer.

    Attributes:
        digits: ``HH:MM:SS``.
        caption: Line under the digits, ``""`` when idle.
        alert: The digits show the alert style (ringing, visible blink phase).
        left: Edit timer, or Restart while ringing.
        middle: Reset, or OK while ringing.
        right: Start, Pause, Resume, or Snooze while ringing.
    """

    digits: str
    caption: str
    alert: bool
    left: ButtonSnapshot
    middle: ButtonSnapshot
    right: ButtonSnapshot
