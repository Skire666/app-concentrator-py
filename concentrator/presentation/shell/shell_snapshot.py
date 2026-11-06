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
    """

    text: str
    tooltip: str
    checked: bool
    highlighted: bool
    enabled: bool
    action: ActionIdEnum


@dataclass(frozen=True, slots=True, kw_only=True)
class ShellSnapshot:
    """Window title, module bar and active page.

    Attributes:
        window_title: Translated window title.
        module_buttons: Focus, Journal and Settings buttons, in bar order.
        active_page_index: Index of the visible page, in the same order.
        focus_zone1_placeholder: Temporary text of zone 1 until the TODO manager exists (phase 5).
        focus_zone2_placeholder: Temporary text of zone 2 until the timer exists (phase 2).
        journal_placeholder: Temporary text of the Journal page (phase 4).
        settings_placeholder: Temporary text of the Settings page (phase 4).
    """

    window_title: str
    module_buttons: tuple[ModuleButtonSnapshot, ...]
    active_page_index: int
    focus_zone1_placeholder: str
    focus_zone2_placeholder: str
    journal_placeholder: str
    settings_placeholder: str


@dataclass(frozen=True, slots=True, kw_only=True)
class StatusBarSnapshot:
    """The one-line status bar.

    Attributes:
        save_state_text: Translated state of the last save.
        language_button: Shows the current language (``ENG``/``FRA``) and toggles it.
    """

    save_state_text: str
    language_button: ButtonSnapshot
