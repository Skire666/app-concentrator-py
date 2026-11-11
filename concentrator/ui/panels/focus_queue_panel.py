"""Focus queue of zone 2: header, search field, quick-add field and the queued tasks in a scroll area."""

from functools import partial

from PySide6.QtCore import QPoint, QSignalBlocker, Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QMenu, QScrollArea, QVBoxLayout, QWidget

from concentrator.presentation.focus.focus_queue_snapshot import FocusQueueSnapshot, FocusRowSnapshot
from concentrator.ui.support.plain_text import without_mnemonic
from concentrator.ui.support.styles import INVALID_PROPERTY, SECTION_TITLE_STYLE, set_dynamic_property
from concentrator.ui.widgets.field_error_label import FieldErrorLabel
from concentrator.ui.widgets.focus_row_widget import FocusRowWidget
from concentrator.ui.widgets.task_picker_widget import TaskPickerWidget


class FocusQueuePanel(QWidget):
    """Emits the intents of the queue; ``render_snapshot`` shows a ``FocusQueueSnapshot``.

    Signals:
        row_action_requested(int, str): Check box, x button, context menu or Alt+Up/Down of a row (action,
            item id).
        picker_text_changed(str): Text of the search field.
        picked(str): Task chosen in the search results.
        quick_add_text_changed(str): Text of the quick-add field.
        quick_add_submitted(str): Enter in the quick-add field.
    """

    row_action_requested = Signal(int, str)
    picker_text_changed = Signal(str)
    picked = Signal(str)
    quick_add_text_changed = Signal(str)
    quick_add_submitted = Signal(str)

    def __init__(self, spacing_px: int, parent: QWidget | None = None) -> None:
        """Build the panel.

        Args:
            spacing_px: Space between its parts.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._title = QLabel(self)
        self._capacity = QLabel(self)
        self._picker = TaskPickerWidget(self)
        self._quick_add = QLineEdit(self)
        self._error = FieldErrorLabel(self)
        self._empty = QLabel(self)
        self._scroll = QScrollArea(self)
        self._host = QWidget(self._scroll)
        self._rows_layout = QVBoxLayout(self._host)
        self._rows: list[FocusRowWidget] = []
        self._snapshot_rows: tuple[FocusRowSnapshot, ...] = ()
        self._quick_add_cleared = 0
        self._menu: QMenu | None = None
        self._moved_item = ""
        self._build(spacing_px)
        self._connect()

    @property
    def rows(self) -> tuple[FocusRowWidget, ...]:
        """One widget per queued task, in order (for tests)."""
        return tuple(self._rows[: len(self._snapshot_rows)])

    @property
    def picker(self) -> TaskPickerWidget:
        """Search field (for tests)."""
        return self._picker

    @property
    def quick_add_input(self) -> QLineEdit:
        """Quick-add field (for tests)."""
        return self._quick_add

    @property
    def capacity_label(self) -> QLabel:
        """Capacity indicator (for tests)."""
        return self._capacity

    @property
    def error_text(self) -> str:
        """Message under the fields (for tests)."""
        return self._error.text() if self._error.isVisibleTo(self) else ""

    @property
    def empty_label(self) -> QLabel:
        """Text shown when the queue is empty (for tests)."""
        return self._empty

    @property
    def last_menu(self) -> QMenu | None:
        """Context menu shown last (for tests)."""
        return self._menu

    def render_snapshot(self, snapshot: FocusQueueSnapshot) -> None:
        """Show the queue (idempotent).

        Args:
            snapshot: Queue state.
        """
        self.setUpdatesEnabled(False)
        self._title.setText(snapshot.title)
        self._capacity.setText(snapshot.capacity)
        self._capacity.setToolTip(snapshot.capacity_tooltip)
        self._picker.apply(snapshot.picker, snapshot.choices)
        self._render_quick_add(snapshot)
        self._error.set_error(snapshot.error)
        self._empty.setText(snapshot.empty_text)
        self._empty.setVisible(not snapshot.rows)
        self._render_rows(snapshot.rows)
        self.setUpdatesEnabled(True)

    def show_menu(self, index: int, global_pos: QPoint) -> None:
        """Open the context menu of a row.

        Args:
            index: Position of the row.
            global_pos: Screen position of the menu.
        """
        row = self._snapshot_rows[index]
        if self._menu is not None:
            self._menu.deleteLater()
        menu = QMenu(self)
        for item in row.menu:
            entry = menu.addAction(without_mnemonic(item.text))
            entry.setToolTip(item.tooltip)
            entry.setEnabled(item.enabled)
            entry.triggered.connect(partial(self.row_action_requested.emit, int(item.action), row.item_id))
        self._menu = menu
        menu.popup(global_pos)

    def _render_quick_add(self, snapshot: FocusQueueSnapshot) -> None:
        """Show the quick-add field; an addition empties it.

        Args:
            snapshot: Queue state.
        """
        field = snapshot.quick_add
        blocker = QSignalBlocker(self._quick_add)
        if self._quick_add.text() != field.text or field.cleared_count != self._quick_add_cleared:
            self._quick_add.setText(field.text)
        self._quick_add_cleared = field.cleared_count
        self._quick_add.setPlaceholderText(field.placeholder)
        self._quick_add.setToolTip(field.tooltip)
        blocker.unblock()
        set_dynamic_property(self._quick_add, INVALID_PROPERTY, bool(snapshot.error))

    def _render_rows(self, rows: tuple[FocusRowSnapshot, ...]) -> None:
        """Keep one widget per row, reused by position; a row moved with the keyboard keeps the focus.

        Args:
            rows: Queued tasks, in order.
        """
        self._snapshot_rows = rows
        while len(self._rows) < len(rows):
            index = len(self._rows)
            widget = FocusRowWidget(self._host)
            widget.action_requested.connect(partial(self._emit_row_action, index))
            widget.menu_requested.connect(partial(self.show_menu, index))
            self._rows_layout.insertWidget(index, widget)
            self._rows.append(widget)
        for widget, row in zip(self._rows, rows, strict=False):
            widget.apply(row)
        for index, widget in enumerate(self._rows):
            widget.setVisible(index < len(rows))
        moved = next((widget for widget in self.rows if widget.item_id == self._moved_item), None)
        if moved is not None:
            moved.setFocus()
        self._moved_item = ""

    def _emit_row_action(self, index: int, action: int) -> None:
        """Forward an action of a row with its item.

        Args:
            index: Position of the row.
            action: Action of the control.
        """
        if index < len(self._snapshot_rows):
            item_id = self._snapshot_rows[index].item_id
            if self._rows[index].hasFocus():
                self._moved_item = item_id
            self.row_action_requested.emit(action, item_id)

    def _build(self, spacing_px: int) -> None:
        """Header, fields, message, then the rows taking the remaining height.

        Args:
            spacing_px: Space between the parts.
        """
        for label in (self._title, self._capacity, self._empty):
            label.setTextFormat(Qt.TextFormat.PlainText)
        self._title.setStyleSheet(SECTION_TITLE_STYLE)
        self._empty.setWordWrap(True)
        self._quick_add.setClearButtonEnabled(True)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.addStretch(1)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._scroll.setWidget(self._host)
        header = QHBoxLayout()
        header.addWidget(self._title, 1)
        header.addWidget(self._capacity)
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(spacing_px)
        column.addLayout(header)
        column.addWidget(self._picker)
        column.addWidget(self._quick_add)
        column.addWidget(self._error)
        column.addWidget(self._empty)
        column.addWidget(self._scroll, 1)

    def _connect(self) -> None:
        """Route the Qt signals to the intent signals."""
        self._picker.text_changed.connect(self.picker_text_changed)
        self._picker.picked.connect(self.picked)
        self._quick_add.textEdited.connect(self.quick_add_text_changed)
        self._quick_add.returnPressed.connect(lambda: self.quick_add_submitted.emit(self._quick_add.text()))
