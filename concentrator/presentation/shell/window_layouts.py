"""Every static size the main window needs, from ``concentrator.ini``."""

from dataclasses import dataclass

from concentrator.presentation.journal.journal_layout import JournalLayout
from concentrator.presentation.shell.shell_layout import ShellLayout
from concentrator.presentation.timer.timer_layout import TimerLayout


@dataclass(frozen=True, slots=True, kw_only=True)
class WindowLayouts:
    """Sizes of the shell and of its pages.

    Attributes:
        shell: Window, module bar and Focus page splitter.
        timer: Timer digits and favorites.
        journal: Journal splitter and columns.
    """

    shell: ShellLayout
    timer: TimerLayout
    journal: JournalLayout
