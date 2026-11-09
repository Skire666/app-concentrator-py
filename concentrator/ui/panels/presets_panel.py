"""Favorites of zone 2: a wrapping row of buttons, a context menu on each, and "Add..."."""

from functools import partial
from typing import override

from PySide6.QtCore import QEvent, QObject, QPoint, Qt, Signal
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtWidgets import QLabel, QMenu, QVBoxLayout, QWidget

from concentrator.presentation.timer.presets_snapshot import PresetSnapshot, PresetsSnapshot
from concentrator.presentation.timer.timer_layout import TimerLayout
from concentrator.ui.support.styles import SECTION_TITLE_STYLE
from concentrator.ui.widgets.flow_layout import FlowLayout
from concentrator.ui.widgets.snapshot_button import SnapshotButton


class PresetsPanel(QWidget):
    """Emits ``preset_action_requested(action, preset_id)`` for a favorite and ``action_requested(int)`` for Add.

    The panel filters the context menu events of the favorite buttons: a disabled button never handles
    nor forwards that event, but its event filters still see it, so the menu also opens while the timer
    runs.
    """

    action_requested = Signal(int)
    preset_action_requested = Signal(int, str)

    def __init__(self, layout: TimerLayout, parent: QWidget | None = None) -> None:
        """Build the panel.

        Args:
            layout: Spacing between the buttons.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._title = QLabel(self)
        self._title.setTextFormat(Qt.TextFormat.PlainText)
        self._title.setStyleSheet(SECTION_TITLE_STYLE)
        self._empty = QLabel(self)
        self._empty.setTextFormat(Qt.TextFormat.PlainText)
        self._empty.setWordWrap(True)
        self._host = QWidget(self)
        self._flow = FlowLayout(self._host, layout.spacing_px)
        self._add = SnapshotButton(self._host)
        self._add.action_requested.connect(self.action_requested)
        self._flow.addWidget(self._add)
        self._buttons: list[SnapshotButton] = []
        self._presets: tuple[PresetSnapshot, ...] = ()
        self._menu: QMenu | None = None
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.addWidget(self._title)
        column.addWidget(self._empty)
        column.addWidget(self._host)

    @property
    def preset_buttons(self) -> tuple[SnapshotButton, ...]:
        """One button per favorite, in display order (for tests)."""
        return tuple(self._buttons)

    @property
    def add_button(self) -> SnapshotButton:
        """The "Add..." button (for tests)."""
        return self._add

    @property
    def title(self) -> QLabel:
        """The panel title (for tests)."""
        return self._title

    @property
    def empty_label(self) -> QLabel:
        """The text shown without favorite (for tests)."""
        return self._empty

    @property
    def last_menu(self) -> QMenu | None:
        """The context menu shown last (for tests)."""
        return self._menu

    def render_snapshot(self, snapshot: PresetsSnapshot) -> None:
        """Show the favorites.

        Args:
            snapshot: Favorites state.
        """
        self.setUpdatesEnabled(False)
        self._presets = snapshot.presets
        self._title.setText(snapshot.title)
        self._empty.setText(snapshot.empty_text)
        self._empty.setVisible(bool(snapshot.empty_text))
        self._resize_buttons(len(snapshot.presets))
        for button, preset in zip(self._buttons, snapshot.presets, strict=True):
            button.apply(preset.button)
        self._add.apply(snapshot.add)
        self.setUpdatesEnabled(True)

    def show_menu(self, index: int, global_pos: QPoint) -> None:
        """Open the context menu of a favorite.

        Args:
            index: Display position of the favorite.
            global_pos: Screen position of the menu.
        """
        preset = self._presets[index]
        if self._menu is not None:
            self._menu.deleteLater()
        menu = QMenu(self)
        for item in preset.menu:
            entry = menu.addAction(item.text)
            entry.setToolTip(item.tooltip)
            entry.setEnabled(item.enabled)
            entry.setVisible(item.visible)
            entry.triggered.connect(partial(self.preset_action_requested.emit, int(item.action), preset.preset_id))
        self._menu = menu
        menu.popup(global_pos)

    @override
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if isinstance(event, QContextMenuEvent) and isinstance(watched, SnapshotButton) and watched in self._buttons:
            self.show_menu(self._buttons.index(watched), event.globalPos())
            return True
        return super().eventFilter(watched, event)

    def _resize_buttons(self, count: int) -> None:
        """Keep one button per favorite, before the "Add..." button.

        Args:
            count: Number of favorites.
        """
        while len(self._buttons) < count:
            index = len(self._buttons)
            button = SnapshotButton(self._host)
            button.action_requested.connect(partial(self._emit_preset_action, index))
            button.installEventFilter(self)
            self._flow.insert_widget(index, button)
            self._buttons.append(button)
        while len(self._buttons) > count:
            button = self._buttons.pop()
            self._flow.removeWidget(button)
            button.deleteLater()

    def _emit_preset_action(self, index: int, action: int) -> None:
        """Forward a click on a favorite with its id.

        Args:
            index: Display position of the clicked button.
            action: Action of its snapshot.
        """
        if index < len(self._presets):
            self.preset_action_requested.emit(action, self._presets[index].preset_id)
