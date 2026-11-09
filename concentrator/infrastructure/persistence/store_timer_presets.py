"""Reader and writer of the timer favorites: the generic collection store on ``UserData.timer_presets``."""

from typing import override

from concentrator.application.ports.entity_reader_port import EntityQueryPort
from concentrator.application.ports.timer_preset_reader_port import TimerPresetReaderPort
from concentrator.application.ports.timer_preset_writer_port import TimerPresetWriterPort
from concentrator.application.storage.user_data import UserData
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.entity_collection import EntityCollection
from concentrator.domain.timer.timer_preset import TimerPreset
from concentrator.domain.timer.timer_presets_collection import TimerPresetsCollection
from concentrator.infrastructure.persistence.store_collection import (
    StoreCollectionReader,
    StoreCollectionWriter,
    UserDataSlot,
)
from concentrator.infrastructure.persistence.user_data_store import UserDataStore


def _read(data: UserData) -> EntityCollection[TimerPreset]:
    """Extract the favorites.

    Args:
        data: Snapshot.

    Returns:
        The favorites, empty before the file was completed.
    """
    return data.timer_presets or TimerPresetsCollection()


def _write(data: UserData, presets: EntityCollection[TimerPreset]) -> UserData:
    """Replace the favorites.

    Args:
        data: Snapshot.
        presets: Changed favorites.

    Returns:
        The changed snapshot.
    """
    return data.with_timer_presets(TimerPresetsCollection(presets))


def timer_presets_slot(store: UserDataStore) -> UserDataSlot[TimerPreset]:
    """Return the slot of the favorites.

    Args:
        store: In-memory store.

    Returns:
        The slot.
    """
    return UserDataSlot(store, _read, _write)


class StoreTimerPresetReader(TimerPresetReaderPort):
    """``exists``, ``read_item``, ``all_items``, ``find`` on the favorites (the generic reader, typed)."""

    def __init__(self, store: UserDataStore) -> None:
        """Create the reader.

        Args:
            store: In-memory store.
        """
        self._slot = timer_presets_slot(store)
        self._generic = StoreCollectionReader(self._slot)

    @override
    def exists(self, entity_id: str) -> DataResult[bool]:
        return self._generic.exists(entity_id)

    @override
    def read_item(self, entity_id: str) -> DataResult[TimerPreset]:
        return self._generic.read_item(entity_id)

    @override
    def all_items(self) -> DataResult[TimerPresetsCollection]:
        return DataResult.ok(TimerPresetsCollection(self._slot.read()))

    @override
    def find(self, query: EntityQueryPort[TimerPreset]) -> DataResult[TimerPresetsCollection]:
        return DataResult.ok(TimerPresetsCollection(self._slot.read()).filtered(query.matches))


class StoreTimerPresetWriter(StoreCollectionWriter[TimerPreset], TimerPresetWriterPort):
    """``create``, ``update``, ``delete``, ``copy_business``, ``copy_technical`` on the favorites."""

    def __init__(self, store: UserDataStore) -> None:
        """Create the writer.

        Args:
            store: In-memory store.
        """
        super().__init__(timer_presets_slot(store))
