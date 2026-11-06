"""Deferred execution on the main thread."""

from collections.abc import Callable
from typing import Protocol


class ScheduledCallPort(Protocol):
    """Handle of a deferred call."""

    def cancel(self) -> None:
        """Prevent the call from running; does nothing if it already ran or was cancelled."""
        ...


class SchedulerPort(Protocol):
    """Runs callbacks later on the main thread's event loop."""

    def call_soon(self, callback: Callable[[], None]) -> ScheduledCallPort:
        """Run a callback on the next event-loop turn.

        Args:
            callback: Function to call.

        Returns:
            A handle to cancel the call.
        """
        ...

    def call_later(self, delay_ms: int, callback: Callable[[], None]) -> ScheduledCallPort:
        """Run a callback after a delay.

        Args:
            delay_ms: Delay in milliseconds (0 behaves like ``call_soon``).
            callback: Function to call.

        Returns:
            A handle to cancel the call.
        """
        ...
