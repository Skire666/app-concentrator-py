"""Valid ``AppConfig`` instances for tests, mirroring the shipped ``concentrator.ini``."""

import logging
from dataclasses import replace
from pathlib import Path

from concentrator.application.common.app_config import (
    AppConfig,
    AppSection,
    I18nSection,
    LoggingSection,
    PathsSection,
    StorageSection,
    TimerSection,
    UiSection,
)
from concentrator.domain.settings.language_enum import LanguageEnum


def make_ui_section(**changes: int) -> UiSection:
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


def make_app_config(
    root: Path = Path("C:/concentrator-tests"), ui: UiSection | None = None, storage: StorageSection | None = None
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
        timer=TimerSection(tick_interval_ms=100),
        logging=LoggingSection(
            level=logging.INFO,
            file_name="concentrator.log",
            file_max_bytes=2_000_000,
            file_backup_count=5,
            journal_buffer_size=5000,
        ),
        i18n=I18nSection(default_language=LanguageEnum.ENGLISH, fallback_language=LanguageEnum.ENGLISH),
    )
