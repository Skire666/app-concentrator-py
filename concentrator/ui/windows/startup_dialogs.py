"""``StartupDialogsPort`` on the first-run and recovery dialogs."""

from typing import override

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog

from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.ports.startup_dialogs_port import StartupDialogsPort
from concentrator.presentation.storage.startup_dialog_layout import StartupDialogLayout
from concentrator.presentation.storage.startup_flow_presenter import StartupFlowPresenter
from concentrator.ui.support.modal_host import DialogRunner
from concentrator.ui.windows.first_run_dialog import FirstRunDialog
from concentrator.ui.windows.recovery_dialog import RecoveryDialog


class StartupDialogs(StartupDialogsPort):
    """Builds both dialogs once, wires them to the flow presenter and registers their sections."""

    def __init__(
        self, presenter: StartupFlowPresenter, renderer: RenderCoordinator, icon: QIcon, layout: StartupDialogLayout
    ) -> None:
        """Create the dialogs (not shown).

        Args:
            presenter: Startup flow.
            renderer: Render coordinator the dialogs are registered with.
            icon: Window icon.
            layout: Sizes from ``concentrator.ini``.
        """
        self._renderer = renderer
        self._first_run = FirstRunDialog(icon, layout)
        self._recovery = RecoveryDialog(icon, layout)
        self._current: QDialog | None = None
        self._runner: DialogRunner | None = None
        self._first_run.panel.action_requested.connect(presenter.on_action_requested)
        self._recovery.panel.action_requested.connect(presenter.on_action_requested)
        self._recovery.panel.candidate_selected.connect(presenter.on_candidate_selected)
        renderer.register(
            RenderSectionEnum.FIRST_RUN, presenter.build_first_run_snapshot, self._first_run.render_snapshot
        )
        renderer.register(RenderSectionEnum.RECOVERY, presenter.build_recovery_snapshot, self._recovery.render_snapshot)

    @property
    def first_run(self) -> FirstRunDialog:
        """First-run dialog (for tests)."""
        return self._first_run

    @property
    def recovery(self) -> RecoveryDialog:
        """Recovery dialog (for tests)."""
        return self._recovery

    def move_to_window(self, runner: DialogRunner) -> None:
        """Run the dialogs over the main window from now on (settings page, ADR-036).

        Args:
            runner: The main window's modal host; its window becomes the parent of the dialogs.
        """
        self._runner = runner
        for dialog in (self._first_run, self._recovery):
            dialog.setParent(runner.parent, dialog.windowFlags())

    @override
    def show_first_run(self) -> None:
        self._exec(self._first_run, RenderSectionEnum.FIRST_RUN)

    @override
    def show_recovery(self) -> None:
        self._exec(self._recovery, RenderSectionEnum.RECOVERY)

    @override
    def close_current(self) -> None:
        if self._current is not None:
            self._current.accept()

    def _exec(self, dialog: QDialog, section: RenderSectionEnum) -> None:
        """Render a dialog, then run it modally.

        Args:
            dialog: Dialog to show.
            section: Its render section.
        """
        self._renderer.request(section)
        self._renderer.flush()
        self._current = dialog
        if self._runner is None:
            dialog.exec()
        else:
            self._runner.run(dialog)
        self._current = None
