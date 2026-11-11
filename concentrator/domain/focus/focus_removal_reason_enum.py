"""Why a task left the focus queue (detail of a ``REMOVED_FROM_FOCUS`` history event)."""

from concentrator.domain.common.base_int_enum import BaseIntEnum


class FocusRemovalReasonEnum(BaseIntEnum):
    """Reason of a removal from the focus queue. Values are never reused."""

    UNKNOWN = -1
    UNSET = 0
    BY_USER = 1
    COMPLETED = 2
    OCCURRENCE_COMPLETED = 3
    ARCHIVED = 4
