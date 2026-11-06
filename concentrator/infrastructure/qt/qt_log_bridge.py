"""Routes Qt's own messages (``qWarning`` and friends) to the ``qt`` logger."""

import logging
from types import MappingProxyType
from typing import Final

from PySide6.QtCore import QMessageLogContext, QtMsgType, qInstallMessageHandler

QT_LOGGER_NAME: Final = "qt"
_LEVELS: Final = MappingProxyType(
    {
        QtMsgType.QtDebugMsg: logging.DEBUG,
        QtMsgType.QtInfoMsg: logging.INFO,
        QtMsgType.QtWarningMsg: logging.WARNING,
        QtMsgType.QtCriticalMsg: logging.ERROR,
        QtMsgType.QtFatalMsg: logging.CRITICAL,
    }
)


class QtLogBridge:
    """Installs a Qt message handler for the lifetime of the application."""

    def __init__(self) -> None:
        """Create an uninstalled bridge."""
        self._logger = logging.getLogger(QT_LOGGER_NAME)
        self._installed = False

    def install(self) -> None:
        """Route Qt messages to logging."""
        qInstallMessageHandler(self._handle)
        self._installed = True

    def uninstall(self) -> None:
        """Restore Qt's default message handler."""
        if self._installed:
            qInstallMessageHandler(None)
            self._installed = False

    def _handle(self, message_type: QtMsgType, context: QMessageLogContext, message: str) -> None:
        """Log one Qt message.

        Args:
            message_type: Qt severity.
            context: Source of the message (the category is logged when it is not ``default``).
            message: Text.
        """
        level = _LEVELS.get(message_type, logging.WARNING)
        category = context.category or ""
        if category and category != "default":
            self._logger.log(level, "[%s] %s", category, message)
        else:
            self._logger.log(level, "%s", message)
