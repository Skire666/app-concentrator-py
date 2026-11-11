"""Kinds of the links detected in the text of a task."""

from concentrator.domain.common.base_int_enum import BaseIntEnum


class LinkKindEnum(BaseIntEnum):
    """What a ``LinkTarget`` points at."""

    UNKNOWN = -1
    UNSET = 0
    URL = 1
    LOCAL_PATH = 2
    UNC_PATH = 3
