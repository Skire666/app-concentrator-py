"""DTO of the ``[hourly_chime]`` section."""

from pydantic import BaseModel

from concentrator.infrastructure.persistence.schemas.schema_types import PERSISTENCE_MODEL_CONFIG, UtcTimestamp
from concentrator.infrastructure.persistence.schemas.timer_config_schema import SoundRefSchema


class HourlyChimeSchema(BaseModel):
    """``[hourly_chime]``: field order is the order written in the file."""

    model_config = PERSISTENCE_MODEL_CONFIG

    id: str
    created_at: UtcTimestamp
    updated_at: UtcTimestamp
    enabled: bool
    sound: SoundRefSchema
    volume: int
    start_hour: int
    end_hour: int
