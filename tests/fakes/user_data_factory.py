"""Sample user data for tests (the values of the phase 1 to 4 spec examples)."""

from datetime import UTC, datetime
from typing import Final

from concentrator.application.settings.settings_defaults import SettingsDefaults
from concentrator.application.storage.user_data import StoredUserData, UserData, UserDataLimits
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.domain.settings.log_level_enum import LogLevelEnum
from concentrator.domain.settings.user_settings import UserSettings, UserSettingsId
from concentrator.domain.timer.timer_config import TimerConfig
from concentrator.domain.todo.task_lists_collection import TaskListsCollection
from tests.fakes.timer_extras_factory import make_chime, make_spec_presets
from tests.fakes.timer_factory import LIMITS, make_timer_config
from tests.fakes.todo_factory import TODO_LIMITS, make_spec_list

SETTINGS_ID: Final = UserSettingsId("019a5c1e-7a40-7c3e-9d5a-1f2b3c4d5e6f")
CREATED_AT: Final = datetime(2026, 11, 6, 16, 40, tzinfo=UTC)
UPDATED_AT: Final = datetime(2026, 11, 6, 16, 44, 3, tzinfo=UTC)
SAVED_AT: Final = datetime(2026, 11, 6, 16, 44, 3, tzinfo=UTC)
SETTINGS_DEFAULTS: Final = SettingsDefaults(log_level=LogLevelEnum.INFO, notify_when_inactive=True)
USER_DATA_LIMITS: Final = UserDataLimits(timer=LIMITS, settings=SETTINGS_DEFAULTS, todo=TODO_LIMITS)

SPEC_EXAMPLE_TEXT: Final = """\
# Concentrator user data. Schema version 1.
# Close Concentrator before editing this file by hand. Comments are not preserved.
schema_version = 1
saved_at = '2026-11-06T16:44:03Z'
app_version = '0.1.0'
tasks = []

[settings]
id = '019a5c1e-7a40-7c3e-9d5a-1f2b3c4d5e6f'
created_at = '2026-11-06T16:40:00Z'
updated_at = '2026-11-06T16:44:03Z'
language = 2
log_level = 2
notify_when_inactive = true

[timer]
id = '019a5c1f-0b2e-7d4a-8c61-2a3b4c5d6e7f'
created_at = '2026-11-06T16:40:00Z'
updated_at = '2026-11-06T16:50:12Z'
duration_seconds = 1500
sound = { kind = 2, value = 'D:/Music/Alarms/long alarm.mp3' }
volume = 80
loop_count = 3
loop_forever = false
auto_stop_seconds = 120
auto_restart = false

[[timer_presets]]
id = '019a5c20-1111-7aaa-8bbb-1c2d3e4f5a6b'
created_at = '2026-11-06T16:40:00Z'
updated_at = '2026-11-06T16:40:00Z'
label = ''
duration_seconds = 900
position = 0

[hourly_chime]
id = '019a5c20-2222-7ccc-8ddd-2d3e4f5a6b7c'
created_at = '2026-11-06T16:40:00Z'
updated_at = '2026-11-06T16:40:00Z'
enabled = false
sound = { kind = 1, value = 'chime' }
volume = 60
start_hour = 8
end_hour = 20

[[task_lists]]
id = '019a5c21-aaaa-7bbb-8ccc-3e4f5a6b7c8d'
created_at = '2026-11-06T16:41:00Z'
updated_at = '2026-11-06T16:41:00Z'
name = 'Work'
description = [
  'Client projects',
  'and admin',
]
priority = 3
position = 0
"""


def make_settings(
    language: LanguageEnum = LanguageEnum.FRENCH,
    log_level: LogLevelEnum = LogLevelEnum.INFO,
    *,
    notify_when_inactive: bool = True,
) -> UserSettings:
    return UserSettings(
        id=SETTINGS_ID,
        created_at=CREATED_AT,
        updated_at=UPDATED_AT,
        language=language,
        log_level=log_level,
        notify_when_inactive=notify_when_inactive,
    )


def make_user_data(language: LanguageEnum = LanguageEnum.FRENCH, timer: TimerConfig | None = None) -> UserData:
    return UserData.initial(
        make_settings(language),
        timer or make_timer_config(),
        make_spec_presets(),
        make_chime(),
        TaskListsCollection((make_spec_list(),)),
    )


def make_stored(language: LanguageEnum = LanguageEnum.FRENCH, saved_at: datetime = SAVED_AT) -> StoredUserData:
    return StoredUserData(data=make_user_data(language), saved_at=saved_at)
