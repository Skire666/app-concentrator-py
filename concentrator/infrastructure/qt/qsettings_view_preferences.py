"""``ViewPreferencesPort`` on ``QSettings`` in ini format (``ui-state.ini``)."""

import logging
from pathlib import Path
from typing import override

from PySide6.QtCore import QSettings

from concentrator.application.ports.view_preferences_port import ViewPreferencesPort

_logger = logging.getLogger(__name__)


class QSettingsViewPreferences(ViewPreferencesPort):
    """The only reader and writer of ``ui-state.ini`` (AGENTS.md section 7.3)."""

    def __init__(self, ini_file: Path) -> None:
        """Open the file (created on the first ``sync`` that has something to write).

        Args:
            ini_file: Resolved ``paths.ui_state_file``.
        """
        self._ini_file = ini_file
        self._settings = QSettings(str(ini_file), QSettings.Format.IniFormat)

    @override
    def get_text(self, key: str) -> str | None:
        value: object = self._settings.value(key)
        return value if isinstance(value, str) else None

    @override
    def set_text(self, key: str, value: str) -> None:
        self._settings.setValue(key, value)

    @override
    def remove(self, key: str) -> None:
        self._settings.remove(key)

    @override
    def remove_group(self, group: str) -> None:
        self._settings.remove(group)

    def sync(self) -> bool:
        """Write pending changes to disk now (Qt also syncs on its own).

        Returns:
            Whether the file was written without error; failures are logged.
        """
        self._settings.sync()
        status = self._settings.status()
        if status != QSettings.Status.NoError:
            _logger.warning("Cannot write UI state file %s: %s", self._ini_file, status.name)
            return False
        return True
