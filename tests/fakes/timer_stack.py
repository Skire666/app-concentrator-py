"""The timer application side wired with fakes, like bootstrap does."""

from typing import Final

from concentrator.application.common.event_bus import EventBus
from concentrator.application.timer.alarm_coordinator import AlarmCoordinator
from concentrator.application.timer.sound_preview import SoundPreview
from concentrator.application.timer.timer_commands import TimerCommands
from concentrator.application.timer.timer_engine import TimerEngine
from concentrator.application.timer.timer_events import TimerChangedEvent, TimerConfigChangedEvent
from concentrator.application.timer.timer_queries import TimerQueries
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.domain.timer.duration import Duration
from concentrator.domain.timer.timer_settings import TimerSettings
from tests.fakes.fake_clock import FakeClock
from tests.fakes.fake_sound import FakeAttention, FakeSoundCatalog, FakeSoundPlayer
from tests.fakes.fake_translator import FakeTranslator
from tests.fakes.in_memory_timer_config import InMemoryTimerConfig
from tests.fakes.recording_error_reporter import RecordingErrorReporter
from tests.fakes.timer_factory import DEFAULT_SETTINGS, DEFAULT_SOUND, LIMITS, make_timer_config

BLINK_MS: Final = 500
SNOOZE: Final = Duration.from_minutes(5)


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
        self.catalog = FakeSoundCatalog(builtin=("alarm-classic", "alarm-soft"))
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
            translator=self.translator,
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

    def advance(self, *, ms: float = 0.0, seconds: float = 0.0) -> None:
        """Move the clock and tick once."""
        self.clock.advance(ms=ms, seconds=seconds)
        self.engine.tick()

    def run_to_ringing(self) -> None:
        """Start and let the configured duration elapse."""
        assert self.commands.start().is_success
        self.advance(seconds=self.engine.settings().duration.seconds)
