"""State of one file inspected at startup (main file, ``.tmp`` or ``.bak``)."""

from concentrator.domain.common.base_int_enum import BaseIntEnum


class FileStateEnum(BaseIntEnum):
    """Whether a file exists and loads."""

    UNKNOWN = -1
    UNSET = 0
    ABSENT = 1
    VALID = 2
    INVALID = 3
