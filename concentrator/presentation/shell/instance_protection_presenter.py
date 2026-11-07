"""Visible warning when the single-instance lock could not be created (ADR-031)."""

import logging

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.presentation.ports.dialog_port import DialogPort

_logger = logging.getLogger(__name__)


class InstanceProtectionPresenter:
    """Startup warning dialog and status bar indicator of the unguarded mode."""

    def __init__(self, translator: TranslatorPort, *, protected: bool) -> None:
        """Create the presenter.

        Args:
            translator: Current-language translator.
            protected: Whether this process holds the instance lock.
        """
        self._translator = translator
        self._protected = protected

    @property
    def protected(self) -> bool:
        """Whether a second launch is blocked."""
        return self._protected

    def warn_if_unprotected(self, dialogs: DialogPort) -> None:
        """Show the warning before any data file is opened, when the lock is missing.

        Args:
            dialogs: Dialog service.
        """
        if self._protected:
            return
        _logger.info("Unguarded single-instance warning shown")
        tr = self._translator.tr
        dialogs.warn(tr("instance.unguarded.title"), tr("instance.unguarded.message"), tr("dialog.button.ok"))

    def status_text(self) -> str:
        """Status bar indicator.

        Returns:
            The warning, ``""`` when protected.
        """
        return "" if self._protected else self._translator.tr("status.instance.unguarded")

    def status_tooltip(self) -> str:
        """Tooltip of the indicator.

        Returns:
            The explanation, ``""`` when protected.
        """
        return "" if self._protected else self._translator.tr("instance.unguarded.message")
