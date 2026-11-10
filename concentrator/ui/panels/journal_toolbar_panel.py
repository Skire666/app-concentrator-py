"""Toolbar of the journal: level toggles and search on the first row, commands on the second."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from concentrator.presentation.journal.journal_snapshot import JournalToolbarSnapshot
from concentrator.ui.widgets.level_toggle_widget import LevelToggleWidget
from concentrator.ui.widgets.search_box_widget import SearchBoxWidget
from concentrator.ui.widgets.snapshot_button import SnapshotButton


class JournalToolbarPanel(QWidget):
    """Emits ``action_requested(int)``, ``level_toggled(int)`` and ``search_changed(str)``."""

    action_requested = Signal(int)
    level_toggled = Signal(int)
    search_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build the toolbar (the level toggles are created by the first render).

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._levels: list[LevelToggleWidget] = []
        self._levels_row = QHBoxLayout()
        self._search = SearchBoxWidget(self)
        self._search.search_changed.connect(self.search_changed.emit)
        self._follow = self._button(checkable=True)
        self._pause = self._button(checkable=True)
        self._paused_caption = QLabel(self)
        self._copy = self._button()
        self._clear_view = self._button()
        self._open_log_folder = self._button()
        self._build_layout()

    @property
    def search_box(self) -> SearchBoxWidget:
        """Search field (for tests)."""
        return self._search

    @property
    def level_toggles(self) -> tuple[LevelToggleWidget, ...]:
        """Level toggles (for tests)."""
        return tuple(self._levels)

    @property
    def paused_caption(self) -> str:
        """Pause counter text (for tests)."""
        return self._paused_caption.text()

    def buttons(self) -> tuple[SnapshotButton, ...]:
        """Follow, Pause, Copy, Clear view and Open log folder (for tests).

        Returns:
            The buttons.
        """
        return (self._follow, self._pause, self._copy, self._clear_view, self._open_log_folder)

    def render_snapshot(self, snapshot: JournalToolbarSnapshot) -> None:
        """Show the toolbar state.

        Args:
            snapshot: Toolbar state.
        """
        while len(self._levels) < len(snapshot.levels):
            toggle = LevelToggleWidget(self)
            toggle.level_toggled.connect(self.level_toggled.emit)
            self._levels_row.insertWidget(len(self._levels), toggle)
            self._levels.append(toggle)
        for toggle, level in zip(self._levels, snapshot.levels, strict=False):
            toggle.apply(level)
        self._search.apply(snapshot.search)
        self._follow.apply(snapshot.follow)
        self._pause.apply(snapshot.pause)
        self._paused_caption.setText(snapshot.paused_caption)
        self._paused_caption.setVisible(bool(snapshot.paused_caption))
        self._copy.apply(snapshot.copy)
        self._clear_view.apply(snapshot.clear_view)
        self._open_log_folder.apply(snapshot.open_log_folder)

    def _button(self, *, checkable: bool = False) -> SnapshotButton:
        """Create a command button forwarding its action.

        Args:
            checkable: Whether it shows an on/off state.

        Returns:
            The button.
        """
        button = SnapshotButton(self)
        button.setCheckable(checkable)
        button.action_requested.connect(self.action_requested.emit)
        return button

    def _build_layout(self) -> None:
        """Two rows: levels and search; Follow, Pause, counter, then Copy, Clear view, Open log folder."""
        self._levels_row.setContentsMargins(0, 0, 0, 0)
        self._levels_row.addStretch(1)
        self._levels_row.addWidget(self._search, 1)
        commands = QHBoxLayout()
        commands.setContentsMargins(0, 0, 0, 0)
        for widget in (self._follow, self._pause, self._paused_caption):
            commands.addWidget(widget)
        commands.addStretch(1)
        for widget in (self._copy, self._clear_view, self._open_log_folder):
            commands.addWidget(widget)
        rows = QVBoxLayout(self)
        rows.setContentsMargins(0, 0, 0, 0)
        rows.addLayout(self._levels_row)
        rows.addLayout(commands)
