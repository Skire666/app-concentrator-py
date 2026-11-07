"""Generic write side of an entity collection (``AGENTS.md`` section 6.2, ADR-012)."""

from datetime import datetime
from typing import Protocol

from concentrator.domain.common.business_copyable import BusinessCopyable
from concentrator.domain.common.data_result import DataResult


class EntityWriterPort[E: BusinessCopyable](Protocol):
    """Changes one aggregate's collection in memory; the save follows through the save coordinator."""

    def create(self, entity: E) -> DataResult[E]:
        """Add an entity.

        Args:
            entity: Validated new entity.

        Returns:
            The stored entity, or ``ENTITY_DUPLICATE_ID``.
        """
        ...

    def update(self, entity: E) -> DataResult[E]:
        """Replace the entity with the same id.

        Args:
            entity: Validated new version.

        Returns:
            The stored entity, or ``ENTITY_NOT_FOUND``.
        """
        ...

    def delete(self, entity_id: str) -> DataResult[E]:
        """Remove an entity.

        Args:
            entity_id: Id of the entity.

        Returns:
            The removed entity, or ``ENTITY_NOT_FOUND``.
        """
        ...

    def copy_business(self, entity_id: str, new_id: str, now: datetime) -> DataResult[E]:
        """Store a duplicate with a new identity (new id, new timestamps, history restarted).

        Args:
            entity_id: Entity to duplicate.
            new_id: Id of the duplicate.
            now: Creation instant of the duplicate.

        Returns:
            The stored duplicate, ``ENTITY_NOT_FOUND`` or ``ENTITY_DUPLICATE_ID``.
        """
        ...

    def copy_technical(self, entity_id: str) -> DataResult[E]:
        """Return an exact clone (same id, timestamps, history) without storing it.

        Args:
            entity_id: Entity to clone.

        Returns:
            The clone, or ``ENTITY_NOT_FOUND``.
        """
        ...
