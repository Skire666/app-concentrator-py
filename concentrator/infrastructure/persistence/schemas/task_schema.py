"""DTOs of one ``[[tasks]]`` element and of its history events."""

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


class TaskSchema(BaseModel):
    """``[[tasks]]``: field order is the order written in the file; unset optional values are not written."""

    model_config = PERSISTENCE_MODEL_CONFIG

    id: str
    created_at: UtcTimestamp
    updated_at: UtcTimestamp
    list_id: str
    text: tuple[str, ...]
    due_date: LocalDate | None = None
    due_time: LocalMinutes | None = None
    state: int
    completed_at: UtcTimestamp | None = None
    history: tuple[TaskEventSchema, ...] = ()
