"""Snapshot of the favorite dialog (``PRESET_EDIT``)."""

from dataclasses import dataclass

from concentrator.presentation.common.button_snapshot import ButtonSnapshot
from concentrator.presentation.timer.timer_edit_snapshot import DurationInputSnapshot


@dataclass(frozen=True, slots=True, kw_only=True)
class LabelInputSnapshot:
    """Label of the favorite.

    Attributes:
        label: Field label.
        text: Label of the draft, as typed.
        placeholder: Automatic label shown while the field is empty.
        blocked_characters: Characters the field refuses to take.
        error: Inline message, ``""`` when valid.
    """

    label: str
    text: str
    placeholder: str
    blocked_characters: str
    error: str


@dataclass(frozen=True, slots=True, kw_only=True)
class PresetEditSnapshot:
    """Everything the favorite dialog shows.

    Attributes:
        title: Window title ("New favorite" or "Edit favorite").
        label: Label field.
        duration: Duration field.
        save: Save button.
        cancel: Cancel button.
    """

    title: str
    label: LabelInputSnapshot
    duration: DurationInputSnapshot
    save: ButtonSnapshot
    cancel: ButtonSnapshot
