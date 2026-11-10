from datetime import UTC, datetime, timedelta

import pytest

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.settings.general_settings import GeneralSettings
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.domain.settings.log_level_enum import LogLevelEnum
from concentrator.domain.settings.user_settings import UserSettings, UserSettingsId
from concentrator.domain.settings.user_settings_rules import UserSettingsRules

NOW = datetime(2026, 11, 6, 16, 40, tzinfo=UTC)
SETTINGS_ID = UserSettingsId("019a5c1e-7a40-7c3e-9d5a-1f2b3c4d5e6f")


def _general(
    language: LanguageEnum = LanguageEnum.ENGLISH, log_level: LogLevelEnum = LogLevelEnum.INFO
) -> GeneralSettings:
    return GeneralSettings(language=language, log_level=log_level, notify_when_inactive=True)


def test_create_sets_both_timestamps_to_now() -> None:
    settings = UserSettings.create(SETTINGS_ID, NOW, _general(LanguageEnum.FRENCH))

    assert settings.id == SETTINGS_ID
    assert settings.created_at == settings.updated_at == NOW
    assert settings.language is LanguageEnum.FRENCH
    assert settings.log_level is LogLevelEnum.INFO
    assert settings.notify_when_inactive is True


def test_with_language_returns_a_changed_copy() -> None:
    settings = UserSettings.create(SETTINGS_ID, NOW, _general())
    later = NOW + timedelta(minutes=4)

    changed = settings.with_language(LanguageEnum.FRENCH, later)

    assert changed.language is LanguageEnum.FRENCH
    assert changed.updated_at == later
    assert changed.created_at == NOW
    assert settings.language is LanguageEnum.ENGLISH


def test_with_general_replaces_the_three_values() -> None:
    settings = UserSettings.create(SETTINGS_ID, NOW, _general())
    later = NOW + timedelta(minutes=4)
    general = GeneralSettings(language=LanguageEnum.FRENCH, log_level=LogLevelEnum.DEBUG, notify_when_inactive=False)

    changed = settings.with_general(general, later)

    assert changed.general == general
    assert changed.updated_at == later
    assert settings.general == _general()


def test_rules_accept_valid_settings() -> None:
    assert UserSettingsRules.validate(UserSettings.create(SETTINGS_ID, NOW, _general())).is_success


@pytest.mark.parametrize(
    ("language", "code"),
    [(LanguageEnum.UNSET, ErrorCodeEnum.ENUM_VALUE_UNSET), (LanguageEnum.UNKNOWN, ErrorCodeEnum.ENUM_VALUE_UNKNOWN)],
)
def test_rules_reject_unset_or_unknown_language(language: LanguageEnum, code: ErrorCodeEnum) -> None:
    result = UserSettingsRules.validate(UserSettings.create(SETTINGS_ID, NOW, _general(language)))

    assert result.error_codes == (code,)
    assert result.issues[0].field == "language"


@pytest.mark.parametrize(
    ("log_level", "code"),
    [(LogLevelEnum.UNSET, ErrorCodeEnum.ENUM_VALUE_UNSET), (LogLevelEnum.UNKNOWN, ErrorCodeEnum.ENUM_VALUE_UNKNOWN)],
)
def test_rules_reject_unset_or_unknown_log_level(log_level: LogLevelEnum, code: ErrorCodeEnum) -> None:
    result = UserSettingsRules.validate_general(_general(log_level=log_level))

    assert result.error_codes == (code,)
    assert result.issues[0].field == "log_level"


def test_rules_include_identity_checks() -> None:
    settings = UserSettings.create(UserSettingsId(""), NOW.replace(tzinfo=None), _general())

    result = UserSettingsRules.validate(settings)

    assert ErrorCodeEnum.REQUIRED_VALUE_MISSING in result.error_codes
    assert ErrorCodeEnum.DATETIME_NOT_UTC in result.error_codes
