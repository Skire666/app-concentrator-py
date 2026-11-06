"""Style sheets. Colors come from the palette (``palette(...)``), never hard-coded."""

from typing import Final

HIGHLIGHTED_PROPERTY: Final = "highlighted"

MODULE_BAR_STYLE: Final = """
QToolButton { border: none; border-radius: 6px; padding: 6px 2px; }
QToolButton:hover { background: palette(midlight); }
QToolButton:checked { background: palette(highlight); color: palette(highlighted-text); }
QToolButton[highlighted="true"] { border: 2px solid palette(highlight); }
"""
