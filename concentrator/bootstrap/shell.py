"""Wiring of the window shell: presenters, window, ticker, on top of the core and storage services."""

import logging
from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from concentrator.application.common.app_config import AppConfig
from concentrator.application.common.app_ticker import AppTicker
from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.application.storage.storage_events import SaveStatusChangedEvent
from concentrator.application.timer.alarm_coordinator import AlarmCoordinator
from concentrator.application.timer.timer_events import TimerChangedEvent
from concentrator.bootstrap.core import Core
from concentrator.bootstrap.runtime import ForwardingErrorReporter
from concentrator.bootstrap.storage import Storage
from concentrator.bootstrap.timer import TimerServices, build_timer, connect_alarm
from concentrator.bootstrap.timer_extras import TimerExtras, build_timer_extras
from concentrator.infrastructure.system.app_paths import AppPaths
from concentrator.presentation.common.date_time_formatter import DateTimeFormatter
from concentrator.presentation.common.layout_state_keeper import LayoutStateKeeper
from concentrator.presentation.shell.instance_protection_presenter import InstanceProtectionPresenter
from concentrator.presentation.shell.main_window_presenters import MainWindowPresenters
from concentrator.presentation.shell.shell_layout import ShellLayout
from concentrator.presentation.shell.shell_presenter import ShellPresenter
from concentrator.presentation.shell.status_bar_presenter import StatusBarPresenter
from concentrator.presentation.shell.unexpected_error_presenter import UnexpectedErrorPresenter
from concentrator.presentation.storage.external_change_presenter import ExternalChangePresenter
from concentrator.presentation.storage.save_status_texts import SaveStatusTexts
from concentrator.presentation.storage.shutdown_presenter import ShutdownPresenter
from concentrator.presentation.timer.timer_layout import TimerLayout
from concentrator.ui.support.icon_loader import IconLoader
from concentrator.ui.support.modal_host import ModalHost
from concentrator.ui.support.qt_dialog_service import QtDialogService
from concentrator.ui.windows.chime_settings_dialog import ChimeSettingsWindow
from concentrator.ui.windows.main_window import MainWindow
from concentrator.ui.windows.preset_edit_dialog import PresetEditWindow
from concentrator.ui.windows.timer_edit_dialog import TimerEditWindow

_logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Heartbeat:
    """The ticker and the Qt timer that drives it, kept alive together by the shell.

    PySide6 does not keep alive the owner of a bound method connected to a signal: a ticker that only
    the connection references is collected at once, and the timer then fires into nothing (the timer
    never counted down and the chime never played, phase 3 review).

    Attributes:
        ticker: Calls the timer engine, then the chime service.
        timer: Qt timer calling ``ticker.tick`` every ``timer.tick_interval_ms`` (not started).
    """

    ticker: AppTicker
    timer: QTimer


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


def _heartbeat(app: QApplication, config: AppConfig, handlers: tuple[Callable[[], None], ...]) -> Heartbeat:
    """Create the ticker and the Qt timer calling it every ``timer.tick_interval_ms`` (not started).

    Args:
        app: Owner of the timer.
        config: Loaded configuration.
        handlers: Called on every tick, in order.

    Returns:
        The heartbeat; the shell keeps it alive.
    """
    ticker = AppTicker()
    for handler in handlers:
        ticker.register(handler)
    timer = QTimer(app)
    timer.setInterval(config.timer.tick_interval_ms)
    timer.timeout.connect(ticker.tick)
    return Heartbeat(ticker=ticker, timer=timer)


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
    *,
    core: Core,
    storage: Storage,
    instance: InstanceProtectionPresenter,
) -> Shell:
    """Build the presenters and the window once a data file is open (step 6).

    Args:
        app: The application (owner of the tick timer).
        config: Loaded configuration.
        paths: Application paths.
        translator: Current-language translator.
        reporter: Reporter of the global hooks; connected to the error dialog here.
        core: Main-thread services.
        storage: Storage services.
        instance: Unguarded single-instance indicator.

    Returns:
        The shell, ready to ``start``.
    """
    timer = build_timer(app, config, paths, translator, core=core, storage=storage)
    extras = build_timer_extras(app, translator, core=core, storage=storage, timer=timer)
    presenters = _presenters(core, storage, translator, instance, (timer, extras))
    window = _main_window(config, paths, core, presenters)
    dialogs = _attach_dialogs(window, config, presenters, (timer, extras), core)
    _connect_dialogs(dialogs, core, storage, translator, reporter)
    return Shell(
        window=window,
        core=core,
        shutdown=presenters.shutdown,
        timer=timer,
        extras=extras,
        alarm=connect_alarm(timer, window, core),
        heartbeat=_heartbeat(app, config, (timer.engine.tick, extras.chime_service.tick)),
    )


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
    return MainWindow(
        presenters=presenters,
        renderer=core.renderer,
        layout_keeper=LayoutStateKeeper(core.preferences),
        shell_layout=ShellLayout.from_ui_section(config.ui),
        timer_layout=TimerLayout.from_ui_section(config.ui),
        icons=IconLoader(paths.icons_dir),
        app_icon=QIcon(str(paths.app_icon_file)),
    )


def _attach_dialogs(
    window: MainWindow,
    config: AppConfig,
    presenters: MainWindowPresenters,
    timer: tuple[TimerServices, TimerExtras],
    core: Core,
) -> QtDialogService:
    """Give the presenters the window and its dialogs, all run over the window (ADR-036).

    Args:
        window: Main window.
        config: Loaded configuration.
        presenters: Presenters of the window.
        timer: Timer services and timer extras (edit, favorite and chime dialogs).
        core: Main-thread services.

    Returns:
        The dialog service of the window.
    """
    services, extras = timer
    host = ModalHost.create(window, config.ui.dialog_overlay_opacity_percent)
    dialogs = QtDialogService(host)
    presenters.shutdown.attach(dialogs)
    layout = TimerLayout.from_ui_section(config.ui)
    services.editor.attach(TimerEditWindow(services.editor, core.renderer, host, layout), dialogs)
    extras.preset_editor.attach(PresetEditWindow(extras.preset_editor, core.renderer, host, layout))
    extras.presets.attach(dialogs)
    extras.chime_editor.attach(ChimeSettingsWindow(extras.chime_editor, core.renderer, host, layout), dialogs)
    return dialogs


def _presenters(
    core: Core,
    storage: Storage,
    translator: TranslatorPort,
    instance: InstanceProtectionPresenter,
    timer: tuple[TimerServices, TimerExtras],
) -> MainWindowPresenters:
    """Create the presenters of the main window panels.

    Args:
        core: Main-thread services.
        storage: Storage services.
        translator: Current-language translator.
        instance: Unguarded single-instance indicator.
        timer: Timer services and timer extras.

    Returns:
        The presenters; the shell presenter follows the timer to highlight the Focus button.
    """
    services, extras = timer
    shell = ShellPresenter(translator, core.gate, core.renderer, services.ringing)
    core.event_bus.subscribe(TimerChangedEvent, shell.on_timer_changed)
    return MainWindowPresenters(
        shell=shell,
        status_bar=_status_bar(core, storage, translator, instance),
        shutdown=ShutdownPresenter(storage.coordinator, translator, services.countdown_active),
        timer=services.presenter,
        presets=extras.presets,
        chime=extras.chime,
    )
