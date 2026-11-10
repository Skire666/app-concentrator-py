"""Identifiers of user actions (buttons, menu items, shortcuts)."""

from concentrator.domain.common.base_int_enum import BaseIntEnum


class ActionIdEnum(BaseIntEnum):
    """Every user action. Later phases append values; values are never renumbered.

    27 and 28 (notification area menu, removed at the phase 2 review, ADR-038), 33 and 34 (moving a
    favorite, removed at the phase 3 review, ADR-039) are never reused.

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
    TIMER_EDIT = 15
    TIMER_START = 16
    TIMER_PAUSE = 17
    TIMER_RESUME = 18
    TIMER_RESET = 19
    TIMER_ACKNOWLEDGE = 20
    TIMER_RESTART = 21
    TIMER_SNOOZE = 22
    TIMER_EDIT_SAVE = 23
    TIMER_EDIT_CANCEL = 24
    TIMER_SOUND_PREVIEW = 25
    TIMER_SOUND_CHOOSE_FILE = 26
    PRESET_APPLY = 29
    PRESET_ADD = 30
    PRESET_EDIT = 31
    PRESET_DELETE = 32
    PRESET_EDIT_SAVE = 35
    PRESET_EDIT_CANCEL = 36
    CHIME_TOGGLE = 37
    CHIME_EDIT = 38
    CHIME_EDIT_SAVE = 39
    CHIME_EDIT_CANCEL = 40
    CHIME_PREVIEW = 41
    CHIME_SOUND_CHOOSE_FILE = 42
    JOURNAL_TOGGLE_LEVEL = 43
    JOURNAL_SEARCH = 44
    JOURNAL_TOGGLE_FOLLOW = 45
    JOURNAL_TOGGLE_PAUSE = 46
    JOURNAL_COPY = 47
    JOURNAL_CLEAR_VIEW = 48
    JOURNAL_OPEN_LOG_FOLDER = 49
    SETTINGS_SAVE = 50
    SETTINGS_REVERT = 51
    SETTINGS_SWITCH_DATA_FILE = 52
    SETTINGS_MOVE_DATA_FILE = 53
    SETTINGS_OPEN_FOLDER = 54
    SETTINGS_RESET_LAYOUT = 55
    SETTINGS_CHIME_PREVIEW = 56
    SETTINGS_CHIME_SOUND_CHOOSE_FILE = 57
    STARTUP_CANCEL = 58
    LIST_ADD = 59
    LIST_EDIT = 60
    LIST_DELETE = 61
    LIST_MOVE_EARLIER = 62
    LIST_MOVE_LATER = 63
    LIST_SELECT = 64
    TASK_NEW = 65
    TASK_QUICK_ADD = 66
    TASK_EDIT = 67
    TASK_COMPLETE = 68
    TASK_REOPEN = 69
    TASK_TOGGLE_DONE = 70
    TASK_ARCHIVE = 71
    TASK_UNARCHIVE = 72
    TASK_DUPLICATE = 73
    TASK_MOVE = 74
    TASK_DELETE = 75
    TASK_EDIT_SAVE = 76
    TASK_EDIT_CANCEL = 77
    LIST_EDIT_SAVE = 78
    LIST_EDIT_CANCEL = 79
    TODO_TOGGLE_SHOW_DONE = 80
    TODO_TOGGLE_SHOW_ARCHIVED = 81
    TODO_SORT = 82
