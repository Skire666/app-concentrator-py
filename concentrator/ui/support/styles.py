"""Style sheets. Colors come from the palette (``palette(...)``), never hard-coded."""

from typing import Final

from PySide6.QtWidgets import QWidget

HIGHLIGHTED_PROPERTY: Final = "highlighted"
WARNING_PROPERTY: Final = "warning"
ALERT_PROPERTY: Final = "alert"
INVALID_PROPERTY: Final = "invalid"

TIMER_DIGITS_STYLE: Final = """
QLabel { padding: 2px 12px; border-radius: 8px; }
QLabel[alert="true"] { background: palette(highlight); color: palette(highlighted-text); }
"""

FIELD_ERROR_STYLE: Final = """
QLabel { font-weight: bold; }
"""

SECTION_TITLE_STYLE: Final = """
QLabel { font-weight: bold; }
"""

INVALID_INPUT_STYLE: Final = """
*[invalid="true"] { border: 2px solid palette(highlight); border-radius: 3px; }
"""


def set_dynamic_property(widget: QWidget, name: str, value: bool) -> None:
    """Set a style sheet property and re-apply the style when it changed.

    Args:
        widget: Styled widget.
        name: Property name used in a style sheet selector.
        value: New value.
    """
    if widget.property(name) == value:
        return
    widget.setProperty(name, value)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


WARNING_TEXT_STYLE: Final = """
QLabel[warning="true"] { font-weight: bold; }
"""

MODULE_BAR_STYLE: Final = """
QToolButton { border: none; border-radius: 6px; padding: 6px 2px; }
QToolButton:hover { background: palette(midlight); }
QToolButton:checked { background: palette(highlight); color: palette(highlighted-text); }
QToolButton[highlighted="true"] { border: 2px solid palette(highlight); }
"""

FOCUS_ROW_STYLE: Final = """
QLabel[warning="true"] { font-weight: bold; }
QLabel[alert="true"] { font-weight: bold; color: palette(highlight); }
"""
