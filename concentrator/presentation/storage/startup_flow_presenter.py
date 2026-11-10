"""Startup dialogs loop: first run and recovery until a data file is open or the user quits (ADR-027)."""

import logging

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.application.storage.startup_commands import StartupCommands
from concentrator.application.storage.startup_plan import StartupPlan
from concentrator.application.storage.startup_step_enum import StartupStepEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.date_time_formatter import DateTimeFormatter
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.ports.dialog_port import DialogPort
from concentrator.presentation.ports.startup_dialogs_port import StartupDialogsPort
from concentrator.presentation.storage.first_run_presenter import FIRST_RUN_ACTIONS, FirstRunPresenter
from concentrator.presentation.storage.recovery_presenter import RecoveryPresenter
from concentrator.presentation.storage.startup_choice import StartupChoice
from concentrator.presentation.storage.startup_snapshots import FirstRunSnapshot, RecoverySnapshot
from concentrator.presentation.storage.startup_support import StartupSupport

_logger = logging.getLogger(__name__)


def _section_for(plan: StartupPlan) -> RenderSectionEnum:
    """Dialog showing a plan.

    Args:
        plan: Situation that is not ``READY``.

    Returns:
        ``FIRST_RUN`` for ``NEEDS_LOCATION``, ``RECOVERY`` otherwise.
    """
    return RenderSectionEnum.FIRST_RUN if plan.step is StartupStepEnum.NEEDS_LOCATION else RenderSectionEnum.RECOVERY


