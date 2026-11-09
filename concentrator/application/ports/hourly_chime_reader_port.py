"""Reads the ``HourlyChime`` singleton."""

from typing import Protocol

from concentrator.domain.common.data_result import DataResult
from concentrator.domain.timer.hourly_chime import HourlyChime


class HourlyChimeReaderPort(Protocol):
    """Read side of the hourly chime."""

    def read(self) -> DataResult[HourlyChime]:
        """Return the hourly chime of the open data file.

        Returns:
            The chime, or ``ENTITY_NOT_FOUND`` before the file was completed (never after startup).
        """
        ...
