"""Identifiers of user actions (buttons, menu items, shortcuts)."""

from concentrator.domain.common.base_int_enum import BaseIntEnum


class ActionIdEnum(BaseIntEnum):
    """Every user action. Later phases append values; values are never renumbered.

    The label of a control bound to an action is the catalog key ``action.<name_lowercase>``, with an
    optional ``action.<name_lowercase>.tooltip``.
    """

    UNKNOWN = -1
    UNSET = 0
    SHELL_SHOW_FOCUS = 1
    SHELL_SHOW_JOURNAL = 2
    SHELL_SHOW_SETTINGS = 3
    SHELL_TOGGLE_LANGUAGE = 4
    STARTUP_USE_DEFAULT_FILE = 5
    STARTUP_CREATE_DEFAULT_FILE = 6
    STARTUP_CREATE_FILE_ELSEWHERE = 7
    STARTUP_OPEN_EXISTING_FILE = 8
    STARTUP_RETRY = 9
    STARTUP_QUIT = 10
    STARTUP_RESTORE = 11
    STARTUP_KEEP_CURRENT_FILE = 12
    STARTUP_CHOOSE_ANOTHER_FILE = 13
    STARTUP_START_EMPTY = 14
