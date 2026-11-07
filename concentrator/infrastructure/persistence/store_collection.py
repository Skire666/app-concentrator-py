"""Generic reader and writer of one entity collection of the store (``AGENTS.md`` section 6.2).

The nine data operations are implemented once here. An aggregate specializes them with a
``UserDataSlot`` naming its section; its own ports may narrow the collection type, since every
``EntityCollection`` operation returns the concrete subclass.
"""

import copy
from collections.abc import Callable
from datetime import datetime
from typing import Protocol, override

from concentrator.application.ports.entity_reader_port import EntityQueryPort, EntityReaderPort
from concentrator.application.ports.entity_writer_port import EntityWriterPort
from concentrator.application.storage.user_data import UserData
from concentrator.domain.common.business_copyable import BusinessCopyable
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.entity_collection import EntityCollection
from concentrator.domain.common.identified import Identified
from concentrator.infrastructure.persistence.user_data_store import UserDataStore


class CollectionSlot[E: Identified](Protocol):
    """Where a collection lives: reading it and storing a changed version."""

    def read(self) -> EntityCollection[E]:
        """Return the current collection.

        Returns:
            The collection.
        """
        ...

    def write(self, collection: EntityCollection[E]) -> None:
        """Store a changed collection.

        Args:
            collection: New version.
        """
        ...


class UserDataSlot[E: Identified](CollectionSlot[E]):
    """A section of the ``UserDataStore`` snapshot."""

    def __init__(
        self,
        store: UserDataStore,
        read: Callable[[UserData], EntityCollection[E]],
        write: Callable[[UserData, EntityCollection[E]], UserData],
    ) -> None:
        """Create the slot.

        Args:
            store: In-memory store.
            read: Extracts the section from a snapshot.
            write: Returns a snapshot with the section replaced.
        """
        self._store = store
        self._read = read
        self._write = write

    @override
    def read(self) -> EntityCollection[E]:
        return self._read(self._store.current())

    @override
    def write(self, collection: EntityCollection[E]) -> None:
        self._store.apply(self._write(self._store.current(), collection))


class StoreCollectionReader[E: Identified](EntityReaderPort[E]):
    """``exists``, ``read_item``, ``all_items``, ``find``."""

    def __init__(self, slot: CollectionSlot[E]) -> None:
        """Create the reader.

        Args:
            slot: The collection.
        """
        self._slot = slot

    @override
    def exists(self, entity_id: str) -> DataResult[bool]:
        return DataResult.ok(self._slot.read().contains(entity_id))

    @override
    def read_item(self, entity_id: str) -> DataResult[E]:
        return self._slot.read().get(entity_id)

    @override
    def all_items(self) -> DataResult[EntityCollection[E]]:
        return DataResult.ok(self._slot.read())

    @override
    def find(self, query: EntityQueryPort[E]) -> DataResult[EntityCollection[E]]:
        return DataResult.ok(self._slot.read().filtered(query.matches))


class StoreCollectionWriter[E: BusinessCopyable](EntityWriterPort[E]):
    """``create``, ``update``, ``delete``, ``copy_business``, ``copy_technical``."""

    def __init__(self, slot: CollectionSlot[E]) -> None:
        """Create the writer.

        Args:
            slot: The collection.
        """
        self._slot = slot

    @override
    def create(self, entity: E) -> DataResult[E]:
        added = self._slot.read().with_added(entity)
        if added.data is None:
            return DataResult.fail(added.validation)
        self._slot.write(added.data)
        return DataResult.ok(entity)

    @override
    def update(self, entity: E) -> DataResult[E]:
        replaced = self._slot.read().with_replaced(entity)
        if replaced.data is None:
            return DataResult.fail(replaced.validation)
        self._slot.write(replaced.data)
        return DataResult.ok(entity)

    @override
    def delete(self, entity_id: str) -> DataResult[E]:
        collection = self._slot.read()
        found = collection.get(entity_id)
        remaining = collection.without(entity_id)
        if found.data is None or remaining.data is None:
            return DataResult.fail(found.validation.merge(remaining.validation))
        self._slot.write(remaining.data)
        return DataResult.ok(found.data)

    @override
    def copy_business(self, entity_id: str, new_id: str, now: datetime) -> DataResult[E]:
        found = self._slot.read().get(entity_id)
        if found.data is None:
            return DataResult.fail(found.validation)
        return self.create(found.data.business_copy(new_id, now))

    @override
    def copy_technical(self, entity_id: str) -> DataResult[E]:
        found = self._slot.read().get(entity_id)
        if found.data is None:
            return DataResult.fail(found.validation)
        return DataResult.ok(copy.copy(found.data))
