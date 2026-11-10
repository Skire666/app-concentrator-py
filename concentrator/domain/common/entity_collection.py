"""Immutable group of entities indexed by id: base class of every ``*Collection``."""

from collections.abc import Callable, Collection, Iterable, Iterator
from typing import TYPE_CHECKING, Final, Self, override

from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.identified import Identified
from concentrator.domain.common.validation_result import ValidationResult

if TYPE_CHECKING:
    from _typeshed import SupportsRichComparison

ID_FIELD: Final = "id"
_DUPLICATE_ID: Final = "duplicate entity id in a collection"


class EntityCollection[E: Identified]:
    """Tuple of entities plus an id index. Every change returns a new collection.

    Feature collections subclass it, keep the ``(items)`` constructor and add their group-level
    business logic (ordering, uniqueness, "next position").
    """

    __slots__ = ("_index", "_items")

    def __init__(self, items: Iterable[E] = ()) -> None:
        """Wrap trusted entities (use ``from_items`` for data read from outside).

        Args:
            items: Entities, in order.

        Raises:
            ValueError: If two entities share an id (programming error).
        """
        self._items: tuple[E, ...] = tuple(items)
        self._index: dict[str, int] = {item.id: position for position, item in enumerate(self._items)}
        if len(self._index) != len(self._items):
            raise ValueError(_DUPLICATE_ID)

    @classmethod
    def from_items(cls, items: Iterable[E], field_prefix: str = "") -> DataResult[Self]:
        """Build a collection from untrusted entities.

        Args:
            items: Entities, in order.
            field_prefix: Dotted path of the collection, used in the issue fields.

        Returns:
            The collection, or one ``ENTITY_DUPLICATE_ID`` issue per repeated id
            (field ``<prefix>.<position>.id``).
        """
        entities = tuple(items)
        seen: set[str] = set()
        issues: list[ValidationResult] = []
        for position, entity in enumerate(entities):
            if entity.id in seen:
                field = ".".join(part for part in (field_prefix, str(position), ID_FIELD) if part)
                issues.append(ValidationResult.failure(ErrorCodeEnum.ENTITY_DUPLICATE_ID, field=field))
            seen.add(entity.id)
        if issues:
            return DataResult.fail(issues[0].merge(*issues[1:]))
        return DataResult.ok(cls(entities))

    @property
    def items(self) -> tuple[E, ...]:
        """The entities, in order."""
        return self._items

    def get(self, entity_id: str) -> DataResult[E]:
        """Find an entity.

        Args:
            entity_id: Id to look for.

        Returns:
            The entity, or ``ENTITY_NOT_FOUND``.
        """
        position = self._index.get(entity_id)
        if position is None:
            return DataResult.fail(ValidationResult.failure(ErrorCodeEnum.ENTITY_NOT_FOUND, field=ID_FIELD))
        return DataResult.ok(self._items[position])

    def contains(self, entity_id: str) -> bool:
        """Tell whether an entity with this id exists.

        Args:
            entity_id: Id to look for.

        Returns:
            Whether it exists.
        """
        return entity_id in self._index

    def with_added(self, entity: E) -> DataResult[Self]:
        """Append an entity.

        Args:
            entity: New entity.

        Returns:
            The new collection, or ``ENTITY_DUPLICATE_ID``.
        """
        if self.contains(entity.id):
            return DataResult.fail(ValidationResult.failure(ErrorCodeEnum.ENTITY_DUPLICATE_ID, field=ID_FIELD))
        return DataResult.ok(self._with_items((*self._items, entity)))

    def with_replaced(self, entity: E) -> DataResult[Self]:
        """Replace the entity with the same id, keeping its position.

        Args:
            entity: New version of the entity.

        Returns:
            The new collection, or ``ENTITY_NOT_FOUND``.
        """
        position = self._index.get(entity.id)
        if position is None:
            return DataResult.fail(ValidationResult.failure(ErrorCodeEnum.ENTITY_NOT_FOUND, field=ID_FIELD))
        items = (*self._items[:position], entity, *self._items[position + 1 :])
        return DataResult.ok(self._with_items(items))

    def without(self, entity_id: str) -> DataResult[Self]:
        """Remove an entity.

        Args:
            entity_id: Id of the entity to remove.

        Returns:
            The new collection, or ``ENTITY_NOT_FOUND``.
        """
        position = self._index.get(entity_id)
        if position is None:
            return DataResult.fail(ValidationResult.failure(ErrorCodeEnum.ENTITY_NOT_FOUND, field=ID_FIELD))
        return DataResult.ok(self._with_items((*self._items[:position], *self._items[position + 1 :])))

    def with_replaced_all(self, entities: Iterable[E]) -> DataResult[Self]:
        """Replace several entities at once, all or nothing, keeping their positions.

        Args:
            entities: New versions of existing entities.

        Returns:
            The new collection, or ``ENTITY_NOT_FOUND`` when one of them does not exist (nothing changed).
        """
        changes = {entity.id: entity for entity in entities}
        if any(not self.contains(entity_id) for entity_id in changes):
            return DataResult.fail(ValidationResult.failure(ErrorCodeEnum.ENTITY_NOT_FOUND, field=ID_FIELD))
        return DataResult.ok(self._with_items(changes.get(item.id, item) for item in self._items))

    def without_all(self, entity_ids: Collection[str]) -> DataResult[Self]:
        """Remove several entities at once, all or nothing.

        Args:
            entity_ids: Ids of the entities to remove.

        Returns:
            The new collection, or ``ENTITY_NOT_FOUND`` when one of them does not exist (nothing changed).
        """
        if any(not self.contains(entity_id) for entity_id in entity_ids):
            return DataResult.fail(ValidationResult.failure(ErrorCodeEnum.ENTITY_NOT_FOUND, field=ID_FIELD))
        removed = set(entity_ids)
        return DataResult.ok(self._with_items(item for item in self._items if item.id not in removed))

    def filtered(self, predicate: Callable[[E], bool]) -> Self:
        """Keep the entities matching a predicate, in order.

        Args:
            predicate: Selection test.

        Returns:
            The matching entities.
        """
        return self._with_items(item for item in self._items if predicate(item))

    def sorted_by(self, key: Callable[[E], SupportsRichComparison], *, reverse: bool = False) -> Self:
        """Sort the entities (stable).

        Args:
            key: Sort key of an entity.
            reverse: Descending order.

        Returns:
            The sorted collection.
        """
        return self._with_items(sorted(self._items, key=key, reverse=reverse))

    def _with_items(self, items: Iterable[E]) -> Self:
        """Build a collection of the same class.

        Args:
            items: Entities, in order.

        Returns:
            The new collection.
        """
        return type(self)(items)

    def __len__(self) -> int:
        """Number of entities.

        Returns:
            The count.
        """
        return len(self._items)

    def __iter__(self) -> Iterator[E]:
        """Iterate over the entities in order.

        Returns:
            The iterator.
        """
        return iter(self._items)

    @override
    def __eq__(self, other: object) -> bool:
        return type(other) is type(self) and other.items == self._items

    @override
    def __hash__(self) -> int:
        return hash(self._items)

    @override
    def __repr__(self) -> str:
        return f"{type(self).__name__}({len(self._items)} items)"
