"""Read-only text whose links are hyperlinks; a click sends the number of the link, never opens it itself."""

import html
from typing import Final

from PySide6.QtCore import QUrl, Signal
from PySide6.QtWidgets import QTextBrowser, QWidget

from concentrator.presentation.todo.task_details_snapshot import NO_LINK, TextLineSnapshot

_HREF_SCHEME: Final = "link"
_LINE_BREAK: Final = "<br>"
_PREFORMATTED: Final = '<div style="white-space: pre-wrap">{body}</div>'
_ANCHOR: Final = '<a href="' + _HREF_SCHEME + ':{index}">{text}</a>'


def lines_html(lines: tuple[TextLineSnapshot, ...]) -> str:
    """Build the HTML of the lines: every user text is escaped, links get an index-based anchor.

    Args:
        lines: Lines of the text with their links.

    Returns:
        The HTML document body.
    """
    parts: list[str] = []
    for line in lines:
        if line.link_index == NO_LINK:
            parts.append(html.escape(line.text))
            continue
        before = html.escape(line.text[: line.link_start])
        link = _ANCHOR.format(index=line.link_index, text=html.escape(line.text[line.link_start : line.link_end]))
        after = html.escape(line.text[line.link_end :])
        parts.append(before + link + after)
    return _PREFORMATTED.format(body=_LINE_BREAK.join(parts))


class LinkTextBrowser(QTextBrowser):
    """Emits ``link_activated(int)`` when a link is clicked; links show in the palette link color, underlined."""

    link_activated = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create an empty browser that never follows its links.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setOpenLinks(False)
        self.setOpenExternalLinks(False)
        self._lines: tuple[TextLineSnapshot, ...] | None = None
        self.anchorClicked.connect(self._emit)

    def set_lines(self, lines: tuple[TextLineSnapshot, ...]) -> None:
        """Show lines (idempotent: the document is rebuilt only when they change).

        Args:
            lines: Lines of the text with their links.
        """
        if lines == self._lines:
            return
        self._lines = lines
        self.setHtml(lines_html(lines))

    def _emit(self, url: QUrl) -> None:
        """Send the number of a clicked link.

        Args:
            url: Anchor clicked (``link:<n>``).
        """
        number = url.path()
        if url.scheme() == _HREF_SCHEME and number.isdigit():
            self.link_activated.emit(int(number))
