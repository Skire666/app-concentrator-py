"""Snapshot of a control labelled by its action (``action.<name>`` catalog keys)."""

from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.button_snapshot import ButtonSnapshot
from concentrator.presentation.common.ui_texts import UiTexts


def action_button(
    texts: UiTexts, gate: ActionGate, action: ActionIdEnum, *, enabled: bool = True, checked: bool = False
) -> ButtonSnapshot:
    """Describe a button, menu item or check box bound to an action.

    Args:
        texts: Translates the action label and tooltip.
        gate: Busy state of the action (its control is disabled while busy).
        action: Action requested by the control.
        enabled: Whether the current state allows the action.
        checked: Checked state of a check box.

    Returns:
        The snapshot.
    """
    return ButtonSnapshot(
        text=texts.action_label(action),
        tooltip=texts.action_tooltip(action),
        enabled=enabled and not gate.is_busy(action),
        visible=True,
        action=action,
        checked=checked,
    )
