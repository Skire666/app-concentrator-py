"""DTO of the whole user data file."""

from typing import Annotated

from pydantic import BaseModel, Field

from concentrator.infrastructure.persistence.schemas.hourly_chime_schema import HourlyChimeSchema
from concentrator.infrastructure.persistence.schemas.schema_types import PERSISTENCE_MODEL_CONFIG, UtcTimestamp
from concentrator.infrastructure.persistence.schemas.timer_config_schema import TimerConfigSchema
from concentrator.infrastructure.persistence.schemas.timer_preset_schema import TimerPresetSchema
from concentrator.infrastructure.persistence.schemas.user_settings_schema import UserSettingsSchema


class UserDataSchema(BaseModel):
    """Root object of the file: field order is the order written in the file.

    Later phases add their sections with defaults, so that older development files still load; an
    absent section is ``None`` and is not written. No favorite is written ``timer_presets = []``.
    """

    model_config = PERSISTENCE_MODEL_CONFIG

    schema_version: Annotated[int, Field(ge=1)]
    saved_at: UtcTimestamp
    app_version: str
    settings: UserSettingsSchema
    timer: TimerConfigSchema | None = None
    timer_presets: tuple[TimerPresetSchema, ...] | None = None
    hourly_chime: HourlyChimeSchema | None = None
