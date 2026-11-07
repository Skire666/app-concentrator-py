"""Why the startup reached its step: one member per row of the ADR-027 matrix."""

from concentrator.domain.common.base_int_enum import BaseIntEnum


class StartupReasonEnum(BaseIntEnum):
    """Situation of the data file and of its side files."""

    UNKNOWN = -1
    UNSET = 0
    OPENED = 1
    FIRST_RUN = 2
    FILE_NOT_FOUND = 3
    NEWER_TEMPORARY = 4
    FILE_DAMAGED = 5
    FILE_MISSING = 6
    FILE_UNREADABLE = 7
    NEWER_VERSION = 8
