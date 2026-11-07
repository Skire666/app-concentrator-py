"""Wiring of the window shell: presenters, window, ticker, on top of the core and storage services."""

import logging

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from concentrator.application.common.app_config import AppConfig
from concentrator.application.common.app_ticker import AppTicker
from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.application.storage.storage_events import SaveStatusChangedEvent
from concentrator.bootstrap.core import Core
from concentrator.bootstrap.runtime import ForwardingErrorReporter
from concentrator.bootstrap.storage import Storage
from concentrator.infrastructure.system.app_paths import AppPaths
from concentrator.presentation.common.date_time_formatter import DateTimeFormatter
from concentrator.presentation.common.layout_state_keeper import LayoutStateKeeper
from concentrator.presentation.shell.instance_protection_presenter import InstanceProtectionPresenter
from concentrator.presentation.shell.shell_layout import ShellLayout
from concentrator.presentation.shell.shell_presenter import ShellPresenter
from concentrator.presentation.shell.status_bar_presenter import StatusBarPresenter
from concentrator.presentation.shell.unexpected_error_presenter import UnexpectedErrorPresenter
from concentrator.presentation.storage.external_change_presenter import ExternalChangePresenter
from concentrator.presentation.storage.save_status_texts import SaveStatusTexts
from concentrator.presentation.storage.shutdown_presenter import ShutdownPresenter
from concentrator.ui.support.icon_loader import IconLoader
from concentrator.ui.support.modal_host import ModalHost
from concentrator.ui.support.qt_dialog_service import QtDialogService
from concentrator.ui.windows.main_window import MainWindow

_logger = logging.getLogger(__name__)


class Shell:
    """Everything the running window needs, kept alive together."""

    def __init__(
        self, *, window: MainWindow, core: Core, shutdown: ShutdownPresenter, ticker: AppTicker, tick_timer: QTimer
    ) -> None:
        """Keep the wired objects.

        Args:
            window: Main window (not shown yet).
            core: Main-thread services.
            shutdown: Flushes pending changes on close, quit and session end.
            ticker: Heartbeat of the runtime engines.
            tick_timer: Qt timer driving the ticker.
        """
        self.window = window
        self.core = core
        self.shutdown_presenter = shutdown
        self.ticker = ticker
        self.tick_timer = tick_timer

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
        self.window.save_layout()
        self.core.preferences.sync()


def _tick_timer(app: QApplication, config: AppConfig, ticker: AppTicker) -> QTimer:
    """Create the Qt timer calling ``AppTicker.tick`` every ``timer.tick_interval_ms`` (not started).

    Args:
        app: Owner of the timer.
        config: Loaded configuration.
        ticker: Ticker to drive.

    Returns:
        The timer.
    """
    timer = QTimer(app)
    timer.setInterval(config.timer.tick_interval_ms)
    timer.timeout.connect(ticker.tick)
    return timer


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
    shutdown = ShutdownPresenter(storage.coordinator, translator)
    window = MainWindow(
        presenter=ShellPresenter(translator, core.gate, core.renderer),
        status_bar=_status_bar(core, storage, translator, instance),
        shutdown=shutdown,
        renderer=core.renderer,
        layout_keeper=LayoutStateKeeper(core.preferences),
        shell_layout=ShellLayout.from_ui_section(config.ui),
        icons=IconLoader(paths.icons_dir),
        app_icon=QIcon(str(paths.app_icon_file)),
    )
    dialogs = QtDialogService(ModalHost.create(window, config.ui.dialog_overlay_opacity_percent))
    shutdown.attach(dialogs)
    _connect_dialogs(dialogs, core, storage, translator, reporter)
    ticker = AppTicker()
    return Shell(
        window=window, core=core, shutdown=shutdown, ticker=ticker, tick_timer=_tick_timer(app, config, ticker)
    )
