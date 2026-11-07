"""``CONCENTRATOR_SELF_CHECK=1``: validates a (frozen) installation without showing a window."""

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from PySide6.QtGui import QIcon, QImageReader

from concentrator.application.common.app_config import AppConfig
from concentrator.application.storage.user_data import StoredUserData, UserData
from concentrator.bootstrap.translator_loader import CATALOG_LANGUAGES
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.domain.settings.user_settings import UserSettings, UserSettingsId
from concentrator.infrastructure.i18n.json_catalog_translator import CATALOG_SUFFIX, load_catalogs
from concentrator.infrastructure.persistence.user_data_codec import UserDataCodec
from concentrator.infrastructure.system.app_paths import AppPaths
from concentrator.ui.panels.module_bar_panel import MODULE_ICON_FILES

_logger = logging.getLogger(__name__)

SVG_FORMAT = b"svg"
ICON_CHECK_SIZE_PX = 32
ROUND_TRIP_ID: Final = UserSettingsId("00000000-0000-7000-8000-000000000000")
ROUND_TRIP_TIME: Final = datetime(2026, 1, 1, tzinfo=UTC)


def _required_files(paths: AppPaths) -> list[Path]:
    """Files the application cannot run without.

    Args:
        paths: Application paths.

    Returns:
        The ini, the catalogs and the icons.
    """
    catalogs = [paths.i18n_dir / f"{language.iso_code}{CATALOG_SUFFIX}" for language in CATALOG_LANGUAGES]
    icons = [paths.icons_dir / name for name in MODULE_ICON_FILES.values()]
    return [paths.config_file, *catalogs, paths.app_icon_file, *icons]


def _svg_failures(paths: AppPaths) -> list[str]:
    """Check that the Qt SVG image plugin is bundled and renders the module icons.

    Args:
        paths: Application paths.

    Returns:
        One description per problem.
    """
    formats = {bytes(item.data()) for item in QImageReader.supportedImageFormats()}
    if SVG_FORMAT not in formats:
        return ["Qt SVG image plugin missing"]
    return [
        f"icon cannot be rendered: {name}"
        for name in MODULE_ICON_FILES.values()
        if QIcon(str(paths.icons_dir / name)).pixmap(ICON_CHECK_SIZE_PX, ICON_CHECK_SIZE_PX).isNull()
    ]


def storage_failures(app_version: str) -> list[str]:
    """Round-trip an in-memory ``UserData`` through codec, schemas and mappers (no file, ADR-034).

    A frozen bundle missing ``tomllib`` or ``pydantic`` pieces fails here.

    Args:
        app_version: Version written in the document.

    Returns:
        One description per problem.
    """
    codec = UserDataCodec(app_version)
    settings = UserSettings.create(ROUND_TRIP_ID, ROUND_TRIP_TIME, LanguageEnum.ENGLISH)
    stored = StoredUserData(data=UserData.initial(settings), saved_at=ROUND_TRIP_TIME)
    decoded = codec.decode(codec.encode(stored))
    if decoded.data == stored:
        return []
    return [f"user data round trip: {[code.name for code in decoded.validation.error_codes]}"]


def run_self_check(paths: AppPaths, config: AppConfig, app_version: str) -> bool:
    """Check the assets, the catalogs, the SVG rendering and the user data pipeline; log the outcome.

    Args:
        paths: Application paths.
        config: Loaded configuration (its loading is the first check).
        app_version: Version used for the user data round trip.

    Returns:
        Whether every check passed.
    """
    failures = [f"missing file: {path}" for path in _required_files(paths) if not path.is_file()]
    catalogs = load_catalogs(paths.i18n_dir, CATALOG_LANGUAGES, config.i18n.fallback_language)
    if not catalogs.is_success or catalogs.validation.has_warnings:
        failures.append(f"catalogs: {[code.name for code in catalogs.validation.error_codes]}")
    failures.extend(_svg_failures(paths))
    failures.extend(storage_failures(app_version))
    if failures:
        _logger.error("Self-check failed: %s", failures)
        return False
    _logger.info("Self-check passed (app dir %s, assets %s)", paths.app_dir, paths.assets_dir)
    return True
