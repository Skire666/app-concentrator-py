"""Writes the ``HourlyChime`` singleton."""

from typing import Protocol

from concentrator.domain.common.data_result import DataResult
from concentrator.domain.timer.hourly_chime import HourlyChime


class HourlyChimeWriterPort(Protocol):
    """Write side of the hourly chime."""

    def update(self, chime: HourlyChime) -> DataResult[HourlyChime]:
        """Replace the chime (in memory; the save follows through the save coordinator).

        Args:
            chime: Validated chime with the id of the current one.

        Returns:
            The stored chime, or ``ENTITY_NOT_FOUND`` when the id differs.
        """
        ...
