"""Layout that places its items left to right and wraps them onto new lines (Qt's flow layout example)."""

from typing import override

from PySide6.QtCore import QMargins, QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import QLayout, QLayoutItem, QWidget, QWidgetItem


class FlowLayout(QLayout):
    """Rows of items at their size hint; the height follows the width (``heightForWidth``).

    Hidden widgets take no room. Items keep their insertion order; ``insert_widget`` places a widget
    before another one (the favorites stay before the "Add..." button).
    """

    def __init__(self, parent: QWidget | None, spacing_px: int) -> None:
        """Create an empty layout.

        Args:
            parent: Widget laid out (or ``None``).
            spacing_px: Horizontal and vertical space between items.
        """
        super().__init__(parent)
        self._items: list[QLayoutItem] = []
        self.setSpacing(spacing_px)
        self.setContentsMargins(QMargins())

    def insert_widget(self, index: int, widget: QWidget) -> None:
        """Insert a widget at a position.

        Args:
            index: Position among the items (clamped to the end).
            widget: Widget to lay out; it becomes a child of the laid out widget.
        """
        self.addChildWidget(widget)
        self._items.insert(min(index, len(self._items)), QWidgetItem(widget))
        self.invalidate()

    @override
    def addItem(self, arg__1: QLayoutItem, /) -> None:
        self._items.append(arg__1)

    @override
    def count(self) -> int:
        return len(self._items)

    @override
    def itemAt(self, arg__1: int, /) -> QLayoutItem | None:
        return self._items[arg__1] if 0 <= arg__1 < len(self._items) else None

    @override
    def takeAt(self, arg__1: int, /) -> QLayoutItem | None:
        if not 0 <= arg__1 < len(self._items):
            return None
        item = self._items.pop(arg__1)
        self.invalidate()
        return item

    @override
    def expandingDirections(self) -> Qt.Orientation:
        return Qt.Orientation(0)

    @override
    def hasHeightForWidth(self) -> bool:
        return True

    @override
    def heightForWidth(self, arg__1: int, /) -> int:
        return self._arrange(QRect(0, 0, arg__1, 0), move=False)

    @override
    def setGeometry(self, arg__1: QRect, /) -> None:
        super().setGeometry(arg__1)
        self._arrange(arg__1, move=True)

    @override
    def sizeHint(self) -> QSize:
        return self.minimumSize()

    @override
    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            if not item.isEmpty():
                size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        return size + QSize(margins.left() + margins.right(), margins.top() + margins.bottom())

    def _arrange(self, rect: QRect, *, move: bool) -> int:
        """Place the items in a rectangle.

        Args:
            rect: Area of the layout.
            move: Whether to set the item geometries (``False`` only measures).

        Returns:
            The height the items need at this width.
        """
        margins = self.contentsMargins()
        area = rect.marginsRemoved(margins)
        spacing = self.spacing()
        x, y, line_height = area.x(), area.y(), 0
        for item in self._items:
            if item.isEmpty():
                continue
            hint = item.sizeHint()
            if x > area.x() and x + hint.width() > area.right() + 1:
                x, y, line_height = area.x(), y + line_height + spacing, 0
            if move:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x += hint.width() + spacing
            line_height = max(line_height, hint.height())
        return y + line_height - rect.y() + margins.bottom()
