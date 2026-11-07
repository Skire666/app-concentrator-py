"""Generic read side of an entity collection (``AGENTS.md`` section 6.2)."""

from typing import Protocol

from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.entity_collection import EntityCollection
from concentrator.domain.common.identified import Identified


class EntityQueryPort[E](Protocol):
    """A ``find`` query: a frozen dataclass that tells which entities match."""

    def matches(self, entity: E) -> bool:
        """Tell whether an entity matches.

        Args:
            entity: Candidate.

        Returns:
            Whether it is part of the result.
        """
        ...


class EntityReaderPort[E: Identified](Protocol):
    """Reads one aggregate's collection. Aggregate ports narrow the collection type."""

    def exists(self, entity_id: str) -> DataResult[bool]:
        """Tell whether an entity exists.

        Args:
            entity_id: Id to look for.

        Returns:
            Whether it exists.
        """
        ...

    def read_item(self, entity_id: str) -> DataResult[E]:
        """Return one entity.

        Args:
            entity_id: Id to look for.

        Returns:
            The entity, or ``ENTITY_NOT_FOUND``.
        """
        ...

    def all_items(self) -> DataResult[EntityCollection[E]]:
        """Return the whole collection.

        Returns:
            The collection.
        """
        ...

    def find(self, query: EntityQueryPort[E]) -> DataResult[EntityCollection[E]]:
        """Return the entities matching a query, in collection order.

        Args:
            query: Selection.

        Returns:
            The matching entities.
        """
        ...
