"""Wiring of the window shell: adapters, event bus, render coordination, gate, presenters, window."""

import logging

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from concentrator.application.common.app_config import AppConfig
from concentrator.application.common.app_ticker import AppTicker
from concentrator.application.common.event_bus import EventBus
from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.bootstrap.runtime import ForwardingErrorReporter
from concentrator.infrastructure.qt.qsettings_view_preferences import QSettingsViewPreferences
from concentrator.infrastructure.qt.qt_main_thread_dispatcher import QtMainThreadDispatcher
from concentrator.infrastructure.qt.qt_scheduler import QtScheduler
from concentrator.infrastructure.system.app_paths import AppPaths
from concentrator.infrastructure.system.system_clock import SystemClock
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.layout_state_keeper import LayoutStateKeeper
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.shell.shell_layout import ShellLayout
from concentrator.presentation.shell.shell_presenter import ShellPresenter
from concentrator.presentation.shell.unexpected_error_presenter import UnexpectedErrorPresenter
from concentrator.ui.support.icon_loader import IconLoader
from concentrator.ui.support.qt_dialog_service import QtDialogService
from concentrator.ui.windows.main_window import MainWindow

_logger = logging.getLogger(__name__)


class Shell:
    """Everything the running window needs, kept alive together."""

    def __init__(
        self,
        *,
        window: MainWindow,
        renderer: RenderCoordinator,
        preferences: QSettingsViewPreferences,
        ticker: AppTicker,
        tick_timer: QTimer,
        event_bus: EventBus,
    ) -> None:
        """Keep the wired objects.

        Args:
            window: Main window (not shown yet).
            renderer: Render coordinator.
            preferences: ``ui-state.ini`` adapter.
            ticker: Heartbeat of the runtime engines.
            tick_timer: Qt timer driving the ticker.
            event_bus: Cross-feature event bus.
        """
        self.window = window
        self.renderer = renderer
        self.preferences = preferences
        self.ticker = ticker
        self.tick_timer = tick_timer
        self.event_bus = event_bus

    def start(self) -> None:
        """Render once, restore the layout, start the ticker and show the window (steps 7 and 8)."""
        self.renderer.request_all()
        self.renderer.flush()
        self.window.restore_layout()
        self.tick_timer.start()
        self.window.show()
        _logger.info("Main window shown")

    def shutdown(self) -> None:
        """Stop the ticker and save the UI state (step 9, ``aboutToQuit``)."""
        self.tick_timer.stop()
        self.window.save_layout()
        self.preferences.sync()


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


def _gate(config: AppConfig, scheduler: QtScheduler, renderer: RenderCoordinator) -> ActionGate:
    """Create the action gate with the ini timings.

    Args:
        config: Loaded configuration.
        scheduler: Qt scheduler.
        renderer: Render coordinator.

    Returns:
        The gate.
    """
    return ActionGate(
        SystemClock(),
        scheduler,
        renderer,
        cooldown_ms=config.ui.action_cooldown_ms,
        slow_threshold_ms=config.ui.slow_action_threshold_ms,
    )


def build_shell(
    app: QApplication, config: AppConfig, paths: AppPaths, translator: TranslatorPort, reporter: ForwardingErrorReporter
) -> Shell:
    """Build adapters, event bus, render coordinator, gate, presenters and the window (step 6).

    Args:
        app: The application (owner of the Qt adapters).
        config: Loaded configuration.
        paths: Application paths.
        translator: Loaded translator.
        reporter: Reporter of the global hooks; connected to the error dialog here.

    Returns:
        The shell, ready to ``start``.
    """
    scheduler = QtScheduler(app)
    renderer = RenderCoordinator(scheduler)
    preferences = QSettingsViewPreferences(config.paths.ui_state_file)
    window = MainWindow(
        presenter=ShellPresenter(translator, _gate(config, scheduler, renderer), renderer),
        renderer=renderer,
        layout_keeper=LayoutStateKeeper(preferences),
        shell_layout=ShellLayout.from_ui_section(config.ui),
        icons=IconLoader(paths.icons_dir),
        app_icon=QIcon(str(paths.app_icon_file)),
    )
    error_presenter = UnexpectedErrorPresenter(QtMainThreadDispatcher(app), translator)
    error_presenter.attach(QtDialogService(window))
    reporter.connect(error_presenter)
    ticker = AppTicker()
    timer = _tick_timer(app, config, ticker)
    return Shell(
        window=window,
        renderer=renderer,
        preferences=preferences,
        ticker=ticker,
        tick_timer=timer,
        event_bus=EventBus(reporter),
    )
