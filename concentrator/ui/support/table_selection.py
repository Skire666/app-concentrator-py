"""Shows the selection of a table snapshot in a ``QTableView`` and keeps the rows the user looks at in view."""

from PySide6.QtCore import QItemSelection, QItemSelectionModel, QSignalBlocker
from PySide6.QtWidgets import QTableView

from concentrator.presentation.common.table_snapshot import TableSnapshot


class TableSelection:
    """Selects the rows of each snapshot without echoing the change, and scrolls only to a new selection.

    After a model reset the view loses its selection: selecting the same rows again must not move the view
    (code review of phase 7); a selection of other rows made elsewhere (Show in list, quick add, duplicate)
    is scrolled into view.
    """

    def __init__(self, view: QTableView, scroll_column: int) -> None:
        """Create the helper.

        Args:
            view: Table view showing a snapshot model.
            scroll_column: Column of the cell scrolled into view.
        """
        self._view = view
        self._scroll_column = scroll_column
        self._keys: tuple[int | str, ...] = ()

    def show(self, table: TableSnapshot, restored_scroll: int | None) -> None:
        """Select the rows of a snapshot, restore the scroll position of a reset, follow a new selection.

        Args:
            table: Rendered table (the model already holds its rows).
            restored_scroll: Scroll position before a model reset, ``None`` when the model was not reset.
        """
        changed = self._select(table.selection)
        if restored_scroll is not None:
            self._view.verticalScrollBar().setValue(restored_scroll)
        rows = table.rows
        keys = tuple(rows[row].key for row in sorted(table.selection) if 0 <= row < len(rows))
        model = self._view.model()
        if changed and keys and keys != self._keys:
            self._view.scrollTo(model.index(min(table.selection), self._scroll_column))
        self._keys = keys

    def _select(self, rows: tuple[int, ...]) -> bool:
        """Select rows when the view shows another selection.

        Args:
            rows: Indices of the rows to select.

        Returns:
            Whether the selection of the view changed.
        """
        selection_model = self._view.selectionModel()
        model = self._view.model()
        if tuple(sorted(index.row() for index in selection_model.selectedRows())) == tuple(sorted(rows)):
            return False
        selection = QItemSelection()
        last_column = max(0, model.columnCount() - 1)
        for row in rows:
            selection.select(model.index(row, 0), model.index(row, last_column))
        blocker = QSignalBlocker(selection_model)
        selection_model.select(selection, QItemSelectionModel.SelectionFlag.ClearAndSelect)
        blocker.unblock()
        return True
