"""DTO of the whole user data file."""

from typing import Annotated

from pydantic import BaseModel, Field

from concentrator.infrastructure.persistence.schemas.schema_types import PERSISTENCE_MODEL_CONFIG, UtcTimestamp
from concentrator.infrastructure.persistence.schemas.user_settings_schema import UserSettingsSchema


class UserDataSchema(BaseModel):
    """Root object of the file: field order is the order written in the file.

    Later phases add their sections with defaults, so that older development files still load.
    """

    model_config = PERSISTENCE_MODEL_CONFIG

    schema_version: Annotated[int, Field(ge=1)]
    saved_at: UtcTimestamp
    app_version: str
    settings: UserSettingsSchema
