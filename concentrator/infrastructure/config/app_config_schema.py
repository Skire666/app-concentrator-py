"""Pydantic DTO of ``concentrator.ini``. Never leaves ``infrastructure.config``.

Validated with ``model_validate_strings`` so that ``strict=True`` stays meaningful for ini text:
``"100"`` is an int, ``"1.5"`` is not.
"""

from typing import Annotated, Final, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

_STRICT: Final = ConfigDict(strict=True, extra="forbid", frozen=True)
_MIN_WINDOW_ABOVE_DEFAULT: Final = "min_window size must not exceed default_window size"

type Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
type FileName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, pattern=r"^[^/\\:*?\"<>|]+$")]
type InstanceKey = Annotated[str, StringConstraints(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")]
type WindowSide = Annotated[int, Field(ge=320, le=10_000)]
type LanguageCode = Literal["en", "fr"]
type LevelName = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class AppSectionSchema(BaseModel):
    """``[app]``."""

    model_config = _STRICT

    name: Text
    organization: Text
    app_user_model_id: Annotated[Text, StringConstraints(max_length=128)]
    single_instance_key: InstanceKey
    single_instance_timeout_ms: Annotated[int, Field(ge=100, le=10_000)]


class PathsSectionSchema(BaseModel):
    """``[paths]``: raw templates, tokens resolved by the loader."""

    model_config = _STRICT

    default_data_file: Text
    ui_state_file: Text
    log_dir: Text
    backup_dir: Text


class UiSectionSchema(BaseModel):
    """``[ui]``."""

    model_config = _STRICT

    module_bar_width_px: Annotated[int, Field(ge=40, le=400)]
    zone1_ratio_percent: Annotated[int, Field(ge=30, le=90)]
    default_window_width_px: WindowSide
    default_window_height_px: WindowSide
    min_window_width_px: WindowSide
    min_window_height_px: WindowSide
    action_cooldown_ms: Annotated[int, Field(ge=100, le=5_000)]
    slow_action_threshold_ms: Annotated[int, Field(ge=1, le=60_000)]

    @model_validator(mode="after")
    def _check_min_window(self) -> Self:
        if self.min_window_width_px > self.default_window_width_px:
            raise ValueError(_MIN_WINDOW_ABOVE_DEFAULT)
        if self.min_window_height_px > self.default_window_height_px:
            raise ValueError(_MIN_WINDOW_ABOVE_DEFAULT)
        return self


class TimerSectionSchema(BaseModel):
    """``[timer]``."""

    model_config = _STRICT

    tick_interval_ms: Annotated[int, Field(ge=10, le=1_000)]


class LoggingSectionSchema(BaseModel):
    """``[logging]``."""

    model_config = _STRICT

    level: LevelName
    file_name: FileName
    file_max_bytes: Annotated[int, Field(ge=10_000, le=1_000_000_000)]
    file_backup_count: Annotated[int, Field(ge=0, le=100)]
    journal_buffer_size: Annotated[int, Field(ge=100, le=100_000)]


class I18nSectionSchema(BaseModel):
    """``[i18n]``."""

    model_config = _STRICT

    default_language: LanguageCode
    fallback_language: LanguageCode


class AppConfigSchema(BaseModel):
    """The whole ini: every section and key is required."""

    model_config = _STRICT

    app: AppSectionSchema
    paths: PathsSectionSchema
    ui: UiSectionSchema
    timer: TimerSectionSchema
    logging: LoggingSectionSchema
    i18n: I18nSectionSchema
