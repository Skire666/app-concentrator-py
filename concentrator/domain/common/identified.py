"""Protocol shared by every entity."""

from datetime import datetime
from typing import Protocol


class Identified(Protocol):
    """An entity: a stable id and timezone-aware UTC creation and update timestamps.

    Members are read-only properties so that frozen dataclasses satisfy the protocol.
    """

    @property
    def id(self) -> str:
        """UUIDv7 string identifying the entity."""
        ...

    @property
    def created_at(self) -> datetime:
        """Creation instant, timezone-aware UTC."""
        ...

    @property
    def updated_at(self) -> datetime:
        """Last change instant, timezone-aware UTC."""
        ...
