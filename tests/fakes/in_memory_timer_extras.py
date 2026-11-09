"""Favorites and hourly chime readers and writers over in-memory values."""

import copy
from datetime import datetime
from typing import override

from concentrator.application.ports.entity_reader_port import EntityQueryPort
from concentrator.application.ports.hourly_chime_reader_port import HourlyChimeReaderPort
from concentrator.application.ports.hourly_chime_writer_port import HourlyChimeWriterPort
from concentrator.application.ports.timer_preset_reader_port import TimerPresetReaderPort
from concentrator.application.ports.timer_preset_writer_port import TimerPresetWriterPort
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.timer.hourly_chime import HourlyChime
from concentrator.domain.timer.timer_preset import TimerPreset
from concentrator.domain.timer.timer_presets_collection import TimerPresetsCollection


class InMemoryTimerPresets(TimerPresetReaderPort, TimerPresetWriterPort):
    """``presets`` is the stored collection; ``write_failure`` scripts every write; ``writes`` counts them."""

    def __init__(self, presets: TimerPresetsCollection) -> None:
        self.presets = presets
        self.write_failure: ValidationResult | None = None
        self.writes = 0

    @override
    def exists(self, entity_id: str) -> DataResult[bool]:
        return DataResult.ok(self.presets.contains(entity_id))

    @override
    def read_item(self, entity_id: str) -> DataResult[TimerPreset]:
        return self.presets.get(entity_id)

    @override
    def all_items(self) -> DataResult[TimerPresetsCollection]:
        return DataResult.ok(self.presets)

    @override
    def find(self, query: EntityQueryPort[TimerPreset]) -> DataResult[TimerPresetsCollection]:
        return DataResult.ok(self.presets.filtered(query.matches))

    @override
    def create(self, entity: TimerPreset) -> DataResult[TimerPreset]:
        return self._store(self.presets.with_added(entity), entity)

    @override
    def update(self, entity: TimerPreset) -> DataResult[TimerPreset]:
        return self._store(self.presets.with_replaced(entity), entity)

    @override
    def delete(self, entity_id: str) -> DataResult[TimerPreset]:
        found = self.presets.get(entity_id)
        if found.data is None:
            return found
        return self._store(self.presets.without(entity_id), found.data)

    @override
    def copy_business(self, entity_id: str, new_id: str, now: datetime) -> DataResult[TimerPreset]:
        found = self.presets.get(entity_id)
        if found.data is None:
            return found
        return self.create(found.data.business_copy(new_id, now))

    @override
    def copy_technical(self, entity_id: str) -> DataResult[TimerPreset]:
        found = self.presets.get(entity_id)
        return found if found.data is None else DataResult.ok(copy.copy(found.data))

    def _store(self, changed: DataResult[TimerPresetsCollection], entity: TimerPreset) -> DataResult[TimerPreset]:
        if self.write_failure is not None:
            return DataResult.fail(self.write_failure)
        if changed.data is None:
            return DataResult.fail(changed.validation)
        self.presets = changed.data
        self.writes += 1
        return DataResult.ok(entity)


class InMemoryHourlyChime(HourlyChimeReaderPort, HourlyChimeWriterPort):
    """``chime`` is ``None`` to simulate a missing section; ``write_failure`` scripts the writer."""

    def __init__(self, chime: HourlyChime | None) -> None:
        self.chime = chime
        self.write_failure: ValidationResult | None = None
        self.updates: list[HourlyChime] = []

    @override
    def read(self) -> DataResult[HourlyChime]:
        if self.chime is None:
            return DataResult.fail(ValidationResult.failure(ErrorCodeEnum.ENTITY_NOT_FOUND, field="hourly_chime"))
        return DataResult.ok(self.chime)

    @override
    def update(self, chime: HourlyChime) -> DataResult[HourlyChime]:
        if self.write_failure is not None:
            return DataResult.fail(self.write_failure)
        self.chime = chime
        self.updates.append(chime)
        return DataResult.ok(chime)
