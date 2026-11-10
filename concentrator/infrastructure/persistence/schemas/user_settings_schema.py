"""DTO of the ``settings`` section."""

from pydantic import BaseModel

from concentrator.infrastructure.persistence.schemas.schema_types import PERSISTENCE_MODEL_CONFIG, UtcTimestamp


class UserSettingsSchema(BaseModel):
    """``settings``: field order is the order written in the file.

    ``log_level`` and ``notify_when_inactive`` came with phase 4: a file without them takes the
    ``[settings]`` defaults of the ini, and they are written at the next save.
    """

    model_config = PERSISTENCE_MODEL_CONFIG

    id: str
    created_at: UtcTimestamp
    updated_at: UtcTimestamp
    language: int
    log_level: int | None = None
    notify_when_inactive: bool | None = None
