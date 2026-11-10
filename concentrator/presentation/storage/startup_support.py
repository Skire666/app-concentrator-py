"""Shared parts of the first-run and recovery presenters: buttons, file pickers, failures."""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Final

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.application.storage.startup_commands import StartupCommands
from concentrator.application.storage.startup_plan import StartupPlan
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.button_snapshot import ButtonSnapshot
from concentrator.presentation.common.ui_texts import UiTexts
from concentrator.presentation.ports.dialog_port import DialogPort
from concentrator.presentation.storage.startup_choice import StartupChoice
from concentrator.presentation.storage.storage_messages import StorageMessages

_logger = logging.getLogger(__name__)

LINE_BREAK: Final = "\n"

type BusyCheck = Callable[[ActionIdEnum], bool]


class StartupSupport:
    """Runs the startup commands for the dialogs and reports their failures."""

    def __init__(self, commands: StartupCommands, dialogs: DialogPort, translator: TranslatorPort) -> None:
        """Create the helper.

        Args:
            commands: Startup use cases.
            dialogs: File pickers and error messages.
            translator: Current-language translator.
        """
        self._commands = commands
        self._dialogs = dialogs
        self._translator = translator
        self._texts = UiTexts(translator)
        self._messages = StorageMessages(translator)

    def use_dialogs(self, dialogs: DialogPort) -> None:
        """Show the pickers and messages with another dialog service (over the main window).

        Args:
            dialogs: New dialog service.
        """
        self._dialogs = dialogs

    @property
    def commands(self) -> StartupCommands:
        """Startup use cases."""
        return self._commands

    @property
    def translator(self) -> TranslatorPort:
        """Current-language translator."""
        return self._translator

    def button(self, action: ActionIdEnum, busy: BusyCheck, *, visible: bool = True) -> ButtonSnapshot:
        """Describe a dialog button.

        Args:
            action: Its action.
            busy: Tells whether an action is running.
            visible: Whether the situation offers it.

        Returns:
            The button snapshot.
        """
        return ButtonSnapshot(
            text=self._texts.action_label(action),
            tooltip=self._texts.action_tooltip(action),
            enabled=not busy(action),
            visible=visible,
            action=action,
        )

    def problem_lines(self, result: ValidationResult) -> tuple[str, ...]:
        """Translate the problems of a data file.

        Args:
            result: Failed load.

        Returns:
            The lines.
        """
        return self._messages.lines(result)

    def choice(self, result: DataResult[StartupPlan]) -> StartupChoice:
        """Turn a command result into a choice; a failure is shown and the dialog stays.

        Args:
            result: Result of a startup command.

        Returns:
            The new plan, or no change after the error message.
        """
        if result.data is None:
            self.show_failure(result.validation)
            return StartupChoice(validation=result.validation)
        return StartupChoice(plan=result.data, validation=result.validation)

    def show_failure(self, result: ValidationResult) -> None:
        """Explain a failed action.

        Args:
            result: The failure.
        """
        _logger.warning("Startup action failed: %s", [code.name for code in result.error_codes])
        tr = self._translator.tr
        message = LINE_BREAK.join(self._messages.lines(result))
        self._dialogs.error(tr("startup.error.title"), message, tr("dialog.button.ok"))

    def open_chosen(self, start: Path) -> StartupChoice:
        """Let the user pick an existing file, then inspect it.

        Args:
            start: Folder or file the picker starts from.

        Returns:
            The plan of the chosen file, or no change when cancelled.
        """
        tr = self._translator.tr
        chosen = self._dialogs.choose_open_file(
            tr("startup.file_dialog.open_title"), start.as_posix(), tr("startup.file_dialog.filter")
        )
        if chosen is None:
            return StartupChoice(validation=ValidationResult.skipped())
        return StartupChoice(plan=self._commands.inspect(Path(chosen)))

    def create_chosen(self, start: Path) -> StartupChoice:
        """Let the user pick where to create a new file, then create it.

        Args:
            start: Path the picker proposes.

        Returns:
            The ``READY`` plan, no change when cancelled, or no change after the error message.
        """
        tr = self._translator.tr
        chosen = self._dialogs.choose_save_file(
            tr("startup.file_dialog.create_title"), start.as_posix(), tr("startup.file_dialog.filter")
        )
        if chosen is None:
            return StartupChoice(validation=ValidationResult.skipped())
        return self.choice(self._commands.create_at(Path(chosen), self._translator.language))
