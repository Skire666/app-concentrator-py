"""Sample user data for tests (the values of the phase 1 spec example)."""

from datetime import UTC, datetime
from typing import Final

from concentrator.application.storage.user_data import StoredUserData, UserData
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.domain.settings.user_settings import UserSettings, UserSettingsId

SETTINGS_ID: Final = UserSettingsId("019a5c1e-7a40-7c3e-9d5a-1f2b3c4d5e6f")
CREATED_AT: Final = datetime(2026, 11, 6, 16, 40, tzinfo=UTC)
UPDATED_AT: Final = datetime(2026, 11, 6, 16, 44, 3, tzinfo=UTC)
SAVED_AT: Final = datetime(2026, 11, 6, 16, 44, 3, tzinfo=UTC)

SPEC_EXAMPLE_TEXT: Final = """\
# Concentrator user data. Schema version 1.
# Close Concentrator before editing this file by hand. Comments are not preserved.
schema_version = 1
saved_at = '2026-11-06T16:44:03Z'
app_version = '0.1.0'

[settings]
id = '019a5c1e-7a40-7c3e-9d5a-1f2b3c4d5e6f'
created_at = '2026-11-06T16:40:00Z'
updated_at = '2026-11-06T16:44:03Z'
language = 2
"""


def make_settings(language: LanguageEnum = LanguageEnum.FRENCH) -> UserSettings:
    return UserSettings(id=SETTINGS_ID, created_at=CREATED_AT, updated_at=UPDATED_AT, language=language)


def make_user_data(language: LanguageEnum = LanguageEnum.FRENCH) -> UserData:
    return UserData.initial(make_settings(language))


def make_stored(language: LanguageEnum = LanguageEnum.FRENCH, saved_at: datetime = SAVED_AT) -> StoredUserData:
    return StoredUserData(data=make_user_data(language), saved_at=saved_at)
