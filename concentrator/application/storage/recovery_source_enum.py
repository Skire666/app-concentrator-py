"""Which side file a recovery restores from."""

from concentrator.domain.common.base_int_enum import BaseIntEnum


class RecoverySourceEnum(BaseIntEnum):
    """Recovery candidates next to the data file."""

    UNKNOWN = -1
    UNSET = 0
    TEMPORARY = 1
    BACKUP = 2
