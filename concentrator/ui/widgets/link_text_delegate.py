"""Item delegate drawing the links of the cells as hyperlinks; a click on a link sends it, elsewhere selects."""

from typing import override

from PySide6.QtCore import QAbstractItemModel, QEvent, QModelIndex, QPersistentModelIndex, QRect, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QMouseEvent, QPainter, QPalette
from PySide6.QtWidgets import QAbstractItemView, QStyle, QStyledItemDelegate, QStyleOptionViewItem

from concentrator.presentation.common.table_snapshot import CellLinkSnapshot
from concentrator.ui.widgets.snapshot_table_model import SnapshotTableModel

type _Index = QModelIndex | QPersistentModelIndex


class LinkTextDelegate(QStyledItemDelegate):
    """Draws the cells that hold links (``TableRowSnapshot.links``) and finds the link under the mouse.

    Signals:
        link_clicked(object, int): Key of the row and number of the link clicked.
    """

    link_clicked = Signal(object, int)

    def __init__(self, model: SnapshotTableModel, view: QAbstractItemView) -> None:
        """Create the delegate of a table.

        Args:
            model: Rows of the table.
            view: The table (its viewport shows a pointing hand over a link).
        """
        super().__init__(view)
        self._model = model
        self._view = view

    @override
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: _Index) -> None:
        links = self._links(index)
        if not links:
            super().paint(painter, option, index)
            return
        item = QStyleOptionViewItem(option)
        self.initStyleOption(item, index)
        text = item.text
        item.text = ""
        style = self._view.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, item, painter, self._view)
        area = style.subElementRect(QStyle.SubElement.SE_ItemViewItemText, item, self._view)
        selected = bool(item.state & QStyle.StateFlag.State_Selected)
        self._draw_text(painter, item, area, (text, links), selected=selected)

    @override
    def editorEvent(
        self, event: QEvent, model: QAbstractItemModel, option: QStyleOptionViewItem, index: _Index
    ) -> bool:
        if not isinstance(event, QMouseEvent):
            return super().editorEvent(event, model, option, index)
        link = self.link_at(option, index, event.position().toPoint().x())
        if event.type() == QEvent.Type.MouseMove:
            viewport = self._view.viewport()
            if link is None:
                viewport.unsetCursor()
            else:
                viewport.setCursor(Qt.CursorShape.PointingHandCursor)
        is_click = event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton
        if is_click and link is not None and 0 <= index.row() < len(self._model.rows):
            self.link_clicked.emit(self._model.rows[index.row()].key, link.index)
        return super().editorEvent(event, model, option, index)

    def link_at(self, option: QStyleOptionViewItem, index: _Index, x: int) -> CellLinkSnapshot | None:
        """Find the link under a horizontal position of a cell.

        Args:
            option: Style of the cell (its rectangle and font).
            index: Cell.
            x: Position in viewport coordinates.

        Returns:
            The link, ``None`` over plain text.
        """
        links = self._links(index)
        if not links:
            return None
        item = QStyleOptionViewItem(option)
        self.initStyleOption(item, index)
        area = self._view.style().subElementRect(QStyle.SubElement.SE_ItemViewItemText, item, self._view)
        text = item.text
        metrics = QFontMetrics(item.font)
        for link in links:
            left = area.left() + metrics.horizontalAdvance(text[: link.start])
            right = left + metrics.horizontalAdvance(text[link.start : link.end])
            if left <= x < right:
                return link
        return None

    def _links(self, index: _Index) -> tuple[CellLinkSnapshot, ...]:
        """Links of a cell.

        Args:
            index: Cell.

        Returns:
            Its links, in order.
        """
        rows = self._model.rows
        if not index.isValid() or not 0 <= index.row() < len(rows):
            return ()
        return tuple(link for link in rows[index.row()].links if link.column == index.column())

    @staticmethod
    def _draw_text(
        painter: QPainter,
        item: QStyleOptionViewItem,
        area: QRect,
        content: tuple[str, tuple[CellLinkSnapshot, ...]],
        *,
        selected: bool,
    ) -> None:
        """Draw the text of a cell, its links underlined in the link color.

        Args:
            painter: Painter of the view.
            item: Style of the cell.
            area: Rectangle of the text.
            content: Text of the cell and its links (sorted, not overlapping).
            selected: Whether the row is selected (the highlighted text color is kept for links).
        """
        palette = item.palette
        plain = palette.color(QPalette.ColorRole.HighlightedText if selected else QPalette.ColorRole.Text)
        link_color = palette.color(QPalette.ColorRole.HighlightedText if selected else QPalette.ColorRole.Link)
        font = QFont(item.font)
        link_font = QFont(font)
        link_font.setUnderline(True)
        painter.save()
        painter.setClipRect(area)
        x = area.left()
        for segment, is_link in _segments(*content):
            x = _draw_segment(
                painter, (area, x), segment, link_font if is_link else font, link_color if is_link else plain
            )
        painter.restore()


def _segments(text: str, links: tuple[CellLinkSnapshot, ...]) -> list[tuple[str, bool]]:
    """Cut a cell text into plain and link pieces.

    Args:
        text: Text of the cell.
        links: Its links, sorted and not overlapping.

    Returns:
        The pieces in order, each with whether it is a link.
    """
    pieces: list[tuple[str, bool]] = []
    position = 0
    for link in links:
        pieces.extend(((text[position : link.start], False), (text[link.start : link.end], True)))
        position = link.end
    pieces.append((text[position:], False))
    return pieces


def _draw_segment(painter: QPainter, place: tuple[QRect, int], text: str, font: QFont, color: QColor) -> int:
    """Draw a piece of text at a horizontal position.

    Args:
        painter: Painter of the view.
        place: Rectangle of the cell text and the left position of the piece.
        text: Piece of text.
        font: Its font.
        color: Its color.

    Returns:
        The position after the piece.
    """
    area, x = place
    if not text:
        return x
    painter.setFont(font)
    painter.setPen(color)
    width = QFontMetrics(font).horizontalAdvance(text)
    painter.drawText(QRect(x, area.top(), width, area.height()), Qt.AlignmentFlag.AlignVCenter, text)
    return x + width
