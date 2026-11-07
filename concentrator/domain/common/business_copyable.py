"""Protocol of the entities that support a business copy (duplicate with a new identity)."""

from datetime import datetime
from typing import Protocol, Self

from concentrator.domain.common.identified import Identified


class BusinessCopyable(Identified, Protocol):
    """An entity that can be duplicated with a new identity (ADR-012)."""

    def business_copy(self, new_id: str, now: datetime) -> Self:
        """Return a duplicate with a new id and new timestamps; history restarts with ``COPIED_FROM``.

        Args:
            new_id: Id of the duplicate.
            now: Creation instant of the duplicate (timezone-aware UTC).

        Returns:
            The duplicate.
        """
        ...
