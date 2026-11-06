"""Scheduler driven by the test: nothing runs until ``run_pending`` or ``advance``."""

from collections.abc import Callable
from typing import override

from concentrator.application.ports.scheduler_port import ScheduledCallPort, SchedulerPort


class ManualCall(ScheduledCallPort):
    """A deferred call registered in a ``ManualScheduler``."""

    def __init__(self, due_ms: int, order: int, callback: Callable[[], None]) -> None:
        self.due_ms = due_ms
        self.order = order
        self.callback = callback
        self.cancelled = False
        self.done = False

    @override
    def cancel(self) -> None:
        self.cancelled = True

    @property
    def pending(self) -> bool:
        return not (self.cancelled or self.done)


class ManualScheduler(SchedulerPort):
    """Keeps its own virtual time in milliseconds."""

    def __init__(self) -> None:
        self.now_ms = 0
        self._calls: list[ManualCall] = []
        self._order = 0

    @override
    def call_soon(self, callback: Callable[[], None]) -> ManualCall:
        return self.call_later(0, callback)

    @override
    def call_later(self, delay_ms: int, callback: Callable[[], None]) -> ManualCall:
        self._order += 1
        call = ManualCall(self.now_ms + max(0, delay_ms), self._order, callback)
        self._calls.append(call)
        return call

    @property
    def pending_count(self) -> int:
        return sum(1 for call in self._calls if call.pending)

    def run_pending(self) -> int:
        """Run every call due now, including calls scheduled by those calls. Returns how many ran."""
        ran = 0
        while (call := self._next_due()) is not None:
            call.done = True
            call.callback()
            ran += 1
        return ran

    def advance(self, ms: int) -> int:
        """Move time forward, running due calls in time order. Returns how many ran."""
        target = self.now_ms + ms
        ran = self.run_pending()
        while (call := self._next_pending()) is not None and call.due_ms <= target:
            self.now_ms = call.due_ms
            ran += self.run_pending()
        self.now_ms = target
        return ran + self.run_pending()

    def _next_pending(self) -> ManualCall | None:
        pending = [call for call in self._calls if call.pending]
        return min(pending, key=lambda call: (call.due_ms, call.order), default=None)

    def _next_due(self) -> ManualCall | None:
        call = self._next_pending()
        return call if call is not None and call.due_ms <= self.now_ms else None
