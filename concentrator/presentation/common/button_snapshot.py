"""Display state of a button."""

from dataclasses import dataclass

from concentrator.presentation.common.action_id_enum import ActionIdEnum


@dataclass(frozen=True, slots=True, kw_only=True)
class ButtonSnapshot:
    """Everything a button shows; the panel emits ``action_requested(int(action))`` on click.

    Attributes:
        text: Translated label.
        tooltip: Translated tooltip, ``""`` for none.
        enabled: Whether the button can be clicked (false while its action is busy).
        visible: Whether the button is shown.
        action: Action requested on click.
        checked: Checked state of a checkable button.
    """

    text: str
    tooltip: str
    enabled: bool
    visible: bool
    action: ActionIdEnum
    checked: bool = False
