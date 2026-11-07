"""Snapshots of the first-run (``FIRST_RUN``) and recovery (``RECOVERY``) dialogs."""

from dataclasses import dataclass

from concentrator.presentation.common.button_snapshot import ButtonSnapshot


@dataclass(frozen=True, slots=True, kw_only=True)
class FirstRunSnapshot:
    """Where to put the data file.

    Attributes:
        title: Window title.
        intro: Explanation.
        notice: "File not found" notice, ``""`` at a real first run.
        default_location: The default path, as shown to the user.
        buttons: Actions, in display order (hidden ones have ``visible=False``).
    """

    title: str
    intro: str
    notice: str
    default_location: str
    buttons: tuple[ButtonSnapshot, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class CandidateSnapshot:
    """One restorable version.

    Attributes:
        text: Which file and when it was saved.
        selected: Whether "Restore" applies to it.
    """

    text: str
    selected: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class RecoverySnapshot:
    """What is wrong with the data file and how to go on.

    Attributes:
        title: Window title.
        intro: The situation.
        path: The data file concerned.
        problems: Translated problem lines (field labels included).
        candidates_caption: Caption of the candidate list, ``""`` without candidates.
        candidates: Restorable versions, newest first.
        buttons: Actions, in display order (hidden ones have ``visible=False``).
    """

    title: str
    intro: str
    path: str
    problems: tuple[str, ...]
    candidates_caption: str
    candidates: tuple[CandidateSnapshot, ...]
    buttons: tuple[ButtonSnapshot, ...]
