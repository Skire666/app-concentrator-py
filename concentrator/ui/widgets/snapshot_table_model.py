"""Read-only table model fed with snapshot rows (``AGENTS.md`` section 8.2)."""

from typing import Final, override

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QObject, QPersistentModelIndex, Qt, Signal
from PySide6.QtGui import QFont, QGuiApplication, QPalette

from concentrator.presentation.common.row_tone_enum import RowToneEnum
from concentrator.presentation.common.table_snapshot import TableRowSnapshot

type _Index = QModelIndex | QPersistentModelIndex

_BOLD_TONES: Final = frozenset({RowToneEnum.WARNING, RowToneEnum.ERROR})
_NO_ROOT: Final = QModelIndex()


def _changed_span(old: tuple[TableRowSnapshot, ...], new: tuple[TableRowSnapshot, ...]) -> tuple[int, int] | None:
    """Tell which rows changed when both tuples show the same keys in the same order.

    Args:
        old: Rows shown now.
        new: Rows to show.

    Returns:
        The first and last changed rows, ``None`` when the keys differ.
    """
    if len(old) != len(new) or any(before.key != after.key for before, after in zip(old, new, strict=True)):
        return None
    changed = [index for index, (before, after) in enumerate(zip(old, new, strict=True)) if before != after]
    return (changed[0], changed[-1]) if changed else None


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
    """Rows appended are inserted, oldest rows dropped are removed, other changes reset the model.

    Changed cells of the same rows (same keys, same order) are updated in place. Inserting, removing and
    updating keep the scroll position and the selection of the other rows; a reset loses them, so the panel
    applies the selection of the snapshot again. Rows with a ``checked`` value show a check box in the check
    column; a click emits ``check_toggled(key)`` and leaves the box as it is: the next snapshot shows the
    stored state.
    """

    check_toggled = Signal(object)

    def __init__(self, parent: QObject | None = None) -> None:
        """Create an empty model.

        Args:
            parent: Owner.
        """
        super().__init__(parent)
        self._columns: tuple[str, ...] = ()
        self._rows: tuple[TableRowSnapshot, ...] = ()
        self._check_column = -1

    @property
    def check_column(self) -> int:
        """Column of the check boxes, ``-1`` for none."""
        return self._check_column

    def set_check_column(self, column: int) -> None:
        """Choose the column that carries the check boxes.

        Args:
            column: Column index, ``-1`` for none.
        """
        if column != self._check_column:
            self.beginResetModel()
            self._check_column = column
            self.endResetModel()

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
        span = _changed_span(old, rows)
        if span is not None:
            self._rows = rows
            last_column = max(0, len(self._columns) - 1)
            self.dataChanged.emit(self.index(span[0], 0), self.index(span[1], last_column))
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
        if role == Qt.ItemDataRole.CheckStateRole and self._has_check(index):
            return Qt.CheckState.Checked if row.checked else Qt.CheckState.Unchecked
        return None

    @override
    def flags(self, index: _Index) -> Qt.ItemFlag:
        flags = super().flags(index)
        if self._has_check(index) and self._rows[index.row()].check_enabled:
            return flags | Qt.ItemFlag.ItemIsUserCheckable
        return flags

    @override
    def setData(self, index: _Index, value: object, role: int = Qt.ItemDataRole.EditRole) -> bool:
        if role == Qt.ItemDataRole.CheckStateRole and self._has_check(index) and self._rows[index.row()].check_enabled:
            self.check_toggled.emit(self._rows[index.row()].key)
        return False

    def _has_check(self, index: _Index) -> bool:
        """Tell whether a cell shows a check box.

        Args:
            index: Cell.

        Returns:
            Whether the cell is in the check column of a row that has a check state.
        """
        if not index.isValid() or index.column() != self._check_column or not 0 <= index.row() < len(self._rows):
            return False
        return self._rows[index.row()].checked is not None

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
