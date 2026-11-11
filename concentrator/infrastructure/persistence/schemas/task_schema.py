"""DTOs of one ``[[tasks]]`` element, of its recurrence and of its history events."""

from typing import Annotated

from pydantic import BaseModel, Field

from concentrator.infrastructure.persistence.schemas.schema_types import (
    PERSISTENCE_MODEL_CONFIG,
    LocalDate,
    LocalMinutes,
    UtcTimestamp,
)


class TaskEventSchema(BaseModel):
    """``{ at = '...', kind = 1, details = {} }``: one history event, written inline."""

    model_config = PERSISTENCE_MODEL_CONFIG

    at: UtcTimestamp
    kind: int
    details: dict[str, str] = Field(default_factory=dict)


class RecurrenceSchema(BaseModel):
    """``recurrence = { frequency = 2, interval = 1, ... }``: written inline; unset end values are absent."""

    model_config = PERSISTENCE_MODEL_CONFIG

    frequency: int
    interval: int
    weekdays: tuple[int, ...] = ()
    anchor_date: LocalDate
    end_kind: int
    end_date: LocalDate | None = None
    end_count: int | None = None


class TaskSchema(BaseModel):
    """``[[tasks]]``: field order is the order written in the file; unset optional values are not written.

    ``recurrence`` and ``occurrences_done`` came with phase 6: a file written before has neither, and a one-off
    task that never completed an occurrence does not write them.
    """

    model_config = PERSISTENCE_MODEL_CONFIG

    id: str
    created_at: UtcTimestamp
    updated_at: UtcTimestamp
    list_id: str
    text: tuple[str, ...]
    due_date: LocalDate | None = None
    due_time: LocalMinutes | None = None
    recurrence: RecurrenceSchema | None = None
    occurrences_done: Annotated[int, Field(ge=0)] | None = None
    state: int
    completed_at: UtcTimestamp | None = None
    history: tuple[TaskEventSchema, ...] = ()
