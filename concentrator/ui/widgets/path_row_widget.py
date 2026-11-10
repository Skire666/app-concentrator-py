"""A read-only path with an "Open folder" button, driven by a ``PathRowSnapshot``."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QWidget

from concentrator.presentation.settings.settings_snapshot import PathRowSnapshot
from concentrator.ui.widgets.snapshot_button import SnapshotButton


class PathRowWidget(QWidget):
    """Emits ``open_requested(int)`` with the ``SettingsFolderEnum`` value of the row."""

    open_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create the row.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._folder = 0
        self._path = QLineEdit(self)
        self._path.setReadOnly(True)
        self._open = SnapshotButton(self)
        self._open.action_requested.connect(self._emit_open)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self._path, 1)
        row.addWidget(self._open)

    @property
    def path(self) -> str:
        """Path shown (for tests)."""
        return self._path.text()

    @property
    def open_button(self) -> SnapshotButton:
        """The "Open folder" button (for tests)."""
        return self._open

    def apply(self, snapshot: PathRowSnapshot) -> None:
        """Show a snapshot (idempotent).

        Args:
            snapshot: Row state.
        """
        self._folder = snapshot.folder
        if self._path.text() != snapshot.path:
            self._path.setText(snapshot.path)
            self._path.setCursorPosition(0)
        self._path.setToolTip(snapshot.path)
        self._open.apply(snapshot.open_folder)

    def _emit_open(self, _action: int) -> None:
        """Forward the button click as the folder of the row.

        Args:
            _action: Action of the button (always ``SETTINGS_OPEN_FOLDER``).
        """
        self.open_requested.emit(self._folder)
