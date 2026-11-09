"""Pydantic DTO of ``concentrator.ini``. Never leaves ``infrastructure.config``.

Validated with ``model_validate_strings`` so that ``strict=True`` stays meaningful for ini text:
``"100"`` is an int, ``"1.5"`` is not.
"""

from typing import Annotated, Final, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

_STRICT: Final = ConfigDict(strict=True, extra="forbid", frozen=True)
_MIN_WINDOW_ABOVE_DEFAULT: Final = "min_window size must not exceed default_window size"
_MAX_DELAY_BELOW_DEBOUNCE: Final = "save_max_delay_ms must not be lower than save_debounce_ms"
_DURATION_ORDER: Final = "min_duration_seconds <= default_duration_seconds <= max_duration_seconds is required"
_LOOP_COUNT_ABOVE_MAX: Final = "default_loop_count must not exceed max_loop_count"
_AUTO_STOP_ORDER: Final = "min_auto_stop_seconds must not exceed max_auto_stop_seconds"
_AUTO_STOP_DEFAULT: Final = "default_auto_stop_seconds must be 0 or between min and max_auto_stop_seconds"
_PRESET_OUT_OF_RANGE: Final = "every default_presets_minutes value must be within the duration range"
_PRESET_DUPLICATE: Final = "default_presets_minutes values must be unique"
_PRESETS_ABOVE_MAX: Final = "default_presets_minutes must not have more values than max_presets"
_CHIME_HOURS_REVERSED: Final = "default_start_hour must not exceed default_end_hour"
_LIST_SEPARATOR: Final = ","
_SECONDS_PER_MINUTE: Final = 60

type Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
type FileName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, pattern=r"^[^/\\:*?\"<>|]+$")]
type InstanceKey = Annotated[str, StringConstraints(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")]
type WindowSide = Annotated[int, Field(ge=320, le=10_000)]
type LanguageCode = Literal["en", "fr"]
type LevelName = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
type SoundName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, pattern=r"^[A-Za-z0-9_.-]+$")]
type TimerSeconds = Annotated[int, Field(ge=1, le=359_999)]
type AutoStopSeconds = Annotated[int, Field(ge=1, le=86_400)]
type MinutesList = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^(\d+(\s*,\s*\d+)*)?$")]
type Volume = Annotated[int, Field(ge=0, le=100)]
type Hour = Annotated[int, Field(ge=0, le=23)]


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
    dialog_overlay_opacity_percent: Annotated[int, Field(ge=0, le=50)]
    startup_dialog_min_width_px: WindowSide
    dialog_spacing_px: Annotated[int, Field(ge=0, le=50)]
    timer_font_family: Text
    timer_font_size_px: Annotated[int, Field(ge=8, le=400)]
    alert_blink_interval_ms: Annotated[int, Field(ge=100, le=5_000)]

    @model_validator(mode="after")
    def _check_min_window(self) -> Self:
        if self.min_window_width_px > self.default_window_width_px:
            raise ValueError(_MIN_WINDOW_ABOVE_DEFAULT)
        if self.min_window_height_px > self.default_window_height_px:
            raise ValueError(_MIN_WINDOW_ABOVE_DEFAULT)
        return self


class StorageSectionSchema(BaseModel):
    """``[storage]``."""

    model_config = _STRICT

    save_debounce_ms: Annotated[int, Field(ge=50, le=10_000)]
    save_max_delay_ms: Annotated[int, Field(ge=500, le=60_000)]
    replace_retry_count: Annotated[int, Field(ge=0, le=20)]
    replace_retry_delay_ms: Annotated[int, Field(ge=10, le=5_000)]
    failed_save_retry_ms: Annotated[int, Field(ge=1_000, le=600_000)]
    shutdown_flush_timeout_ms: Annotated[int, Field(ge=500, le=60_000)]
    blocking_write_timeout_ms: Annotated[int, Field(ge=500, le=60_000)]
    daily_backup_enabled: bool
    daily_backup_retention_days: Annotated[int, Field(ge=1, le=365)]

    @model_validator(mode="after")
    def _check_max_delay(self) -> Self:
        if self.save_max_delay_ms < self.save_debounce_ms:
            raise ValueError(_MAX_DELAY_BELOW_DEBOUNCE)
        return self


class TimerSectionSchema(BaseModel):
    """``[timer]``."""

    model_config = _STRICT

    tick_interval_ms: Annotated[int, Field(ge=10, le=1_000)]
    snooze_minutes: Annotated[int, Field(ge=1, le=1_440)]
    default_duration_seconds: TimerSeconds
    min_duration_seconds: TimerSeconds
    max_duration_seconds: TimerSeconds
    default_sound: SoundName
    default_volume: Volume
    default_loop_count: Annotated[int, Field(ge=1, le=999)]
    max_loop_count: Annotated[int, Field(ge=1, le=999)]
    default_auto_stop_seconds: Annotated[int, Field(ge=0, le=86_400)]
    min_auto_stop_seconds: AutoStopSeconds
    max_auto_stop_seconds: AutoStopSeconds
    default_presets_minutes: MinutesList
    max_presets: Annotated[int, Field(ge=1, le=50)]
    max_preset_label_length: Annotated[int, Field(ge=1, le=200)]

    def preset_minutes(self) -> tuple[int, ...]:
        """Return the values of ``default_presets_minutes``.

        Returns:
            The minutes, in order; empty for an empty value.
        """
        return tuple(int(part) for part in self.default_presets_minutes.split(_LIST_SEPARATOR) if part.strip())

    @model_validator(mode="after")
    def _check_limits(self) -> Self:
        if not self.min_duration_seconds <= self.default_duration_seconds <= self.max_duration_seconds:
            raise ValueError(_DURATION_ORDER)
        if self.default_loop_count > self.max_loop_count:
            raise ValueError(_LOOP_COUNT_ABOVE_MAX)
        if self.min_auto_stop_seconds > self.max_auto_stop_seconds:
            raise ValueError(_AUTO_STOP_ORDER)
        stop = self.default_auto_stop_seconds
        if stop and not self.min_auto_stop_seconds <= stop <= self.max_auto_stop_seconds:
            raise ValueError(_AUTO_STOP_DEFAULT)
        return self

    @model_validator(mode="after")
    def _check_presets(self) -> Self:
        minutes = self.preset_minutes()
        seconds = [value * _SECONDS_PER_MINUTE for value in minutes]
        if any(not self.min_duration_seconds <= value <= self.max_duration_seconds for value in seconds):
            raise ValueError(_PRESET_OUT_OF_RANGE)
        if len(set(minutes)) != len(minutes):
            raise ValueError(_PRESET_DUPLICATE)
        if len(minutes) > self.max_presets:
            raise ValueError(_PRESETS_ABOVE_MAX)
        return self


class ChimeSectionSchema(BaseModel):
    """``[chime]``."""

    model_config = _STRICT

    default_enabled: bool
    default_sound: SoundName
    default_volume: Volume
    default_start_hour: Hour
    default_end_hour: Hour
    trigger_window_seconds: Annotated[int, Field(ge=1, le=3_599)]

    @model_validator(mode="after")
    def _check_hours(self) -> Self:
        if self.default_start_hour > self.default_end_hour:
            raise ValueError(_CHIME_HOURS_REVERSED)
        return self


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
    storage: StorageSectionSchema
    timer: TimerSectionSchema
    chime: ChimeSectionSchema
    logging: LoggingSectionSchema
    i18n: I18nSectionSchema
