"""``ClipboardPort`` on ``QGuiApplication.clipboard()``."""

from typing import override

from PySide6.QtGui import QGuiApplication

from concentrator.presentation.ports.clipboard_port import ClipboardPort


class QtClipboard(ClipboardPort):
    """The clipboard of the running application."""

    @override
    def set_text(self, text: str) -> None:
        QGuiApplication.clipboard().setText(text)
