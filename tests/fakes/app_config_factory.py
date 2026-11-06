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
    )
    return replace(section, **changes)


def make_app_config(root: Path = Path("C:/concentrator-tests"), ui: UiSection | None = None) -> AppConfig:
    return AppConfig(
        app=AppSection(
            name="Concentrator",
            organization="skire666",
            app_user_model_id="skire666.Concentrator",
            single_instance_key="concentrator-tests",
            single_instance_timeout_ms=1000,
        ),
        paths=PathsSection(
            default_data_file=root / "roaming" / "concentrator.json5",
            ui_state_file=root / "roaming" / "ui-state.ini",
            log_dir=root / "local" / "logs",
            backup_dir=root / "roaming" / "backups",
        ),
        ui=ui or make_ui_section(),
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
