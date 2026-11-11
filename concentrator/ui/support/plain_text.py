"""Show user text as typed in Qt places that would otherwise interpret it."""

import html
from typing import Final

_MNEMONIC: Final = "&"
_ESCAPED_MNEMONIC: Final = "&&"
_LINE_BREAK: Final = "\n"
_HTML_LINE_BREAK: Final = "<br>"
_TOOLTIP_TEMPLATE: Final = "<p style='white-space:pre-wrap'>{text}</p>"


def without_mnemonic(text: str) -> str:
    """Escape ``&`` for tab labels and menu items, where Qt reads it as a keyboard shortcut.

    Args:
        text: Text as typed ("R&D").

    Returns:
        The text Qt shows unchanged ("R&&D").
    """
    return text.replace(_MNEMONIC, _ESCAPED_MNEMONIC)


def plain_tooltip(text: str) -> str:
    """Turn plain text into a tooltip Qt cannot take for rich text (``AGENTS.md`` section 8.5).

    Args:
        text: Text as typed, possibly with line breaks.

    Returns:
        Escaped HTML keeping the line breaks, ``""`` for no tooltip.
    """
    if not text:
        return ""
    escaped = html.escape(text).replace(_LINE_BREAK, _HTML_LINE_BREAK)
    return _TOOLTIP_TEMPLATE.format(text=escaped)
