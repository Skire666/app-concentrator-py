"""The two answers to a data file changed outside Concentrator (ADR-033)."""

import logging

from concentrator.application.ports.user_data_file_port import UserDataFilePort
from concentrator.application.ports.user_data_session_port import UserDataSessionPort
from concentrator.application.storage.save_coordinator import SaveCoordinator
from concentrator.application.storage.user_data import StoredUserData
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult

_logger = logging.getLogger(__name__)


class ExternalChangeCommands:
    """Reload the externally changed file, or keep Concentrator's version."""

    def __init__(self, file: UserDataFilePort, session: UserDataSessionPort, coordinator: SaveCoordinator) -> None:
        """Create the use cases.

        Args:
            file: Data file adapter.
            session: In-memory data.
            coordinator: Save coordinator holding the conflict.
        """
        self._file = file
        self._session = session
        self._coordinator = coordinator

    def reload(self) -> DataResult[StoredUserData]:
        """Load the file as changed on disk; changes made in Concentrator since the last save are lost.

        Returns:
            The reloaded data, or the load failure (the session and the conflict are then unchanged).
        """
        path = self._coordinator.status.path
        if path is None:
            return DataResult.fail(ValidationResult.failure(ErrorCodeEnum.STORAGE_FILE_NOT_FOUND))
        loaded = self._file.load(path)
        if loaded.data is None:
            return loaded
        self._session.reset(loaded.data.data)
        self._coordinator.attach(path, loaded.data.saved_at)
        _logger.info("Data file reloaded after an external change")
        return loaded

    def keep_concentrator_version(self) -> ValidationResult:
        """Overwrite the file with the in-memory data at once.

        Returns:
            Success (the save result arrives through ``SaveStatusChangedEvent``).
        """
        self._coordinator.keep_local_version()
        return ValidationResult.success()
