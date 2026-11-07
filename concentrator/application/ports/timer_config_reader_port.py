"""Reads the ``TimerConfig`` singleton."""

from typing import Protocol

from concentrator.domain.common.data_result import DataResult
from concentrator.domain.timer.timer_config import TimerConfig


class TimerConfigReaderPort(Protocol):
    """Read side of the timer configuration."""

    def read(self) -> DataResult[TimerConfig]:
        """Return the timer configuration of the open data file.

        Returns:
            The configuration, or ``ENTITY_NOT_FOUND`` before the file was completed (never after startup).
        """
        ...
