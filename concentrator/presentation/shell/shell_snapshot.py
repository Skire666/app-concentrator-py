"""Snapshots of the window shell: module bar and pages (``SHELL``) and status bar (``STATUS_BAR``)."""

from dataclasses import dataclass

from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.button_snapshot import ButtonSnapshot


@dataclass(frozen=True, slots=True, kw_only=True)
class ModuleButtonSnapshot:
    """One button of the module bar.

    Attributes:
        text: Translated label.
        tooltip: Translated tooltip.
        checked: Whether its page is the active one.
        highlighted: Whether it asks for attention (for example a ringing timer on another page).
        enabled: False while its action is busy.
        action: Page action requested on click.
        badge: Small count shown on the button (new errors for the Journal), ``""`` for none.
    """

    text: str
    tooltip: str
    checked: bool
    highlighted: bool
    enabled: bool
    action: ActionIdEnum
    badge: str = ""


@dataclass(frozen=True, slots=True, kw_only=True)
class ShellSnapshot:
    """Window title, module bar and active page.

    Attributes:
        window_title: Translated window title.
        module_buttons: Focus, Journal and Settings buttons, in bar order.
        active_page_index: Index of the visible page, in the same order.
    """

    window_title: str
    module_buttons: tuple[ModuleButtonSnapshot, ...]
    active_page_index: int


@dataclass(frozen=True, slots=True, kw_only=True)
class StatusBarSnapshot:
    """The one-line status bar.

    Attributes:
        save_state_text: Translated state of the last save.
        save_state_tooltip: Data file path and issues of the last save.
        instance_warning_text: Unguarded single-instance indicator, ``""`` when protected (ADR-031).
        instance_warning_tooltip: Its explanation.
        language_button: Shows the current language (``ENG``/``FRA``) and toggles it.
    """

    save_state_text: str
    save_state_tooltip: str
    instance_warning_text: str
    instance_warning_tooltip: str
    language_button: ButtonSnapshot
