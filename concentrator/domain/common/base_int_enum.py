"""Base class of every enumeration of the application."""

from enum import IntEnum
from typing import Final, Self

UNKNOWN_VALUE: Final = -1
UNSET_VALUE: Final = 0


class BaseIntEnum(IntEnum):
    """Integer enumeration with forward-compatible parsing.

    Every subclass defines ``UNKNOWN = -1`` ("value not understood") and ``UNSET = 0`` ("not chosen
    yet"). Values are explicit and never renumbered or reused.
    """

    @classmethod
    def parse(cls, value: int) -> Self:
        """Convert an integer read from outside the application into a member.

        Args:
            value: Raw integer, for example read from the user data file.

        Returns:
            The matching member, or ``UNKNOWN`` when the value is not recognized.
        """
        try:
            return cls(value)
        except ValueError:
            return cls["UNKNOWN"]

    @property
    def is_set(self) -> bool:
        """Whether the member is a real value (neither ``UNKNOWN`` nor ``UNSET``)."""
        return self.value not in {UNKNOWN_VALUE, UNSET_VALUE}
