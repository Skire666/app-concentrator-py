"""Hourly chime dialog, run over the main window by ``ModalHost`` (ADR-036)."""

from typing import override

from PySide6.QtWidgets import QDialog, QVBoxLayout, QWidget

from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.ports.editor_dialog_port import EditorDialogPort
from concentrator.presentation.timer.chime_settings_presenter import ChimeSettingsPresenter
from concentrator.presentation.timer.chime_settings_snapshot import ChimeSettingsSnapshot
from concentrator.presentation.timer.timer_layout import TimerLayout
from concentrator.ui.panels.chime_settings_form_panel import ChimeSettingsFormPanel
from concentrator.ui.support.modal_host import DialogRunner


class ChimeSettingsDialog(QDialog):
    """Hosts the form panel; Cancel, Escape and the title bar button close it without asking (ADR-038)."""

    def __init__(self, layout: TimerLayout, parent: QWidget | None) -> None:
        """Build the dialog (not shown).

        Args:
            layout: Spacing of the dialog.
            parent: Main window (Qt centers the dialog on it).
        """
        super().__init__(parent)
        self._panel = ChimeSettingsFormPanel(layout, self)
        QVBoxLayout(self).addWidget(self._panel)

    @property
    def panel(self) -> ChimeSettingsFormPanel:
        """The form panel."""
        return self._panel

    def render_snapshot(self, snapshot: ChimeSettingsSnapshot) -> None:
        """Show the title and the fields.

        Args:
            snapshot: Dialog state.
        """
        self.setWindowTitle(snapshot.title)
        self._panel.render_snapshot(snapshot)


class ChimeSettingsWindow(EditorDialogPort):
    """``EditorDialogPort`` on one ``ChimeSettingsDialog``, wired to its presenter."""

    def __init__(
        self, presenter: ChimeSettingsPresenter, renderer: RenderCoordinator, runner: DialogRunner, layout: TimerLayout
    ) -> None:
        """Build the dialog, connect its panel and register ``CHIME_EDIT``.

        Args:
            presenter: Chime dialog presenter.
            renderer: Render coordinator.
            runner: The main window's modal host.
            layout: Spacing of the dialog.
        """
        self._renderer = renderer
        self._runner = runner
        self._dialog = ChimeSettingsDialog(layout, runner.parent)
        panel = self._dialog.panel
        panel.sound_selected.connect(presenter.on_sound_selected)
        panel.volume_changed.connect(presenter.on_volume_changed)
        panel.start_hour_changed.connect(presenter.on_start_hour_changed)
        panel.end_hour_changed.connect(presenter.on_end_hour_changed)
        panel.action_requested.connect(presenter.on_action_requested)
        renderer.register(RenderSectionEnum.CHIME_EDIT, presenter.build_snapshot, self._dialog.render_snapshot)

    @property
    def dialog(self) -> ChimeSettingsDialog:
        """The dialog (for tests)."""
        return self._dialog

    @override
    def show_editor(self) -> None:
        self._renderer.request(RenderSectionEnum.CHIME_EDIT)
        self._renderer.flush()
        self._runner.run(self._dialog)

    @override
    def close_editor(self) -> None:
        self._dialog.done(QDialog.DialogCode.Accepted)
