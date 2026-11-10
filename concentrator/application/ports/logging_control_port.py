"""Changes the detail level of the application log at run time."""

from typing import Protocol

from concentrator.domain.settings.log_level_enum import LogLevelEnum


class LoggingControlPort(Protocol):
    """Level of the root logger: records below it reach neither the log file nor the journal."""

    def set_level(self, level: LogLevelEnum) -> None:
        """Apply a detail level at once.

        Args:
            level: New level; ``UNKNOWN`` and ``UNSET`` are ignored (logged at WARNING).
        """
        ...
