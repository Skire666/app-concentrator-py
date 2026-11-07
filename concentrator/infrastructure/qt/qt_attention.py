"""``AttentionPort`` on the notification area icon and the taskbar button."""

import logging
from collections.abc import Callable
from typing import override

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QWidget

from concentrator.application.ports.attention_port import AttentionPort
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult

_logger = logging.getLogger(__name__)


def messages_supported() -> bool:
    """Tell whether Windows can show notification area messages.

    Returns:
        Whether a notification area exists and supports messages.
    """
    return QSystemTrayIcon.isSystemTrayAvailable() and QSystemTrayIcon.supportsMessages()


class QtAttention(AttentionPort):
    """Windows notification through ``QSystemTrayIcon.showMessage`` and ``QApplication.alert``.

    The icon is owned by the ui (it shows the tray snapshot); bootstrap hands it over, together with the
    main window, so this adapter needs no presentation type.
    """

    def __init__(
        self,
        tray: QSystemTrayIcon,
        window: QWidget,
        duration_ms: int,
        *,
        supported: Callable[[], bool] = messages_supported,
        application_state: Callable[[], Qt.ApplicationState] = QGuiApplication.applicationState,
    ) -> None:
        """Create the adapter.

        Args:
            tray: Notification area icon (visible).
            window: Main window whose taskbar button flashes.
            duration_ms: ``timer.notification_duration_ms``.
            supported: Tells whether messages can be shown.
            application_state: Current application state.
        """
        self._tray = tray
        self._window = window
        self._duration_ms = duration_ms
        self._supported = supported
        self._application_state = application_state

    @override
    def is_application_active(self) -> bool:
        return self._application_state() is Qt.ApplicationState.ApplicationActive

    @override
    def notify(self, title: str, message: str) -> ValidationResult:
        if not self._supported() or not self._tray.isVisible():
            _logger.warning("Windows notifications are not available")
            return ValidationResult.failure(ErrorCodeEnum.NOTIFICATION_UNAVAILABLE)
        self._tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, self._duration_ms)
        return ValidationResult.success()

    @override
    def request_attention(self) -> None:
        QApplication.alert(self._window, 0)
