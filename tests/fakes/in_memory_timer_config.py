"""Timer configuration reader and writer over one in-memory value."""

from typing import override

from concentrator.application.ports.timer_config_reader_port import TimerConfigReaderPort
from concentrator.application.ports.timer_config_writer_port import TimerConfigWriterPort
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.timer.timer_config import TimerConfig


class InMemoryTimerConfig(TimerConfigReaderPort, TimerConfigWriterPort):
    """``config`` is ``None`` to simulate a missing section; ``write_failure`` scripts the writer."""

    def __init__(self, config: TimerConfig | None) -> None:
        self.config = config
        self.write_failure: ValidationResult | None = None
        self.updates: list[TimerConfig] = []

    @override
    def read(self) -> DataResult[TimerConfig]:
        if self.config is None:
            return DataResult.fail(ValidationResult.failure(ErrorCodeEnum.ENTITY_NOT_FOUND, field="timer"))
        return DataResult.ok(self.config)

    @override
    def update(self, config: TimerConfig) -> DataResult[TimerConfig]:
        if self.write_failure is not None:
            return DataResult.fail(self.write_failure)
        self.config = config
        self.updates.append(config)
        return DataResult.ok(config)
