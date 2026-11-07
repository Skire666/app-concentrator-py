from dataclasses import dataclass, replace
from datetime import UTC, datetime

import pytest

from concentrator.domain.common.entity_collection import EntityCollection
from concentrator.domain.common.error_code_enum import ErrorCodeEnum

NOW = datetime(2026, 11, 6, 9, 0, tzinfo=UTC)


@dataclass(frozen=True, slots=True, kw_only=True)
class Item:
    id: str
    created_at: datetime = NOW
    updated_at: datetime = NOW
    rank: int = 0


class ItemsCollection(EntityCollection[Item]):
    pass


def _items(*ids: str) -> ItemsCollection:
    return ItemsCollection(Item(id=item_id, rank=position) for position, item_id in enumerate(ids))


def test_constructor_rejects_duplicate_ids() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        ItemsCollection([Item(id="a"), Item(id="a")])


def test_from_items_reports_each_duplicate_with_its_field() -> None:
    result = ItemsCollection.from_items([Item(id="a"), Item(id="b"), Item(id="a"), Item(id="b")], "items")

    assert result.data is None
    assert result.validation.error_codes == (ErrorCodeEnum.ENTITY_DUPLICATE_ID,) * 2
    assert [issue.field for issue in result.validation.issues] == ["items.2.id", "items.3.id"]


def test_from_items_without_prefix_and_without_duplicates() -> None:
    duplicate = ItemsCollection.from_items([Item(id="a"), Item(id="a")])
    valid = ItemsCollection.from_items([Item(id="a"), Item(id="b")])

    assert duplicate.validation.issues[0].field == "1.id"
    assert isinstance(valid.data, ItemsCollection)
    assert [item.id for item in valid.data] == ["a", "b"]


def test_get_and_contains() -> None:
    collection = _items("a", "b")

    assert collection.get("b").data == Item(id="b", rank=1)
    assert collection.contains("a")
    assert not collection.contains("z")
    assert collection.get("z").validation.error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)


def test_with_added_appends_and_rejects_duplicate() -> None:
    collection = _items("a")

    added = collection.with_added(Item(id="b"))
    duplicate = collection.with_added(Item(id="a"))

    assert [item.id for item in added.value_or(collection)] == ["a", "b"]
    assert duplicate.validation.error_codes == (ErrorCodeEnum.ENTITY_DUPLICATE_ID,)
    assert len(collection) == 1


def test_with_replaced_keeps_position_and_rejects_unknown_id() -> None:
    collection = _items("a", "b", "c")
    changed = replace(collection.get("b").value_or(Item(id="?")), rank=9)

    replaced = collection.with_replaced(changed).value_or(collection)
    unknown = collection.with_replaced(Item(id="z"))

    assert [(item.id, item.rank) for item in replaced] == [("a", 0), ("b", 9), ("c", 2)]
    assert unknown.validation.error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)


def test_without_removes_and_rejects_unknown_id() -> None:
    collection = _items("a", "b", "c")

    removed = collection.without("b").value_or(collection)

    assert [item.id for item in removed] == ["a", "c"]
    assert not removed.contains("b")
    assert removed.get("c").data == Item(id="c", rank=2)
    assert collection.without("z").validation.error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)


def test_filtered_and_sorted_by_keep_the_collection_class() -> None:
    collection = _items("a", "b", "c", "d")

    even = collection.filtered(lambda item: item.rank % 2 == 0)
    descending = collection.sorted_by(lambda item: item.rank, reverse=True)

    assert isinstance(even, ItemsCollection)
    assert [item.id for item in even] == ["a", "c"]
    assert [item.id for item in descending] == ["d", "c", "b", "a"]
    assert [item.id for item in collection.sorted_by(lambda item: item.id)] == ["a", "b", "c", "d"]


def test_equality_hash_and_repr() -> None:
    assert _items("a", "b") == _items("a", "b")
    assert _items("a", "b") != _items("b", "a")
    assert _items("a") != EntityCollection([Item(id="a")])
    assert _items("a") != ("a",)
    assert hash(_items("a")) == hash(_items("a"))
    assert repr(_items("a", "b")) == "ItemsCollection(2 items)"
    assert _items("a").items == (Item(id="a"),)
    assert len(ItemsCollection()) == 0
