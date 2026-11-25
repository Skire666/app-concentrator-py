import json
import logging
from pathlib import Path

import pytest

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.infrastructure.i18n.json_catalog_translator import JsonCatalogTranslator, load_catalog, load_catalogs
from concentrator.infrastructure.system.app_paths import AppPaths

LANGUAGES = (LanguageEnum.ENGLISH, LanguageEnum.FRENCH)
TRANSLATOR_LOGGER = "concentrator.infrastructure.i18n.json_catalog_translator"
CATALOGS = {
    LanguageEnum.ENGLISH: {
        "greeting": "Hello {name}",
        "only.english": "Only in English",
        "minutes.one": "{count} minute",
        "minutes.other": "{count} minutes",
        "broken": "Hello {",
    },
    LanguageEnum.FRENCH: {
        "greeting": "Bonjour {name}",
        "minutes.one": "{count} minute",
        "minutes.other": "{count} minutes",
    },
}


def _translator(language: LanguageEnum = LanguageEnum.FRENCH) -> JsonCatalogTranslator:
    return JsonCatalogTranslator(CATALOGS, language=language, fallback_language=LanguageEnum.ENGLISH)


def _write(directory: Path, name: str, content: object) -> None:
    (directory / name).write_text(json.dumps(content), encoding="utf-8")


def test_shipped_catalogs_load_without_warning() -> None:
    result = load_catalogs(AppPaths.from_runtime().i18n_dir, LANGUAGES, LanguageEnum.ENGLISH)

    assert result.is_success
    assert not result.validation.has_warnings


def test_tr_uses_current_language_and_fills_placeholders() -> None:
    assert _translator().tr("greeting", name="Ana") == "Bonjour Ana"


def test_tr_falls_back_to_english_then_to_the_key() -> None:
    translator = _translator()

    assert translator.tr("only.english") == "Only in English"
    assert translator.tr("nowhere.at.all") == "nowhere.at.all"


def test_missing_key_is_logged_once_per_language(caplog: pytest.LogCaptureFixture) -> None:
    translator = _translator()

    with caplog.at_level(logging.WARNING, logger=TRANSLATOR_LOGGER):
        translator.tr("only.english")
        translator.tr("only.english")
        translator.set_language(LanguageEnum.ENGLISH)
        translator.tr("only.english")

    assert len(caplog.records) == 1
    assert "only.english" in caplog.records[0].getMessage()


def test_missing_placeholder_value_stays_visible_and_bad_template_is_returned_as_is() -> None:
    translator = _translator(LanguageEnum.ENGLISH)

    assert translator.tr("greeting") == "Hello {name}"
    assert translator.tr("greeting", other="x") == "Hello {name}"
    assert translator.tr("broken", name="x") == "Hello {"


@pytest.mark.parametrize(("count", "expected"), [(0, "0 minute"), (1, "1 minute"), (2, "2 minutes")])
def test_french_plural_uses_singular_for_zero_and_one(count: int, expected: str) -> None:
    assert _translator(LanguageEnum.FRENCH).tr_plural("minutes", count) == expected


@pytest.mark.parametrize(("count", "expected"), [(0, "0 minutes"), (1, "1 minute"), (2, "2 minutes")])
def test_english_plural_uses_singular_for_one_only(count: int, expected: str) -> None:
    assert _translator(LanguageEnum.ENGLISH).tr_plural("minutes", count) == expected


def test_set_language_switches_and_rejects_unset_or_unknown() -> None:
    translator = _translator(LanguageEnum.ENGLISH)

    assert translator.set_language(LanguageEnum.FRENCH).is_success
    assert translator.language is LanguageEnum.FRENCH
    assert translator.set_language(LanguageEnum.UNSET).error_codes == (ErrorCodeEnum.ENUM_VALUE_UNSET,)
    assert translator.set_language(LanguageEnum.UNKNOWN).error_codes == (ErrorCodeEnum.ENUM_VALUE_UNKNOWN,)
    assert translator.language is LanguageEnum.FRENCH


def test_has_looks_in_current_and_fallback_catalogs() -> None:
    translator = _translator()

    assert translator.has("greeting")
    assert translator.has("only.english")
    assert not translator.has("nowhere.at.all")


def test_empty_translator_returns_keys() -> None:
    translator = JsonCatalogTranslator({}, language=LanguageEnum.ENGLISH, fallback_language=LanguageEnum.ENGLISH)

    assert translator.tr("app.title") == "app.title"


def test_load_catalog_reports_missing_file(tmp_path: Path) -> None:
    result = load_catalog(tmp_path / "en.json")

    assert result.validation.error_codes == (ErrorCodeEnum.CATALOG_FILE_NOT_FOUND,)


@pytest.mark.parametrize("content", ['{"a": ', '["a"]', '{"a": 1}'])
def test_load_catalog_reports_invalid_content(tmp_path: Path, content: str) -> None:
    (tmp_path / "en.json").write_text(content, encoding="utf-8")

    result = load_catalog(tmp_path / "en.json")

    assert result.validation.error_codes == (ErrorCodeEnum.CATALOG_SYNTAX_INVALID,)


def test_load_catalogs_fails_when_one_file_fails(tmp_path: Path) -> None:
    _write(tmp_path, "en.json", {"a": "A"})

    result = load_catalogs(tmp_path, LANGUAGES, LanguageEnum.ENGLISH)

    assert result.data is None
    assert result.validation.error_codes == (ErrorCodeEnum.CATALOG_FILE_NOT_FOUND,)


def test_load_catalogs_warns_about_keys_missing_from_a_catalog(tmp_path: Path) -> None:
    _write(tmp_path, "en.json", {"a": "A", "b": "B"})
    _write(tmp_path, "fr.json", {"a": "A"})

    result = load_catalogs(tmp_path, LANGUAGES, LanguageEnum.ENGLISH)

    assert result.is_success
    assert result.validation.error_codes == (ErrorCodeEnum.CATALOG_KEY_MISSING,)
    assert result.validation.issues[0].field == "b"
    assert result.validation.issues[0].params == (("language", "fr"),)
