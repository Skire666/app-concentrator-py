"""Modal timer edit dialog, implemented by ``ui.windows.timer_edit_dialog``."""

from typing import Protocol


class TimerEditDialogPort(Protocol):
    """Shows the edit dialog; its panel is registered with the render coordinator (``TIMER_EDIT``)."""

    def show_editor(self) -> None:
        """Render and show the dialog over the main window; return when it closes."""
        ...

    def close_editor(self) -> None:
        """Close the dialog (saved, or cancelled after confirmation)."""
        ...
