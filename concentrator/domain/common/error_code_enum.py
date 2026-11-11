"""Error codes carried by validation issues.

Ranges: ``1xxx`` common validation, ``2xxx`` storage, ``3xxx`` config and i18n, ``4xxx`` timer,
``5xxx`` todo, ``6xxx`` focus, ``7xxx`` system. Every code has the UI message key
``error.<name_lowercase>`` in both catalogs.
"""

from typing import Final

from concentrator.domain.common.base_int_enum import BaseIntEnum
from concentrator.domain.common.error_category_enum import ErrorCategoryEnum

_CATEGORY_RANGE_SIZE: Final = 1000


class ErrorCodeEnum(BaseIntEnum):
    """Every expected failure of the application. Values are never renumbered or reused."""

    UNKNOWN = -1
    UNSET = 0

    # 1xxx common validation
    REQUIRED_VALUE_MISSING = 1001
    VALUE_OUT_OF_RANGE = 1002
    TEXT_TOO_LONG = 1003
    FORMAT_INVALID = 1004
    ENTITY_NOT_FOUND = 1005
    ENTITY_DUPLICATE_ID = 1006
    ENUM_VALUE_UNSET = 1007
    ENUM_VALUE_UNKNOWN = 1008
    DATETIME_NOT_UTC = 1009

    # 2xxx storage (2020 is retired and never reused, ADR-035)
    STORAGE_FILE_NOT_FOUND = 2001
    STORAGE_FILE_UNREADABLE = 2002
    STORAGE_ENCODING_INVALID = 2003
    STORAGE_SYNTAX_INVALID = 2004
    STORAGE_FIELD_MISSING = 2005
    STORAGE_FIELD_UNEXPECTED = 2006
    STORAGE_FIELD_INVALID_TYPE = 2007
    STORAGE_FIELD_INVALID_VALUE = 2008
    STORAGE_SCHEMA_VERSION_UNSUPPORTED = 2009
    STORAGE_WRITE_FAILED = 2010
    STORAGE_VERIFY_FAILED = 2011
    STORAGE_REPLACE_FAILED = 2012
    STORAGE_BACKUP_FAILED = 2013
    STORAGE_FLUSH_TIMEOUT = 2014
    STORAGE_FILE_ALREADY_EXISTS = 2015
    STORAGE_DIRECTORY_NOT_WRITABLE = 2016
    STORAGE_DISK_FULL = 2017
    STORAGE_TARGET_IS_CURRENT_FILE = 2018
    STORAGE_MOVE_FAILED = 2019
    STORAGE_FILE_CHANGED_EXTERNALLY = 2021

    # 3xxx configuration
    CONFIG_FILE_NOT_FOUND = 3001
    CONFIG_SYNTAX_INVALID = 3002
    CONFIG_KEY_MISSING = 3003
    CONFIG_VALUE_INVALID = 3004
    CONFIG_KEY_UNEXPECTED = 3005

    # 31xx i18n catalogs
    CATALOG_FILE_NOT_FOUND = 3101
    CATALOG_SYNTAX_INVALID = 3102
    CATALOG_KEY_MISSING = 3103

    # 4xxx timer
    TIMER_DURATION_TOO_SHORT = 4001
    TIMER_DURATION_TOO_LONG = 4002
    TIMER_VOLUME_OUT_OF_RANGE = 4003
    TIMER_LOOP_COUNT_OUT_OF_RANGE = 4004
    TIMER_AUTO_STOP_OUT_OF_RANGE = 4005
    TIMER_TRANSITION_INVALID = 4006
    TIMER_SOUND_UNSET = 4007

    # 41xx timer favorites
    PRESET_DURATION_DUPLICATE = 4101
    PRESET_LABEL_TOO_LONG = 4102
    PRESET_LIMIT_REACHED = 4103
    PRESET_LABEL_CHARACTER_INVALID = 4104

    # 42xx hourly chime
    CHIME_HOUR_OUT_OF_RANGE = 4201
    CHIME_HOURS_REVERSED = 4202

    # 5xxx tasks
    TASK_TEXT_EMPTY = 5001
    TASK_TEXT_TOO_LONG = 5002
    TASK_DUE_TIME_WITHOUT_DATE = 5003
    TASK_STATE_TRANSITION_INVALID = 5004
    TASK_LIST_NOT_FOUND = 5005

    # 51xx task lists
    LIST_NAME_EMPTY = 5101
    LIST_NAME_TOO_LONG = 5102
    LIST_NAME_DUPLICATE = 5103
    LIST_DESCRIPTION_TOO_LONG = 5104
    LIST_NOT_EMPTY = 5105
    LIST_LAST_CANNOT_DELETE = 5106
    LIST_PRIORITY_UNSET = 5107

    # 52xx task recurrence
    RECURRENCE_REQUIRES_DUE_DATE = 5201
    RECURRENCE_INTERVAL_OUT_OF_RANGE = 5202
    RECURRENCE_WEEKDAYS_EMPTY = 5203
    RECURRENCE_END_DATE_BEFORE_DUE = 5204
    RECURRENCE_COUNT_OUT_OF_RANGE = 5205
    RECURRENCE_FREQUENCY_UNSET = 5206
    RECURRENCE_END_KIND_UNSET = 5207
    RECURRENCE_END_DATE_MISSING = 5208

    # 70xx links and folders
    LINK_OPEN_FAILED = 7003

    # 71xx audio
    AUDIO_FILE_NOT_FOUND = 7101
    AUDIO_FORMAT_UNSUPPORTED = 7102
    AUDIO_PLAYBACK_FAILED = 7103
    AUDIO_DEVICE_UNAVAILABLE = 7104

    # 72xx process and Windows shell (7204 is retired and never reused: no Windows notification, ADR-038)
    INSTANCE_LOCK_FAILED = 7201
    INSTANCE_SERVER_FAILED = 7202
    APP_USER_MODEL_ID_FAILED = 7203

    @property
    def category(self) -> ErrorCategoryEnum:
        """Category derived from the thousands digit (``UNKNOWN``/``UNSET`` map to the same members)."""
        return ErrorCategoryEnum.parse(self.value // _CATEGORY_RANGE_SIZE)
