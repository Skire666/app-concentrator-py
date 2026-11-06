"""Menu A page. Feature panels replace the placeholders in later phases."""

from typing import Final

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtWidgets import QSplitter, QVBoxLayout, QWidget

from concentrator.presentation.shell.shell_snapshot import ShellSnapshot
from concentrator.ui.widgets.placeholder_widget import PlaceholderWidget

_PERCENT: Final = 100


class FocusPage(QWidget):
    """Menu A: zone 1 (TODO manager) and zone 2 (vertical stack of panels) in a horizontal splitter."""

    def __init__(self, zone1_ratio_percent: int, parent: QWidget | None = None) -> None:
        """Build the page.

        Args:
            zone1_ratio_percent: Initial share of zone 1 (``ui.zone1_ratio_percent``).
            parent: Parent widget.
        """
        super().__init__(parent)
        self._ratio = zone1_ratio_percent
        self._splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self._splitter.setChildrenCollapsible(False)
        self._zone1 = PlaceholderWidget(self._splitter)
        zone2 = QWidget(self._splitter)
        self._zone2 = PlaceholderWidget(zone2)
        QVBoxLayout(zone2).addWidget(self._zone2)
        self._splitter.addWidget(self._zone1)
        self._splitter.addWidget(zone2)
        self._splitter.setStretchFactor(0, zone1_ratio_percent)
        self._splitter.setStretchFactor(1, _PERCENT - zone1_ratio_percent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._splitter)
        self.reset_splitter()

    @property
    def zone_texts(self) -> tuple[str, str]:
        """Texts of the two zones (for tests)."""
        return self._zone1.text, self._zone2.text

    def render_snapshot(self, snapshot: ShellSnapshot) -> None:
        """Show the zone placeholders.

        Args:
            snapshot: Shell state.
        """
        self._zone1.set_text(snapshot.focus_zone1_placeholder)
        self._zone2.set_text(snapshot.focus_zone2_placeholder)

    def splitter_state(self) -> QByteArray:
        """Return the splitter blob to persist."""
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
        """Apply the ini ratio (sizes are distributed proportionally to the available width)."""
        self._splitter.setSizes([self._ratio, _PERCENT - self._ratio])

    def splitter_sizes(self) -> list[int]:
        """Return the current zone widths (for tests).

        Returns:
            Width of zone 1 and zone 2 in pixels.
        """
        return self._splitter.sizes()
