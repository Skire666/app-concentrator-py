"""Application constants loaded from ``concentrator.ini`` (plain frozen dataclasses, no pydantic).

Every field mirrors one ini key; there is no code-level default (ADR-009). Path tokens are already
resolved by the loader.
"""

from dataclasses import dataclass
from pathlib import Path

from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.domain.settings.log_level_enum import LogLevelEnum
from concentrator.domain.todo.priority_enum import PriorityEnum
from concentrator.domain.todo.task_sort_key_enum import TaskSortKeyEnum


@dataclass(frozen=True, slots=True, kw_only=True)
class AppSection:
    """``[app]``: identity of the application and of its single running instance."""

    name: str
    organization: str
    app_user_model_id: str
    single_instance_key: str
    single_instance_timeout_ms: int


@dataclass(frozen=True, slots=True, kw_only=True)
class PathsSection:
    """``[paths]``: files and folders, with tokens resolved."""

    default_data_file: Path
    ui_state_file: Path
    log_dir: Path
    backup_dir: Path


@dataclass(frozen=True, slots=True, kw_only=True)
class UiSection:
    """``[ui]``: sizes and timings of the user interface."""

    module_bar_width_px: int
    zone1_ratio_percent: int
    default_window_width_px: int
    default_window_height_px: int
    min_window_width_px: int
    min_window_height_px: int
    action_cooldown_ms: int
    slow_action_threshold_ms: int
    dialog_overlay_opacity_percent: int
    startup_dialog_min_width_px: int
    dialog_spacing_px: int
    timer_font_family: str
    timer_font_size_px: int
    alert_blink_interval_ms: int


@dataclass(frozen=True, slots=True, kw_only=True)
class StorageSection:
    """``[storage]``: saving the user data file (ADR-028, ADR-029)."""

    save_debounce_ms: int
    save_max_delay_ms: int
    replace_retry_count: int
    replace_retry_delay_ms: int
    failed_save_retry_ms: int
    shutdown_flush_timeout_ms: int
    blocking_write_timeout_ms: int
    daily_backup_enabled: bool
    daily_backup_retention_days: int


@dataclass(frozen=True, slots=True, kw_only=True)
class TimerSection:
    """``[timer]``: heartbeat, snooze, limits and defaults of the timer configuration and favorites."""

    tick_interval_ms: int
    snooze_minutes: int
    default_duration_seconds: int
    min_duration_seconds: int
    max_duration_seconds: int
    default_sound: str
    default_volume: int
    default_loop_count: int
    max_loop_count: int
    default_auto_stop_seconds: int
    min_auto_stop_seconds: int
    max_auto_stop_seconds: int
    default_presets_minutes: tuple[int, ...]
    max_presets: int
    max_preset_label_length: int


@dataclass(frozen=True, slots=True, kw_only=True)
class ChimeSection:
    """``[chime]``: defaults of the hourly chime and its trigger window."""

    default_enabled: bool
    default_sound: str
    default_volume: int
    default_start_hour: int
    default_end_hour: int
    trigger_window_seconds: int


@dataclass(frozen=True, slots=True, kw_only=True)
class TodoSection:
    """``[todo]``: limits of the lists and tasks, defaults of the TODO manager (zone 1)."""

    max_task_text_length: int
    max_list_name_length: int
    max_list_description_length: int
    max_history_events: int
    max_recurrence_interval: int
    max_recurrence_count: int
    recurrence_preview_count: int
    search_debounce_ms: int
    default_list_priority: PriorityEnum
    default_sort: TaskSortKeyEnum
    default_sort_descending: bool
    default_table_ratio_percent: int
    default_column_widths_px: tuple[int, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class LoggingSection:
    """``[logging]``: log level, rotating file and journal buffer."""

    level: int
    file_name: str
    file_max_bytes: int
    file_backup_count: int
    journal_buffer_size: int


@dataclass(frozen=True, slots=True, kw_only=True)
class JournalSection:
    """``[journal]``: the log viewer page (Menu B)."""

    search_debounce_ms: int
    copy_max_rows: int
    default_table_ratio_percent: int
    default_column_widths_px: tuple[int, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class SettingsSection:
    """``[settings]``: General values of a new data file, and of a file written before they existed."""

    default_log_level: LogLevelEnum
    default_notify_when_inactive: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class LinksSection:
    """``[links]``: links detected in the text of the tasks (ADR-014)."""

    url_schemes: tuple[str, ...]
    max_links_in_menu: int


@dataclass(frozen=True, slots=True, kw_only=True)
class I18nSection:
    """``[i18n]``: UI languages."""

    default_language: LanguageEnum
    fallback_language: LanguageEnum


@dataclass(frozen=True, slots=True, kw_only=True)
class AppConfig:
    """Every section of ``concentrator.ini``."""

    app: AppSection
    paths: PathsSection
    ui: UiSection
    storage: StorageSection
    timer: TimerSection
    chime: ChimeSection
    todo: TodoSection
    logging: LoggingSection
    journal: JournalSection
    settings: SettingsSection
    links: LinksSection
    i18n: I18nSection
