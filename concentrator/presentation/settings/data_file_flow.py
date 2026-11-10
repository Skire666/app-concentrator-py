"""The "Use another file..." and "Move file..." dialogs of the settings page."""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.application.settings.settings_queries import SettingsQueries
from concentrator.application.storage.data_file_commands import DataFileCommands
from concentrator.application.storage.startup_plan import StartupPlan
from concentrator.application.storage.startup_step_enum import StartupStepEnum
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.presentation.common.pending_edits import PendingEdits, PendingEditsQuestion, resolve_pending_edits
from concentrator.presentation.ports.dialog_port import DialogPort
from concentrator.presentation.shell.language_switcher import LanguageSwitcher
from concentrator.presentation.storage.storage_messages import StorageMessages

_logger = logging.getLogger(__name__)

OPEN_ANSWER: Final = 0
CREATE_ANSWER: Final = 1
CANCEL_ANSWER: Final = 2
LINE_BREAK: Final = "\n"
_NOT_FOUND: Final = ValidationResult.failure(ErrorCodeEnum.STORAGE_FILE_NOT_FOUND)

type RecoveryFlow = Callable[[StartupPlan], bool]


@dataclass(frozen=True, slots=True, kw_only=True)
class DataFileServices:
    """What switching and moving the data file needs.

    Attributes:
        commands: Switch, create and move use cases.
        settings: Language of the file just opened.
        switcher: Shows that language and re-renders everything.
        recovery: Runs the recovery dialog on a file that is not ready; returns whether it opened.
    """

    commands: DataFileCommands
    settings: SettingsQueries
    switcher: LanguageSwitcher
    recovery: RecoveryFlow


