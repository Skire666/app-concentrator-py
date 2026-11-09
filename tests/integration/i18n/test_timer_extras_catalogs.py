"""Favorite labels and chime hours rendered with the real catalogs, in both languages."""

import pytest

from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.domain.timer.duration import Duration
from concentrator.infrastructure.i18n.json_catalog_translator import JsonCatalogTranslator, load_catalogs
from concentrator.infrastructure.system.app_paths import AppPaths
from concentrator.presentation.common.duration_label_formatter import DurationLabelFormatter
from concentrator.presentation.timer.chime_hours import hour_options, hour_text

LANGUAGES = (LanguageEnum.ENGLISH, LanguageEnum.FRENCH)


def _translator(language: LanguageEnum) -> JsonCatalogTranslator:
    catalogs = load_catalogs(AppPaths.from_runtime().i18n_dir, LANGUAGES, LanguageEnum.ENGLISH)
    return JsonCatalogTranslator(catalogs.value_or({}), language=language, fallback_language=LanguageEnum.ENGLISH)


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (900, "15 min"),
        (3600, "1 h"),
        (5400, "1 h 30"),
        (3900, "1 h 05"),
        (90, "1 min 30 s"),
        (45, "45 s"),
        (3605, "1 h 5 s"),
    ],
)
def test_automatic_favorite_labels(language: LanguageEnum, seconds: int, expected: str) -> None:
    assert DurationLabelFormatter(_translator(language)).label(Duration(seconds)) == expected


@pytest.mark.parametrize("language", LANGUAGES)
def test_chime_hours_are_zero_padded(language: LanguageEnum) -> None:
    translator = _translator(language)

    assert hour_text(translator, 8) == "08:00"
    assert hour_options(translator)[-1] == "23:00"


@pytest.mark.parametrize(
    ("language", "expected"),
    [(LanguageEnum.ENGLISH, "Start a countdown of 00:15:00"), (LanguageEnum.FRENCH, "Lancer un décompte de 00:15:00")],
)
def test_favorite_tooltip(language: LanguageEnum, expected: str) -> None:
    assert _translator(language).tr("presets.tooltip.start", duration="00:15:00") == expected
