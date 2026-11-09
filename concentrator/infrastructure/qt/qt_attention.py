"""``AttentionPort`` on the taskbar button."""

from collections.abc import Callable
from typing import override

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QWidget

from concentrator.application.ports.attention_port import AttentionPort


class QtAttention(AttentionPort):
    """``QApplication.alert`` flashes the taskbar button; the application state tells whether it is needed."""

    def __init__(
        self,
        window: QWidget,
        *,
        application_state: Callable[[], Qt.ApplicationState] = QGuiApplication.applicationState,
    ) -> None:
        """Create the adapter.

        Args:
            window: Main window whose taskbar button flashes.
            application_state: Current application state.
        """
        self._window = window
        self._application_state = application_state

    @override
    def is_application_active(self) -> bool:
        return self._application_state() is Qt.ApplicationState.ApplicationActive

    @override
    def request_attention(self) -> None:
        QApplication.alert(self._window, 0)
