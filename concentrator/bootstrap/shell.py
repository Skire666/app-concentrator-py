"""Wiring of the window shell: presenters, window, ticker, on top of the core and storage services."""

import logging
from dataclasses import dataclass

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from concentrator.application.common.app_config import AppConfig
from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.application.settings.settings_events import UserSettingsChangedEvent
from concentrator.application.storage.storage_events import SaveStatusChangedEvent, UserDataReplacedEvent
from concentrator.application.timer.alarm_coordinator import AlarmCoordinator
from concentrator.application.timer.timer_events import HourlyChimeChangedEvent, TimerChangedEvent
from concentrator.bootstrap.core import Core
from concentrator.bootstrap.heartbeat import Heartbeat, create_heartbeat
from concentrator.bootstrap.journal import build_journal
from concentrator.bootstrap.runtime import ForwardingErrorReporter
from concentrator.bootstrap.settings import build_settings
from concentrator.bootstrap.shell_services import ShellServices
from concentrator.bootstrap.storage import Storage
from concentrator.bootstrap.timer import TimerServices, build_timer, connect_alarm
from concentrator.bootstrap.timer_extras import TimerExtras, build_timer_extras
from concentrator.bootstrap.todo import attach_todo_dialogs, build_todo
from concentrator.infrastructure.system.app_paths import AppPaths
from concentrator.presentation.common.date_time_formatter import DateTimeFormatter
from concentrator.presentation.common.layout_state_keeper import LayoutStateKeeper
from concentrator.presentation.journal.journal_layout import JournalLayout
from concentrator.presentation.journal.journal_presenter import JournalPresenter
from concentrator.presentation.settings.settings_files_presenter import SettingsFilesPresenter
from concentrator.presentation.settings.settings_presenter import SettingsPresenter
from concentrator.presentation.shell.instance_protection_presenter import InstanceProtectionPresenter
from concentrator.presentation.shell.main_window_presenters import MainWindowPresenters
from concentrator.presentation.shell.shell_layout import ShellLayout
from concentrator.presentation.shell.shell_page_enum import ShellPageEnum
from concentrator.presentation.shell.shell_presenter import ShellPresenter
from concentrator.presentation.shell.status_bar_presenter import StatusBarPresenter
from concentrator.presentation.shell.unexpected_error_presenter import UnexpectedErrorPresenter
from concentrator.presentation.shell.window_layouts import WindowLayouts
from concentrator.presentation.storage.external_change_presenter import ExternalChangePresenter
from concentrator.presentation.storage.save_status_texts import SaveStatusTexts
from concentrator.presentation.storage.shutdown_presenter import ShutdownPresenter
from concentrator.presentation.timer.timer_layout import TimerLayout
from concentrator.presentation.todo.todo_layout import TodoLayout
from concentrator.presentation.todo.todo_presenters import TodoPresenters
from concentrator.ui.support.icon_loader import IconLoader
from concentrator.ui.support.modal_host import ModalHost
from concentrator.ui.support.qt_dialog_service import QtDialogService
from concentrator.ui.windows.chime_settings_dialog import ChimeSettingsWindow
from concentrator.ui.windows.main_window import MainWindow
from concentrator.ui.windows.preset_edit_dialog import PresetEditWindow
from concentrator.ui.windows.timer_edit_dialog import TimerEditWindow

_logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _Pages:
    """Presenters of the TODO manager and of the Journal and Settings pages."""

    journal: JournalPresenter
    settings: SettingsPresenter
    settings_files: SettingsFilesPresenter
    todo: TodoPresenters


class Shell:
    """Everything the running window needs, kept alive together."""

    def __init__(
        self,
        *,
        window: MainWindow,
        core: Core,
        shutdown: ShutdownPresenter,
        timer: TimerServices,
        extras: TimerExtras,
        alarm: AlarmCoordinator,
        heartbeat: Heartbeat,
    ) -> None:
        """Keep the wired objects.

        Args:
            window: Main window (not shown yet).
            core: Main-thread services.
            shutdown: Flushes pending changes on close, quit and session end.
            timer: Timer services (its engine is registered on the ticker).
            extras: Favorites and hourly chime (its service is registered on the ticker).
            alarm: Plays the alarm when the timer rings.
            heartbeat: Ticker and the Qt timer driving it.
        """
        self.window = window
        self.core = core
        self.shutdown_presenter = shutdown
        self.timer = timer
        self.extras = extras
        self.alarm = alarm
        self.heartbeat = heartbeat

    @property
    def tick_timer(self) -> QTimer:
        """Qt timer driving the ticker."""
        return self.heartbeat.timer

    def start(self) -> None:
        """Render once, restore the layout, start the ticker and show the window (steps 7 and 8)."""
        self.core.renderer.request_all()
        self.core.renderer.flush()
        self.window.restore_layout()
        self.tick_timer.start()
        self.window.show()
        _logger.info("Main window shown")

    def shutdown(self) -> None:
        """Flush pending changes without dialog, stop the ticker, save the UI state (``aboutToQuit``)."""
        self.shutdown_presenter.flush_without_dialog()
        self.tick_timer.stop()
        self.timer.alarm_player.stop()
        self.extras.chime_player.stop()
        self.window.save_layout()
        self.core.preferences.sync()


