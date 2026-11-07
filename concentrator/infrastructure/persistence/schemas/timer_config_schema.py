"""DTO of the ``[timer]`` section."""

from pydantic import BaseModel

from concentrator.infrastructure.persistence.schemas.schema_types import PERSISTENCE_MODEL_CONFIG, UtcTimestamp


class SoundRefSchema(BaseModel):
    """``sound = { kind = 2, value = '...' }``: a built-in sound name or a file path."""

    model_config = PERSISTENCE_MODEL_CONFIG

    kind: int
    value: str


class TimerConfigSchema(BaseModel):
    """``[timer]``: field order is the order written in the file."""

    model_config = PERSISTENCE_MODEL_CONFIG

    id: str
    created_at: UtcTimestamp
    updated_at: UtcTimestamp
    duration_seconds: int
    sound: SoundRefSchema
    volume: int
    loop_count: int
    loop_forever: bool
    auto_stop_seconds: int
    auto_restart: bool
