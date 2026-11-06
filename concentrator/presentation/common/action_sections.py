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
