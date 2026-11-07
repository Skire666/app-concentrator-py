"""The nine data operations, with a test-only entity and collection."""

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Self, override

import pytest

from concentrator.application.common.event_bus import EventBus
from concentrator.application.storage.storage_events import UserDataChangedEvent
from concentrator.application.storage.user_data import UserData
from concentrator.domain.common.entity_collection import EntityCollection
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.infrastructure.persistence.store_collection import (
    CollectionSlot,
    StoreCollectionReader,
    StoreCollectionWriter,
    UserDataSlot,
)
from concentrator.infrastructure.persistence.user_data_store import UserDataStore
from tests.fakes.recording_error_reporter import RecordingErrorReporter
from tests.fakes.user_data_factory import make_user_data

NOW = datetime(2026, 11, 6, 9, 0, tzinfo=UTC)
LATER = NOW + timedelta(hours=1)


@dataclass(frozen=True, slots=True, kw_only=True)
class Note:
    id: str
    created_at: datetime = NOW
    updated_at: datetime = NOW
    text: str = ""
    history: tuple[str, ...] = ()

    def business_copy(self, new_id: str, now: datetime) -> Self:
        return replace(self, id=new_id, created_at=now, updated_at=now, history=(f"COPIED_FROM {self.id}",))


class NotesCollection(EntityCollection[Note]):
    pass


class MemorySlot(CollectionSlot[Note]):
    def __init__(self, collection: EntityCollection[Note]) -> None:
        self.collection = collection
        self.writes = 0

    @override
    def read(self) -> EntityCollection[Note]:
        return self.collection

    @override
    def write(self, collection: EntityCollection[Note]) -> None:
        self.writes += 1
        self.collection = collection


@dataclass(frozen=True, slots=True)
class TextQuery:
    word: str

    def matches(self, entity: Note) -> bool:
        return self.word in entity.text


@pytest.fixture
def slot() -> MemorySlot:
    return MemorySlot(NotesCollection([Note(id="a", text="buy milk"), Note(id="b", text="call bob", history=("x",))]))


def test_reader_exists_read_item_all_items_and_find(slot: MemorySlot) -> None:
    reader = StoreCollectionReader(slot)

    assert reader.exists("a").data is True
    assert reader.exists("z").data is False
    assert reader.read_item("b").data == Note(id="b", text="call bob", history=("x",))
    assert reader.read_item("z").validation.error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)
    assert reader.all_items().data is slot.collection
    found = reader.find(TextQuery("milk")).data
    assert isinstance(found, NotesCollection)
    assert [note.id for note in found] == ["a"]


def test_create_adds_and_refuses_a_duplicate(slot: MemorySlot) -> None:
    writer = StoreCollectionWriter(slot)

    created = writer.create(Note(id="c"))
    duplicate = writer.create(Note(id="a"))

    assert created.data == Note(id="c")
    assert isinstance(slot.collection, NotesCollection)
    assert [note.id for note in slot.collection] == ["a", "b", "c"]
    assert duplicate.validation.error_codes == (ErrorCodeEnum.ENTITY_DUPLICATE_ID,)
    assert slot.writes == 1


def test_update_replaces_and_refuses_an_unknown_id(slot: MemorySlot) -> None:
    writer = StoreCollectionWriter(slot)

    updated = writer.update(Note(id="a", text="buy bread"))
    unknown = writer.update(Note(id="z"))

    assert updated.data == Note(id="a", text="buy bread")
    assert slot.collection.get("a").data == Note(id="a", text="buy bread")
    assert unknown.validation.error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)
    assert slot.writes == 1


def test_delete_returns_the_removed_entity(slot: MemorySlot) -> None:
    writer = StoreCollectionWriter(slot)

    deleted = writer.delete("a")
    unknown = writer.delete("z")

    assert deleted.data == Note(id="a", text="buy milk")
    assert [note.id for note in slot.collection] == ["b"]
    assert ErrorCodeEnum.ENTITY_NOT_FOUND in unknown.validation.error_codes
    assert slot.writes == 1


def test_copy_business_stores_a_duplicate_with_a_new_identity(slot: MemorySlot) -> None:
    writer = StoreCollectionWriter(slot)

    copied = writer.copy_business("b", "c", LATER)

    assert copied.data == Note(id="c", created_at=LATER, updated_at=LATER, text="call bob", history=("COPIED_FROM b",))
    assert slot.collection.get("c").data == copied.data
    assert writer.copy_business("z", "d", LATER).validation.error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)
    assert writer.copy_business("a", "b", LATER).validation.error_codes == (ErrorCodeEnum.ENTITY_DUPLICATE_ID,)


def test_copy_technical_is_an_equal_clone_and_stores_nothing(slot: MemorySlot) -> None:
    writer = StoreCollectionWriter(slot)
    before = slot.collection

    clone = writer.copy_technical("b")

    original = before.get("b").data
    assert clone.data == original
    assert clone.data is not original
    assert slot.collection is before
    assert slot.writes == 0
    assert writer.copy_technical("z").validation.error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)


def test_user_data_slot_reads_and_applies_through_the_store() -> None:
    bus = EventBus(RecordingErrorReporter())
    events: list[UserDataChangedEvent] = []
    bus.subscribe(UserDataChangedEvent, events.append)
    store = UserDataStore(bus)
    store.reset(make_user_data())
    notes = NotesCollection([Note(id="a")])
    written: list[EntityCollection[Note]] = []

    def read(_data: UserData) -> EntityCollection[Note]:
        return notes

    def write(data: UserData, collection: EntityCollection[Note]) -> UserData:
        written.append(collection)
        return data.with_settings(replace(data.settings, updated_at=LATER))

    user_slot = UserDataSlot(store, read, write)

    StoreCollectionWriter(user_slot).create(Note(id="b"))

    assert [note.id for note in written[0]] == ["a", "b"]
    assert events == [UserDataChangedEvent(revision=2)]
    assert StoreCollectionReader(user_slot).all_items().data is notes
