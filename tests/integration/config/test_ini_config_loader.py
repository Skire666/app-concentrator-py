import logging
from pathlib import Path

import pytest

from concentrator.application.common.app_config import ChimeSection, JournalSection, SettingsSection, TodoSection
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.domain.settings.log_level_enum import LogLevelEnum
from concentrator.domain.todo.priority_enum import PriorityEnum
from concentrator.domain.todo.task_sort_key_enum import TaskSortKeyEnum
from concentrator.infrastructure.config.ini_config_loader import IniConfigLoader
from concentrator.infrastructure.system.app_paths import AppPaths

SHIPPED_INI = AppPaths.from_runtime().config_file


@pytest.fixture
def paths(tmp_path: Path) -> AppPaths:
    environment = {"APPDATA": str(tmp_path / "roaming"), "LOCALAPPDATA": str(tmp_path / "local")}
    return AppPaths(
        app_dir=tmp_path / "app",
        assets_dir=tmp_path / "assets",
        config_file=tmp_path / "x.ini",
        environment=environment,
    )


def _write_ini(tmp_path: Path, replacements: dict[str, str]) -> Path:
    text = SHIPPED_INI.read_text(encoding="utf-8")
    for old, new in replacements.items():
        assert old in text
        text = text.replace(old, new)
    target = tmp_path / "concentrator.ini"
    target.write_text(text, encoding="utf-8")
    return target


def test_shipped_ini_loads_with_tokens_resolved(paths: AppPaths, tmp_path: Path) -> None:
    result = IniConfigLoader(paths).load(SHIPPED_INI)

    assert result.is_success
    config = result.data
    assert config is not None
    assert config.app.name == "Concentrator"
    assert config.app.single_instance_timeout_ms == 1000
    assert config.ui.module_bar_width_px == 100
    assert config.ui.zone1_ratio_percent == 70
    assert config.timer.tick_interval_ms == 100
    assert config.timer.snooze_minutes == 5
    assert config.timer.default_sound == "alarm"
    assert config.timer.max_duration_seconds == 359_999
    assert config.timer.default_presets_minutes == (15, 30, 45)
    assert (config.timer.max_presets, config.timer.max_preset_label_length) == (12, 40)
    assert config.chime == ChimeSection(
        default_enabled=False,
        default_sound="chime",
        default_volume=60,
        default_start_hour=8,
        default_end_hour=20,
        trigger_window_seconds=59,
    )
    assert config.ui.timer_font_family == "Cascadia Mono"
    assert config.ui.alert_blink_interval_ms == 500
    assert config.storage.save_debounce_ms == 500
    assert config.storage.save_max_delay_ms == 1500
    assert config.storage.blocking_write_timeout_ms == 5000
    assert config.storage.daily_backup_enabled is True
    assert config.storage.daily_backup_retention_days == 7
    assert config.logging.level == logging.INFO
    assert config.i18n.default_language is LanguageEnum.ENGLISH
    assert config.paths.ui_state_file == tmp_path / "roaming" / "Concentrator" / "ui-state.ini"
    assert config.paths.log_dir == tmp_path / "local" / "Concentrator" / "logs"
    assert config.journal == JournalSection(
        search_debounce_ms=150,
        copy_max_rows=2000,
        default_table_ratio_percent=70,
        default_column_widths_px=(110, 90, 240, 120),
    )
    assert config.settings == SettingsSection(default_log_level=LogLevelEnum.INFO, default_notify_when_inactive=True)
    assert config.todo == TodoSection(
        max_task_text_length=5000,
        max_list_name_length=80,
        max_list_description_length=2000,
        max_history_events=10,
        default_list_priority=PriorityEnum.NORMAL,
        default_sort=TaskSortKeyEnum.CREATED,
        default_sort_descending=True,
        default_table_ratio_percent=75,
        default_column_widths_px=(60, 140, 140, 140),
    )


def test_missing_file_is_reported(paths: AppPaths, tmp_path: Path) -> None:
    result = IniConfigLoader(paths).load(tmp_path / "absent.ini")

    assert result.validation.error_codes == (ErrorCodeEnum.CONFIG_FILE_NOT_FOUND,)


@pytest.mark.parametrize("content", ["no section header\n", "[app]\nname = a\n[app]\nname = b\n", b"\xff\xfe\x00"])
def test_syntax_error_is_reported(paths: AppPaths, tmp_path: Path, content: str | bytes) -> None:
    target = tmp_path / "broken.ini"
    if isinstance(content, bytes):
        target.write_bytes(content)
    else:
        target.write_text(content, encoding="utf-8")

    result = IniConfigLoader(paths).load(target)

    assert result.validation.error_codes == (ErrorCodeEnum.CONFIG_SYNTAX_INVALID,)


