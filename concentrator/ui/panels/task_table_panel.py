"""Task table of the current list: check boxes, sortable headers, keyboard shortcuts and context menu."""

from collections.abc import Callable
from functools import partial
from typing import override

from PySide6.QtCore import (
    QByteArray,
    QEvent,
    QItemSelection,
    QItemSelectionModel,
    QModelIndex,
    QObject,
    QPoint,
    QSignalBlocker,
    Qt,
    Signal,
)
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QLabel, QMenu, QStackedLayout, QTableView, QWidget

from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.table_snapshot import TableSnapshot
from concentrator.presentation.todo.task_menu_snapshot import TaskMenuSnapshot
from concentrator.presentation.todo.task_table_snapshot import TaskTableSnapshot
from concentrator.ui.support.plain_text import without_mnemonic
from concentrator.ui.widgets.snapshot_table_model import SnapshotTableModel


class TaskTablePanel(QWidget):
    """Emits the intents of the table; ``render_snapshot`` shows a ``TaskTableSnapshot``.

    Signals:
        selection_changed(tuple[str, ...]): Ids of the selected rows, in table order.
        sort_requested(int): Header clicked.
        check_toggled(str): Check box of a row clicked.
        activated(str): Double click or Enter on a row.
        toggle_requested(): Space.
        action_requested(int): Context menu item, Del (``TASK_DELETE``).
        move_requested(str): "Move to list" item of the context menu.
    """

    selection_changed = Signal(object)
    sort_requested = Signal(int)
    check_toggled = Signal(str)
    activated = Signal(str)
    toggle_requested = Signal()
    action_requested = Signal(int)
    move_requested = Signal(str)

    def __init__(self, column_widths_px: tuple[int, ...], parent: QWidget | None = None) -> None:
        """Build the table.

        Args:
            column_widths_px: Default widths of every column but the task column.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._column_widths = column_widths_px
        self._model = SnapshotTableModel(self)
        self._table = QTableView(self)
        self._empty = QLabel(self)
        self._menu = TaskMenuSnapshot(buttons=(), move_targets=())
        self._popup: QMenu | None = None
        self._sort_indicator = (-1, Qt.SortOrder.AscendingOrder)
        self._configure_table()
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setWordWrap(True)
        self._empty.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        stack = QStackedLayout(self)
        stack.setStackingMode(QStackedLayout.StackingMode.StackAll)
        stack.addWidget(self._empty)
        stack.addWidget(self._table)
        self._connect()
        self._table.installEventFilter(self)

    @property
    def model(self) -> SnapshotTableModel:
        """Table model (for tests)."""
        return self._model

    @property
    def table(self) -> QTableView:
        """Table view (for tests)."""
        return self._table

    @property
    def last_menu(self) -> QMenu | None:
        """Last context menu shown (for tests)."""
        return self._popup

    def render_snapshot(self, snapshot: TaskTableSnapshot) -> None:
        """Show the rows, the selection, the sort indicator and keep the context menu actions.

        Args:
            snapshot: Table state.
        """
        table = snapshot.table
        self.setUpdatesEnabled(False)
        scroll = self._table.verticalScrollBar().value()
        blocker = QSignalBlocker(self._table.selectionModel())
        self._model.set_check_column(table.check_column)
        self._model.set_columns(table.columns)
        reset = self._model.set_rows(table.rows)
        blocker.unblock()
        self._apply_selection(table.selection)
        if reset:
            self._table.verticalScrollBar().setValue(scroll)
        self._apply_header(table)
        self._empty.setText(table.empty_text)
        self._empty.setVisible(not table.rows)
        self._menu = snapshot.menu
        self.setUpdatesEnabled(True)

    def show_menu(self, global_pos: QPoint) -> None:
        """Open the context menu with the task actions of the last snapshot.

        Args:
            global_pos: Screen position of the menu.
        """
        if self._popup is not None:
            self._popup.deleteLater()
        menu = QMenu(self)
        for button in self._menu.buttons:
            if button.action is ActionIdEnum.TASK_MOVE:
                self._add_move_menu(menu, button.text, enabled=button.enabled)
                continue
            entry = menu.addAction(button.text)
            entry.setToolTip(button.tooltip)
            entry.setEnabled(button.enabled)
            entry.triggered.connect(partial(self.action_requested.emit, int(button.action)))
        self._popup = menu
        menu.popup(global_pos)

    def header_state(self) -> QByteArray:
        """Return the column widths and order blob to persist.

        Returns:
            The blob.
        """
        return self._table.horizontalHeader().saveState()

    def restore_header_state(self, state: QByteArray) -> bool:
        """Restore a persisted column blob.

        Args:
            state: Blob from ``header_state``.

        Returns:
            Whether Qt accepted it.
        """
        return self._table.horizontalHeader().restoreState(state)

    def reset_columns(self) -> None:
        """Apply the default column order and widths of the ini; the task column takes the rest."""
        header = self._table.horizontalHeader()
        for logical in range(header.count()):
            header.moveSection(header.visualIndex(logical), logical)
        widths = (self._column_widths[0], 0, *self._column_widths[1:])
        for column, width in enumerate(widths):
            if width:
                header.resizeSection(column, width)

    def _apply_header(self, table: TableSnapshot) -> None:
        """Show the sort indicator and the hidden columns of a snapshot.

        Args:
            table: Table state.
        """
        header = self._table.horizontalHeader()
        blocker = QSignalBlocker(header)
        order = Qt.SortOrder.DescendingOrder if table.sort_descending else Qt.SortOrder.AscendingOrder
        self._sort_indicator = (table.sort_column, order)
        header.setSortIndicator(table.sort_column, order)
        blocker.unblock()
        for column in range(self._model.columnCount()):
            hidden = column in table.hidden_columns
            if self._table.isColumnHidden(column) != hidden:
                self._table.setColumnHidden(column, hidden)

    def _add_move_menu(self, menu: QMenu, text: str, *, enabled: bool) -> None:
        """Add the "Move to list" submenu.

        Args:
            menu: Context menu.
            text: Submenu label.
            enabled: Whether moving is possible.
        """
        submenu = menu.addMenu(text)
        submenu.setEnabled(enabled)
        for target in self._menu.move_targets:
            entry = submenu.addAction(without_mnemonic(target.text))
            entry.setEnabled(target.enabled)
            entry.triggered.connect(partial(self.move_requested.emit, target.list_id))

    def _configure_table(self) -> None:
        """Whole rows, several at once; sortable and movable headers; the task column stretches."""
        table = self._table
        table.setModel(self._model)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setWordWrap(False)
        table.setAlternatingRowColors(True)
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        header = table.horizontalHeader()
        header.setSectionsClickable(True)
        header.setSectionsMovable(True)
        header.setSortIndicatorShown(True)
        header.setHighlightSections(False)
        header.setStretchLastSection(False)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

    def _connect(self) -> None:
        """Route the Qt signals to the intent signals."""
        selection = self._table.selectionModel()
        selection.selectionChanged.connect(self._emit_selection)
        self._model.check_toggled.connect(self._emit_check)
        self._table.horizontalHeader().sectionClicked.connect(self._emit_sort)
        self._table.doubleClicked.connect(self._emit_activated)
        self._table.customContextMenuRequested.connect(self._open_menu_at)
        self._model.modelReset.connect(self._stretch_task_column)

    @override
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self._table and isinstance(event, QKeyEvent) and event.type() == QEvent.Type.KeyPress:
            handler = self._key_handler(event)
            if handler is not None:
                handler()
                return True
        return super().eventFilter(watched, event)

    def _key_handler(self, event: QKeyEvent) -> Callable[[], None] | None:
        """Space toggles done, Enter opens, Del deletes (while the table has the focus).

        Args:
            event: Key press on the table.

        Returns:
            The handler of the key, ``None`` for any other key (the table handles it).
        """
        if event.modifiers() not in {Qt.KeyboardModifier.NoModifier, Qt.KeyboardModifier.KeypadModifier}:
            return None
        handlers: dict[int, Callable[[], None]] = {
            Qt.Key.Key_Space: self.toggle_requested.emit,
            Qt.Key.Key_Return: self._activate_current,
            Qt.Key.Key_Enter: self._activate_current,
            Qt.Key.Key_Delete: lambda: self.action_requested.emit(int(ActionIdEnum.TASK_DELETE)),
        }
        return handlers.get(event.key())

    def _emit_sort(self, column: int) -> None:
        """Send the column clicked; the header keeps the indicator of the rendered order.

        Qt moves the indicator itself on a click. The next snapshot shows the new order; when the click is
        ignored (cooldown), no render comes, so the indicator must not show an order the rows do not have.

        Args:
            column: Header clicked.
        """
        header = self._table.horizontalHeader()
        blocker = QSignalBlocker(header)
        header.setSortIndicator(*self._sort_indicator)
        blocker.unblock()
        self.sort_requested.emit(column)

    def _emit_check(self, key: object) -> None:
        """Send the id of the row whose check box was clicked.

        Args:
            key: Row key from the model.
        """
        self.check_toggled.emit(str(key))

    def _open_menu_at(self, pos: QPoint) -> None:
        """Open the context menu where the table was right-clicked.

        Args:
            pos: Position in the viewport.
        """
        self.show_menu(self._table.viewport().mapToGlobal(pos))

    def _stretch_task_column(self) -> None:
        """Let the task column take the free width."""
        header = self._table.horizontalHeader()
        if header.count() > 1:
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

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
        """Send the ids of the selected rows, in table order."""
        rows = sorted(index.row() for index in self._table.selectionModel().selectedRows())
        keys = self._model.rows
        self.selection_changed.emit(tuple(str(keys[row].key) for row in rows if 0 <= row < len(keys)))

    def _emit_activated(self, index: QModelIndex) -> None:
        """Send the id of the row double clicked.

        Args:
            index: Cell clicked.
        """
        rows = self._model.rows
        if index.isValid() and 0 <= index.row() < len(rows) and index.column() != self._model.check_column:
            self.activated.emit(str(rows[index.row()].key))

    def _activate_current(self) -> None:
        """Enter: open the current row."""
        index = self._table.currentIndex()
        rows = self._model.rows
        if index.isValid() and 0 <= index.row() < len(rows):
            self.activated.emit(str(rows[index.row()].key))
