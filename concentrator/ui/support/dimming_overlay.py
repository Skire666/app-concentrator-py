"""Darkens the main window behind a dialog (ADR-036)."""

from typing import Final, override

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QPainter, QPaintEvent, QPalette
from PySide6.QtWidgets import QWidget

FULL_ALPHA: Final = 255
PERCENT: Final = 100


class DimmingOverlay(QWidget):
    """Child of the main window covering its whole client area while at least one dialog is open.

    The color is the palette's shadow color at ``ui.dialog_overlay_opacity_percent``: 10 % makes the
    window 10 % darker.
    """

    def __init__(self, host: QWidget, opacity_percent: int) -> None:
        """Create the overlay (hidden).

        Args:
            host: Main window.
            opacity_percent: ``ui.dialog_overlay_opacity_percent``.
        """
        super().__init__(host)
        self._host = host
        self._alpha = round(FULL_ALPHA * opacity_percent / PERCENT)
        self._depth = 0
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.hide()
        host.installEventFilter(self)

    @property
    def alpha(self) -> int:
        """Alpha of the shadow color, 0..255."""
        return self._alpha

    def acquire(self) -> None:
        """Show the overlay for one more open dialog."""
        self._depth += 1
        if self._depth == 1:
            self.setGeometry(self._host.rect())
            self.raise_()
            self.show()

    def release(self) -> None:
        """Hide the overlay once the last open dialog is closed."""
        self._depth = max(0, self._depth - 1)
        if self._depth == 0:
            self.hide()

    @override
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self._host and event.type() == QEvent.Type.Resize:
            self.setGeometry(self._host.rect())
        return False

    @override
    def paintEvent(self, event: QPaintEvent) -> None:
        color = self.palette().color(QPalette.ColorRole.Shadow)
        color.setAlpha(self._alpha)
        painter = QPainter(self)
        painter.fillRect(self.rect(), color)
        painter.end()
