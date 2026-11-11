"""Valid ``AppConfig`` instances for tests, mirroring the shipped ``concentrator.ini``."""

import logging
from dataclasses import replace
from pathlib import Path

from concentrator.application.common.app_config import (
    AppConfig,
    AppSection,
    ChimeSection,
    I18nSection,
    JournalSection,
    LinksSection,
    LoggingSection,
    PathsSection,
    SettingsSection,
    StorageSection,
    TimerSection,
    TodoSection,
    UiSection,
)
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.domain.settings.log_level_enum import LogLevelEnum
from concentrator.domain.todo.priority_enum import PriorityEnum
from concentrator.domain.todo.task_sort_key_enum import TaskSortKeyEnum


def make_ui_section(**changes: int | str) -> UiSection:
    section = UiSection(
        module_bar_width_px=100,
        zone1_ratio_percent=70,
        default_window_width_px=1400,
        default_window_height_px=860,
        min_window_width_px=1000,
        min_window_height_px=640,
        action_cooldown_ms=100,
        slow_action_threshold_ms=200,
        dialog_overlay_opacity_percent=10,
        startup_dialog_min_width_px=560,
        dialog_spacing_px=10,
        timer_font_family="Cascadia Mono",
        timer_font_size_px=64,
        alert_blink_interval_ms=500,
    )
    return replace(section, **changes)


def make_storage_section(**changes: int | bool) -> StorageSection:
    section = StorageSection(
        save_debounce_ms=500,
        save_max_delay_ms=1500,
        replace_retry_count=5,
        replace_retry_delay_ms=200,
        failed_save_retry_ms=10_000,
        shutdown_flush_timeout_ms=5000,
        blocking_write_timeout_ms=5000,
        daily_backup_enabled=True,
        daily_backup_retention_days=7,
    )
    return replace(section, **changes)


def make_timer_section(**changes: int | str | tuple[int, ...]) -> TimerSection:
    section = TimerSection(
        tick_interval_ms=100,
        snooze_minutes=5,
        default_duration_seconds=1500,
        min_duration_seconds=1,
        max_duration_seconds=359_999,
        default_sound="alarm",
        default_volume=80,
        default_loop_count=3,
        max_loop_count=99,
        default_auto_stop_seconds=120,
        min_auto_stop_seconds=5,
        max_auto_stop_seconds=3600,
        default_presets_minutes=(15, 30, 45),
        max_presets=12,
        max_preset_label_length=40,
    )
    return replace(section, **changes)


def make_chime_section(**changes: int | str | bool) -> ChimeSection:
    section = ChimeSection(
        default_enabled=False,
        default_sound="chime",
        default_volume=60,
        default_start_hour=8,
        default_end_hour=20,
        trigger_window_seconds=59,
    )
    return replace(section, **changes)


def make_journal_section(**changes: int | tuple[int, ...]) -> JournalSection:
    section = JournalSection(
        search_debounce_ms=150,
        copy_max_rows=2000,
        default_table_ratio_percent=70,
        default_column_widths_px=(110, 90, 240, 120),
    )
    return replace(section, **changes)


def make_todo_section(**changes: object) -> TodoSection:
    section = TodoSection(
        max_task_text_length=5000,
        max_list_name_length=80,
        max_list_description_length=2000,
        max_history_events=10,
        max_recurrence_interval=999,
        max_recurrence_count=9999,
        recurrence_preview_count=4,
        default_list_priority=PriorityEnum.NORMAL,
        default_sort=TaskSortKeyEnum.CREATED,
        default_sort_descending=True,
        default_table_ratio_percent=75,
        default_column_widths_px=(60, 140, 140, 140),
    )
    return replace(section, **changes)


def make_settings_section(**changes: LogLevelEnum | bool) -> SettingsSection:
    section = SettingsSection(default_log_level=LogLevelEnum.INFO, default_notify_when_inactive=True)
    return replace(section, **changes)


def make_app_config(
    root: Path = Path("C:/concentrator-tests"),
    ui: UiSection | None = None,
    storage: StorageSection | None = None,
    timer: TimerSection | None = None,
    chime: ChimeSection | None = None,
    journal: JournalSection | None = None,
    todo: TodoSection | None = None,
) -> AppConfig:
    return AppConfig(
        app=AppSection(
            name="Concentrator",
            organization="skire666",
            app_user_model_id="skire666.Concentrator",
            single_instance_key="concentrator-tests",
            single_instance_timeout_ms=1000,
        ),
        paths=PathsSection(
            default_data_file=root / "roaming" / "concentrator.toml",
            ui_state_file=root / "roaming" / "ui-state.ini",
            log_dir=root / "local" / "logs",
            backup_dir=root / "roaming" / "backups",
        ),
        ui=ui or make_ui_section(),
        storage=storage or make_storage_section(),
        timer=timer or make_timer_section(),
        chime=chime or make_chime_section(),
        todo=todo or make_todo_section(),
        logging=LoggingSection(
            level=logging.INFO,
            file_name="concentrator.log",
            file_max_bytes=2_000_000,
            file_backup_count=5,
            journal_buffer_size=5000,
        ),
        journal=journal or make_journal_section(),
        settings=make_settings_section(),
        links=LinksSection(url_schemes=("http", "https"), max_links_in_menu=10),
        i18n=I18nSection(default_language=LanguageEnum.ENGLISH, fallback_language=LanguageEnum.ENGLISH),
    )