class DataFileFlow:
    """Asks, runs the use case, then explains the outcome; the current file stays open on any failure."""

    def __init__(self, translator: TranslatorPort, services: DataFileServices) -> None:
        """Create the flow; the dialog service and the settings form come with ``attach``.

        Args:
            translator: Current-language translator.
            services: Use cases and collaborators.
        """
        self._translator = translator
        self._services = services
        self._messages = StorageMessages(translator)
        self._dialogs: DialogPort | None = None
        self._edits: PendingEdits | None = None

    def attach(self, dialogs: DialogPort, edits: PendingEdits) -> None:
        """Set the dialog service of the main window and the settings form.

        Args:
            dialogs: Questions, pickers and messages.
            edits: The settings form, saved or discarded before another file opens.
        """
        self._dialogs = dialogs
        self._edits = edits

    def switch(self) -> ValidationResult:
        """Open or create another data file ("Use another file...").

        Returns:
            Success once another file is open, skipped when the user cancelled, or the failure (shown).
        """
        if self._edits is not None:
            pending = resolve_pending_edits(self._edits, self._dialogs_or_fail(), self._pending_question())
            if not pending.is_success:
                return pending
        tr = self._translator.tr
        answer = self._dialogs_or_fail().choose(
            tr("settings.switch.title"),
            tr("settings.switch.message"),
            (tr("dialog.button.open_file"), tr("dialog.button.create_file"), tr("dialog.button.cancel")),
            CANCEL_ANSWER,
        )
        if answer == OPEN_ANSWER:
            return self._open_another()
        if answer == CREATE_ANSWER:
            return self._create_another()
        return ValidationResult.skipped()

    def move(self) -> ValidationResult:
        """Write the data to a new file and use it ("Move file...").

        Returns:
            Success once moved, skipped when the user cancelled, or the failure (shown).
        """
        current = self._services.commands.current_path
        if current is None:
            return self._failed(_NOT_FOUND)
        tr = self._translator.tr
        dialogs = self._dialogs_or_fail()
        chosen = dialogs.choose_save_file(
            tr("settings.move.title"), current.as_posix(), tr("startup.file_dialog.filter")
        )
        if chosen is None:
            return ValidationResult.skipped()
        target = Path(chosen)
        message = tr("settings.move.confirm", target=target.as_posix(), current=current.as_posix())
        if not dialogs.confirm(
            tr("settings.move.title"), message, tr("dialog.button.move"), tr("dialog.button.cancel")
        ):
            return ValidationResult.skipped()
        moved = self._services.commands.move_to(target)
        if moved.data is None:
            return self._failed(moved.validation)
        done = tr("settings.move.done", current=moved.data.current.as_posix(), previous=moved.data.previous.as_posix())
        dialogs.inform(tr("settings.move.title"), done, tr("dialog.button.ok"))
        return moved.validation

    def _open_another(self) -> ValidationResult:
        """Pick an existing file and open it, through the recovery dialog when it is not ready.

        Returns:
            The outcome.
        """
        tr = self._translator.tr
        chosen = self._dialogs_or_fail().choose_open_file(
            tr("startup.file_dialog.open_title"), self._start_folder(), tr("startup.file_dialog.filter")
        )
        if chosen is None:
            return ValidationResult.skipped()
        return self._opened(self._services.commands.switch_to(Path(chosen)))

    def _create_another(self) -> ValidationResult:
        """Pick where to create a file with default content and open it.

        Returns:
            The outcome.
        """
        tr = self._translator.tr
        chosen = self._dialogs_or_fail().choose_save_file(
            tr("startup.file_dialog.create_title"), self._start_folder(), tr("startup.file_dialog.filter")
        )
        if chosen is None:
            return ValidationResult.skipped()
        return self._opened(self._services.commands.create_new(Path(chosen), self._translator.language))

    def _opened(self, result: DataResult[StartupPlan]) -> ValidationResult:
        """Finish a switch: recovery when needed, then the language of the new file and a message.

        Args:
            result: Result of the switch or creation.

        Returns:
            The outcome.
        """
        plan = result.data
        if plan is None:
            return self._failed(result.validation)
        if plan.step is StartupStepEnum.NEEDS_LOCATION:
            return self._failed(_NOT_FOUND)
        if plan.step is not StartupStepEnum.READY and not self._services.recovery(plan):
            _logger.info("Another data file was not opened: recovery cancelled")
            return ValidationResult.skipped()
        settings = self._services.settings.current_settings().data
        if settings is not None:
            self._services.switcher.follow(settings.language)
        tr = self._translator.tr
        path = self._services.commands.current_path
        done = tr("settings.switch.done", path=path.as_posix() if path is not None else "")
        self._dialogs_or_fail().inform(tr("settings.switch.title"), done, tr("dialog.button.ok"))
        return result.validation

    def _start_folder(self) -> str:
        """Folder the pickers start from.

        Returns:
            The folder of the open data file, ``""`` when none is open.
        """
        current = self._services.commands.current_path
        return "" if current is None else current.parent.as_posix()

    def _pending_question(self) -> PendingEditsQuestion:
        """Texts of the question about unsaved settings.

        Returns:
            The question.
        """
        tr = self._translator.tr
        return PendingEditsQuestion(
            title=tr("settings.leave.title"),
            message=tr("settings.leave.message"),
            answers=(tr("dialog.button.save"), tr("dialog.button.discard"), tr("dialog.button.cancel")),
        )

    def _failed(self, result: ValidationResult) -> ValidationResult:
        """Explain a failure; the current file stays open.

        Args:
            result: The failure.

        Returns:
            The failure.
        """
        _logger.warning("Data file action failed: %s", [code.name for code in result.error_codes])
        tr = self._translator.tr
        message = LINE_BREAK.join(self._messages.lines(result))
        self._dialogs_or_fail().error(tr("startup.error.title"), message, tr("dialog.button.ok"))
        return result

    def _dialogs_or_fail(self) -> DialogPort:
        """The dialog service.

        Returns:
            The service given to ``attach``.

        Raises:
            RuntimeError: If ``attach`` was not called (a wiring error).
        """
        if self._dialogs is None:
            message = "DataFileFlow.attach() was not called"
            raise RuntimeError(message)
        return self._dialogs
