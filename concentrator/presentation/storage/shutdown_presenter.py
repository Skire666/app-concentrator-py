"""Pending changes on close, quit and Windows session end (ADR-032)."""

import logging
from typing import Final

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.application.storage.save_coordinator import SaveCoordinator
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.presentation.ports.dialog_port import DialogPort
from concentrator.presentation.storage.storage_messages import StorageMessages

_logger = logging.getLogger(__name__)

LINE_BREAK: Final = "\n"


class ShutdownPresenter:
    """Flushes synchronously; on the normal close path a failure asks the user."""

    def __init__(self, coordinator: SaveCoordinator, translator: TranslatorPort) -> None:
        """Create the presenter; its dialogs come with ``attach`` once the main window exists (ADR-036).

        Args:
            coordinator: Saves the pending changes.
            translator: Current-language translator.
        """
        self._coordinator = coordinator
        self._translator = translator
        self._messages = StorageMessages(translator)
        self._dialogs: DialogPort | None = None

    def attach(self, dialogs: DialogPort) -> None:
        """Set the dialog service, parented to the main window this presenter guards.

        Args:
            dialogs: Questions shown when the flush fails.
        """
        self._dialogs = dialogs

    def can_close(self) -> bool:
        """Flush before the main window closes (``closeEvent``).

        An external change asks "Keep Concentrator's version" (overwrite, then quit; Escape) or "Quit
        without saving". Any other failure asks "Quit without saving" or "Retry"; Retry keeps the window
        open (Escape) and the automatic retries go on.

        Returns:
            Whether the window may close.
        """
        result = self._coordinator.flush_for_shutdown(interactive=True)
        if result.is_failure and ErrorCodeEnum.STORAGE_FILE_CHANGED_EXTERNALLY in result.error_codes:
            result = self._ask_external_change()
            if result.is_skipped:
                return self._quit_without_saving()
        if result.is_success:
            self._coordinator.close()
            return True
        tr = self._translator.tr
        message = tr("shutdown.failed.message", reason=LINE_BREAK.join(self._messages.lines(result)))
        if self._attached_dialogs().confirm(
            tr("shutdown.failed.title"), message, tr("dialog.button.quit_without_saving"), tr("dialog.button.retry")
        ):
            return self._quit_without_saving()
        _logger.info("Close cancelled: the changes could not be saved yet")
        return False

    def flush_without_dialog(self) -> None:
        """Flush on ``aboutToQuit``: no dialog can be shown, the result is logged, saving stops."""
        result = self._coordinator.flush_for_shutdown()
        if result.is_failure:
            _logger.error("Pending changes not saved at shutdown: %s", [code.name for code in result.error_codes])
        self._coordinator.close()

    def flush_on_session_end(self) -> None:
        """Flush on Windows session end (``commitDataRequest``): no dialog, the result is logged.

        Saving goes on: another application can cancel the session end, and Concentrator then keeps
        running. ``aboutToQuit`` stops saving if the session really ends.
        """
        result = self._coordinator.flush_for_shutdown()
        if result.is_failure:
            codes = [code.name for code in result.error_codes]
            _logger.error("Pending changes not saved at the end of the Windows session: %s", codes)

    def _ask_external_change(self) -> ValidationResult:
        """Ask about a file changed outside Concentrator while changes are pending.

        Returns:
            The result of overwriting, or ``skipped`` when the user quits without saving.
        """
        tr = self._translator.tr
        quit_without_saving = self._attached_dialogs().confirm(
            tr("external_change.title"),
            tr("shutdown.changed.message"),
            tr("dialog.button.quit_without_saving"),
            tr("dialog.button.keep_version"),
        )
        if quit_without_saving:
            return ValidationResult.skipped()
        return self._coordinator.flush_for_shutdown(overwrite_external=True, interactive=True)

    def _attached_dialogs(self) -> DialogPort:
        """The dialog service.

        Returns:
            The service given to ``attach``.

        Raises:
            RuntimeError: If ``attach`` was not called (a wiring error: bootstrap attaches it right after
                building the main window).
        """
        if self._dialogs is None:
            message = "ShutdownPresenter.attach() was not called"
            raise RuntimeError(message)
        return self._dialogs

    def _quit_without_saving(self) -> bool:
        """Stop saving and let the window close.

        Returns:
            ``True``.
        """
        _logger.warning("Quitting without saving the latest changes")
        self._coordinator.close()
        return True