def _status_bar(
    core: Core, storage: Storage, translator: TranslatorPort, instance: InstanceProtectionPresenter
) -> StatusBarPresenter:
    """Create the status bar presenter and subscribe it to the save status.

    Args:
        core: Main-thread services.
        storage: Storage services.
        translator: Current-language translator.
        instance: Unguarded single-instance indicator.

    Returns:
        The presenter.
    """
    presenter = StatusBarPresenter(
        translator,
        core.gate,
        core.renderer,
        switcher=storage.switcher,
        save_texts=SaveStatusTexts(translator, DateTimeFormatter(translator, core.clock)),
        coordinator=storage.coordinator,
        instance=instance,
    )
    core.event_bus.subscribe(SaveStatusChangedEvent, presenter.on_save_status_changed)
    return presenter


def _connect_dialogs(
    dialogs: QtDialogService,
    core: Core,
    storage: Storage,
    translator: TranslatorPort,
    reporter: ForwardingErrorReporter,
) -> None:
    """Give the window's dialog service to the error and external change presenters.

    Args:
        dialogs: Dialog service over the main window (ADR-036).
        core: Main-thread services.
        storage: Storage services.
        translator: Current-language translator.
        reporter: Reporter of the global hooks.
    """
    error_presenter = UnexpectedErrorPresenter(core.dispatcher, translator)
    error_presenter.attach(dialogs)
    reporter.connect(error_presenter)
    external = ExternalChangePresenter(storage.external, dialogs, translator, core.scheduler, storage.switcher)
    core.event_bus.subscribe(SaveStatusChangedEvent, external.on_save_status_changed)


def build_shell(
    app: QApplication,
    config: AppConfig,
    paths: AppPaths,
    translator: TranslatorPort,
    reporter: ForwardingErrorReporter,
    services: ShellServices,
) -> Shell:
    """Build the presenters and the window once a data file is open (step 6).

    Args:
        app: The application (owner of the tick timer).
        config: Loaded configuration.
        paths: Application paths.
        translator: Current-language translator.
        reporter: Reporter of the global hooks; connected to the error dialog here.
        services: Core, storage, single-instance indicator and log buffer.

    Returns:
        The shell, ready to ``start``.
    """
    core, storage = services.core, services.storage
    timer = build_timer(app, config, paths, translator, core=core, storage=storage)
    extras = build_timer_extras(app, translator, core=core, storage=storage, timer=timer)
    pages = _pages(config, paths, translator, services, timer)
    presenters = _presenters(services, translator, (timer, extras), pages)
    window = _main_window(config, paths, core, presenters)
    _wire_window(window, config, presenters, (timer, extras), (services, translator, reporter))
    return Shell(
        window=window,
        core=core,
        shutdown=presenters.shutdown,
        timer=timer,
        extras=extras,
        alarm=connect_alarm(timer, window, core, storage.settings_queries.notify_when_inactive),
        heartbeat=create_heartbeat(
            app, config, (timer.engine.tick, extras.chime_service.tick, pages.journal.on_tick, pages.todo.table.on_tick)
        ),
    )


def _wire_window(
    window: MainWindow,
    config: AppConfig,
    presenters: MainWindowPresenters,
    timer: tuple[TimerServices, TimerExtras],
    context: tuple[ShellServices, TranslatorPort, ForwardingErrorReporter],
) -> None:
    """Attach the dialogs over the window and connect the presenters that need the window.

    Args:
        window: Main window.
        config: Loaded configuration.
        presenters: Presenters of the window.
        timer: Timer services and timer extras.
        context: Shell services, translator and the reporter of the global hooks.
    """
    services, translator, reporter = context
    dialogs = _attach_dialogs(window, config, presenters, timer, services)
    _connect_dialogs(dialogs, services.core, services.storage, translator, reporter)
    _connect_settings(window, presenters, services.core)


def _pages(
    config: AppConfig, paths: AppPaths, translator: TranslatorPort, services: ShellServices, timer: TimerServices
) -> _Pages:
    """Create the presenters of the TODO manager and of the Journal and Settings pages.

    Args:
        config: Loaded configuration.
        paths: Application paths.
        translator: Current-language translator.
        services: Core, storage, log buffer and startup flow.
        timer: Sounds and preview of the chime fields.

    Returns:
        The presenters.
    """
    settings, settings_files = build_settings(config, paths, translator, services, timer)
    journal = build_journal(config, translator, services.core, services.feed)
    todo = build_todo(config, translator, services.core, services.storage.store)
    return _Pages(journal, settings, settings_files, todo)


