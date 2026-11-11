"""Makes the mouse wheel scroll a page instead of changing the value of the control under the cursor.

Lists, spin boxes and sliders take the wheel by default, so a page that scrolls stops scrolling as
soon as the cursor passes over one of them, and the value changes instead. The redirect filters the
wheel events of those controls and hands them to the viewport of the scroll area, which scrolls.
The controls keep the keyboard and the mouse buttons; the wheel no longer gives them the focus.
"""

from typing import Final, override

from PySide6.QtCore import QCoreApplication, QEvent, QObject, Qt
from PySide6.QtWidgets import QAbstractScrollArea, QAbstractSlider, QAbstractSpinBox, QComboBox, QWidget

VALUE_CONTROLS: Final = (QComboBox, QAbstractSpinBox, QAbstractSlider)


class WheelScrollRedirect(QObject):
    """Event filter that sends the wheel of value controls to a scroll area."""

    def __init__(self, area: QAbstractScrollArea) -> None:
        """Create the filter, owned by the scroll area.

        Args:
            area: Scroll area that receives the wheel events.
        """
        super().__init__(area)
        self._area = area

    def watch(self, content: QWidget) -> None:
        """Filter every value control found under a widget.

        Args:
            content: Widget whose descendants are watched (build it completely first).
        """
        for control in content.findChildren(QWidget):
            if isinstance(control, VALUE_CONTROLS):
                control.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
                control.installEventFilter(self)

    @override
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() != QEvent.Type.Wheel:
            return False
        QCoreApplication.sendEvent(self._area.viewport(), event)
        return True
