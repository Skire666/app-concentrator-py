"""``SchedulerPort`` on single-shot ``QTimer`` objects."""

from collections.abc import Callable
from typing import override

from PySide6.QtCore import QObject, QTimer

from concentrator.application.ports.scheduler_port import ScheduledCallPort, SchedulerPort


class _QtScheduledCall(ScheduledCallPort):
    """A pending single-shot timer; forgets itself once fired or cancelled."""

    def __init__(self, timer: QTimer, forget: Callable[[_QtScheduledCall], None]) -> None:
        """Wrap a configured timer.

        Args:
            timer: Single-shot timer owning the callback connection.
            forget: Removes the call from the scheduler's live set.
        """
        self._timer = timer
        self._forget = forget
        self._done = False

    @override
    def cancel(self) -> None:
        self.finish()

    def finish(self) -> None:
        """Stop and dispose of the timer (idempotent: the timer is deleted only once)."""
        if self._done:
            return
        self._done = True
        self._timer.stop()
        self._timer.deleteLater()
        self._forget(self)


class QtScheduler(SchedulerPort):
    """Runs callbacks on the Qt event loop of the main thread."""

    def __init__(self, parent: QObject) -> None:
        """Create a scheduler.

        Args:
            parent: Owner of the timers (lives on the main thread).
        """
        self._parent = parent
        self._live: set[_QtScheduledCall] = set()

    @override
    def call_soon(self, callback: Callable[[], None]) -> ScheduledCallPort:
        return self.call_later(0, callback)

    @override
    def call_later(self, delay_ms: int, callback: Callable[[], None]) -> ScheduledCallPort:
        timer = QTimer(self._parent)
        timer.setSingleShot(True)
        timer.setInterval(max(0, delay_ms))
        call = _QtScheduledCall(timer, self._live.discard)
        timer.timeout.connect(lambda: self._fire(call, callback))
        self._live.add(call)
        timer.start()
        return call

    @property
    def pending_count(self) -> int:
        """Number of calls not yet run nor cancelled."""
        return len(self._live)

    @staticmethod
    def _fire(call: _QtScheduledCall, callback: Callable[[], None]) -> None:
        """Release the timer, then run the callback.

        Args:
            call: Fired call.
            callback: User callback.
        """
        call.finish()
        callback()
