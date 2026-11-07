"""Which render sections show the controls bound to each action.

``ActionGate`` requests only these sections when an action becomes busy or is released, so a click
never rebuilds unrelated snapshots. ``RenderCoordinator.request_all()`` stays reserved for language
changes and data file switches. A test checks that every action is mapped.
"""

from types import MappingProxyType
from typing import Final

from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.render_section_enum import RenderSectionEnum

ACTION_SECTIONS: Final = MappingProxyType(
    {
        ActionIdEnum.SHELL_SHOW_FOCUS: (RenderSectionEnum.SHELL,),
        ActionIdEnum.SHELL_SHOW_JOURNAL: (RenderSectionEnum.SHELL,),
        ActionIdEnum.SHELL_SHOW_SETTINGS: (RenderSectionEnum.SHELL,),
        ActionIdEnum.SHELL_TOGGLE_LANGUAGE: (RenderSectionEnum.STATUS_BAR,),
        ActionIdEnum.STARTUP_USE_DEFAULT_FILE: (RenderSectionEnum.FIRST_RUN,),
        ActionIdEnum.STARTUP_CREATE_DEFAULT_FILE: (RenderSectionEnum.FIRST_RUN,),
        ActionIdEnum.STARTUP_CREATE_FILE_ELSEWHERE: (RenderSectionEnum.FIRST_RUN,),
        ActionIdEnum.STARTUP_OPEN_EXISTING_FILE: (RenderSectionEnum.FIRST_RUN,),
        ActionIdEnum.STARTUP_RETRY: (RenderSectionEnum.FIRST_RUN, RenderSectionEnum.RECOVERY),
        ActionIdEnum.STARTUP_QUIT: (RenderSectionEnum.FIRST_RUN, RenderSectionEnum.RECOVERY),
        ActionIdEnum.STARTUP_RESTORE: (RenderSectionEnum.RECOVERY,),
        ActionIdEnum.STARTUP_KEEP_CURRENT_FILE: (RenderSectionEnum.RECOVERY,),
        ActionIdEnum.STARTUP_CHOOSE_ANOTHER_FILE: (RenderSectionEnum.RECOVERY,),
        ActionIdEnum.STARTUP_START_EMPTY: (RenderSectionEnum.RECOVERY,),
        ActionIdEnum.TIMER_EDIT: (RenderSectionEnum.TIMER,),
        ActionIdEnum.TIMER_START: (RenderSectionEnum.TIMER,),
        ActionIdEnum.TIMER_PAUSE: (RenderSectionEnum.TIMER,),
        ActionIdEnum.TIMER_RESUME: (RenderSectionEnum.TIMER,),
        ActionIdEnum.TIMER_RESET: (RenderSectionEnum.TIMER,),
        ActionIdEnum.TIMER_ACKNOWLEDGE: (RenderSectionEnum.TIMER,),
        ActionIdEnum.TIMER_RESTART: (RenderSectionEnum.TIMER,),
        ActionIdEnum.TIMER_SNOOZE: (RenderSectionEnum.TIMER,),
        ActionIdEnum.TIMER_EDIT_SAVE: (RenderSectionEnum.TIMER_EDIT,),
        ActionIdEnum.TIMER_EDIT_CANCEL: (RenderSectionEnum.TIMER_EDIT,),
        ActionIdEnum.TIMER_SOUND_PREVIEW: (RenderSectionEnum.TIMER_EDIT,),
        ActionIdEnum.TIMER_SOUND_CHOOSE_FILE: (RenderSectionEnum.TIMER_EDIT,),
        ActionIdEnum.TRAY_SHOW: (RenderSectionEnum.TRAY,),
        ActionIdEnum.TRAY_QUIT: (RenderSectionEnum.TRAY,),
    }
)


def sections_for(action: ActionIdEnum) -> tuple[RenderSectionEnum, ...]:
    """Return the sections displaying the controls bound to an action.

    Args:
        action: Action.

    Returns:
        The sections, empty for an unmapped action.
    """
    return ACTION_SECTIONS.get(action, ())
