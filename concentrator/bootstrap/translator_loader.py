"""Startup step 5: catalogs and translator."""

import logging
from typing import Final

from concentrator.application.common.app_config import AppConfig
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.infrastructure.i18n.json_catalog_translator import JsonCatalogTranslator, load_catalogs
from concentrator.infrastructure.system.app_paths import AppPaths

_logger = logging.getLogger(__name__)

CATALOG_LANGUAGES: Final = (LanguageEnum.ENGLISH, LanguageEnum.FRENCH)


def load_translator(paths: AppPaths, config: AppConfig) -> JsonCatalogTranslator:
    """Load the catalogs; on failure every text falls back to its key and the failure is logged at ERROR.

    Args:
        paths: Application paths.
        config: Loaded configuration.

    Returns:
        The translator, in ``i18n.default_language`` (in-memory language until phase 1 stores it).
    """
    catalogs = load_catalogs(paths.i18n_dir, CATALOG_LANGUAGES, config.i18n.fallback_language)
    if catalogs.data is None:
        _logger.error("Catalogs not loaded, texts fall back to their keys: %s", catalogs.validation.error_codes)
    else:
        _logger.info("Catalogs loaded from %s", paths.i18n_dir)
    return JsonCatalogTranslator(
        catalogs.value_or({}), language=config.i18n.default_language, fallback_language=config.i18n.fallback_language
    )
