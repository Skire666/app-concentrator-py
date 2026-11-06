import logging
from pathlib import Path

import pytest

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.settings.language_enum import LanguageEnum
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
    assert config.logging.level == logging.INFO
    assert config.i18n.default_language is LanguageEnum.ENGLISH
    assert config.paths.ui_state_file == tmp_path / "roaming" / "Concentrator" / "ui-state.ini"
    assert config.paths.log_dir == tmp_path / "local" / "Concentrator" / "logs"


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
    ini = _write_ini(tmp_path, {"[timer]\n": "", "tick_interval_ms = 100\n": ""})

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
        ("level = INFO", "level = VERBOSE", "logging.level"),
        ("default_language = en", "default_language = de", "i18n.default_language"),
        ("file_name = concentrator.log", "file_name = logs/concentrator.log", "logging.file_name"),
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
