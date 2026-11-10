"""Detail level of the application log."""

from concentrator.domain.common.base_int_enum import BaseIntEnum


class LogLevelEnum(BaseIntEnum):
    """Lowest severity of the records kept by the log, from the most to the least detailed."""

    UNKNOWN = -1
    UNSET = 0
    DEBUG = 1
    INFO = 2
    WARNING = 3
    ERROR = 4
    CRITICAL = 5
