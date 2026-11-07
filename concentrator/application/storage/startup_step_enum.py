"""What the startup has to do before the main window can open (ADR-027)."""

from concentrator.domain.common.base_int_enum import BaseIntEnum


class StartupStepEnum(BaseIntEnum):
    """Outcome of the data file resolution."""

    UNKNOWN = -1
    UNSET = 0
    READY = 1
    NEEDS_LOCATION = 2
    NEEDS_RECOVERY = 3
    FATAL = 4
