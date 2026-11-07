"""DTO of the ``settings`` section."""

from pydantic import BaseModel

from concentrator.infrastructure.persistence.schemas.schema_types import PERSISTENCE_MODEL_CONFIG, UtcTimestamp


class UserSettingsSchema(BaseModel):
    """``settings``: field order is the order written in the file."""

    model_config = PERSISTENCE_MODEL_CONFIG

    id: str
    created_at: UtcTimestamp
    updated_at: UtcTimestamp
    language: int
