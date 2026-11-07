"""Draws the user's attention to the application (Windows notification, taskbar button)."""

from typing import Protocol

from concentrator.domain.common.validation_result import ValidationResult


class AttentionPort(Protocol):
    """Notification area message and flashing taskbar button."""

    def is_application_active(self) -> bool:
        """Tell whether a Concentrator window (main window or one of its dialogs) is the active window.

        Returns:
            Whether the user is looking at the application.
        """
        ...

    def notify(self, title: str, message: str) -> ValidationResult:
        """Show a Windows notification.

        Args:
            title: Translated title.
            message: Translated message.

        Returns:
            Success or ``NOTIFICATION_UNAVAILABLE``.
        """
        ...

    def request_attention(self) -> None:
        """Flash the taskbar button until the main window is activated."""
        ...
