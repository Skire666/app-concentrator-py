"""``LoggingControlPort`` on the root logger."""

import logging
from typing import override

from concentrator.application.journal.log_levels import python_level_of
from concentrator.application.ports.logging_control_port import LoggingControlPort
from concentrator.domain.settings.log_level_enum import LogLevelEnum

_logger = logging.getLogger(__name__)


class LoggingControl(LoggingControlPort):
    """Sets the level of the root logger (the handlers have no level of their own)."""

    def __init__(self, root: logging.Logger | None = None) -> None:
        """Create the control.

        Args:
            root: Logger to drive; the root logger by default.
        """
        self._root = root or logging.getLogger()

    @override
    def set_level(self, level: LogLevelEnum) -> None:
        python_level = python_level_of(level)
        if python_level is None:
            _logger.warning("Log level %s ignored: not a real level", level.name)
            return
        if self._root.level == python_level:
            return
        self._root.setLevel(python_level)
        _logger.info("Log level set to %s", logging.getLevelName(python_level))
