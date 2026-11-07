from pathlib import Path

import pytest

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.infrastructure.system.app_paths import AppPaths

ENVIRONMENT = {"APPDATA": "C:/Users/me/AppData/Roaming", "LOCALAPPDATA": "C:/Users/me/AppData/Local"}


def _dev_paths(environment: dict[str, str] | None = None) -> AppPaths:
    return AppPaths.for_layout(
        frozen=False,
        executable=Path("C:/Python/python.exe"),
        bundle_dir=None,
        environment=ENVIRONMENT if environment is None else environment,
        source_root=Path("D:/src/app"),
    )


def test_dev_layout_uses_the_repository_tree() -> None:
    paths = _dev_paths()

    assert paths.app_dir == Path("D:/src/app")
    assert paths.assets_dir == Path("D:/src/app/assets")
    assert paths.config_file == Path("D:/src/app/assets/config/concentrator.ini")
    assert paths.i18n_dir == Path("D:/src/app/assets/i18n")
    assert paths.app_icon_file == Path("D:/src/app/assets/icons/concentrator.ico")


def test_frozen_layout_reads_ini_next_to_exe_and_assets_from_bundle() -> None:
    paths = AppPaths.for_layout(
        frozen=True,
        executable=Path("E:/Apps/Concentrator/Concentrator.exe"),
        bundle_dir=Path("E:/Apps/Concentrator/_internal"),
        environment=ENVIRONMENT,
    )

    assert paths.app_dir == Path("E:/Apps/Concentrator")
    assert paths.config_file == Path("E:/Apps/Concentrator/concentrator.ini")
    assert paths.assets_dir == Path("E:/Apps/Concentrator/_internal/assets")


def test_frozen_layout_without_bundle_dir_uses_exe_folder() -> None:
    paths = AppPaths.for_layout(
        frozen=True, executable=Path("E:/Apps/C/Concentrator.exe"), bundle_dir=None, environment=ENVIRONMENT
    )

    assert paths.assets_dir == Path("E:/Apps/C/assets")


@pytest.mark.parametrize(
    ("template", "expected"),
    [
        ("{appdata}/Concentrator/ui-state.ini", Path("C:/Users/me/AppData/Roaming/Concentrator/ui-state.ini")),
        ("{localappdata}/Concentrator/logs", Path("C:/Users/me/AppData/Local/Concentrator/logs")),
        ("{app_dir}/data", Path("D:/src/app/data")),
        ("relative/logs", Path("D:/src/app/relative/logs")),
        ("F:/absolute/file.toml", Path("F:/absolute/file.toml")),
    ],
)
def test_resolve_replaces_tokens(template: str, expected: Path) -> None:
    result = _dev_paths().resolve(template, "paths.x")

    assert result.data == expected


@pytest.mark.parametrize(
    ("template", "environment"), [("{home}/x", ENVIRONMENT), ("{appdata}/x", {"LOCALAPPDATA": "C:/L"})]
)
def test_resolve_rejects_unknown_token_or_undefined_variable(template: str, environment: dict[str, str]) -> None:
    result = _dev_paths(environment).resolve(template, "paths.log_dir")

    assert result.data is None
    assert result.validation.error_codes == (ErrorCodeEnum.CONFIG_VALUE_INVALID,)
    assert result.validation.issues_for("paths.log_dir")


def test_from_runtime_in_development_finds_the_shipped_ini() -> None:
    paths = AppPaths.from_runtime()

    assert paths.config_file.is_file()
    assert paths.app_icon_file.is_file()
