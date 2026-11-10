"""The system clipboard, implemented by ``ui.support.QtClipboard``."""

from typing import Protocol


class ClipboardPort(Protocol):
    """Puts plain text in the clipboard."""

    def set_text(self, text: str) -> None:
        """Replace the clipboard content.

        Args:
            text: Plain text, lines separated by LF.
        """
        ...
