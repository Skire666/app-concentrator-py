"""First-run dialog: where to put the data file (also shown when the remembered file is missing)."""

from typing import Final

from concentrator.application.storage.startup_plan import StartupPlan
from concentrator.application.storage.startup_reason_enum import StartupReasonEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.storage.startup_choice import StartupChoice
from concentrator.presentation.storage.startup_snapshots import FirstRunSnapshot
from concentrator.presentation.storage.startup_support import BusyCheck, StartupSupport

FIRST_RUN_ACTIONS: Final = (
    ActionIdEnum.STARTUP_USE_DEFAULT_FILE,
    ActionIdEnum.STARTUP_CREATE_DEFAULT_FILE,
    ActionIdEnum.STARTUP_CREATE_FILE_ELSEWHERE,
    ActionIdEnum.STARTUP_OPEN_EXISTING_FILE,
    ActionIdEnum.STARTUP_RETRY,
    ActionIdEnum.STARTUP_QUIT,
)


class FirstRunPresenter:
    """Builds the ``FIRST_RUN`` snapshot and performs its actions."""

    def __init__(self, support: StartupSupport) -> None:
        """Create the presenter.

        Args:
            support: Commands, pickers and failure messages.
        """
        self._support = support

    def build_snapshot(self, plan: StartupPlan, busy: BusyCheck) -> FirstRunSnapshot:
        """Describe the dialog for a ``NEEDS_LOCATION`` plan.

        Args:
            plan: Current situation.
            busy: Tells whether an action is running.

        Returns:
            The snapshot.
        """
        tr = self._support.translator.tr
        missing = plan.path if plan.reason is StartupReasonEnum.FILE_NOT_FOUND else None
        visible = {
            ActionIdEnum.STARTUP_USE_DEFAULT_FILE: plan.default_exists,
            ActionIdEnum.STARTUP_CREATE_DEFAULT_FILE: not plan.default_exists,
            ActionIdEnum.STARTUP_RETRY: plan.can_retry,
        }
        return FirstRunSnapshot(
            title=tr("startup.first_run.title"),
            intro=tr("startup.first_run.intro"),
            notice=tr("startup.first_run.not_found", path=missing.as_posix()) if missing is not None else "",
            default_location=tr("startup.first_run.default_location", path=plan.default_path.as_posix()),
            buttons=tuple(
                self._support.button(action, busy, visible=visible.get(action, True)) for action in FIRST_RUN_ACTIONS
            ),
        )

    def handle(self, action: ActionIdEnum, plan: StartupPlan) -> StartupChoice:
        """Perform one action.

        Args:
            action: Clicked action.
            plan: Current situation.

        Returns:
            What the flow does next.
        """
        commands = self._support.commands
        language = self._support.translator.language
        match action:
            case ActionIdEnum.STARTUP_USE_DEFAULT_FILE:
                return StartupChoice(plan=commands.inspect(plan.default_path))
            case ActionIdEnum.STARTUP_CREATE_DEFAULT_FILE:
                return self._support.choice(commands.create_at(plan.default_path, language))
            case ActionIdEnum.STARTUP_CREATE_FILE_ELSEWHERE:
                return self._support.create_chosen(plan.default_path)
            case ActionIdEnum.STARTUP_OPEN_EXISTING_FILE:
                return self._support.open_chosen(plan.path or plan.default_path)
            case ActionIdEnum.STARTUP_RETRY:
                return StartupChoice(plan=commands.inspect(plan.path) if plan.path else commands.resolve_startup())
            case ActionIdEnum.STARTUP_QUIT:
                return StartupChoice(quit=True)
            case _:
                return StartupChoice(validation=ValidationResult.skipped())
