"""Snapshot of the settings page (``SETTINGS``): the editable form and the file and layout commands."""

from dataclasses import dataclass

from concentrator.presentation.common.button_snapshot import ButtonSnapshot
from concentrator.presentation.timer.chime_settings_snapshot import ChimeFieldsSnapshot


@dataclass(frozen=True, slots=True, kw_only=True)
class ChoiceFieldSnapshot:
    """A list to choose one value from.

    Attributes:
        label: Field label.
        tooltip: Translated tooltip, ``""`` for none.
        options: Texts of the choices.
        selected: Index of the chosen one.
        error: Inline message, ``""`` when valid.
    """

    label: str
    tooltip: str
    options: tuple[str, ...]
    selected: int
    error: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ToggleFieldSnapshot:
    """A check box editing a form value (not an action).

    Attributes:
        text: Label.
        checked: Value of the draft.
    """

    text: str
    checked: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class GeneralSectionSnapshot:
    """The General section.

    Attributes:
        title: Section title.
        language: UI language.
        log_level: Journal detail level.
        notify_when_inactive: Taskbar alert.
    """

    title: str
    language: ChoiceFieldSnapshot
    log_level: ChoiceFieldSnapshot
    notify_when_inactive: ToggleFieldSnapshot


@dataclass(frozen=True, slots=True, kw_only=True)
class ChimeSectionSnapshot:
    """The Hourly chime section.

    Attributes:
        title: Section title.
        enabled: "Chime every hour".
        fields: Sound, volume and hours.
        hint: How the hours are used.
    """

    title: str
    enabled: ToggleFieldSnapshot
    fields: ChimeFieldsSnapshot
    hint: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SettingsFormSnapshot:
    """The values stored in the data file, with Save and Revert.

    Attributes:
        general: General section.
        chime: Hourly chime section.
        status: "Unsaved changes" while the form differs from the stored values, else ``""``.
        save: Enabled when something changed and nothing fails.
        revert: Enabled when something changed.
    """

    general: GeneralSectionSnapshot
    chime: ChimeSectionSnapshot
    status: str
    save: ButtonSnapshot
    revert: ButtonSnapshot


@dataclass(frozen=True, slots=True, kw_only=True)
class PathRowSnapshot:
    """A read-only path with an "Open folder" button.

    Attributes:
        label: What the path is.
        path: The path, with ``/`` separators.
        folder: ``SettingsFolderEnum`` value sent back by the button.
        open_folder: The button.
    """

    label: str
    path: str
    folder: int
    open_folder: ButtonSnapshot


@dataclass(frozen=True, slots=True, kw_only=True)
class DataFileSectionSnapshot:
    """The Data file section.

    Attributes:
        title: Section title.
        current: Path of the open data file.
        hint: How the file is saved.
        switch: "Use another file...".
        move: "Move file...".
    """

    title: str
    current: PathRowSnapshot
    hint: str
    switch: ButtonSnapshot
    move: ButtonSnapshot


@dataclass(frozen=True, slots=True, kw_only=True)
class InterfaceSectionSnapshot:
    """The Interface section.

    Attributes:
        title: Section title.
        hint: What "Reset layout" restores.
        reset_layout: The button.
    """

    title: str
    hint: str
    reset_layout: ButtonSnapshot


@dataclass(frozen=True, slots=True, kw_only=True)
class AboutSectionSnapshot:
    """The About section.

    Attributes:
        title: Section title.
        version_label: "Version".
        version: Installed version.
        paths: Configuration file, interface state file, log folder and backup folder.
    """

    title: str
    version_label: str
    version: str
    paths: tuple[PathRowSnapshot, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class SettingsFilesSnapshot:
    """Sections that act at once (not part of the form).

    Attributes:
        data_file: Data file section.
        interface: Interface section.
        about: About section.
    """

    data_file: DataFileSectionSnapshot
    interface: InterfaceSectionSnapshot
    about: AboutSectionSnapshot


@dataclass(frozen=True, slots=True, kw_only=True)
class SettingsSnapshot:
    """The settings page.

    Attributes:
        form: General and Hourly chime sections, Save and Revert.
        files: Data file, Interface and About sections.
    """

    form: SettingsFormSnapshot
    files: SettingsFilesSnapshot
