"""Read-only table model fed with snapshot rows (``AGENTS.md`` section 8.2)."""

from typing import Final, override

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QObject, QPersistentModelIndex, Qt
from PySide6.QtGui import QFont, QGuiApplication, QPalette

from concentrator.presentation.common.row_tone_enum import RowToneEnum
from concentrator.presentation.common.table_snapshot import TableRowSnapshot

type _Index = QModelIndex | QPersistentModelIndex

_BOLD_TONES: Final = frozenset({RowToneEnum.WARNING, RowToneEnum.ERROR})
_NO_ROOT: Final = QModelIndex()


def _dropped_head(old: tuple[TableRowSnapshot, ...], new: tuple[TableRowSnapshot, ...]) -> int | None:
    """Tell how many leading rows went when ``new`` is ``old`` without its head, plus appended rows.

    Args:
        old: Rows shown now.
        new: Rows to show.

    Returns:
        The number of leading rows removed (0 for a pure append), ``None`` for any other change.
    """
    if not old:
        return 0
    if not new:
        return None
    first_key = new[0].key
    head = next((index for index, row in enumerate(old) if row.key == first_key), None)
    if head is None:
        return None
    kept = old[head:]
    return head if new[: len(kept)] == kept else None


class SnapshotTableModel(QAbstractTableModel):
    """Appending rows inserts them, dropping the oldest rows removes them, anything else resets the model.

    Inserting and removing keep the scroll position and the selection of the other rows; a reset loses
    them, so the panel applies the selection of the snapshot again.
    """

    def __init__(self, parent: QObject | None = None) -> None:
        """Create an empty model.

        Args:
            parent: Owner.
        """
        super().__init__(parent)
        self._columns: tuple[str, ...] = ()
        self._rows: tuple[TableRowSnapshot, ...] = ()

    @property
    def rows(self) -> tuple[TableRowSnapshot, ...]:
        """Rows shown."""
        return self._rows

    def set_columns(self, columns: tuple[str, ...]) -> None:
        """Show other header texts (same number of columns, or a reset).

        Args:
            columns: Header texts.
        """
        if columns == self._columns:
            return
        if len(columns) != len(self._columns):
            self.beginResetModel()
            self._columns = columns
            self.endResetModel()
            return
        self._columns = columns
        self.headerDataChanged.emit(Qt.Orientation.Horizontal, 0, len(columns) - 1)

    def set_rows(self, rows: tuple[TableRowSnapshot, ...]) -> bool:
        """Show other rows with the smallest change.

        Args:
            rows: Rows to show, in order.

        Returns:
            Whether the model was reset.
        """
        old = self._rows
        if rows == old:
            return False
        head = _dropped_head(old, rows)
        if head is None:
            self.beginResetModel()
            self._rows = rows
            self.endResetModel()
            return True
        if head:
            self.beginRemoveRows(_NO_ROOT, 0, head - 1)
            self._rows = old[head:]
            self.endRemoveRows()
        kept = len(old) - head
        if len(rows) > kept:
            self.beginInsertRows(_NO_ROOT, kept, len(rows) - 1)
            self._rows = rows
            self.endInsertRows()
        return False

    @override
    def rowCount(self, parent: _Index = _NO_ROOT) -> int:
        return 0 if parent.isValid() else len(self._rows)

    @override
    def columnCount(self, parent: _Index = _NO_ROOT) -> int:
        return 0 if parent.isValid() else len(self._columns)

    @override
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if orientation is Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self._columns[section] if 0 <= section < len(self._columns) else None
        return None

    @override
    def data(self, index: _Index, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return None
        row = self._rows[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            cells = row.cells
            return cells[index.column()] if 0 <= index.column() < len(cells) else ""
        if role == Qt.ItemDataRole.FontRole and row.tone in _BOLD_TONES:
            font = QFont()
            font.setBold(True)
            return font
        if role == Qt.ItemDataRole.ForegroundRole:
            return self._foreground(row.tone)
        return None

    @staticmethod
    def _foreground(tone: RowToneEnum) -> object:
        """Text color of a tone, taken from the palette.

        Args:
            tone: Emphasis of the row.

        Returns:
            The brush, ``None`` for the default color.
        """
        palette = QGuiApplication.palette()
        if tone is RowToneEnum.MUTED:
            return palette.brush(QPalette.ColorRole.PlaceholderText)
        if tone is RowToneEnum.ERROR:
            return palette.brush(QPalette.ColorRole.Highlight)
        return None
