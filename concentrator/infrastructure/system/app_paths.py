"""Locations of the application files, in development and in the frozen (PyInstaller) build."""

import logging
import os
import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult

_logger = logging.getLogger(__name__)

_SOURCE_ROOT: Final = Path(__file__).resolve().parents[3]
_TOKEN: Final = re.compile(r"\{([^{}]*)\}")
CONFIG_FILE_NAME: Final = "concentrator.ini"
ASSETS_DIR_NAME: Final = "assets"
CONFIG_DIR_NAME: Final = "config"
I18N_DIR_NAME: Final = "i18n"
ICONS_DIR_NAME: Final = "icons"
SOUNDS_DIR_NAME: Final = "sounds"
APP_ICON_FILE_NAME: Final = "concentrator.ico"
APPDATA_TOKEN: Final = "appdata"
LOCALAPPDATA_TOKEN: Final = "localappdata"
APP_DIR_TOKEN: Final = "app_dir"


@dataclass(frozen=True, slots=True)
class AppPaths:
    """Where the application finds its ini, assets and per-user folders.

    Attributes:
        app_dir: Repository root in development, folder of ``Concentrator.exe`` when frozen.
        assets_dir: Bundled assets (icons, catalogs, sounds).
        config_file: ``concentrator.ini``: ``assets/config/`` in development, next to the exe when frozen.
        environment: Environment variables used to resolve the ``{appdata}`` and ``{localappdata}`` tokens.
    """

    app_dir: Path
    assets_dir: Path
    config_file: Path
    environment: Mapping[str, str] = field(default_factory=dict[str, str])

    @classmethod
    def from_runtime(cls) -> AppPaths:
        """Build the paths of the running process.

        Returns:
            Paths for the development tree or for the PyInstaller bundle (``sys.frozen``).
        """
        bundle = getattr(sys, "_MEIPASS", None)
        return cls.for_layout(
            frozen=bool(getattr(sys, "frozen", False)),
            executable=Path(sys.executable),
            bundle_dir=Path(bundle) if isinstance(bundle, str) else None,
            environment=dict(os.environ),
        )

    @classmethod
    def for_layout(
        cls,
        *,
        frozen: bool,
        executable: Path,
        bundle_dir: Path | None,
        environment: Mapping[str, str],
        source_root: Path = _SOURCE_ROOT,
    ) -> AppPaths:
        """Build the paths of a development tree or of a frozen bundle.

        Args:
            frozen: Whether the process runs from the PyInstaller bundle.
            executable: Path of the running executable.
            bundle_dir: PyInstaller data folder (``sys._MEIPASS``), if any.
            environment: Environment variables.
            source_root: Repository root, used in development only.

        Returns:
            The paths.
        """
        if not frozen:
            assets_dir = source_root / ASSETS_DIR_NAME
            return cls(source_root, assets_dir, assets_dir / CONFIG_DIR_NAME / CONFIG_FILE_NAME, environment)
        app_dir = executable.parent
        data_dir = bundle_dir or app_dir
        return cls(app_dir, data_dir / ASSETS_DIR_NAME, app_dir / CONFIG_FILE_NAME, environment)

    @property
    def i18n_dir(self) -> Path:
        """Folder of the ``en.json`` and ``fr.json`` catalogs."""
        return self.assets_dir / I18N_DIR_NAME

    @property
    def icons_dir(self) -> Path:
        """Folder of the application and module icons."""
        return self.assets_dir / ICONS_DIR_NAME

    @property
    def sounds_dir(self) -> Path:
        """Folder of the built-in alarm sounds."""
        return self.assets_dir / SOUNDS_DIR_NAME

    @property
    def app_icon_file(self) -> Path:
        """Application icon (window, taskbar, exe)."""
        return self.icons_dir / APP_ICON_FILE_NAME

    def resolve(self, template: str, field_path: str) -> DataResult[Path]:
        """Replace the ``{appdata}``, ``{localappdata}`` and ``{app_dir}`` tokens of a configured path.

        Args:
            template: Path text from the ini, for example ``{appdata}/Concentrator/ui-state.ini``.
            field_path: Dotted ini key reported on failure, for example ``paths.ui_state_file``.

        Returns:
            The absolute path (a relative result is taken from ``app_dir``), or ``CONFIG_VALUE_INVALID``
            for an unknown token or an undefined environment variable.
        """
        values = self._token_values()
        unresolved = [name for name in _TOKEN.findall(template) if not values.get(name)]
        if unresolved:
            _logger.warning("Cannot resolve token {%s} in %s", unresolved[0], field_path)
            failure = ValidationResult.failure(
                ErrorCodeEnum.CONFIG_VALUE_INVALID, field=field_path, token=unresolved[0]
            )
            return DataResult.fail(failure)
        path = Path(_TOKEN.sub(lambda match: values[match.group(1)], template))
        return DataResult.ok(path if path.is_absolute() else self.app_dir / path)

    def _token_values(self) -> dict[str, str]:
        """Return the value of every supported token (empty when the variable is undefined).

        Returns:
            Token name to replacement text.
        """
        return {
            APPDATA_TOKEN: self.environment.get("APPDATA", ""),
            LOCALAPPDATA_TOKEN: self.environment.get("LOCALAPPDATA", ""),
            APP_DIR_TOKEN: str(self.app_dir),
        }
