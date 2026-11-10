"""Table of the journal entries: appended rows are inserted, Follow keeps the newest in view."""

from PySide6.QtCore import QByteArray, QItemSelection, QItemSelectionModel, QModelIndex, QSignalBlocker, Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QLabel, QStackedLayout, QTableView, QWidget

from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.table_snapshot import TableSnapshot
from concentrator.ui.widgets.snapshot_table_model import SnapshotTableModel


class JournalTablePanel(QWidget):
    """Emits ``selection_changed(rows, current)`` and ``action_requested(int)`` (Ctrl+C copies).

    ``rows`` is a tuple of the selected row indices, ``current`` the current row or -1.
    """

    selection_changed = Signal(object, int)
    action_requested = Signal(int)

    def __init__(self, column_widths_px: tuple[int, ...], parent: QWidget | None = None) -> None:
        """Build the table.

        Args:
            column_widths_px: Default widths of every column but the last one (``journal.default_column_widths_px``).
            parent: Parent widget.
        """
        super().__init__(parent)
        self._column_widths = column_widths_px
        self._model = SnapshotTableModel(self)
        self._table = QTableView(self)
        self._empty = QLabel(self)
        self._configure_table()
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        stack = QStackedLayout(self)
        stack.setStackingMode(QStackedLayout.StackingMode.StackAll)
        stack.addWidget(self._empty)
        stack.addWidget(self._table)
        shortcut = QShortcut(QKeySequence.StandardKey.Copy, self._table)
        shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        shortcut.activated.connect(lambda: self.action_requested.emit(int(ActionIdEnum.JOURNAL_COPY)))
        selection = self._table.selectionModel()
        selection.selectionChanged.connect(self._emit_selection)
        selection.currentRowChanged.connect(self._emit_selection)

    @property
    def model(self) -> SnapshotTableModel:
        """Table model (for tests)."""
        return self._model

    @property
    def table(self) -> QTableView:
        """Table view (for tests)."""
        return self._table

    @property
    def empty_text(self) -> str:
        """Text shown over an empty table (for tests)."""
        return self._empty.text() if self._empty.isVisibleTo(self) else ""

    def render_snapshot(self, snapshot: TableSnapshot) -> None:
        """Show the rows; keep the newest one in view when Follow is on.

        Args:
            snapshot: Table state.
        """
        changed = self._model.rows != snapshot.rows
        blocker = QSignalBlocker(self._table.selectionModel())
        self._model.set_columns(snapshot.columns)
        self._model.set_rows(snapshot.rows)
        blocker.unblock()
        self._apply_selection(snapshot.selection)
        self._empty.setText(snapshot.empty_text)
        self._empty.setVisible(not snapshot.rows)
        if changed and snapshot.scroll_to_end:
            self._table.scrollToBottom()

    def header_state(self) -> QByteArray:
        """Return the column widths blob to persist.

        Returns:
            The blob.
        """
        return self._table.horizontalHeader().saveState()

    def restore_header_state(self, state: QByteArray) -> bool:
        """Restore a persisted column widths blob.

        Args:
            state: Blob from ``header_state``.

        Returns:
            Whether Qt accepted it.
        """
        return self._table.horizontalHeader().restoreState(state)

    def reset_columns(self) -> None:
        """Apply the default column widths of the ini."""
        header = self._table.horizontalHeader()
        for column, width in enumerate(self._column_widths):
            header.resizeSection(column, width)

    def _configure_table(self) -> None:
        """Rows selected as a whole, several at once; fixed row height; the last column stretches."""
        table = self._table
        table.setModel(self._model)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setWordWrap(False)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        header = table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setHighlightSections(False)

    def _apply_selection(self, rows: tuple[int, ...]) -> None:
        """Select the rows of the snapshot when the table shows another selection.

        Args:
            rows: Indices of the rows to select.
        """
        model = self._table.selectionModel()
        if tuple(sorted(index.row() for index in model.selectedRows())) == tuple(sorted(rows)):
            return
        selection = QItemSelection()
        last_column = max(0, self._model.columnCount() - 1)
        for row in rows:
            selection.select(self._model.index(row, 0), self._model.index(row, last_column))
        blocker = QSignalBlocker(model)
        model.select(selection, QItemSelectionModel.SelectionFlag.ClearAndSelect)
        blocker.unblock()

    def _emit_selection(self, *_args: object) -> None:
        """Send the selected rows and the current row."""
        model = self._table.selectionModel()
        rows = tuple(sorted(index.row() for index in model.selectedRows()))
        current: QModelIndex = model.currentIndex()
        self.selection_changed.emit(rows, current.row() if current.isValid() else -1)
