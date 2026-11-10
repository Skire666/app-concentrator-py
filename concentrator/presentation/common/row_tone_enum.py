"""Emphasis of a table row (the ui picks the colors)."""

from concentrator.domain.common.base_int_enum import BaseIntEnum


class RowToneEnum(BaseIntEnum):
    """How a row stands out."""

    UNKNOWN = -1
    UNSET = 0
    NORMAL = 1
    MUTED = 2
    WARNING = 3
    ERROR = 4
