"""Periodic heartbeat of the runtime engines (timer, chime, journal polling)."""

from collections.abc import Callable


class AppTicker:
    """Fans each tick out to the registered handlers, in registration order.

    Bootstrap owns the Qt timer that calls ``tick()`` every ``timer.tick_interval_ms``; nothing in the
    UI owns business timers.
    """

    def __init__(self) -> None:
        """Create a ticker without handlers."""
        self._handlers: list[Callable[[], None]] = []

    def register(self, handler: Callable[[], None]) -> None:
        """Add a handler called on every tick.

        Args:
            handler: Function to call; must stay fast (it runs on the main thread).
        """
        self._handlers.append(handler)

    def tick(self) -> None:
        """Call every registered handler once."""
        for handler in tuple(self._handlers):
            handler()
