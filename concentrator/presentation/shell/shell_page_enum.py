"""Pages of the main window."""

from concentrator.domain.common.base_int_enum import BaseIntEnum


class ShellPageEnum(BaseIntEnum):
    """Menu A (Focus), menu B (Journal), menu C (Settings)."""

    UNKNOWN = -1
    UNSET = 0
    FOCUS = 1
    JOURNAL = 2
    SETTINGS = 3
