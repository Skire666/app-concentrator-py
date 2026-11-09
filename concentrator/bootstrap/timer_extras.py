"""Wiring of the timer favorites and of the hourly chime (phase 3)."""

from dataclasses import dataclass

from PySide6.QtWidgets import QApplication

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.application.timer.chime_commands import ChimeCommands
from concentrator.application.timer.chime_queries import ChimeQueries
from concentrator.application.timer.chime_service import ChimeService
from concentrator.application.timer.preset_commands import PresetCommands
from concentrator.application.timer.preset_queries import PresetQueries
from concentrator.application.timer.timer_events import (
    HourlyChimeChangedEvent,
    TimerChangedEvent,
    TimerPresetsChangedEvent,
)
from concentrator.bootstrap.core import Core
from concentrator.bootstrap.storage import Storage
from concentrator.bootstrap.timer import TimerServices
from concentrator.infrastructure.persistence.store_hourly_chime import StoreHourlyChimeReader, StoreHourlyChimeWriter
from concentrator.infrastructure.persistence.store_timer_presets import StoreTimerPresetReader, StoreTimerPresetWriter
from concentrator.infrastructure.qt.qt_sound_player import QtSoundPlayer
from concentrator.presentation.timer.chime_presenter import ChimePresenter
from concentrator.presentation.timer.chime_settings_presenter import ChimeSettingsPresenter
from concentrator.presentation.timer.preset_edit_presenter import PresetEditPresenter
from concentrator.presentation.timer.presets_presenter import PresetsPresenter


@dataclass(frozen=True, slots=True, kw_only=True)
class TimerExtras:
    """Favorites and hourly chime, kept alive by the shell.

    Attributes:
        presets: Favorites panel presenter (its delete confirmation is attached with the main window).
        preset_editor: Favorite dialog presenter (its dialog is attached with the main window).
        chime: Special options presenter.
        chime_editor: Chime dialog presenter (its dialog is attached with the main window).
        chime_service: Plays the chime (registered on the ticker).
        chime_player: Player of the chime (stopped on exit).
    """

    presets: PresetsPresenter
    preset_editor: PresetEditPresenter
    chime: ChimePresenter
    chime_editor: ChimeSettingsPresenter
    chime_service: ChimeService
    chime_player: QtSoundPlayer


def build_timer_extras(
    app: QApplication, translator: TranslatorPort, *, core: Core, storage: Storage, timer: TimerServices
) -> TimerExtras:
    """Create the favorites and the hourly chime once the data file is open.

    Args:
        app: Owner of the chime player.
        translator: Current-language translator.
        core: Main-thread services.
        storage: Store, timer limits and chime defaults.
        timer: Timer services (commands, queries, sound catalog, preview, ringing state).

    Returns:
        The services, subscribed to their events.
    """
    presets, preset_editor = _presets(translator, core, storage, timer)
    chime, chime_editor, chime_queries = _chime(translator, core, storage, timer)
    chime_player = QtSoundPlayer("chime", app)
    service = ChimeService(
        clock=core.clock,
        queries=chime_queries,
        ringing=timer.ringing,
        player=chime_player,
        catalog=timer.catalog,
        window_seconds=storage.chime_defaults.trigger_window_seconds,
    )
    return TimerExtras(
        presets=presets,
        preset_editor=preset_editor,
        chime=chime,
        chime_editor=chime_editor,
        chime_service=service,
        chime_player=chime_player,
    )


def _chime(
    translator: TranslatorPort, core: Core, storage: Storage, timer: TimerServices
) -> tuple[ChimePresenter, ChimeSettingsPresenter, ChimeQueries]:
    """Create the chime presenters and subscribe the special options to the chime events.

    Args:
        translator: Current-language translator.
        core: Main-thread services.
        storage: Store and chime defaults.
        timer: Timer services (sounds and preview).

    Returns:
        The special options presenter, the dialog presenter and the chime queries.
    """
    queries = ChimeQueries(StoreHourlyChimeReader(storage.store), storage.chime_defaults)
    commands = ChimeCommands(
        StoreHourlyChimeReader(storage.store), StoreHourlyChimeWriter(storage.store), core.clock, core.event_bus
    )
    editor = ChimeSettingsPresenter(
        translator,
        core.gate,
        core.renderer,
        queries=queries,
        commands=commands,
        sounds=timer.queries,
        preview=timer.preview,
    )
    presenter = ChimePresenter(translator, core.gate, core.renderer, queries, commands, editor.open)
    core.event_bus.subscribe(HourlyChimeChangedEvent, presenter.on_chime_changed)
    return presenter, editor, queries


def _presets(
    translator: TranslatorPort, core: Core, storage: Storage, timer: TimerServices
) -> tuple[PresetsPresenter, PresetEditPresenter]:
    """Create the favorite presenters and subscribe the panel to the timer and favorite events.

    Args:
        translator: Current-language translator.
        core: Main-thread services.
        storage: Store and timer limits.
        timer: Timer services.

    Returns:
        The panel presenter and the dialog presenter.
    """
    limits = storage.timer_defaults.limits
    queries = PresetQueries(StoreTimerPresetReader(storage.store), limits)
    commands = PresetCommands(
        reader=StoreTimerPresetReader(storage.store),
        writer=StoreTimerPresetWriter(storage.store),
        timer=timer.commands,
        ids=core.ids,
        clock=core.clock,
        event_bus=core.event_bus,
        limits=limits,
    )
    editor = PresetEditPresenter(translator, core.gate, core.renderer, queries, commands)
    presenter = PresetsPresenter(
        translator, core.gate, core.renderer, queries=queries, timer=timer.queries, commands=commands, editor=editor
    )
    core.event_bus.subscribe(TimerChangedEvent, presenter.on_timer_changed)
    core.event_bus.subscribe(TimerPresetsChangedEvent, presenter.on_presets_changed)
    return presenter, editor
