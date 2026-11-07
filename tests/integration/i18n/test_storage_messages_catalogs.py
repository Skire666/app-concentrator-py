"""Storage messages rendered with the real catalogs, in both languages."""

import pytest

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.infrastructure.i18n.json_catalog_translator import JsonCatalogTranslator, load_catalogs
from concentrator.infrastructure.system.app_paths import AppPaths
from concentrator.presentation.storage.storage_messages import StorageMessages

LANGUAGES = (LanguageEnum.ENGLISH, LanguageEnum.FRENCH)


def _translator(language: LanguageEnum) -> JsonCatalogTranslator:
    catalogs = load_catalogs(AppPaths.from_runtime().i18n_dir, LANGUAGES, LanguageEnum.ENGLISH)
    return JsonCatalogTranslator(catalogs.value_or({}), language=language, fallback_language=LanguageEnum.ENGLISH)


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        (LanguageEnum.ENGLISH, "Language: A value has the wrong type."),
        (LanguageEnum.FRENCH, "Langue : Une valeur n'a pas le bon type."),
    ],
)
def test_field_level_message_contains_the_label(language: LanguageEnum, expected: str) -> None:
    result = ValidationResult.failure(ErrorCodeEnum.STORAGE_FIELD_INVALID_TYPE, field="settings.language")

    assert StorageMessages(_translator(language)).lines(result) == (expected,)


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        (LanguageEnum.ENGLISH, "The data file is damaged: syntax error at line 3, column 6."),
        (LanguageEnum.FRENCH, "Le fichier de données est endommagé : erreur de syntaxe ligne 3, colonne 6."),
    ],
)
def test_syntax_message_fills_its_position(language: LanguageEnum, expected: str) -> None:
    result = ValidationResult.failure(ErrorCodeEnum.STORAGE_SYNTAX_INVALID, line=3, column=6)

    assert StorageMessages(_translator(language)).lines(result) == (expected,)


@pytest.mark.parametrize(
    ("language", "count", "expected"),
    [
        (LanguageEnum.ENGLISH, 6, "and 1 more problem"),
        (LanguageEnum.ENGLISH, 7, "and 2 more problems"),
        (LanguageEnum.FRENCH, 6, "et 1 autre problème"),
        (LanguageEnum.FRENCH, 8, "et 3 autres problèmes"),
    ],
)
def test_hidden_issue_count_uses_the_plural_rules(language: LanguageEnum, count: int, expected: str) -> None:
    issues = [ValidationResult.failure(ErrorCodeEnum.STORAGE_FIELD_MISSING, field="settings.id") for _ in range(count)]

    lines = StorageMessages(_translator(language)).lines(issues[0].merge(*issues[1:]))

    assert lines[-1] == expected
