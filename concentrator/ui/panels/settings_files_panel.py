"""Data file, Interface and About sections of the settings page (commands that act at once)."""

from typing import Final

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFormLayout, QGroupBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from concentrator.presentation.settings.settings_snapshot import (
    AboutSectionSnapshot,
    DataFileSectionSnapshot,
    InterfaceSectionSnapshot,
    SettingsFilesSnapshot,
)
from concentrator.ui.widgets.path_row_widget import PathRowWidget
from concentrator.ui.widgets.snapshot_button import SnapshotButton

ABOUT_PATH_ROWS: Final = 4


def _hint(parent: QWidget) -> QLabel:
    """Create a wrapped plain text label.

    Args:
        parent: Parent widget.

    Returns:
        The label.
    """
    label = QLabel(parent)
    label.setWordWrap(True)
    label.setTextFormat(Qt.TextFormat.PlainText)
    return label


class SettingsFilesPanel(QWidget):
    """Emits ``action_requested(int)`` for the commands and ``open_requested(int)`` for "Open folder"."""

    action_requested = Signal(int)
    open_requested = Signal(int)

    def __init__(self, spacing_px: int, parent: QWidget | None = None) -> None:
        """Build the three sections.

        Args:
            spacing_px: ``ui.dialog_spacing_px``.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._data_box = QGroupBox(self)
        self._data_label = QLabel(self._data_box)
        self._data_path = PathRowWidget(self._data_box)
        self._data_hint = _hint(self._data_box)
        self._switch = SnapshotButton(self._data_box)
        self._move = SnapshotButton(self._data_box)
        self._interface_box = QGroupBox(self)
        self._interface_hint = _hint(self._interface_box)
        self._reset_layout = SnapshotButton(self._interface_box)
        self._about_box = QGroupBox(self)
        self._version_label = QLabel(self._about_box)
        self._version = QLabel(self._about_box)
        self._version.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._path_labels = tuple(QLabel(self._about_box) for _row in range(ABOUT_PATH_ROWS))
        self._paths = tuple(PathRowWidget(self._about_box) for _row in range(ABOUT_PATH_ROWS))
        self._connect()
        self._build_layout(spacing_px)

    @property
    def data_path(self) -> PathRowWidget:
        """Path of the open data file (for tests)."""
        return self._data_path

    @property
    def about_paths(self) -> tuple[PathRowWidget, ...]:
        """Paths of the About section (for tests)."""
        return self._paths

    def buttons(self) -> tuple[SnapshotButton, ...]:
        """The "Use another file...", "Move file..." and "Reset layout" buttons (for tests).

        Returns:
            The buttons.
        """
        return (self._switch, self._move, self._reset_layout)

    def render_snapshot(self, snapshot: SettingsFilesSnapshot) -> None:
        """Show the three sections.

        Args:
            snapshot: Sections state.
        """
        self._render_data_file(snapshot.data_file)
        self._render_interface(snapshot.interface)
        self._render_about(snapshot.about)

    def _render_data_file(self, data_file: DataFileSectionSnapshot) -> None:
        """Show the Data file section.

        Args:
            data_file: Section state.
        """
        self._data_box.setTitle(data_file.title)
        self._data_label.setText(data_file.current.label)
        self._data_path.apply(data_file.current)
        self._data_hint.setText(data_file.hint)
        self._switch.apply(data_file.switch)
        self._move.apply(data_file.move)

    def _render_interface(self, interface: InterfaceSectionSnapshot) -> None:
        """Show the Interface section.

        Args:
            interface: Section state.
        """
        self._interface_box.setTitle(interface.title)
        self._interface_hint.setText(interface.hint)
        self._reset_layout.apply(interface.reset_layout)

    def _render_about(self, about: AboutSectionSnapshot) -> None:
        """Show the About section.

        Args:
            about: Section state.
        """
        self._about_box.setTitle(about.title)
        self._version_label.setText(about.version_label)
        self._version.setText(about.version)
        for label, row, path in zip(self._path_labels, self._paths, about.paths, strict=False):
            label.setText(path.label)
            row.apply(path)

    def _connect(self) -> None:
        """Forward the button signals."""
        for button in (self._switch, self._move, self._reset_layout):
            button.action_requested.connect(self.action_requested)
        for row in (self._data_path, *self._paths):
            row.open_requested.connect(self.open_requested)

    def _build_layout(self, spacing_px: int) -> None:
        """Data file, Interface and About group boxes, one under the other.

        Args:
            spacing_px: ``ui.dialog_spacing_px``.
        """
        data = QFormLayout(self._data_box)
        data.setSpacing(spacing_px)
        data.addRow(self._data_label, self._data_path)
        data.addRow(self._data_hint)
        commands = QHBoxLayout()
        commands.addWidget(self._switch)
        commands.addWidget(self._move)
        commands.addStretch(1)
        data.addRow(commands)
        interface = QHBoxLayout(self._interface_box)
        interface.addWidget(self._interface_hint, 1)
        interface.addWidget(self._reset_layout)
        about = QFormLayout(self._about_box)
        about.setSpacing(spacing_px)
        about.addRow(self._version_label, self._version)
        for label, row in zip(self._path_labels, self._paths, strict=True):
            about.addRow(label, row)
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(spacing_px)
        for box in (self._data_box, self._interface_box, self._about_box):
            column.addWidget(box)
