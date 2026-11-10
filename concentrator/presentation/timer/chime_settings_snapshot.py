"""Snapshots of the special options panel (``SPECIAL_OPTIONS``) and of the chime dialog (``CHIME_EDIT``)."""

from dataclasses import dataclass

from concentrator.presentation.common.button_snapshot import ButtonSnapshot
from concentrator.presentation.timer.timer_edit_snapshot import SoundPickerSnapshot, VolumeInputSnapshot


@dataclass(frozen=True, slots=True, kw_only=True)
class SpecialOptionsSnapshot:
    """The special options block of zone 2.

    Attributes:
        title: Block title.
        chime: "Chime every hour" check box (``checked`` is the stored switch).
        chime_hours: Active hours of the chime, for example ``08:00 - 20:00`` (catalog ``chime.hours``).
        chime_edit: "..." button opening the chime dialog.
    """

    title: str
    chime: ButtonSnapshot
    chime_hours: str
    chime_edit: ButtonSnapshot


@dataclass(frozen=True, slots=True, kw_only=True)
class HourRangeSnapshot:
    """First and last full hour that chime.

    Attributes:
        start_label: Label of the first hour list.
        end_label: Label of the last hour list.
        options: ``00:00`` to ``23:00``; the index of an option is its hour.
        start: Index of the first hour.
        end: Index of the last hour.
        start_error: Inline message of the first hour, ``""`` when valid.
        end_error: Inline message of the last hour, ``""`` when valid.
    """

    start_label: str
    end_label: str
    options: tuple[str, ...]
    start: int
    end: int
    start_error: str
    end_error: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ChimeFieldsSnapshot:
    """The four chime fields, shown by the chime dialog and by the settings page.

    Attributes:
        sound: Sound field.
        volume: Volume field and "Preview".
        hours: Active hours.
    """

    sound: SoundPickerSnapshot
    volume: VolumeInputSnapshot
    hours: HourRangeSnapshot


@dataclass(frozen=True, slots=True, kw_only=True)
class ChimeSettingsSnapshot:
    """Everything the chime dialog shows.

    Attributes:
        title: Window title.
        fields: Sound, volume and active hours.
        hint: How the hours are used.
        save: Save button (enabled when the draft changed and is valid).
        cancel: Cancel button.
    """

    title: str
    fields: ChimeFieldsSnapshot
    hint: str
    save: ButtonSnapshot
    cancel: ButtonSnapshot