def test_missing_key_is_reported_with_its_path(paths: AppPaths, tmp_path: Path) -> None:
    ini = _write_ini(tmp_path, {"module_bar_width_px = 100\n": ""})

    result = IniConfigLoader(paths).load(ini)

    assert result.data is None
    assert result.validation.error_codes == (ErrorCodeEnum.CONFIG_KEY_MISSING,)
    assert result.validation.issues_for("ui.module_bar_width_px")


def test_missing_section_is_reported(paths: AppPaths, tmp_path: Path) -> None:
    text = SHIPPED_INI.read_text(encoding="utf-8")
    section = text[text.index("[timer]") : text.index("[chime]")]
    ini = _write_ini(tmp_path, {section: ""})

    result = IniConfigLoader(paths).load(ini)

    assert result.validation.error_codes == (ErrorCodeEnum.CONFIG_KEY_MISSING,)
    assert result.validation.issues_for("timer")


def test_unexpected_key_is_reported(paths: AppPaths, tmp_path: Path) -> None:
    ini = _write_ini(tmp_path, {"module_bar_width_px = 100\n": "module_bar_widht_px = 100\n"})

    result = IniConfigLoader(paths).load(ini)

    assert set(result.validation.error_codes) == {ErrorCodeEnum.CONFIG_KEY_MISSING, ErrorCodeEnum.CONFIG_KEY_UNEXPECTED}
    assert result.validation.issues_for("ui.module_bar_widht_px")[0].code is ErrorCodeEnum.CONFIG_KEY_UNEXPECTED


@pytest.mark.parametrize(
    ("old", "new", "field"),
    [
        ("module_bar_width_px = 100", "module_bar_width_px = 401", "ui.module_bar_width_px"),
        ("module_bar_width_px = 100", "module_bar_width_px = wide", "ui.module_bar_width_px"),
        ("zone1_ratio_percent = 70", "zone1_ratio_percent = 70.5", "ui.zone1_ratio_percent"),
        ("action_cooldown_ms = 100", "action_cooldown_ms = 99", "ui.action_cooldown_ms"),
        ("min_window_width_px = 1000", "min_window_width_px = 1500", "ui"),
        ("min_window_height_px = 640", "min_window_height_px = 900", "ui"),
        ("\nlevel = INFO", "\nlevel = VERBOSE", "logging.level"),
        ("default_language = en", "default_language = de", "i18n.default_language"),
        ("file_name = concentrator.log", "file_name = logs/concentrator.log", "logging.file_name"),
        ("save_max_delay_ms = 1500", "save_max_delay_ms = 499", "storage.save_max_delay_ms"),
        ("save_debounce_ms = 500", "save_debounce_ms = 2000", "storage"),
        ("replace_retry_count = 5", "replace_retry_count = 21", "storage.replace_retry_count"),
        ("blocking_write_timeout_ms = 5000", "blocking_write_timeout_ms = 60001", "storage.blocking_write_timeout_ms"),
        ("daily_backup_enabled = true", "daily_backup_enabled = maybe", "storage.daily_backup_enabled"),
        ("daily_backup_retention_days = 7", "daily_backup_retention_days = 0", "storage.daily_backup_retention_days"),
        ("timer_font_family = Cascadia Mono", "timer_font_family =  ", "ui.timer_font_family"),
        ("alert_blink_interval_ms = 500", "alert_blink_interval_ms = 99", "ui.alert_blink_interval_ms"),
        ("max_duration_seconds = 359999", "max_duration_seconds = 360000", "timer.max_duration_seconds"),
        ("min_duration_seconds = 1", "min_duration_seconds = 1501", "timer"),
        ("default_duration_seconds = 1500", "default_duration_seconds = 360000", "timer.default_duration_seconds"),
        ("max_loop_count = 99", "max_loop_count = 2", "timer"),
        ("max_auto_stop_seconds = 3600", "max_auto_stop_seconds = 4", "timer"),
        ("default_auto_stop_seconds = 120", "default_auto_stop_seconds = 4000", "timer"),
        ("default_sound = alarm\n", "default_sound = sounds/alarm\n", "timer.default_sound"),
        ("default_volume = 80", "default_volume = 101", "timer.default_volume"),
        ("snooze_minutes = 5", "snooze_minutes = 0", "timer.snooze_minutes"),
        ("default_presets_minutes = 15, 30, 45", "default_presets_minutes = 15, x", "timer.default_presets_minutes"),
        ("default_presets_minutes = 15, 30, 45", "default_presets_minutes = 15,,30", "timer.default_presets_minutes"),
        ("default_presets_minutes = 15, 30, 45", "default_presets_minutes = 15, 15", "timer"),
        ("default_presets_minutes = 15, 30, 45", "default_presets_minutes = 15, 6000", "timer"),
        ("max_presets = 12", "max_presets = 2", "timer"),
        ("max_presets = 12", "max_presets = 51", "timer.max_presets"),
        ("max_preset_label_length = 40", "max_preset_label_length = 0", "timer.max_preset_label_length"),
        ("default_enabled = false", "default_enabled = maybe", "chime.default_enabled"),
        ("default_sound = chime", "default_sound = sounds/chime", "chime.default_sound"),
        ("default_volume = 60", "default_volume = -1", "chime.default_volume"),
        ("default_start_hour = 8", "default_start_hour = 24", "chime.default_start_hour"),
        ("default_end_hour = 20", "default_end_hour = 7", "chime"),
        ("trigger_window_seconds = 59", "trigger_window_seconds = 3600", "chime.trigger_window_seconds"),
        ("search_debounce_ms = 150", "search_debounce_ms = 2001", "journal.search_debounce_ms"),
        ("copy_max_rows = 2000", "copy_max_rows = 0", "journal.copy_max_rows"),
        ("default_table_ratio_percent = 70", "default_table_ratio_percent = 96", "journal.default_table_ratio_percent"),
        ("default_column_widths_px = 110, 90, 240, 120", "default_column_widths_px = 110, 90", "journal"),
        ("default_column_widths_px = 110, 90, 240, 120", "default_column_widths_px = 110, 90, 240, 5", "journal"),
        (
            "default_column_widths_px = 110, 90, 240, 120",
            "default_column_widths_px = a, b",
            "journal.default_column_widths_px",
        ),
        ("default_log_level = INFO", "default_log_level = 2", "settings.default_log_level"),
        ("max_task_text_length = 5000", "max_task_text_length = 0", "todo.max_task_text_length"),
        ("max_list_name_length = 80", "max_list_name_length = 501", "todo.max_list_name_length"),
        ("max_history_events = 10", "max_history_events = 0", "todo.max_history_events"),
        ("default_list_priority = NORMAL", "default_list_priority = MEDIUM", "todo.default_list_priority"),
        ("default_sort = CREATED", "default_sort = NAME", "todo.default_sort"),
        ("default_sort_descending = true", "default_sort_descending = 2", "todo.default_sort_descending"),
        ("default_column_widths_px = 60, 140, 140, 140", "default_column_widths_px = 60, 140", "todo"),
        ("default_column_widths_px = 60, 140, 140, 140", "default_column_widths_px = 60, 140, 140, 9", "todo"),
        (
            "default_notify_when_inactive = true",
            "default_notify_when_inactive = 2",
            "settings.default_notify_when_inactive",
        ),
    ],
)
def test_invalid_value_is_reported(paths: AppPaths, tmp_path: Path, old: str, new: str, field: str) -> None:
    ini = _write_ini(tmp_path, {old: new})

    result = IniConfigLoader(paths).load(ini)

    assert result.validation.error_codes == (ErrorCodeEnum.CONFIG_VALUE_INVALID,)
    assert result.validation.issues_for(field)


