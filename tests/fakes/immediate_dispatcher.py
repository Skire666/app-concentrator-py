"""Dispatcher running callbacks synchronously."""

from collections.abc import Callable
from typing import override

from concentrator.application.ports.main_thread_dispatcher_port import MainThreadDispatcherPort


class ImmediateDispatcher(MainThreadDispatcherPort):
    """Runs each callback at once, on the calling thread."""

    def __init__(self) -> None:
        self.dispatched = 0

    @override
    def dispatch(self, callback: Callable[[], None]) -> None:
        self.dispatched += 1
        callback()
