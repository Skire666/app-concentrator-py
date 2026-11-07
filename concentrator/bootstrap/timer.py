"""Wiring of the timer: engine, use cases, sound players, presenters, alarm."""

from dataclasses import dataclass

from PySide6.QtWidgets import QApplication

from concentrator.application.common.app_config import AppConfig
from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.application.timer.alarm_coordinator import AlarmCoordinator
from concentrator.application.timer.sound_preview import SoundPreview
from concentrator.application.timer.timer_commands import TimerCommands
from concentrator.application.timer.timer_defaults import TimerDefaults
from concentrator.application.timer.timer_engine import TimerEngine
from concentrator.application.timer.timer_events import TimerChangedEvent, TimerConfigChangedEvent
from concentrator.application.timer.timer_queries import TimerQueries
from concentrator.bootstrap.core import Core
from concentrator.bootstrap.storage import Storage
from concentrator.domain.timer.timer_state_enum import TimerStateEnum
from concentrator.infrastructure.persistence.store_timer_config import StoreTimerConfigReader, StoreTimerConfigWriter
from concentrator.infrastructure.qt.qt_attention import QtAttention
from concentrator.infrastructure.qt.qt_sound_player import QtSoundPlayer
from concentrator.infrastructure.system.app_paths import AppPaths
from concentrator.infrastructure.system.builtin_sound_catalog import BuiltinSoundCatalog
from concentrator.presentation.common.date_time_formatter import DateTimeFormatter
from concentrator.presentation.timer.timer_edit_presenter import TimerEditPresenter
from concentrator.presentation.timer.timer_presenter import TimerPresenter
from concentrator.ui.windows.main_window import MainWindow


@dataclass(frozen=True, slots=True, kw_only=True)
class TimerServices:
    """The timer side, kept alive by the shell.

    Attributes:
        engine: Runtime countdown (registered on the ticker).
        queries: Read use cases.
        catalog: Built-in sounds and sound files.
        alarm_player: Player of the alarm.
        defaults: Timer values of ``concentrator.ini``.
        editor: Edit dialog presenter (its dialog is attached with the main window).
        presenter: Timer panel presenter.
    """

    engine: TimerEngine
    queries: TimerQueries
    catalog: BuiltinSoundCatalog
    alarm_player: QtSoundPlayer
    defaults: TimerDefaults
    editor: TimerEditPresenter
    presenter: TimerPresenter

    def ringing(self) -> bool:
        """Tell whether the alarm rings (module bar highlight).

        Returns:
            Whether the timer is ``RINGING``.
        """
        return self.queries.current_view().state is TimerStateEnum.RINGING

    def countdown_active(self) -> bool:
        """Tell whether a countdown would be lost by quitting.

        Returns:
            Whether the timer is running, paused or ringing.
        """
        return self.queries.current_view().state is not TimerStateEnum.IDLE


def build_timer(
    app: QApplication, config: AppConfig, paths: AppPaths, translator: TranslatorPort, *, core: Core, storage: Storage
) -> TimerServices:
    """Create the timer side once the data file is open.

    Args:
        app: Owner of the sound players.
        config: Loaded configuration.
        paths: Application paths (``assets/sounds``).
        translator: Current-language translator.
        core: Main-thread services.
        storage: Storage services (store and timer defaults).

    Returns:
        The services.
    """
    defaults = storage.timer_defaults
    engine = TimerEngine(
        clock=core.clock,
        config=StoreTimerConfigReader(storage.store),
        event_bus=core.event_bus,
        fallback=defaults.settings,
        blink_interval_ms=config.ui.alert_blink_interval_ms,
    )
    catalog = BuiltinSoundCatalog(paths.sounds_dir)
    preview_player = QtSoundPlayer("preview", app)
    queries = TimerQueries(engine, StoreTimerConfigReader(storage.store), catalog, preview_player, defaults.snooze)
    commands = _commands(engine, core, storage)
    editor = TimerEditPresenter(
        translator, core.gate, core.renderer, queries, commands, SoundPreview(preview_player, catalog), defaults.limits
    )
    return TimerServices(
        engine=engine,
        queries=queries,
        catalog=catalog,
        alarm_player=QtSoundPlayer("alarm", app),
        defaults=defaults,
        editor=editor,
        presenter=_presenter(config, translator, core, (queries, commands, editor)),
    )


def _commands(engine: TimerEngine, core: Core, storage: Storage) -> TimerCommands:
    """Create the timer write use cases.

    Args:
        engine: Runtime countdown.
        core: Main-thread services.
        storage: Store and timer defaults.

    Returns:
        The use cases.
    """
    return TimerCommands(
        engine=engine,
        reader=StoreTimerConfigReader(storage.store),
        writer=StoreTimerConfigWriter(storage.store),
        clock=core.clock,
        event_bus=core.event_bus,
        limits=storage.timer_defaults.limits,
        snooze=storage.timer_defaults.snooze,
    )


def _presenter(
    config: AppConfig,
    translator: TranslatorPort,
    core: Core,
    parts: tuple[TimerQueries, TimerCommands, TimerEditPresenter],
) -> TimerPresenter:
    """Create the timer panel presenter and subscribe it to the timer events.

    Args:
        config: Loaded configuration (blink interval).
        translator: Current-language translator.
        core: Main-thread services.
        parts: Queries, commands and the edit presenter it opens.

    Returns:
        The presenter.
    """
    queries, commands, editor = parts
    presenter = TimerPresenter(
        translator,
        core.gate,
        core.renderer,
        queries,
        commands,
        DateTimeFormatter(translator, core.clock),
        editor.open,
        config.ui.alert_blink_interval_ms,
    )
    core.event_bus.subscribe(TimerChangedEvent, presenter.on_timer_changed)
    core.event_bus.subscribe(TimerConfigChangedEvent, presenter.on_config_changed)
    return presenter


def connect_alarm(
    timer: TimerServices, window: MainWindow, config: AppConfig, translator: TranslatorPort, core: Core
) -> AlarmCoordinator:
    """Start the alarm coordinator once the notification area icon exists.

    Args:
        timer: Timer services.
        window: Main window (taskbar button and notification area icon).
        config: Loaded configuration (notification duration).
        translator: Texts of the notification.
        core: Main-thread services (event bus).

    Returns:
        The coordinator, subscribed to ``TimerChangedEvent``.
    """
    attention = QtAttention(window.tray.tray_icon, window, config.timer.notification_duration_ms)
    alarm = AlarmCoordinator(
        player=timer.alarm_player,
        catalog=timer.catalog,
        attention=attention,
        translator=translator,
        settings=timer.engine.settings,
        fallback_sound=timer.defaults.fallback_sound,
    )
    core.event_bus.subscribe(TimerChangedEvent, alarm.on_timer_changed)
    return alarm
