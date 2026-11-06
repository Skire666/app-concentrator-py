"""Hand-over from any thread to the main thread."""

from collections.abc import Callable
from typing import Protocol


class MainThreadDispatcherPort(Protocol):
    """Thread-safe queue of callbacks executed on the main thread."""

    def dispatch(self, callback: Callable[[], None]) -> None:
        """Run a callback on the main thread; may be called from any thread.

        Args:
            callback: Function to call on the main thread.
        """
        ...
