"""Kinds of the events kept in the history of a task."""

from concentrator.domain.common.base_int_enum import BaseIntEnum


class TaskEventKindEnum(BaseIntEnum):
    """What happened to a task. Phases 6 and 7 append values; values are never reused."""

    UNKNOWN = -1
    UNSET = 0
    CREATED = 1
    TEXT_EDITED = 2
    DUE_CHANGED = 3
    COMPLETED = 4
    REOPENED = 5
    ARCHIVED = 6
    UNARCHIVED = 7
    MOVED = 8
    COPIED_FROM = 9
    OCCURRENCE_COMPLETED = 10
    RECURRENCE_CHANGED = 11
    ADDED_TO_FOCUS = 12
    REMOVED_FROM_FOCUS = 13
