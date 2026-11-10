"""Locations the settings page can open in the file explorer."""

from concentrator.domain.common.base_int_enum import BaseIntEnum


class SettingsFolderEnum(BaseIntEnum):
    """One member per "Open folder" button."""

    UNKNOWN = -1
    UNSET = 0
    DATA_FILE = 1
    APP_CONFIG = 2
    UI_STATE = 3
    LOG = 4
    BACKUP = 5
