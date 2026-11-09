"""Reader and writer of the ``HourlyChime`` singleton of the store."""

from typing import Final, override

from concentrator.application.ports.hourly_chime_reader_port import HourlyChimeReaderPort
from concentrator.application.ports.hourly_chime_writer_port import HourlyChimeWriterPort
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.timer.hourly_chime import HourlyChime
from concentrator.infrastructure.persistence.user_data_store import UserDataStore

CHIME_FIELD: Final = "hourly_chime"
ID_FIELD: Final = "hourly_chime.id"


class StoreHourlyChimeReader(HourlyChimeReaderPort):
    """Reads ``UserData.hourly_chime``."""

    def __init__(self, store: UserDataStore) -> None:
        """Create the reader.

        Args:
            store: In-memory store.
        """
        self._store = store

    @override
    def read(self) -> DataResult[HourlyChime]:
        chime = self._store.current().hourly_chime
        if chime is None:
            return DataResult.fail(ValidationResult.failure(ErrorCodeEnum.ENTITY_NOT_FOUND, field=CHIME_FIELD))
        return DataResult.ok(chime)


class StoreHourlyChimeWriter(HourlyChimeWriterPort):
    """Replaces ``UserData.hourly_chime``."""

    def __init__(self, store: UserDataStore) -> None:
        """Create the writer.

        Args:
            store: In-memory store.
        """
        self._store = store

    @override
    def update(self, chime: HourlyChime) -> DataResult[HourlyChime]:
        data = self._store.current()
        if data.hourly_chime is None or chime.id != data.hourly_chime.id:
            return DataResult.fail(ValidationResult.failure(ErrorCodeEnum.ENTITY_NOT_FOUND, field=ID_FIELD))
        self._store.apply(data.with_hourly_chime(chime))
        return DataResult.ok(chime)
