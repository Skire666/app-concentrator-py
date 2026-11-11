"""DTO of one ``[[focus_queue]]`` element."""

from pydantic import BaseModel

from concentrator.infrastructure.persistence.schemas.schema_types import PERSISTENCE_MODEL_CONFIG, UtcTimestamp


class FocusItemSchema(BaseModel):
    """``[[focus_queue]]``: field order is the order written in the file."""

    model_config = PERSISTENCE_MODEL_CONFIG

    id: str
    created_at: UtcTimestamp
    updated_at: UtcTimestamp
    task_id: str
    position: int