def test_unresolvable_path_tokens_are_all_reported(paths: AppPaths, tmp_path: Path) -> None:
    ini = _write_ini(
        tmp_path, {"log_dir = {localappdata}": "log_dir = {home}", "backup_dir = {appdata}": "backup_dir = {x}"}
    )

    result = IniConfigLoader(paths).load(ini)

    assert result.validation.error_codes == (ErrorCodeEnum.CONFIG_VALUE_INVALID, ErrorCodeEnum.CONFIG_VALUE_INVALID)
    assert [issue.field for issue in result.validation.issues] == ["paths.log_dir", "paths.backup_dir"]


@pytest.mark.parametrize(("text", "expected"), [("false", False), ("TRUE", True), ("0", False)])
def test_storage_boolean_accepts_ini_spellings(paths: AppPaths, tmp_path: Path, text: str, expected: bool) -> None:
    ini = _write_ini(tmp_path, {"daily_backup_enabled = true": f"daily_backup_enabled = {text}"})

    config = IniConfigLoader(paths).load(ini).data

    assert config is not None
    assert config.storage.daily_backup_enabled is expected


def test_max_delay_equal_to_debounce_is_accepted(paths: AppPaths, tmp_path: Path) -> None:
    ini = _write_ini(tmp_path, {"save_max_delay_ms = 1500": "save_max_delay_ms = 500"})

    assert IniConfigLoader(paths).load(ini).is_success


def test_empty_default_favorites_are_accepted(paths: AppPaths, tmp_path: Path) -> None:
    ini = _write_ini(tmp_path, {"default_presets_minutes = 15, 30, 45": "default_presets_minutes ="})

    config = IniConfigLoader(paths).load(ini).data

    assert config is not None
    assert config.timer.default_presets_minutes == ()


def test_chime_all_day_is_accepted(paths: AppPaths, tmp_path: Path) -> None:
    ini = _write_ini(
        tmp_path, {"default_start_hour = 8": "default_start_hour = 0", "default_end_hour = 20": "default_end_hour = 23"}
    )

    config = IniConfigLoader(paths).load(ini).data

    assert config is not None
    assert (config.chime.default_start_hour, config.chime.default_end_hour) == (0, 23)
