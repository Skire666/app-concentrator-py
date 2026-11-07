"""Main-thread services shared by the startup dialogs and the main window."""

from dataclasses import dataclass

from PySide6.QtWidgets import QApplication

from concentrator.application.common.app_config import AppConfig
from concentrator.application.common.event_bus import EventBus
from concentrator.application.ports.error_reporter_port import ErrorReporterPort
from concentrator.infrastructure.qt.qsettings_view_preferences import QSettingsViewPreferences
from concentrator.infrastructure.qt.qt_main_thread_dispatcher import QtMainThreadDispatcher
from concentrator.infrastructure.qt.qt_scheduler import QtScheduler
from concentrator.infrastructure.system.system_clock import SystemClock
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.render_coordinator import RenderCoordinator


@dataclass(frozen=True, slots=True, kw_only=True)
class Core:
    """Services built once, before any dialog.

    Attributes:
        clock: System clock.
        scheduler: Qt scheduler (main thread).
        dispatcher: Brings writer-thread results to the main thread.
        renderer: Render coordinator of every dialog and panel.
        gate: Action gate of every control.
        event_bus: Cross-feature event bus.
        preferences: ``ui-state.ini`` adapter.
    """

    clock: SystemClock
    scheduler: QtScheduler
    dispatcher: QtMainThreadDispatcher
    renderer: RenderCoordinator
    gate: ActionGate
    event_bus: EventBus
    preferences: QSettingsViewPreferences


def build_core(app: QApplication, config: AppConfig, reporter: ErrorReporterPort) -> Core:
    """Create the main-thread services.

    Args:
        app: Owner of the Qt adapters.
        config: Loaded configuration.
        reporter: Receives the exceptions of event handlers.

    Returns:
        The services.
    """
    clock = SystemClock()
    scheduler = QtScheduler(app)
    renderer = RenderCoordinator(scheduler)
    gate = ActionGate(
        clock,
        scheduler,
        renderer,
        cooldown_ms=config.ui.action_cooldown_ms,
        slow_threshold_ms=config.ui.slow_action_threshold_ms,
    )
    return Core(
        clock=clock,
        scheduler=scheduler,
        dispatcher=QtMainThreadDispatcher(app),
        renderer=renderer,
        gate=gate,
        event_bus=EventBus(reporter),
        preferences=QSettingsViewPreferences(config.paths.ui_state_file),
    )
