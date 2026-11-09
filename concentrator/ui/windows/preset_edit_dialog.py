"""Favorite dialog, run over the main window by ``ModalHost`` (ADR-036)."""

from typing import override

from PySide6.QtWidgets import QDialog, QVBoxLayout, QWidget

from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.ports.editor_dialog_port import EditorDialogPort
from concentrator.presentation.timer.preset_edit_presenter import PresetEditPresenter
from concentrator.presentation.timer.preset_edit_snapshot import PresetEditSnapshot
from concentrator.presentation.timer.timer_layout import TimerLayout
from concentrator.ui.panels.preset_edit_form_panel import PresetEditFormPanel
from concentrator.ui.support.modal_host import DialogRunner


class PresetEditDialog(QDialog):
    """Hosts the form panel; Cancel, Escape and the title bar button close it without asking (ADR-038)."""

    def __init__(self, layout: TimerLayout, parent: QWidget | None) -> None:
        """Build the dialog (not shown).

        Args:
            layout: Spacing of the dialog.
            parent: Main window (Qt centers the dialog on it).
        """
        super().__init__(parent)
        self._panel = PresetEditFormPanel(layout, self)
        QVBoxLayout(self).addWidget(self._panel)

    @property
    def panel(self) -> PresetEditFormPanel:
        """The form panel."""
        return self._panel

    def render_snapshot(self, snapshot: PresetEditSnapshot) -> None:
        """Show the title and the fields.

        Args:
            snapshot: Dialog state.
        """
        self.setWindowTitle(snapshot.title)
        self._panel.render_snapshot(snapshot)


class PresetEditWindow(EditorDialogPort):
    """``EditorDialogPort`` on one ``PresetEditDialog``, wired to its presenter."""

    def __init__(
        self, presenter: PresetEditPresenter, renderer: RenderCoordinator, runner: DialogRunner, layout: TimerLayout
    ) -> None:
        """Build the dialog, connect its panel and register ``PRESET_EDIT``.

        Args:
            presenter: Favorite dialog presenter.
            renderer: Render coordinator.
            runner: The main window's modal host.
            layout: Spacing of the dialog.
        """
        self._renderer = renderer
        self._runner = runner
        self._dialog = PresetEditDialog(layout, runner.parent)
        panel = self._dialog.panel
        panel.label_changed.connect(presenter.on_label_changed)
        panel.duration_changed.connect(presenter.on_duration_changed)
        panel.action_requested.connect(presenter.on_action_requested)
        renderer.register(RenderSectionEnum.PRESET_EDIT, presenter.build_snapshot, self._dialog.render_snapshot)

    @property
    def dialog(self) -> PresetEditDialog:
        """The dialog (for tests)."""
        return self._dialog

    @override
    def show_editor(self) -> None:
        self._renderer.request(RenderSectionEnum.PRESET_EDIT)
        self._renderer.flush()
        self._dialog.panel.label_input.setFocus()
        self._runner.run(self._dialog)

    @override
    def close_editor(self) -> None:
        self._dialog.done(QDialog.DialogCode.Accepted)
