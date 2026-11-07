"""Snapshot of the timer edit dialog (``TIMER_EDIT``)."""

from dataclasses import dataclass

from concentrator.presentation.common.button_snapshot import ButtonSnapshot


@dataclass(frozen=True, slots=True, kw_only=True)
class DurationInputSnapshot:
    """Hours, minutes and seconds of the countdown.

    Attributes:
        label: Field label.
        hours: Hours of the draft.
        minutes: Minutes of the draft.
        seconds: Seconds of the draft.
        max_hours: Highest hour value (from ``timer.max_duration_seconds``).
        hours_unit: Unit shown after the hours.
        minutes_unit: Unit shown after the minutes.
        seconds_unit: Unit shown after the seconds.
        error: Inline message, ``""`` when valid.
    """

    label: str
    hours: int
    minutes: int
    seconds: int
    max_hours: int
    hours_unit: str
    minutes_unit: str
    seconds_unit: str
    error: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SoundPickerSnapshot:
    """Alarm sound: built-in sounds and the files chosen in this dialog.

    Attributes:
        label: Field label.
        options: Text of each choice.
        tooltips: Tooltip of each choice (the full path of a file).
        selected: Index of the draft's sound.
        choose_file: "Choose an MP3 file..." button.
        error: Inline message, ``""`` when valid.
    """

    label: str
    options: tuple[str, ...]
    tooltips: tuple[str, ...]
    selected: int
    choose_file: ButtonSnapshot
    error: str


@dataclass(frozen=True, slots=True, kw_only=True)
class VolumeInputSnapshot:
    """Alarm volume.

    Attributes:
        label: Field label.
        value: Volume of the draft, in percent.
        maximum: Highest value.
        value_text: Value shown next to the slider.
        preview: "Preview" button.
        error: Inline message, ``""`` when valid.
    """

    label: str
    value: int
    maximum: int
    value_text: str
    preview: ButtonSnapshot
    error: str


@dataclass(frozen=True, slots=True, kw_only=True)
class LoopInputSnapshot:
    """Play count or "Repeat until stopped".

    Attributes:
        label: Field label.
        count: Play count of the draft.
        maximum: Highest play count.
        count_enabled: Whether the count can be edited (not when repeating until stopped).
        forever_label: Label of the "Repeat until stopped" check box.
        forever: Whether the sound repeats until stopped.
        error: Inline message, ``""`` when valid.
    """

    label: str
    count: int
    maximum: int
    count_enabled: bool
    forever_label: str
    forever: bool
    error: str


@dataclass(frozen=True, slots=True, kw_only=True)
class AutoStopInputSnapshot:
    """Automatic stop and automatic restart.

    Attributes:
        label: Field label.
        seconds: Delay of the draft, ``0`` for never.
        maximum: Highest delay.
        unit: Unit and hint shown after the delay.
        restart_label: Label of the "Restart automatically" check box.
        restart: Whether the countdown restarts after the automatic stop.
        restart_enabled: Whether restarting can be chosen (only with an automatic stop).
        error: Inline message, ``""`` when valid.
    """

    label: str
    seconds: int
    maximum: int
    unit: str
    restart_label: str
    restart: bool
    restart_enabled: bool
    error: str


@dataclass(frozen=True, slots=True, kw_only=True)
class TimerEditSnapshot:
    """Everything the timer edit dialog shows.

    Attributes:
        title: Window title.
        duration: Duration field.
        sound: Sound field.
        volume: Volume field.
        loops: Play count field.
        auto_stop: Automatic stop field.
        note: When the timer runs: changes apply to the next start or ringing; ``""`` otherwise.
        save: Save button (enabled when the draft changed and is valid).
        cancel: Cancel button.
    """

    title: str
    duration: DurationInputSnapshot
    sound: SoundPickerSnapshot
    volume: VolumeInputSnapshot
    loops: LoopInputSnapshot
    auto_stop: AutoStopInputSnapshot
    note: str
    save: ButtonSnapshot
    cancel: ButtonSnapshot
