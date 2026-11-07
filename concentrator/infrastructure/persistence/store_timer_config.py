"""Reader and writer of the ``TimerConfig`` singleton of the store."""

from typing import Final, override

from concentrator.application.ports.timer_config_reader_port import TimerConfigReaderPort
from concentrator.application.ports.timer_config_writer_port import TimerConfigWriterPort
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.timer.timer_config import TimerConfig
from concentrator.infrastructure.persistence.user_data_store import UserDataStore

TIMER_FIELD: Final = "timer"
ID_FIELD: Final = "timer.id"


class StoreTimerConfigReader(TimerConfigReaderPort):
    """Reads ``UserData.timer``."""

    def __init__(self, store: UserDataStore) -> None:
        """Create the reader.

        Args:
            store: In-memory store.
        """
        self._store = store

    @override
    def read(self) -> DataResult[TimerConfig]:
        timer = self._store.current().timer
        if timer is None:
            return DataResult.fail(ValidationResult.failure(ErrorCodeEnum.ENTITY_NOT_FOUND, field=TIMER_FIELD))
        return DataResult.ok(timer)


class StoreTimerConfigWriter(TimerConfigWriterPort):
    """Replaces ``UserData.timer``."""

    def __init__(self, store: UserDataStore) -> None:
        """Create the writer.

        Args:
            store: In-memory store.
        """
        self._store = store

    @override
    def update(self, config: TimerConfig) -> DataResult[TimerConfig]:
        data = self._store.current()
        if data.timer is None or config.id != data.timer.id:
            return DataResult.fail(ValidationResult.failure(ErrorCodeEnum.ENTITY_NOT_FOUND, field=ID_FIELD))
        self._store.apply(data.with_timer(config))
        return DataResult.ok(config)
