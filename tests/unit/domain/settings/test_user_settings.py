from datetime import UTC, datetime, timedelta

import pytest

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.domain.settings.user_settings import UserSettings, UserSettingsId
from concentrator.domain.settings.user_settings_rules import UserSettingsRules

NOW = datetime(2026, 11, 6, 16, 40, tzinfo=UTC)
SETTINGS_ID = UserSettingsId("019a5c1e-7a40-7c3e-9d5a-1f2b3c4d5e6f")


def test_create_sets_both_timestamps_to_now() -> None:
    settings = UserSettings.create(SETTINGS_ID, NOW, LanguageEnum.FRENCH)

    assert settings.id == SETTINGS_ID
    assert settings.created_at == settings.updated_at == NOW
    assert settings.language is LanguageEnum.FRENCH


def test_with_language_returns_a_changed_copy() -> None:
    settings = UserSettings.create(SETTINGS_ID, NOW, LanguageEnum.ENGLISH)
    later = NOW + timedelta(minutes=4)

    changed = settings.with_language(LanguageEnum.FRENCH, later)

    assert changed.language is LanguageEnum.FRENCH
    assert changed.updated_at == later
    assert changed.created_at == NOW
    assert settings.language is LanguageEnum.ENGLISH


def test_rules_accept_valid_settings() -> None:
    assert UserSettingsRules.validate(UserSettings.create(SETTINGS_ID, NOW, LanguageEnum.ENGLISH)).is_success


@pytest.mark.parametrize(
    ("language", "code"),
    [(LanguageEnum.UNSET, ErrorCodeEnum.ENUM_VALUE_UNSET), (LanguageEnum.UNKNOWN, ErrorCodeEnum.ENUM_VALUE_UNKNOWN)],
)
def test_rules_reject_unset_or_unknown_language(language: LanguageEnum, code: ErrorCodeEnum) -> None:
    result = UserSettingsRules.validate(UserSettings.create(SETTINGS_ID, NOW, language))

    assert result.error_codes == (code,)
    assert result.issues[0].field == "language"


def test_rules_include_identity_checks() -> None:
    settings = UserSettings.create(UserSettingsId(""), NOW.replace(tzinfo=None), LanguageEnum.ENGLISH)

    result = UserSettingsRules.validate(settings)

    assert ErrorCodeEnum.REQUIRED_VALUE_MISSING in result.error_codes
    assert ErrorCodeEnum.DATETIME_NOT_UTC in result.error_codes
