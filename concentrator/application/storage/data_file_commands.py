"""Opening another data file and moving the open one, from the settings page (phase 4)."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from concentrator.application.ports.user_data_file_port import UserDataFilePort
from concentrator.application.ports.user_data_session_port import UserDataSessionPort
from concentrator.application.ports.view_preferences_port import ViewPreferencesPort
from concentrator.application.storage.save_coordinator import SaveCoordinator
from concentrator.application.storage.startup_commands import DATA_FILE_PATH_KEY, StartupCommands
from concentrator.application.storage.startup_plan import StartupPlan
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.settings.language_enum import LanguageEnum

_logger = logging.getLogger(__name__)

_NO_FILE: Final = ValidationResult.failure(ErrorCodeEnum.STORAGE_FILE_NOT_FOUND)
_SAME_FILE: Final = ValidationResult.failure(ErrorCodeEnum.STORAGE_TARGET_IS_CURRENT_FILE)
_MOVE_FAILED: Final = ValidationResult.failure(ErrorCodeEnum.STORAGE_MOVE_FAILED)


@dataclass(frozen=True, slots=True, kw_only=True)
class MovedDataFile:
    """Both paths of a moved data file.

    Attributes:
        previous: File used before the move; it is kept as it was last saved.
        current: File now open.
    """

    previous: Path
    current: Path


class DataFileCommands:
    """The "Use another file" and "Move file" actions; the current file stays open whenever they fail."""

    def __init__(
        self,
        *,
        file: UserDataFilePort,
        session: UserDataSessionPort,
        coordinator: SaveCoordinator,
        startup: StartupCommands,
        preferences: ViewPreferencesPort,
    ) -> None:
        """Create the use cases.

        Args:
            file: Data file adapter.
            session: In-memory data.
            coordinator: Saves the pending changes; knows the open file.
            startup: The phase 1 load, recovery and creation use cases.
            preferences: ``ui-state.ini`` (remembered path).
        """
        self._file = file
        self._session = session
        self._coordinator = coordinator
        self._startup = startup
        self._preferences = preferences

    @property
    def current_path(self) -> Path | None:
        """Data file open now, ``None`` before one is open."""
        return self._coordinator.status.path

    def switch_to(self, path: Path) -> DataResult[StartupPlan]:
        """Save the pending changes, then inspect another data file and open it when it is ready.

        Args:
            path: Existing file chosen by the user.

        Returns:
            The plan: ``READY`` once the file is open; another step leaves the current file open and
            asks the caller to run the recovery dialog on it. Fails with
            ``STORAGE_TARGET_IS_CURRENT_FILE`` or the save failure, the current file staying open.
        """
        ready = self._before_switch(path)
        if ready.is_failure:
            return DataResult.fail(ready)
        return DataResult.ok(self._startup.inspect(path))

    def create_new(self, path: Path, language: LanguageEnum) -> DataResult[StartupPlan]:
        """Save the pending changes, then create a data file with default content and open it.

        Args:
            path: Where to create it.
            language: UI language of the new settings.

        Returns:
            The ``READY`` plan, or the failure (``STORAGE_FILE_ALREADY_EXISTS``, write errors); the
            current file then stays open.
        """
        ready = self._before_switch(path)
        if ready.is_failure:
            return DataResult.fail(ready)
        return self._startup.create_at(path, language)

    def move_to(self, target: Path) -> DataResult[MovedDataFile]:
        """Write the current data to a new file, check that it loads back, then use it.

        The previous file is neither changed nor deleted: it keeps its last saved content.

        Args:
            target: Path of the new file; it must not exist.

        Returns:
            Both paths, or ``STORAGE_TARGET_IS_CURRENT_FILE``, ``STORAGE_FILE_ALREADY_EXISTS``, a write
            failure or ``STORAGE_MOVE_FAILED``; the current file then stays open.
        """
        current = self.current_path
        if current is None:
            return DataResult.fail(_NO_FILE)
        if self._file.is_same_file(current, target):
            return DataResult.fail(_SAME_FILE)
        data = self._session.current()
        created = self._file.create(target, data)
        if created.data is None:
            return DataResult.fail(created.validation)
        loaded = self._file.load(target)
        if loaded.data is None or loaded.data.data != data:
            codes = [code.name for code in loaded.validation.error_codes]
            _logger.warning("Moved data file %s does not load back the same data: %s", target, codes)
            return DataResult.fail(_MOVE_FAILED)
        self._coordinator.attach(target, loaded.data.saved_at)
        self._preferences.set_text(DATA_FILE_PATH_KEY, target.as_posix())
        _logger.info("Data file moved from %s to %s; the previous file is kept", current, target)
        return DataResult.ok(MovedDataFile(previous=current, current=target), created.validation)

    def _before_switch(self, path: Path) -> ValidationResult:
        """Refuse the open file and write the pending changes before another file replaces it.

        Args:
            path: File about to be opened or created.

        Returns:
            Success, ``STORAGE_TARGET_IS_CURRENT_FILE``, or the save failure.
        """
        current = self.current_path
        if current is not None and self._file.is_same_file(current, path):
            return _SAME_FILE
        flushed = self._coordinator.flush_for_shutdown()
        if flushed.is_failure:
            _logger.warning(
                "Another data file is not opened: pending changes not saved (%s)",
                [code.name for code in flushed.error_codes],
            )
        return flushed
