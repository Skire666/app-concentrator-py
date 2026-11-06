"""Source of entity ids."""

from typing import Protocol


class IdGeneratorPort(Protocol):
    """Produces new, unique, time-ordered entity ids."""

    def new_id(self) -> str:
        """Return a new id.

        Returns:
            A UUIDv7 string.
        """
        ...
