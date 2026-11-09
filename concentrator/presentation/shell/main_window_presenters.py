"""Presenters of the panels the main window composes."""

from dataclasses import dataclass

from concentrator.presentation.shell.shell_presenter import ShellPresenter
from concentrator.presentation.shell.status_bar_presenter import StatusBarPresenter
from concentrator.presentation.storage.shutdown_presenter import ShutdownPresenter
from concentrator.presentation.timer.chime_presenter import ChimePresenter
from concentrator.presentation.timer.presets_presenter import PresetsPresenter
from concentrator.presentation.timer.timer_presenter import TimerPresenter


@dataclass(frozen=True, slots=True, kw_only=True)
class MainWindowPresenters:
    """Everything ``MainWindow`` wires its panels to.

    Attributes:
        shell: Module bar, pages and title.
        status_bar: Status bar.
        shutdown: Quit question and flush on close.
        timer: Timer panel.
        presets: Favorites panel.
        chime: Special options panel.
    """

    shell: ShellPresenter
    status_bar: StatusBarPresenter
    shutdown: ShutdownPresenter
    timer: TimerPresenter
    presets: PresetsPresenter
    chime: ChimePresenter
