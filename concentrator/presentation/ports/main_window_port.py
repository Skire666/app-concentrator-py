"""The main window as seen by presenters (notification area menu), implemented by ``MainWindow``."""

from typing import Protocol


class MainWindowPort(Protocol):
    """Shows or closes the main window."""

    def show_in_front(self) -> None:
        """Restore the window if minimized and bring it to the front."""
        ...

    def request_close(self) -> None:
        """Close the window as its close button does (quit confirmation, pending changes)."""
        ...
