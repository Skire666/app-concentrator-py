"""Reader and writer of the focus queue: the generic collection store on ``UserData``."""

from typing import override

from concentrator.application.ports.entity_reader_port import EntityQueryPort
from concentrator.application.ports.focus_item_reader_port import FocusItemReaderPort
from concentrator.application.ports.focus_item_writer_port import FocusItemWriterPort
from concentrator.application.storage.user_data import UserData
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.entity_collection import EntityCollection
from concentrator.domain.focus.focus_item import FocusItem
from concentrator.domain.focus.focus_items_collection import FocusItemsCollection
from concentrator.infrastructure.persistence.store_collection import (
    StoreCollectionReader,
    StoreCollectionWriter,
    UserDataSlot,
)
from concentrator.infrastructure.persistence.user_data_store import UserDataStore


def _read_queue(data: UserData) -> EntityCollection[FocusItem]:
    """Extract the queue.

    Args:
        data: Snapshot.

    Returns:
        The queue, empty before the file was completed.
    """
    return data.focus_queue or FocusItemsCollection()


def _write_queue(data: UserData, queue: EntityCollection[FocusItem]) -> UserData:
    """Replace the queue.

    Args:
        data: Snapshot.
        queue: Changed queue.

    Returns:
        The changed snapshot.
    """
    return data.with_focus_queue(FocusItemsCollection(queue))


class StoreFocusItemReader(FocusItemReaderPort):
    """``exists``, ``read_item``, ``all_items``, ``find`` on the focus queue (the generic reader, typed)."""

    def __init__(self, store: UserDataStore) -> None:
        """Create the reader.

        Args:
            store: In-memory store.
        """
        self._slot = UserDataSlot(store, _read_queue, _write_queue)
        self._generic = StoreCollectionReader(self._slot)

    @override
    def exists(self, entity_id: str) -> DataResult[bool]:
        return self._generic.exists(entity_id)

    @override
    def read_item(self, entity_id: str) -> DataResult[FocusItem]:
        return self._generic.read_item(entity_id)

    @override
    def all_items(self) -> DataResult[FocusItemsCollection]:
        return DataResult.ok(FocusItemsCollection(self._slot.read()))

    @override
    def find(self, query: EntityQueryPort[FocusItem]) -> DataResult[FocusItemsCollection]:
        return DataResult.ok(FocusItemsCollection(self._slot.read()).filtered(query.matches))


class StoreFocusItemWriter(StoreCollectionWriter[FocusItem], FocusItemWriterPort):
    """The nine operations and the bulk changes on the focus queue."""

    def __init__(self, store: UserDataStore) -> None:
        """Create the writer.

        Args:
            store: In-memory store.
        """
        super().__init__(UserDataSlot(store, _read_queue, _write_queue))
