"""Asks what to do when the data file was changed outside Concentrator (ADR-033)."""

import logging
from typing import Final

from concentrator.application.ports.scheduler_port import SchedulerPort
from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.application.storage.external_change_commands import ExternalChangeCommands
from concentrator.application.storage.save_state_enum import SaveStateEnum
from concentrator.application.storage.storage_events import SaveStatusChangedEvent
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.presentation.ports.dialog_port import DialogPort
from concentrator.presentation.shell.language_switcher import LanguageSwitcher
from concentrator.presentation.storage.storage_messages import StorageMessages

_logger = logging.getLogger(__name__)

LINE_BREAK: Final = "\n"


class ExternalChangePresenter:
    """Subscribed to ``SaveStatusChangedEvent``; the question is asked on the next event-loop turn."""

    def __init__(
        self,
        commands: ExternalChangeCommands,
        dialogs: DialogPort,
        translator: TranslatorPort,
        scheduler: SchedulerPort,
        switcher: LanguageSwitcher,
    ) -> None:
        """Create the presenter.

        Args:
            commands: Reload or keep Concentrator's version.
            dialogs: The question and the reload error.
            translator: Current-language translator.
            scheduler: Defers the modal question out of the save callback.
            switcher: Shows the language of the reloaded settings and re-renders everything.
        """
        self._commands = commands
        self._dialogs = dialogs
        self._translator = translator
        self._scheduler = scheduler
        self._switcher = switcher
        self._messages = StorageMessages(translator)
        self._pending = False

    def on_save_status_changed(self, status: SaveStatusChangedEvent) -> None:
        """Schedule the question when a save was refused because of an external change.

        Args:
            status: New save status.
        """
        external = ErrorCodeEnum.STORAGE_FILE_CHANGED_EXTERNALLY in status.validation.error_codes
        if status.state is SaveStateEnum.FAILED and external:
            self._schedule()

    def _schedule(self) -> None:
        """Ask once, on the next event-loop turn."""
        if not self._pending:
            self._pending = True
            self._scheduler.call_soon(self._ask)

    def _ask(self) -> None:
        """Ask "Reload the file" or "Keep Concentrator's version" (Escape keeps it)."""
        self._pending = False
        tr = self._translator.tr
        reload = self._dialogs.confirm(
            tr("external_change.title"),
            tr("external_change.message"),
            tr("dialog.button.reload_file"),
            tr("dialog.button.keep_version"),
        )
        if not reload:
            _logger.info("External change: keeping Concentrator's version")
            self._commands.keep_concentrator_version()
            return
        loaded = self._commands.reload()
        stored = loaded.data
        if stored is None:
            message = LINE_BREAK.join((tr("external_change.reload_failed"), *self._messages.lines(loaded.validation)))
            self._dialogs.error(tr("external_change.title"), message, tr("dialog.button.ok"))
            self._schedule()
            return
        self._switcher.follow(stored.data.settings.language)
