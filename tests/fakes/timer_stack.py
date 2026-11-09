"""The timer application side wired with fakes, like bootstrap does."""

from typing import Final

from concentrator.application.common.event_bus import EventBus
from concentrator.application.timer.alarm_coordinator import AlarmCoordinator
from concentrator.application.timer.chime_commands import ChimeCommands
from concentrator.application.timer.chime_defaults import ChimeDefaults
from concentrator.application.timer.chime_queries import ChimeQueries
from concentrator.application.timer.chime_service import ChimeService
from concentrator.application.timer.preset_commands import PresetCommands
from concentrator.application.timer.preset_queries import PresetQueries
from concentrator.application.timer.sound_preview import SoundPreview
from concentrator.application.timer.timer_commands import TimerCommands
from concentrator.application.timer.timer_engine import TimerEngine
from concentrator.application.timer.timer_events import (
    HourlyChimeChangedEvent,
    TimerChangedEvent,
    TimerConfigChangedEvent,
    TimerPresetsChangedEvent,
)
from concentrator.application.timer.timer_queries import TimerQueries
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.domain.timer.duration import Duration
from concentrator.domain.timer.timer_settings import TimerSettings
from concentrator.domain.timer.timer_state_enum import TimerStateEnum
from tests.fakes.app_config_factory import make_chime_section
from tests.fakes.fake_clock import FakeClock
from tests.fakes.fake_id_generator import FakeIdGenerator
from tests.fakes.fake_sound import FakeAttention, FakeSoundCatalog, FakeSoundPlayer
from tests.fakes.fake_translator import FakeTranslator
from tests.fakes.in_memory_timer_config import InMemoryTimerConfig
from tests.fakes.in_memory_timer_extras import InMemoryHourlyChime, InMemoryTimerPresets
from tests.fakes.recording_error_reporter import RecordingErrorReporter
from tests.fakes.timer_extras_factory import make_chime, make_presets
from tests.fakes.timer_factory import DEFAULT_SETTINGS, DEFAULT_SOUND, LIMITS, make_timer_config

BLINK_MS: Final = 500
SNOOZE: Final = Duration.from_minutes(5)
BUILTIN_SOUNDS: Final = ("alarm-classic", "alarm-soft")


class TimerStack:
    """Engine, alarm, commands and queries with recorded events."""

    def __init__(
        self, settings: TimerSettings = DEFAULT_SETTINGS, language: LanguageEnum = LanguageEnum.ENGLISH
    ) -> None:
        self.clock = FakeClock()
        self.reporter = RecordingErrorReporter()
        self.bus = EventBus(self.reporter)
        self.events: list[TimerChangedEvent] = []
        self.config_events: list[TimerConfigChangedEvent] = []
        self.bus.subscribe(TimerChangedEvent, self.events.append)
        self.bus.subscribe(TimerConfigChangedEvent, self.config_events.append)
        self.config = InMemoryTimerConfig(make_timer_config(settings))
        self.translator = FakeTranslator(language)
        self.catalog = FakeSoundCatalog(builtin=BUILTIN_SOUNDS)
        self.alarm_player = FakeSoundPlayer()
        self.preview_player = FakeSoundPlayer()
        self.attention = FakeAttention()
        self.engine = TimerEngine(
            clock=self.clock,
            config=self.config,
            event_bus=self.bus,
            fallback=DEFAULT_SETTINGS,
            blink_interval_ms=BLINK_MS,
        )
        self.alarm = AlarmCoordinator(
            player=self.alarm_player,
            catalog=self.catalog,
            attention=self.attention,
            settings=self.engine.settings,
            fallback_sound=DEFAULT_SOUND,
        )
        self.bus.subscribe(TimerChangedEvent, self.alarm.on_timer_changed)
        self.commands = TimerCommands(
            engine=self.engine,
            reader=self.config,
            writer=self.config,
            clock=self.clock,
            event_bus=self.bus,
            limits=LIMITS,
            snooze=SNOOZE,
        )
        self.queries = TimerQueries(self.engine, self.config, self.catalog, self.preview_player, SNOOZE)
        self.preview = SoundPreview(self.preview_player, self.catalog)
        self._build_extras()

    def _build_extras(self) -> None:
        """Favorites (15, 30, 45 min) and the hourly chime (off, 08-20), with recorded events."""
        self.preset_events: list[TimerPresetsChangedEvent] = []
        self.chime_events: list[HourlyChimeChangedEvent] = []
        self.bus.subscribe(TimerPresetsChangedEvent, self.preset_events.append)
        self.bus.subscribe(HourlyChimeChangedEvent, self.chime_events.append)
        self.presets = InMemoryTimerPresets(make_presets())
        self.preset_commands = PresetCommands(
            reader=self.presets,
            writer=self.presets,
            timer=self.commands,
            ids=FakeIdGenerator("preset"),
            clock=self.clock,
            event_bus=self.bus,
            limits=LIMITS,
        )
        self.preset_queries = PresetQueries(self.presets, LIMITS)
        self.chime = InMemoryHourlyChime(make_chime())
        self.chime_defaults = ChimeDefaults.from_section(make_chime_section())
        self.chime_commands = ChimeCommands(self.chime, self.chime, self.clock, self.bus)
        self.chime_queries = ChimeQueries(self.chime, self.chime_defaults)
        self.chime_player = FakeSoundPlayer()
        self.chime_service = ChimeService(
            clock=self.clock,
            queries=self.chime_queries,
            ringing=lambda: self.engine.session.state is TimerStateEnum.RINGING,
            player=self.chime_player,
            catalog=self.catalog,
            window_seconds=self.chime_defaults.trigger_window_seconds,
        )

    def advance(self, *, ms: float = 0.0, seconds: float = 0.0) -> None:
        """Move the clock and tick once."""
        self.clock.advance(ms=ms, seconds=seconds)
        self.engine.tick()

    def run_to_ringing(self) -> None:
        """Start and let the configured duration elapse."""
        assert self.commands.start().is_success
        self.advance(seconds=self.engine.settings().duration.seconds)
