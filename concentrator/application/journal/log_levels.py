"""Conversion between ``LogLevelEnum`` and the numeric levels of the ``logging`` module."""

import logging
from types import MappingProxyType
from typing import Final

from concentrator.domain.settings.log_level_enum import LogLevelEnum

_PYTHON_LEVELS: Final = MappingProxyType(
    {
        LogLevelEnum.DEBUG: logging.DEBUG,
        LogLevelEnum.INFO: logging.INFO,
        LogLevelEnum.WARNING: logging.WARNING,
        LogLevelEnum.ERROR: logging.ERROR,
        LogLevelEnum.CRITICAL: logging.CRITICAL,
    }
)


def python_level_of(level: LogLevelEnum) -> int | None:
    """Return the ``logging`` level of a member.

    Args:
        level: Member to convert.

    Returns:
        ``logging.DEBUG`` ... ``logging.CRITICAL``, ``None`` for ``UNKNOWN`` and ``UNSET``.
    """
    return _PYTHON_LEVELS.get(level)


def log_level_of(python_level: int) -> LogLevelEnum:
    """Return the member of a record level; a custom level counts as the standard level below it.

    Args:
        python_level: ``LogRecord.levelno``.

    Returns:
        The member; a level below ``DEBUG`` is ``DEBUG``.
    """
    found = LogLevelEnum.DEBUG
    for level, value in _PYTHON_LEVELS.items():
        if python_level >= value:
            found = level
    return found
