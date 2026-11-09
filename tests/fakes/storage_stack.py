"""The storage side wired with fakes, for presenter tests."""

from pathlib import Path
from typing import Final, Protocol

from concentrator.application.common.event_bus import EventBus
from concentrator.application.settings.language_hint import LanguageHint
from concentrator.application.settings.settings_commands import SettingsCommands
from concentrator.application.storage.external_change_commands import ExternalChangeCommands
from concentrator.application.storage.save_coordinator import SaveCoordinator
from concentrator.application.storage.startup_commands import StartupCommands
from concentrator.application.storage.storage_events import SaveStatusChangedEvent
from concentrator.application.storage.user_data_defaults import UserDataDefaults
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.date_time_formatter import DateTimeFormatter
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.shell.language_switcher import LanguageSwitcher
from tests.fakes.app_config_factory import make_storage_section
from tests.fakes.fake_clock import FakeClock
from tests.fakes.fake_dialogs import FakeDialogs
from tests.fakes.fake_id_generator import FakeIdGenerator
from tests.fakes.fake_translator import FakeTranslator
from tests.fakes.fake_user_data_file import FakeUserDataFile
from tests.fakes.in_memory_session import InMemorySession
from tests.fakes.in_memory_user_settings import InMemoryUserSettings
from tests.fakes.in_memory_view_preferences import InMemoryViewPreferences
from tests.fakes.manual_scheduler import ManualScheduler
from tests.fakes.recording_error_reporter import RecordingErrorReporter
from tests.fakes.timer_extras_factory import DEFAULT_SECTIONS
from tests.fakes.user_data_factory import make_settings

DATA_PATH: Final = Path("D:/sync/concentrator.toml")
DEFAULT_PATH: Final = Path("C:/Users/me/AppData/Roaming/Concentrator/concentrator.toml")
COOLDOWN_MS: Final = 100


class ActionHandler(Protocol):
    def on_action_requested(self, action_value: int) -> None: ...


class StorageStack:
    """Every collaborator of the storage presenters, wired like bootstrap does."""

    def __init__(self, language: LanguageEnum = LanguageEnum.ENGLISH) -> None:
        self.clock = FakeClock()
        self.scheduler = ManualScheduler()
        self.bus = EventBus(RecordingErrorReporter())
        self.statuses: list[SaveStatusChangedEvent] = []
        self.bus.subscribe(SaveStatusChangedEvent, self.statuses.append)
        self.session = InMemorySession(self.bus)
        self.file = FakeUserDataFile()
        self.preferences = InMemoryViewPreferences()
        self.translator = FakeTranslator(language)
        self.dialogs = FakeDialogs()
        self.renderer = RenderCoordinator(self.scheduler)
        self.gate = ActionGate(
            self.clock, self.scheduler, self.renderer, cooldown_ms=COOLDOWN_MS, slow_threshold_ms=200
        )
        self.formatter = DateTimeFormatter(self.translator, self.clock)
        self.coordinator = SaveCoordinator(
            session=self.session,
            file=self.file,
            scheduler=self.scheduler,
            event_bus=self.bus,
            storage=make_storage_section(),
        )
        ids = FakeIdGenerator()
        defaults = UserDataDefaults(ids, self.clock, DEFAULT_SECTIONS)
        self.commands = StartupCommands(
            file=self.file,
            session=self.session,
            coordinator=self.coordinator,
            preferences=self.preferences,
            ids=ids,
            clock=self.clock,
            defaults=defaults,
            default_path=DEFAULT_PATH,
        )
        self.external = ExternalChangeCommands(self.file, self.session, self.coordinator, defaults)
        self.settings = InMemoryUserSettings(make_settings(language))
        self.hint = LanguageHint(self.preferences)
        self.switcher = LanguageSwitcher(
            self.translator,
            self.hint,
            self.renderer,
            SettingsCommands(self.settings, self.settings, self.clock, self.bus),
        )

    def after_cooldown(self) -> None:
        """Let the action gate release every action."""
        self.scheduler.advance(COOLDOWN_MS)

    def click(self, handler: ActionHandler, action: ActionIdEnum) -> None:
        """Release the gate, then send an action to a presenter."""
        self.after_cooldown()
        handler.on_action_requested(int(action))