class StartupFlowPresenter:
    """Owns the current plan; the dialogs render it and send their actions here.

    An action that changes which dialog is needed closes the current one, and the loop opens the next.
    Closing a dialog any other way (window button, Escape) quits. Once the main window exists, the same
    flow runs the recovery dialog for a file chosen on the settings page (``resume``): Quit becomes
    Cancel, which keeps the current file.
    """

    def __init__(
        self,
        *,
        commands: StartupCommands,
        dialogs: DialogPort,
        gate: ActionGate,
        renderer: RenderCoordinator,
        translator: TranslatorPort,
        formatter: DateTimeFormatter,
    ) -> None:
        """Create the flow.

        Args:
            commands: Startup use cases.
            dialogs: File pickers and error messages (parented to no window yet).
            gate: Runs every dialog action.
            renderer: Renders the dialogs.
            translator: Current-language translator (the startup hint language).
            formatter: Dates of the recovery candidates.
        """
        support = StartupSupport(commands, dialogs, translator)
        self._support = support
        self._commands = commands
        self._gate = gate
        self._renderer = renderer
        self._first_run = FirstRunPresenter(support)
        self._recovery = RecoveryPresenter(support, formatter)
        self._ui: StartupDialogsPort | None = None
        self._plan: StartupPlan | None = None
        self._selected = 0
        self._quit = False
        self._closed_by_action = False
        self._in_session = False

    @property
    def plan(self) -> StartupPlan | None:
        """Current situation, ``None`` before ``run``."""
        return self._plan

    def attach(self, ui: StartupDialogsPort) -> None:
        """Connect the dialogs (they need this presenter's builders, so they are created after it).

        Args:
            ui: Startup dialogs.
        """
        self._ui = ui

    def attach_session(self, ui: StartupDialogsPort, dialogs: DialogPort) -> None:
        """Run the next flows over the main window (``resume``).

        Args:
            ui: Startup dialogs, now run by the main window's modal host.
            dialogs: Pickers and messages over the main window.
        """
        self._ui = ui
        self._support.use_dialogs(dialogs)
        self._in_session = True

    def resume(self, plan: StartupPlan) -> bool:
        """Show the recovery dialog of a data file that is not ready, until it opens or the user cancels.

        Args:
            plan: ``NEEDS_RECOVERY`` or ``FATAL`` plan of the chosen file.

        Returns:
            Whether a data file was opened.
        """
        self._plan = plan
        self._selected = 0
        self._quit = False
        while self._plan.step in {StartupStepEnum.NEEDS_RECOVERY, StartupStepEnum.FATAL} and not self._quit:
            self._show(self._plan)
        opened = self._plan.step is StartupStepEnum.READY and not self._quit
        _logger.info("Recovery of another data file: %s", "opened" if opened else "cancelled")
        return opened

    def run(self) -> bool:
        """Resolve the data file and show the dialogs until it is open.

        Returns:
            Whether a data file is open (``False``: the user quit).
        """
        self._plan = self._commands.resolve_startup()
        while self._plan.step is not StartupStepEnum.READY and not self._quit:
            self._show(self._plan)
        if self._quit:
            _logger.info("Startup cancelled by the user")
            return False
        return True

    def build_first_run_snapshot(self) -> FirstRunSnapshot | None:
        """Snapshot of the first-run dialog.

        Returns:
            The snapshot, ``None`` when no plan needs it.
        """
        if self._plan is None or _section_for(self._plan) is not RenderSectionEnum.FIRST_RUN:
            return None
        return self._first_run.build_snapshot(self._plan, self._gate.is_busy)

    def build_recovery_snapshot(self) -> RecoverySnapshot | None:
        """Snapshot of the recovery dialog.

        Returns:
            The snapshot, ``None`` when no plan needs it.
        """
        if self._plan is None or self._plan.step not in {StartupStepEnum.NEEDS_RECOVERY, StartupStepEnum.FATAL}:
            return None
        return self._recovery.build_snapshot(
            self._plan, self._selected, self._gate.is_busy, in_session=self._in_session
        )

    def on_action_requested(self, action_value: int) -> None:
        """Handle a button of either dialog.

        Args:
            action_value: ``ActionIdEnum`` value emitted by the panel.
        """
        action = ActionIdEnum.parse(action_value)
        result = self._gate.run(action, lambda: self._perform(action), interactive=True)
        if result.is_failure:
            _logger.warning("Startup action %s failed: %s", action.name, [code.name for code in result.error_codes])

    def on_candidate_selected(self, index: int) -> None:
        """Select the version "Restore" applies to.

        Args:
            index: Position in the candidate list.
        """
        if index != self._selected:
            self._selected = index
            self._renderer.request(RenderSectionEnum.RECOVERY)

    def _show(self, plan: StartupPlan) -> None:
        """Show the dialog of a plan and wait until it closes.

        Args:
            plan: Situation to show.
        """
        if self._ui is None:
            _logger.error("Startup dialogs are not attached; quitting")
            self._quit = True
            return
        self._closed_by_action = False
        if _section_for(plan) is RenderSectionEnum.FIRST_RUN:
            self._ui.show_first_run()
        else:
            self._ui.show_recovery()
        if not self._closed_by_action:
            self._quit = True

    def _perform(self, action: ActionIdEnum) -> ValidationResult:
        """Run an action on the current plan and move the flow on.

        Args:
            action: Clicked action.

        Returns:
            The action result.
        """
        plan = self._plan
        if plan is None:
            return ValidationResult.skipped()
        on_first_run = _section_for(plan) is RenderSectionEnum.FIRST_RUN
        if on_first_run and action in FIRST_RUN_ACTIONS:
            choice = self._first_run.handle(action, plan)
        else:
            choice = self._recovery.handle(action, plan, self._selected)
        self._apply(choice, plan)
        return choice.validation

    def _apply(self, choice: StartupChoice, previous: StartupPlan) -> None:
        """Update the plan; close the dialog when another one (or none) is needed.

        Args:
            choice: Outcome of the action.
            previous: Plan the dialog showed.
        """
        if choice.quit:
            self._quit = True
            self._close()
            return
        if choice.plan is None:
            return
        self._plan = choice.plan
        self._selected = 0
        same_dialog = choice.plan.step is not StartupStepEnum.READY and _section_for(choice.plan) is _section_for(
            previous
        )
        if same_dialog:
            self._renderer.request(_section_for(choice.plan))
        else:
            self._close()

    def _close(self) -> None:
        """Close the current dialog on behalf of an action."""
        self._closed_by_action = True
        if self._ui is not None:
            self._ui.close_current()
