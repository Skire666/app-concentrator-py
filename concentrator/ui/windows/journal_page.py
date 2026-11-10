"""Menu B page: the application log, with its toolbar above a table and a detail pane."""

from typing import Final

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtWidgets import QSplitter, QVBoxLayout, QWidget

from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.journal.journal_layout import JournalLayout
from concentrator.presentation.journal.journal_presenter import JournalPresenter
from concentrator.presentation.journal.journal_snapshot import JournalSnapshot
from concentrator.ui.panels.journal_detail_panel import JournalDetailPanel
from concentrator.ui.panels.journal_table_panel import JournalTablePanel
from concentrator.ui.panels.journal_toolbar_panel import JournalToolbarPanel

_PERCENT: Final = 100


class JournalPage(QWidget):
    """Toolbar, then the table above the detail pane in a vertical splitter."""

    def __init__(self, layout: JournalLayout, parent: QWidget | None = None) -> None:
        """Build the page.

        Args:
            layout: Default splitter ratio and column widths.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._ratio = layout.table_ratio_percent
        self._toolbar = JournalToolbarPanel(self)
        self._splitter = QSplitter(Qt.Orientation.Vertical, self)
        self._splitter.setChildrenCollapsible(False)
        self._table = JournalTablePanel(layout.column_widths_px, self._splitter)
        self._detail = JournalDetailPanel(self._splitter)
        self._splitter.addWidget(self._table)
        self._splitter.addWidget(self._detail)
        self._splitter.setStretchFactor(0, self._ratio)
        self._splitter.setStretchFactor(1, _PERCENT - self._ratio)
        page = QVBoxLayout(self)
        page.addWidget(self._toolbar)
        page.addWidget(self._splitter, 1)
        self.reset_splitter()
        self._table.reset_columns()

    @property
    def toolbar(self) -> JournalToolbarPanel:
        """Toolbar (for tests)."""
        return self._toolbar

    @property
    def table(self) -> JournalTablePanel:
        """Entry table (for tests)."""
        return self._table

    @property
    def detail(self) -> JournalDetailPanel:
        """Detail pane (for tests)."""
        return self._detail

    def connect_presenter(self, presenter: JournalPresenter, renderer: RenderCoordinator) -> None:
        """Wire the panels to the presenter and register the ``JOURNAL`` section.

        Args:
            presenter: Journal presenter.
            renderer: Render coordinator.
        """
        self._toolbar.action_requested.connect(presenter.on_action_requested)
        self._toolbar.level_toggled.connect(presenter.on_level_toggled)
        self._toolbar.search_changed.connect(presenter.on_search_changed)
        self._table.action_requested.connect(presenter.on_action_requested)
        self._table.selection_changed.connect(presenter.on_selection_changed)
        renderer.register(RenderSectionEnum.JOURNAL, presenter.build_snapshot, self.render_snapshot)

    def render_snapshot(self, snapshot: JournalSnapshot) -> None:
        """Show the page state.

        Args:
            snapshot: Journal state.
        """
        self.setUpdatesEnabled(False)
        self._toolbar.render_snapshot(snapshot.toolbar)
        self._table.render_snapshot(snapshot.table)
        self._detail.render_snapshot(snapshot.detail)
        self.setUpdatesEnabled(True)

    def splitter_state(self) -> QByteArray:
        """Return the splitter blob to persist.

        Returns:
            The blob.
        """
        return self._splitter.saveState()

    def restore_splitter_state(self, state: QByteArray) -> bool:
        """Restore a persisted splitter blob.

        Args:
            state: Blob from ``splitter_state``.

        Returns:
            Whether Qt accepted it.
        """
        return self._splitter.restoreState(state)

    def reset_splitter(self) -> None:
        """Apply the ini ratio between the table and the detail pane."""
        self._splitter.setSizes([self._ratio, _PERCENT - self._ratio])

    def header_state(self) -> QByteArray:
        """Return the column widths blob to persist.

        Returns:
            The blob.
        """
        return self._table.header_state()

    def restore_header_state(self, state: QByteArray) -> bool:
        """Restore a persisted column widths blob.

        Args:
            state: Blob from ``header_state``.

        Returns:
            Whether Qt accepted it.
        """
        return self._table.restore_header_state(state)

    def reset_columns(self) -> None:
        """Apply the default column widths of the ini."""
        self._table.reset_columns()