def _connect_settings(window: MainWindow, presenters: MainWindowPresenters, core: Core) -> None:
    """Let the settings follow stored values, reset the layout and guard the window close.

    Args:
        window: Main window (applies the default layout).
        presenters: Presenters of the window.
        core: Main-thread services (event bus).
    """
    settings = presenters.settings
    for event_type in (UserSettingsChangedEvent, HourlyChimeChangedEvent, UserDataReplacedEvent):
        core.event_bus.subscribe(event_type, settings.on_stored_values_changed)
    presenters.settings_files.add_layout_reset_listener(window.reset_layout)
    presenters.settings_files.add_layout_reset_listener(presenters.journal.reset_layout)
    presenters.settings_files.add_layout_reset_listener(presenters.todo.refresher.reset_layout)
    presenters.shutdown.watch_edits(settings)


def _main_window(config: AppConfig, paths: AppPaths, core: Core, presenters: MainWindowPresenters) -> MainWindow:
    """Create the main window (not shown).

    Args:
        config: Loaded configuration.
        paths: Application paths (icons).
        core: Main-thread services.
        presenters: Presenters of its panels.

    Returns:
        The window.
    """
    layouts = WindowLayouts(
        shell=ShellLayout.from_ui_section(config.ui),
        timer=TimerLayout.from_ui_section(config.ui),
        journal=JournalLayout.from_journal_section(config.journal),
        todo=TodoLayout.from_config(config),
    )
    return MainWindow(
        presenters=presenters,
        renderer=core.renderer,
        layout_keeper=LayoutStateKeeper(core.preferences),
        layouts=layouts,
        icons=IconLoader(paths.icons_dir),
        app_icon=QIcon(str(paths.app_icon_file)),
    )


def _attach_dialogs(
    window: MainWindow,
    config: AppConfig,
    presenters: MainWindowPresenters,
    timer: tuple[TimerServices, TimerExtras],
    services: ShellServices,
) -> QtDialogService:
    """Give the presenters the window and its dialogs, all run over the window (ADR-036).

    The startup dialogs move over the window too: the settings page runs the recovery dialog.

    Args:
        window: Main window.
        config: Loaded configuration.
        presenters: Presenters of the window.
        timer: Timer services and timer extras (edit, favorite and chime dialogs).
        services: Core services and the startup flow.

    Returns:
        The dialog service of the window.
    """
    timer_services, extras = timer
    renderer = services.core.renderer
    host = ModalHost.create(window, config.ui.dialog_overlay_opacity_percent)
    dialogs = QtDialogService(host)
    presenters.shutdown.attach(dialogs)
    presenters.settings.attach(dialogs)
    layout = TimerLayout.from_ui_section(config.ui)
    timer_services.editor.attach(TimerEditWindow(timer_services.editor, renderer, host, layout), dialogs)
    extras.preset_editor.attach(PresetEditWindow(extras.preset_editor, renderer, host, layout))
    extras.presets.attach(dialogs)
    extras.chime_editor.attach(ChimeSettingsWindow(extras.chime_editor, renderer, host, layout), dialogs)
    attach_todo_dialogs(presenters.todo, host, dialogs, services.core, TodoLayout.from_config(config))
    if services.startup is not None:
        services.startup.dialogs.move_to_window(host)
        services.startup.presenter.attach_session(services.startup.dialogs, dialogs)
    return dialogs


def _presenters(
    services: ShellServices, translator: TranslatorPort, timer: tuple[TimerServices, TimerExtras], pages: _Pages
) -> MainWindowPresenters:
    """Create the presenters of the main window panels.

    Args:
        services: Core, storage and single-instance indicator.
        translator: Current-language translator.
        timer: Timer services and timer extras.
        pages: Journal and Settings presenters.

    Returns:
        The presenters; the shell presenter follows the timer to highlight the Focus button, shows the
        journal badge, tells the pages when they are shown and asks the settings before leaving them.
    """
    core, storage = services.core, services.storage
    timer_services, extras = timer
    journal, settings = pages.journal, pages.settings
    shell = ShellPresenter(
        translator, core.gate, core.renderer, timer_services.ringing, journal_badge=journal.badge_count
    )
    shell.add_page_listener(journal.on_page_changed)
    shell.add_page_listener(settings.on_page_changed)
    shell.set_leave_guard(ShellPageEnum.SETTINGS, settings.may_leave)
    core.event_bus.subscribe(TimerChangedEvent, shell.on_timer_changed)
    return MainWindowPresenters(
        shell=shell,
        status_bar=_status_bar(core, storage, translator, services.instance),
        shutdown=ShutdownPresenter(storage.coordinator, translator, timer_services.countdown_active),
        timer=timer_services.presenter,
        presets=extras.presets,
        chime=extras.chime,
        journal=journal,
        settings=settings,
        settings_files=pages.settings_files,
        todo=pages.todo,
    )
