"""DTO of one ``[[task_lists]]`` element."""

from pydantic import BaseModel

from concentrator.infrastructure.persistence.schemas.schema_types import PERSISTENCE_MODEL_CONFIG, UtcTimestamp


class TaskListSchema(BaseModel):
    """``[[task_lists]]``: field order is the order written in the file."""

    model_config = PERSISTENCE_MODEL_CONFIG

    id: str
    created_at: UtcTimestamp
    updated_at: UtcTimestamp
    name: str
    description: tuple[str, ...] = ()
    priority: int
    position: int
