"""Actions that share their busy state in ``ActionGate`` (ADR-038).

The three timer buttons change action with the timer state: after a click on Start, the same button
shows Pause. Grouping the actions of those buttons gives each physical button its cooldown, whatever
action it shows next; a click on an enabled button always counts.
"""

from types import MappingProxyType
from typing import Final

from concentrator.presentation.common.action_id_enum import ActionIdEnum

TIMER_BUTTON_ACTIONS: Final = frozenset(
    {
        ActionIdEnum.TIMER_EDIT,
        ActionIdEnum.TIMER_START,
        ActionIdEnum.TIMER_PAUSE,
        ActionIdEnum.TIMER_RESUME,
        ActionIdEnum.TIMER_RESET,
        ActionIdEnum.TIMER_ACKNOWLEDGE,
        ActionIdEnum.TIMER_RESTART,
        ActionIdEnum.TIMER_SNOOZE,
    }
)
ACTION_GROUPS: Final = MappingProxyType(dict.fromkeys(TIMER_BUTTON_ACTIONS, TIMER_BUTTON_ACTIONS))


def group_of(action: ActionIdEnum) -> frozenset[ActionIdEnum]:
    """Return the actions sharing the busy state of an action.

    Args:
        action: Action.

    Returns:
        Its group, or the action alone.
    """
    return ACTION_GROUPS.get(action, frozenset({action}))
