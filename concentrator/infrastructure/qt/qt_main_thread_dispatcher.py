"""``MainThreadDispatcherPort`` on a queued Qt signal."""

from collections.abc import Callable
from typing import override

from PySide6.QtCore import QObject, Qt, Signal, Slot

from concentrator.application.ports.main_thread_dispatcher_port import MainThreadDispatcherPort


class _DispatchBridge(QObject):
    """Main-thread receiver of the queued callbacks."""

    requested = Signal(object)

    def __init__(self, parent: QObject) -> None:
        """Create the bridge and connect it to itself with a queued connection.

        Args:
            parent: Main-thread owner; fixes the thread the callbacks run on.
        """
        super().__init__(parent)
        self.requested.connect(self._run, Qt.ConnectionType.QueuedConnection)

    @Slot(object)
    def _run(self, callback: Callable[[], None]) -> None:  # ruff: ignore[no-self-use] - bound slot runs on this QObject's thread
        """Run one callback on the main thread.

        Args:
            callback: Function to call.
        """
        callback()


class QtMainThreadDispatcher(MainThreadDispatcherPort):
    """Thread-safe: ``dispatch`` may be called from the writer thread or any other thread."""

    def __init__(self, parent: QObject) -> None:
        """Create a dispatcher.

        Args:
            parent: Main-thread owner of the internal bridge object.
        """
        self._bridge = _DispatchBridge(parent)

    @override
    def dispatch(self, callback: Callable[[], None]) -> None:
        self._bridge.requested.emit(callback)
