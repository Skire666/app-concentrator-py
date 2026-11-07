"""Reader and writer of the ``UserSettings`` singleton of the store."""

from typing import Final, override

from concentrator.application.ports.user_settings_reader_port import UserSettingsReaderPort
from concentrator.application.ports.user_settings_writer_port import UserSettingsWriterPort
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.settings.user_settings import UserSettings
from concentrator.infrastructure.persistence.user_data_store import UserDataStore

ID_FIELD: Final = "id"


class StoreUserSettingsReader(UserSettingsReaderPort):
    """Reads ``UserData.settings``."""

    def __init__(self, store: UserDataStore) -> None:
        """Create the reader.

        Args:
            store: In-memory store.
        """
        self._store = store

    @override
    def read(self) -> DataResult[UserSettings]:
        return DataResult.ok(self._store.current().settings)


class StoreUserSettingsWriter(UserSettingsWriterPort):
    """Replaces ``UserData.settings``."""

    def __init__(self, store: UserDataStore) -> None:
        """Create the writer.

        Args:
            store: In-memory store.
        """
        self._store = store

    @override
    def update(self, settings: UserSettings) -> DataResult[UserSettings]:
        data = self._store.current()
        if settings.id != data.settings.id:
            return DataResult.fail(ValidationResult.failure(ErrorCodeEnum.ENTITY_NOT_FOUND, field=ID_FIELD))
        self._store.apply(data.with_settings(settings))
        return DataResult.ok(settings)
