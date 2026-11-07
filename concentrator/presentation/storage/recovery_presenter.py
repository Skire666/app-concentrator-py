"""Recovery dialog: what is wrong with the data file, which versions can be restored (ADR-027)."""

from types import MappingProxyType
from typing import Final

from concentrator.application.storage.recovery_source_enum import RecoverySourceEnum
from concentrator.application.storage.startup_plan import RecoveryCandidate, StartupPlan
from concentrator.application.storage.startup_reason_enum import StartupReasonEnum
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.date_time_formatter import DateTimeFormatter
from concentrator.presentation.storage.startup_choice import StartupChoice
from concentrator.presentation.storage.startup_snapshots import CandidateSnapshot, RecoverySnapshot
from concentrator.presentation.storage.startup_support import BusyCheck, StartupSupport

RECOVERY_ACTIONS: Final = (
    ActionIdEnum.STARTUP_RESTORE,
    ActionIdEnum.STARTUP_KEEP_CURRENT_FILE,
    ActionIdEnum.STARTUP_CHOOSE_ANOTHER_FILE,
    ActionIdEnum.STARTUP_START_EMPTY,
    ActionIdEnum.STARTUP_RETRY,
    ActionIdEnum.STARTUP_QUIT,
)
_INTRO_KEYS: Final = MappingProxyType(
    {
        StartupReasonEnum.NEWER_TEMPORARY: "startup.recovery.intro.newer_temporary",
        StartupReasonEnum.FILE_DAMAGED: "startup.recovery.intro.file_damaged",
        StartupReasonEnum.FILE_MISSING: "startup.recovery.intro.file_missing",
        StartupReasonEnum.FILE_UNREADABLE: "startup.recovery.intro.file_unreadable",
        StartupReasonEnum.NEWER_VERSION: "startup.recovery.intro.newer_version",
    }
)
_CANDIDATE_KEYS: Final = MappingProxyType(
    {
        RecoverySourceEnum.TEMPORARY: "startup.recovery.candidate.temporary",
        RecoverySourceEnum.BACKUP: "startup.recovery.candidate.backup",
    }
)
_NO_PATH: Final = ValidationResult.failure(ErrorCodeEnum.STORAGE_FILE_NOT_FOUND)


class RecoveryPresenter:
    """Builds the ``RECOVERY`` snapshot and performs its actions."""

    def __init__(self, support: StartupSupport, formatter: DateTimeFormatter) -> None:
        """Create the presenter.

        Args:
            support: Commands, pickers and failure messages.
            formatter: ``saved_at`` of the candidates.
        """
        self._support = support
        self._formatter = formatter

    def build_snapshot(self, plan: StartupPlan, selected: int, busy: BusyCheck) -> RecoverySnapshot:
        """Describe the dialog for a ``NEEDS_RECOVERY`` or ``FATAL`` plan.

        Args:
            plan: Current situation.
            selected: Index of the selected candidate.
            busy: Tells whether an action is running.

        Returns:
            The snapshot.
        """
        tr = self._support.translator.tr
        visible = {
            ActionIdEnum.STARTUP_RESTORE: bool(plan.candidates),
            ActionIdEnum.STARTUP_KEEP_CURRENT_FILE: plan.can_keep_current,
            ActionIdEnum.STARTUP_CHOOSE_ANOTHER_FILE: plan.can_choose_another,
            ActionIdEnum.STARTUP_START_EMPTY: plan.can_start_empty,
            ActionIdEnum.STARTUP_RETRY: plan.can_retry,
        }
        return RecoverySnapshot(
            title=tr("startup.recovery.title"),
            intro=tr(_INTRO_KEYS.get(plan.reason, "startup.recovery.intro.file_damaged")),
            path=tr("startup.recovery.path", path=plan.path.as_posix()) if plan.path is not None else "",
            problems=self._support.problem_lines(plan.problem),
            candidates_caption=tr("startup.recovery.candidates") if plan.candidates else "",
            candidates=tuple(
                self._candidate(candidate, position == selected) for position, candidate in enumerate(plan.candidates)
            ),
            buttons=tuple(
                self._support.button(action, busy, visible=visible.get(action, True)) for action in RECOVERY_ACTIONS
            ),
        )

    def handle(self, action: ActionIdEnum, plan: StartupPlan, selected: int) -> StartupChoice:
        """Perform one action.

        Args:
            action: Clicked action.
            plan: Current situation.
            selected: Index of the selected candidate.

        Returns:
            What the flow does next.
        """
        if action is ActionIdEnum.STARTUP_QUIT:
            return StartupChoice(quit=True)
        path = plan.path
        if path is None:
            return StartupChoice(validation=_NO_PATH)
        commands = self._support.commands
        match action:
            case ActionIdEnum.STARTUP_RESTORE if 0 <= selected < len(plan.candidates):
                return self._support.choice(commands.restore(path, plan.candidates[selected].source))
            case ActionIdEnum.STARTUP_KEEP_CURRENT_FILE:
                return self._support.choice(commands.keep_current(path))
            case ActionIdEnum.STARTUP_CHOOSE_ANOTHER_FILE:
                return self._support.open_chosen(path.parent)
            case ActionIdEnum.STARTUP_START_EMPTY:
                return self._support.choice(commands.start_empty(path, self._support.translator.language))
            case ActionIdEnum.STARTUP_RETRY:
                return StartupChoice(plan=commands.inspect(path))
            case _:
                return StartupChoice(validation=ValidationResult.skipped())

    def _candidate(self, candidate: RecoveryCandidate, selected: bool) -> CandidateSnapshot:
        """Describe one restorable version.

        Args:
            candidate: The version.
            selected: Whether it is selected.

        Returns:
            Its snapshot.
        """
        key = _CANDIDATE_KEYS.get(candidate.source, "startup.recovery.candidate.backup")
        text = self._support.translator.tr(key, saved_at=self._formatter.date_time(candidate.saved_at))
        return CandidateSnapshot(text=text, selected=selected)
