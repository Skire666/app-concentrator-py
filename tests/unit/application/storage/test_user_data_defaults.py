from dataclasses import replace
from pathlib import Path

from concentrator.application.common.event_bus import EventBus
from concentrator.application.storage.save_coordinator import SaveCoordinator
from concentrator.application.storage.save_state_enum import SaveStateEnum
from concentrator.application.storage.startup_commands import StartupCommands
from concentrator.application.storage.storage_events import UserDataChangedEvent
from concentrator.application.storage.user_data import StoredUserData
from concentrator.application.storage.user_data_defaults import UserDataDefaults
from concentrator.application.timer.timer_defaults import TimerDefaults
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.domain.timer.duration import Duration
from concentrator.domain.timer.sound_ref import SoundRef
from concentrator.domain.timer.timer_config import TimerConfig, TimerConfigId
from concentrator.domain.timer.timer_limits import TimerLimits
from concentrator.domain.timer.volume import Volume
from tests.fakes.app_config_factory import make_storage_section, make_timer_section
from tests.fakes.fake_clock import FakeClock
from tests.fakes.fake_id_generator import FakeIdGenerator
from tests.fakes.fake_user_data_file import FakeUserDataFile, report, valid
from tests.fakes.in_memory_session import InMemorySession
from tests.fakes.in_memory_view_preferences import InMemoryViewPreferences
from tests.fakes.manual_scheduler import ManualScheduler
from tests.fakes.recording_error_reporter import RecordingErrorReporter
from tests.fakes.timer_factory import DEFAULT_SETTINGS
from tests.fakes.user_data_factory import SAVED_AT, make_settings, make_user_data

PATH = Path("D:/sync/concentrator.toml")


def test_timer_defaults_come_from_the_ini_section() -> None:
    defaults = TimerDefaults.from_section(make_timer_section(default_sound="alarm-soft", snooze_minutes=7))

    assert defaults.settings.duration == Duration(1500)
    assert defaults.settings.sound == SoundRef.builtin("alarm-soft")
    assert defaults.settings.volume == Volume(80)
    assert defaults.settings.loop_count == 3
    assert not defaults.settings.loop_forever
    assert defaults.settings.auto_stop_seconds == 120
    assert not defaults.settings.auto_restart
    assert defaults.snooze == Duration(420)
    assert defaults.fallback_sound == SoundRef.builtin("alarm-soft")
    assert defaults.limits == TimerLimits(
        min_duration_seconds=1,
        max_duration_seconds=359_999,
        max_loop_count=99,
        min_auto_stop_seconds=5,
        max_auto_stop_seconds=3600,
        max_presets=12,
        max_preset_label_length=40,
    )
    assert defaults.presets == (Duration(900), Duration(1800), Duration(2700))


def _defaults(clock: FakeClock | None = None) -> UserDataDefaults:
    return UserDataDefaults(FakeIdGenerator("timer"), clock or FakeClock(), DEFAULT_SETTINGS)


def test_initial_data_has_a_timer_from_the_defaults() -> None:
    clock = FakeClock()

    data = _defaults(clock).initial(make_settings())

    assert data.timer == TimerConfig.create(TimerConfigId("timer-0001"), clock.now_utc(), DEFAULT_SETTINGS)
    assert data.settings == make_settings()


def test_complete_adds_a_missing_timer() -> None:
    completed = _defaults().complete(replace(make_user_data(), timer=None))

    assert completed.timer is not None
    assert completed.timer.settings == DEFAULT_SETTINGS


def test_complete_keeps_a_complete_file_as_it_is() -> None:
    data = make_user_data()

    assert _defaults().complete(data) is data


def test_complete_session_publishes_a_change_only_when_a_section_was_added() -> None:
    bus = EventBus(RecordingErrorReporter())
    events: list[UserDataChangedEvent] = []
    bus.subscribe(UserDataChangedEvent, events.append)
    session = InMemorySession(bus, make_user_data())
    defaults = _defaults()

    defaults.complete_session(session)
    assert events == []

    session.reset(replace(make_user_data(), timer=None))
    defaults.complete_session(session)
    assert len(events) == 1
    assert session.current().timer is not None


def test_opening_a_file_without_timer_saves_the_completed_file() -> None:
    bus = EventBus(RecordingErrorReporter())
    session = InMemorySession(bus)
    file = FakeUserDataFile()
    coordinator = SaveCoordinator(
        session=session, file=file, scheduler=ManualScheduler(), event_bus=bus, storage=make_storage_section()
    )
    preferences = InMemoryViewPreferences()
    preferences.values["storage/data_file_path"] = PATH.as_posix()
    stored = StoredUserData(data=replace(make_user_data(LanguageEnum.ENGLISH), timer=None), saved_at=SAVED_AT)
    file.reports[PATH] = report(PATH, valid(stored))
    commands = StartupCommands(
        file=file,
        session=session,
        coordinator=coordinator,
        preferences=preferences,
        ids=FakeIdGenerator(),
        clock=FakeClock(),
        defaults=_defaults(),
        default_path=PATH,
    )

    commands.resolve_startup()

    assert session.current().timer is not None
    assert coordinator.status.state is SaveStateEnum.PENDING
