"""Tool button with a small count in its top right corner (Journal button of the module bar)."""

from typing import Final, override

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QFont, QPainter, QPaintEvent, QPalette
from PySide6.QtWidgets import QToolButton, QWidget

_PADDING_RATIO: Final = 0.3
_FONT_RATIO: Final = 0.85


class BadgeButton(QToolButton):
    """Draws its badge text over the button, in the highlight colors of the palette."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create a button without badge.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._badge = ""

    @property
    def badge(self) -> str:
        """Badge text, ``""`` when hidden."""
        return self._badge

    def set_badge(self, text: str) -> None:
        """Show or hide the badge.

        Args:
            text: Badge text, ``""`` to hide it.
        """
        if text != self._badge:
            self._badge = text
            self.update()

    @override
    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        if not self._badge:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        font = QFont(self.font())
        font.setBold(True)
        font.setPointSizeF(font.pointSizeF() * _FONT_RATIO)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        height = metrics.height()
        padding = height * _PADDING_RATIO
        width = max(float(height), metrics.horizontalAdvance(self._badge) + 2 * padding)
        area = QRectF(self.width() - width - padding, padding, width, height)
        palette = self.palette()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(palette.color(QPalette.ColorRole.Highlight))
        painter.drawRoundedRect(area, height / 2, height / 2)
        painter.setPen(palette.color(QPalette.ColorRole.HighlightedText))
        painter.drawText(area, Qt.AlignmentFlag.AlignCenter, self._badge)
        painter.end()
