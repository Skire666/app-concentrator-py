"""Modal startup dialogs shown before the main window, implemented by ``ui.windows.startup_dialogs``."""

from typing import Protocol


class StartupDialogsPort(Protocol):
    """Shows the first-run and recovery dialogs; their panels are registered with the render coordinator."""

    def show_first_run(self) -> None:
        """Render and show the first-run dialog; return when it closes."""
        ...

    def show_recovery(self) -> None:
        """Render and show the recovery dialog; return when it closes."""
        ...

    def close_current(self) -> None:
        """Close the dialog being shown (an action moved the startup on)."""
        ...
