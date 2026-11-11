"""List tabs, the "+" button and the description of the current list."""

from functools import partial

from PySide6.QtCore import QPoint, QSignalBlocker, Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMenu, QTabBar, QVBoxLayout, QWidget

from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.todo.todo_tabs_snapshot import TabSnapshot, TodoTabsSnapshot
from concentrator.ui.support.plain_text import plain_tooltip, without_mnemonic
from concentrator.ui.widgets.snapshot_button import SnapshotButton


class TodoTabsPanel(QWidget):
    """Emits ``action_requested(int)`` for "+" and ``list_action_requested(int, str)`` for a tab.

    Choosing a tab sends ``LIST_SELECT``; its context menu sends Edit, Move earlier, Move later and Delete.
    """

    action_requested = Signal(int)
    list_action_requested = Signal(int, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build the panel.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._tab_bar = QTabBar(self)
        self._tab_bar.setExpanding(False)
        self._tab_bar.setUsesScrollButtons(True)
        self._tab_bar.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._add = SnapshotButton(self)
        self._description = QLabel(self)
        self._description.setTextFormat(Qt.TextFormat.PlainText)
        self._description.setWordWrap(True)
        self._tabs: tuple[TabSnapshot, ...] = ()
        self._selected_index = -1
        self._menu: QMenu | None = None
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self._tab_bar, 1)
        row.addWidget(self._add)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(row)
        layout.addWidget(self._description)
        self._tab_bar.currentChanged.connect(self._emit_select)
        self._tab_bar.customContextMenuRequested.connect(self._open_menu_at)
        self._add.action_requested.connect(self.action_requested.emit)

    @property
    def tab_bar(self) -> QTabBar:
        """Tab bar (for tests)."""
        return self._tab_bar

    @property
    def description_text(self) -> str:
        """Description shown under the tabs (for tests)."""
        return self._description.text() if self._description.isVisibleTo(self) else ""

    @property
    def last_menu(self) -> QMenu | None:
        """Last context menu shown (for tests)."""
        return self._menu

    def render_snapshot(self, snapshot: TodoTabsSnapshot) -> None:
        """Show the tabs, the current one and its description (idempotent).

        Args:
            snapshot: Tabs state.
        """
        self.setUpdatesEnabled(False)
        blocker = QSignalBlocker(self._tab_bar)
        while self._tab_bar.count() > len(snapshot.tabs):
            self._tab_bar.removeTab(self._tab_bar.count() - 1)
        while self._tab_bar.count() < len(snapshot.tabs):
            self._tab_bar.addTab("")
        for index, tab in enumerate(snapshot.tabs):
            self._tab_bar.setTabText(index, without_mnemonic(tab.text))
            self._tab_bar.setTabToolTip(index, plain_tooltip(tab.tooltip))
        self._tab_bar.setCurrentIndex(snapshot.selected_index)
        self._selected_index = snapshot.selected_index
        blocker.unblock()
        self._tabs = snapshot.tabs
        self._add.apply(snapshot.add)
        self._description.setText(snapshot.description)
        self._description.setVisible(bool(snapshot.description))
        self.setUpdatesEnabled(True)

    def show_menu(self, index: int, global_pos: QPoint) -> None:
        """Open the context menu of a tab.

        Args:
            index: Tab index.
            global_pos: Screen position of the menu.
        """
        if not 0 <= index < len(self._tabs):
            return
        tab = self._tabs[index]
        if self._menu is not None:
            self._menu.deleteLater()
        menu = QMenu(self)
        for item in tab.menu:
            entry = menu.addAction(without_mnemonic(item.text))
            entry.setToolTip(item.tooltip)
            entry.setEnabled(item.enabled)
            entry.triggered.connect(partial(self.list_action_requested.emit, int(item.action), tab.list_id))
        self._menu = menu
        menu.popup(global_pos)

    def _open_menu_at(self, pos: QPoint) -> None:
        """Open the menu of the tab under the mouse.

        Args:
            pos: Position in the tab bar.
        """
        self.show_menu(self._tab_bar.tabAt(pos), self._tab_bar.mapToGlobal(pos))

    def _emit_select(self, index: int) -> None:
        """Send ``LIST_SELECT`` for the tab the user chose; the tab bar keeps showing the rendered tab.

        The next snapshot moves it. When the choice is ignored (cooldown), the snapshot does not change and
        no render comes, so the tab bar must not show a list the table does not show (code review).

        Args:
            index: New current tab.
        """
        blocker = QSignalBlocker(self._tab_bar)
        self._tab_bar.setCurrentIndex(self._selected_index)
        blocker.unblock()
        if 0 <= index < len(self._tabs):
            self.list_action_requested.emit(int(ActionIdEnum.LIST_SELECT), self._tabs[index].list_id)
