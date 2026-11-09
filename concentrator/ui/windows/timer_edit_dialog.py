"""Timer edit dialog, run over the main window by ``ModalHost`` (ADR-036)."""

from typing import override

from PySide6.QtWidgets import QDialog, QVBoxLayout, QWidget

from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.ports.timer_edit_dialog_port import TimerEditDialogPort
from concentrator.presentation.timer.timer_edit_presenter import TimerEditPresenter
from concentrator.presentation.timer.timer_edit_snapshot import TimerEditSnapshot
from concentrator.presentation.timer.timer_layout import TimerLayout
from concentrator.ui.panels.timer_edit_form_panel import TimerEditFormPanel
from concentrator.ui.support.modal_host import DialogRunner


class TimerEditDialog(QDialog):
    """Hosts the form panel; Cancel, Escape and the title bar button close it without asking (ADR-038)."""

    def __init__(self, layout: TimerLayout, parent: QWidget | None) -> None:
        """Build the dialog (not shown).

        Args:
            layout: Spacing of the dialog.
            parent: Main window (Qt centers the dialog on it).
        """
        super().__init__(parent)
        self._panel = TimerEditFormPanel(layout, self)
        QVBoxLayout(self).addWidget(self._panel)

    @property
    def panel(self) -> TimerEditFormPanel:
        """The form panel."""
        return self._panel

    def render_snapshot(self, snapshot: TimerEditSnapshot) -> None:
        """Show the title and the fields.

        Args:
            snapshot: Dialog state.
        """
        self.setWindowTitle(snapshot.title)
        self._panel.render_snapshot(snapshot)


class TimerEditWindow(TimerEditDialogPort):
    """``TimerEditDialogPort`` on one ``TimerEditDialog``, wired to its presenter."""

    def __init__(
        self, presenter: TimerEditPresenter, renderer: RenderCoordinator, runner: DialogRunner, layout: TimerLayout
    ) -> None:
        """Build the dialog, connect its panel and register ``TIMER_EDIT``.

        Args:
            presenter: Edit presenter.
            renderer: Render coordinator.
            runner: The main window's modal host.
            layout: Spacing of the dialog.
        """
        self._renderer = renderer
        self._runner = runner
        self._dialog = TimerEditDialog(layout, runner.parent)
        panel = self._dialog.panel
        panel.duration_changed.connect(presenter.on_duration_changed)
        panel.sound_selected.connect(presenter.on_sound_selected)
        panel.volume_changed.connect(presenter.on_volume_changed)
        panel.loop_count_changed.connect(presenter.on_loop_count_changed)
        panel.loop_forever_changed.connect(presenter.on_loop_forever_changed)
        panel.auto_stop_changed.connect(presenter.on_auto_stop_changed)
        panel.auto_restart_changed.connect(presenter.on_auto_restart_changed)
        panel.action_requested.connect(presenter.on_action_requested)
        renderer.register(RenderSectionEnum.TIMER_EDIT, presenter.build_snapshot, self._dialog.render_snapshot)

    @property
    def dialog(self) -> TimerEditDialog:
        """The dialog (for tests)."""
        return self._dialog

    @override
    def show_editor(self) -> None:
        self._renderer.request(RenderSectionEnum.TIMER_EDIT)
        self._renderer.flush()
        self._runner.run(self._dialog)

    @override
    def close_editor(self) -> None:
        self._dialog.done(QDialog.DialogCode.Accepted)
