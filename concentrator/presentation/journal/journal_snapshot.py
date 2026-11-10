"""Snapshot of the journal page (``JOURNAL``): toolbar, entry table and detail pane."""

from dataclasses import dataclass

from concentrator.presentation.common.button_snapshot import ButtonSnapshot
from concentrator.presentation.common.table_snapshot import TableSnapshot


@dataclass(frozen=True, slots=True, kw_only=True)
class LevelToggleSnapshot:
    """One level toggle of the toolbar.

    Attributes:
        level: ``LogLevelEnum`` value sent back when the toggle is clicked.
        text: Level name and count, for example ``Error (3)``.
        tooltip: Translated tooltip.
        checked: Whether the level is shown.
        enabled: False while the toggles are busy.
    """

    level: int
    text: str
    tooltip: str
    checked: bool
    enabled: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchBoxSnapshot:
    """The search field; it is never disabled, so typing is never interrupted.

    Attributes:
        text: Text typed so far.
        placeholder: Shown while empty.
        tooltip: Translated tooltip.
    """

    text: str
    placeholder: str
    tooltip: str


@dataclass(frozen=True, slots=True, kw_only=True)
class JournalToolbarSnapshot:
    """Filters and commands above the table.

    Attributes:
        levels: Debug, Info, Warning, Error and Critical toggles.
        search: Search field.
        follow: Keeps the newest entry in view (checkable).
        pause: Freezes the view (checkable).
        paused_caption: Number of new entries hidden by the pause, ``""`` when running.
        copy: Copies the selected entries.
        clear_view: Hides the entries shown so far.
        open_log_folder: Opens the folder of the log files.
    """

    levels: tuple[LevelToggleSnapshot, ...]
    search: SearchBoxSnapshot
    follow: ButtonSnapshot
    pause: ButtonSnapshot
    paused_caption: str
    copy: ButtonSnapshot
    clear_view: ButtonSnapshot
    open_log_folder: ButtonSnapshot


@dataclass(frozen=True, slots=True, kw_only=True)
class JournalDetailSnapshot:
    """The selected entry in full.

    Attributes:
        text: Every line of the entry (message and traceback), ``""`` without selection.
        placeholder: Shown without selection.
    """

    text: str
    placeholder: str


@dataclass(frozen=True, slots=True, kw_only=True)
class JournalSnapshot:
    """The journal page.

    Attributes:
        toolbar: Filters and commands.
        table: Entries of the view.
        detail: Selected entry.
    """

    toolbar: JournalToolbarSnapshot
    table: TableSnapshot
    detail: JournalDetailSnapshot
