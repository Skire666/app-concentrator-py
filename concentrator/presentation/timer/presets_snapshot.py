"""Snapshot of the favorites panel (``PRESETS``)."""

from dataclasses import dataclass

from concentrator.presentation.common.button_snapshot import ButtonSnapshot


@dataclass(frozen=True, slots=True, kw_only=True)
class PresetSnapshot:
    """One favorite button and its context menu.

    Attributes:
        preset_id: Id sent back with the action.
        button: Label (or automatic label), tooltip, enabled except during the cooldown; ``PRESET_APPLY``.
        menu: Edit, Delete.
    """

    preset_id: str
    button: ButtonSnapshot
    menu: tuple[ButtonSnapshot, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class PresetsSnapshot:
    """Everything the favorites panel shows.

    Attributes:
        title: Panel title.
        presets: Favorites in display order.
        add: "Add..." button (disabled at ``timer.max_presets``).
        empty_text: Shown when there is no favorite, ``""`` otherwise.
    """

    title: str
    presets: tuple[PresetSnapshot, ...]
    add: ButtonSnapshot
    empty_text: str
