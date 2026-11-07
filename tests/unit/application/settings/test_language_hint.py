import pytest

from concentrator.application.settings.language_hint import LANGUAGE_HINT_KEY, LanguageHint
from concentrator.domain.settings.language_enum import LanguageEnum
from tests.fakes.in_memory_view_preferences import InMemoryViewPreferences


def test_key_is_outside_the_layout_prefix() -> None:
    assert LANGUAGE_HINT_KEY == "shell/language_hint"
    assert not LANGUAGE_HINT_KEY.startswith("layout/")


@pytest.mark.parametrize(
    ("stored", "expected"),
    [
        (None, LanguageEnum.UNSET),
        ("fr", LanguageEnum.FRENCH),
        ("en", LanguageEnum.ENGLISH),
        ("de", LanguageEnum.UNKNOWN),
    ],
)
def test_read(stored: str | None, expected: LanguageEnum) -> None:
    preferences = InMemoryViewPreferences({} if stored is None else {LANGUAGE_HINT_KEY: stored})

    assert LanguageHint(preferences).read() is expected


def test_write_stores_the_iso_code_and_ignores_unset_values() -> None:
    preferences = InMemoryViewPreferences()
    hint = LanguageHint(preferences)

    hint.write(LanguageEnum.FRENCH)
    hint.write(LanguageEnum.UNKNOWN)
    hint.write(LanguageEnum.UNSET)

    assert preferences.values == {LANGUAGE_HINT_KEY: "fr"}
