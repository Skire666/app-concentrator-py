"""Writes the ``TimerConfig`` singleton."""

from typing import Protocol

from concentrator.domain.common.data_result import DataResult
from concentrator.domain.timer.timer_config import TimerConfig


class TimerConfigWriterPort(Protocol):
    """Write side of the timer configuration."""

    def update(self, config: TimerConfig) -> DataResult[TimerConfig]:
        """Replace the configuration (in memory; the save follows through the save coordinator).

        Args:
            config: Validated configuration with the id of the current one.

        Returns:
            The stored configuration, or ``ENTITY_NOT_FOUND`` when the id differs.
        """
        ...
