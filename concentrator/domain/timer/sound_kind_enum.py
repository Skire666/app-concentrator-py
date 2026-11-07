"""Where a sound comes from."""

from concentrator.domain.common.base_int_enum import BaseIntEnum


class SoundKindEnum(BaseIntEnum):
    """Built-in sound shipped with the application, or an audio file chosen by the user."""

    UNKNOWN = -1
    UNSET = 0
    BUILTIN = 1
    FILE = 2
