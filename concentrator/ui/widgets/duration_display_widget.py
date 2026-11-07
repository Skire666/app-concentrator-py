"""Large ``HH:MM:SS`` digits of the timer."""

from typing import Final

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QWidget

from concentrator.ui.support.styles import ALERT_PROPERTY, TIMER_DIGITS_STYLE, set_dynamic_property

TABULAR_NUMBERS: Final = "tnum"
"""OpenType feature giving every digit the same width."""
FEATURE_ON: Final = 1


class DurationDisplayWidget(QLabel):
    """Monospaced digits with tabular numbers, so the width never jitters; ``alert`` restyles them."""

    def __init__(self, font_family: str, font_size_px: int, parent: QWidget | None = None) -> None:
        """Create the display.

        Args:
            font_family: ``ui.timer_font_family`` (a monospaced font is used if it is not installed).
            font_size_px: ``ui.timer_font_size_px``.
            parent: Parent widget.
        """
        super().__init__(parent)
        font = QFont(font_family)
        font.setPixelSize(font_size_px)
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setFixedPitch(True)
        font.setFeature(QFont.Tag(TABULAR_NUMBERS), FEATURE_ON)
        self.setFont(font)
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(TIMER_DIGITS_STYLE)
        set_dynamic_property(self, ALERT_PROPERTY, False)

    @property
    def alert(self) -> bool:
        """Whether the alert style is shown (for tests)."""
        return bool(self.property(ALERT_PROPERTY))

    def apply(self, digits: str, *, alert: bool) -> None:
        """Show the digits.

        Args:
            digits: ``HH:MM:SS``.
            alert: Whether to show the alert style (blink phase of a ringing timer).
        """
        self.setText(digits)
        set_dynamic_property(self, ALERT_PROPERTY, alert)
