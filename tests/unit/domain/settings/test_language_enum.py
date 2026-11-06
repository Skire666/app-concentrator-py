import pytest

from concentrator.domain.settings.language_enum import LanguageEnum


@pytest.mark.parametrize(
    ("language", "expected"),
    [(LanguageEnum.ENGLISH, "en"), (LanguageEnum.FRENCH, "fr"), (LanguageEnum.UNSET, ""), (LanguageEnum.UNKNOWN, "")],
)
def test_iso_code(language: LanguageEnum, expected: str) -> None:
    assert language.iso_code == expected


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("en", LanguageEnum.ENGLISH),
        (" FR ", LanguageEnum.FRENCH),
        ("de", LanguageEnum.UNKNOWN),
        ("", LanguageEnum.UNKNOWN),
    ],
)
def test_from_iso_code(code: str, expected: LanguageEnum) -> None:
    assert LanguageEnum.from_iso_code(code) is expected
