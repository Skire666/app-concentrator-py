"""Presenters of the panels the main window composes."""

from dataclasses import dataclass

from concentrator.presentation.journal.journal_presenter import JournalPresenter
from concentrator.presentation.settings.settings_files_presenter import SettingsFilesPresenter
from concentrator.presentation.settings.settings_presenter import SettingsPresenter
from concentrator.presentation.shell.shell_presenter import ShellPresenter
from concentrator.presentation.shell.status_bar_presenter import StatusBarPresenter
from concentrator.presentation.storage.shutdown_presenter import ShutdownPresenter
from concentrator.presentation.timer.chime_presenter import ChimePresenter
from concentrator.presentation.timer.presets_presenter import PresetsPresenter
from concentrator.presentation.timer.timer_presenter import TimerPresenter
from concentrator.presentation.todo.todo_presenters import TodoPresenters


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
        journal: Journal page.
        settings: Settings form.
        settings_files: File sections of the settings page.
        todo: TODO manager of zone 1.
    """

    shell: ShellPresenter
    status_bar: StatusBarPresenter
    shutdown: ShutdownPresenter
    timer: TimerPresenter
    presets: PresetsPresenter
    chime: ChimePresenter
    journal: JournalPresenter
    settings: SettingsPresenter
    settings_files: SettingsFilesPresenter
    todo: TodoPresenters
