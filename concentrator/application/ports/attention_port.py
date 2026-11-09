"""Draws the user's attention to the application (taskbar button)."""

from typing import Protocol


class AttentionPort(Protocol):
    """Flashing taskbar button. Concentrator shows nothing in the notification area (ADR-038)."""

    def is_application_active(self) -> bool:
        """Tell whether a Concentrator window (main window or one of its dialogs) is the active window.

        Returns:
            Whether the user is looking at the application.
        """
        ...

    def request_attention(self) -> None:
        """Flash the taskbar button until the main window is activated."""
        ...
