"""State of the user data file shown in the status bar."""

from concentrator.domain.common.base_int_enum import BaseIntEnum


class SaveStateEnum(BaseIntEnum):
    """Where the in-memory data stands compared with the file."""

    UNKNOWN = -1
    UNSET = 0
    NO_FILE = 1
    SAVED = 2
    PENDING = 3
    SAVING = 4
    FAILED = 5
