"""DTO of one ``[[timer_presets]]`` element."""

from pydantic import BaseModel

from concentrator.infrastructure.persistence.schemas.schema_types import PERSISTENCE_MODEL_CONFIG, UtcTimestamp


class TimerPresetSchema(BaseModel):
    """``[[timer_presets]]``: field order is the order written in the file."""

    model_config = PERSISTENCE_MODEL_CONFIG

    id: str
    created_at: UtcTimestamp
    updated_at: UtcTimestamp
    label: str
    duration_seconds: int
    position: int
