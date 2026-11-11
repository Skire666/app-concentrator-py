"""Item delegate drawing long cell texts cut with an overflow text, and links as hyperlinks.

A click on a link sends it; a click elsewhere selects, as usual.
"""

from typing import Final, override

from PySide6.QtCore import QAbstractItemModel, QEvent, QModelIndex, QPersistentModelIndex, QRect, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QMouseEvent, QPainter, QPalette
from PySide6.QtWidgets import QAbstractItemView, QStyle, QStyledItemDelegate, QStyleOptionViewItem

from concentrator.presentation.common.table_snapshot import CellLinkSnapshot
from concentrator.ui.widgets.snapshot_table_model import SnapshotTableModel

type _Index = QModelIndex | QPersistentModelIndex

_PERCENT: Final = 100


def shown_length(text: str, metrics: QFontMetrics, limit: int) -> int:
    """Count the characters of a text that fit in a width.

    Args:
        text: Text of the cell.
        metrics: Font of the cell.
        limit: Width the text may fill, in pixels.

    Returns:
        ``len(text)`` when the whole text fits, otherwise the longest prefix that fits.
    """
    if metrics.horizontalAdvance(text) <= limit:
        return len(text)
    low, high = 0, len(text)
    while low < high:
        middle = (low + high + 1) // 2
        if metrics.horizontalAdvance(text[:middle]) <= limit:
            low = middle
        else:
            high = middle - 1
    return low


def visible_links(links: tuple[CellLinkSnapshot, ...], length: int) -> tuple[CellLinkSnapshot, ...]:
    """Keep the parts of the links within the shown characters.

    Args:
        links: Links of the cell.
        length: Number of characters shown.

    Returns:
        The links that start before the cut, ended at the cut.
    """
    return tuple(
        CellLinkSnapshot(column=link.column, start=link.start, end=min(link.end, length), index=link.index)
        for link in links
        if link.start < length
    )


class LinkTextDelegate(QStyledItemDelegate):
    """Draws the cells that hold links or an overflow text and finds the link under the mouse.

    The cells of the overflow column show as much text as fits in ``text_width_percent`` of their width;
    a longer text is cut there and followed by the ``overflow`` of its row (``... (5 lines)``).

    Signals:
        link_clicked(object, int): Key of the row and number of the link clicked.
    """

    link_clicked = Signal(object, int)

    def __init__(self, model: SnapshotTableModel, view: QAbstractItemView, text_width_percent: int) -> None:
        """Create the delegate of a table.

        Args:
            model: Rows of the table.
            view: The table (its viewport shows a pointing hand over a link).
            text_width_percent: Share of the cell a text may fill before it is cut.
        """
        super().__init__(view)
        self._model = model
        self._view = view
        self._percent = text_width_percent
        self._overflow_column = -1

    def set_overflow_column(self, column: int) -> None:
        """Choose the column whose long texts are cut (``TableSnapshot.overflow_column``).

        Args:
            column: Column, ``-1`` for none.
        """
        self._overflow_column = column

    @override
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: _Index) -> None:
        links, overflow = self._cell(index)
        if not links and not overflow:
            super().paint(painter, option, index)
            return
        item = QStyleOptionViewItem(option)
        self.initStyleOption(item, index)
        text = item.text
        item.text = ""
        style = self._view.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, item, painter, self._view)
        area = style.subElementRect(QStyle.SubElement.SE_ItemViewItemText, item, self._view)
        length = self._length(text, QFontMetrics(item.font), area, overflow=overflow)
        suffix = overflow if length < len(text) else ""
        content = (text[:length], visible_links(links, length), suffix)
        self._draw_text(painter, item, area, content, selected=bool(item.state & QStyle.StateFlag.State_Selected))

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
        """Find the shown link under a horizontal position of a cell.

        Args:
            option: Style of the cell (its rectangle and font).
            index: Cell.
            x: Position in viewport coordinates.

        Returns:
            The link, ``None`` over plain text or over the overflow text.
        """
        links, overflow = self._cell(index)
        if not links:
            return None
        item = QStyleOptionViewItem(option)
        self.initStyleOption(item, index)
        area = self._view.style().subElementRect(QStyle.SubElement.SE_ItemViewItemText, item, self._view)
        text = item.text
        metrics = QFontMetrics(item.font)
        length = self._length(text, metrics, area, overflow=overflow)
        for link in visible_links(links, length):
            left = area.left() + metrics.horizontalAdvance(text[: link.start])
            right = left + metrics.horizontalAdvance(text[link.start : link.end])
            if left <= x < right:
                return link
        return None

    def _length(self, text: str, metrics: QFontMetrics, area: QRect, *, overflow: str) -> int:
        """Number of characters of a cell text that are shown.

        Args:
            text: Text of the cell.
            metrics: Its font.
            area: Rectangle of the text.
            overflow: Overflow text of the row; without one, the text is never cut (Qt clips it).

        Returns:
            The number of characters.
        """
        if not overflow:
            return len(text)
        return shown_length(text, metrics, area.width() * self._percent // _PERCENT)

    def _cell(self, index: _Index) -> tuple[tuple[CellLinkSnapshot, ...], str]:
        """Links and overflow text of a cell.

        Args:
            index: Cell.

        Returns:
            Its links in order, and the overflow text of its row in the overflow column (``""`` elsewhere).
        """
        rows = self._model.rows
        if not index.isValid() or not 0 <= index.row() < len(rows):
            return (), ""
        row = rows[index.row()]
        links = tuple(link for link in row.links if link.column == index.column())
        return links, row.overflow if index.column() == self._overflow_column else ""

    @staticmethod
    def _draw_text(
        painter: QPainter,
        item: QStyleOptionViewItem,
        area: QRect,
        content: tuple[str, tuple[CellLinkSnapshot, ...], str],
        *,
        selected: bool,
    ) -> None:
        """Draw the shown text of a cell, its links underlined in the link color, then the overflow text.

        Args:
            painter: Painter of the view.
            item: Style of the cell.
            area: Rectangle of the text.
            content: Shown text, its links (sorted, not overlapping) and the overflow text (``""`` when the
                whole text is shown).
            selected: Whether the row is selected (the highlighted text color is kept for links).
        """
        text, links, suffix = content
        palette = item.palette
        plain = palette.color(QPalette.ColorRole.HighlightedText if selected else QPalette.ColorRole.Text)
        link_color = palette.color(QPalette.ColorRole.HighlightedText if selected else QPalette.ColorRole.Link)
        font = QFont(item.font)
        link_font = QFont(font)
        link_font.setUnderline(True)
        painter.save()
        painter.setClipRect(area)
        x = area.left()
        for segment, is_link in (*_segments(text, links), (suffix, False)):
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
