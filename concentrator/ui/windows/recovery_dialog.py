"""Modal recovery dialog shown before the main window."""

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog, QVBoxLayout, QWidget

from concentrator.presentation.storage.startup_dialog_layout import StartupDialogLayout
from concentrator.presentation.storage.startup_snapshots import RecoverySnapshot
from concentrator.ui.panels.recovery_panel import RecoveryPanel
from concentrator.ui.support.styles import WARNING_TEXT_STYLE


class RecoveryDialog(QDialog):
    """Hosts the ``RecoveryPanel``; closing it without an action quits (decided by the presenter)."""

    def __init__(self, icon: QIcon, layout: StartupDialogLayout, parent: QWidget | None = None) -> None:
        """Build the dialog (not shown).

        Args:
            icon: Window icon.
            layout: Sizes from ``concentrator.ini``.
            parent: Parent widget, ``None`` before the main window exists.
        """
        super().__init__(parent)
        self.setWindowIcon(icon)
        self.setModal(True)
        self.setMinimumWidth(layout.min_width_px)
        self.setStyleSheet(WARNING_TEXT_STYLE)
        self._panel = RecoveryPanel(layout.spacing_px, self)
        QVBoxLayout(self).addWidget(self._panel)

    @property
    def panel(self) -> RecoveryPanel:
        """Content panel."""
        return self._panel

    def render_snapshot(self, snapshot: RecoverySnapshot | None) -> None:
        """Show a snapshot (``None`` when the startup no longer needs this dialog).

        Args:
            snapshot: Dialog state.
        """
        if snapshot is None:
            return
        self.setWindowTitle(snapshot.title)
        self._panel.render_snapshot(snapshot)
