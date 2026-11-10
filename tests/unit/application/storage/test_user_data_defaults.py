from dataclasses import replace
from pathlib import Path

import pytest

from concentrator.application.common.event_bus import EventBus
from concentrator.application.settings.settings_defaults import SettingsDefaults
from concentrator.application.storage.save_coordinator import SaveCoordinator
from concentrator.application.storage.save_state_enum import SaveStateEnum
from concentrator.application.storage.startup_commands import StartupCommands
from concentrator.application.storage.storage_events import UserDataChangedEvent
from concentrator.application.storage.user_data import StoredUserData
from concentrator.application.storage.user_data_defaults import SectionDefaults, UserDataDefaults
from concentrator.application.timer.chime_defaults import ChimeDefaults
from concentrator.application.timer.timer_defaults import TimerDefaults
from concentrator.application.todo.todo_defaults import TodoDefaults
from concentrator.domain.settings.general_settings import GeneralSettings
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.domain.settings.log_level_enum import LogLevelEnum
from concentrator.domain.timer.duration import Duration
from concentrator.domain.timer.hourly_chime import HourlyChime, HourlyChimeId
from concentrator.domain.timer.sound_ref import SoundRef
from concentrator.domain.timer.timer_config import TimerConfig, TimerConfigId
from concentrator.domain.timer.timer_limits import TimerLimits
from concentrator.domain.timer.timer_presets_collection import TimerPresetsCollection
from concentrator.domain.timer.volume import Volume
from concentrator.domain.todo.priority_enum import PriorityEnum
from concentrator.domain.todo.task_lists_collection import TaskListsCollection
from concentrator.domain.todo.tasks_collection import TasksCollection
from tests.fakes.app_config_factory import (
    make_chime_section,
    make_settings_section,
    make_storage_section,
    make_timer_section,
    make_todo_section,
)
from tests.fakes.fake_clock import FakeClock
from tests.fakes.fake_id_generator import FakeIdGenerator
from tests.fakes.fake_translator import FakeTranslator
from tests.fakes.fake_user_data_file import FakeUserDataFile, report, valid
from tests.fakes.in_memory_session import InMemorySession
from tests.fakes.in_memory_view_preferences import InMemoryViewPreferences
from tests.fakes.manual_scheduler import ManualScheduler
from tests.fakes.recording_error_reporter import RecordingErrorReporter
from tests.fakes.timer_extras_factory import DEFAULT_CHIME_SETTINGS, DEFAULT_SECTIONS
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
    return UserDataDefaults(FakeIdGenerator("timer"), clock or FakeClock(), DEFAULT_SECTIONS, FakeTranslator())


def test_initial_data_has_a_timer_from_the_defaults() -> None:
    clock = FakeClock()

    data = _defaults(clock).initial(make_settings())

    assert data.timer == TimerConfig.create(TimerConfigId("timer-0001"), clock.now_utc(), DEFAULT_SETTINGS)
    assert data.settings == make_settings()


def test_initial_data_seeds_the_favorites_and_the_chime() -> None:
    clock = FakeClock()

    data = _defaults(clock).initial(make_settings())

    assert data.timer_presets is not None
    assert [(preset.id, preset.label, preset.duration.seconds, preset.position) for preset in data.timer_presets] == [
        ("timer-0002", "", 900, 0),
        ("timer-0003", "", 1800, 1),
        ("timer-0004", "", 2700, 2),
    ]
    assert {preset.created_at for preset in data.timer_presets} == {clock.now_utc()}
    assert data.hourly_chime == HourlyChime.create(
        HourlyChimeId("timer-0005"), clock.now_utc(), enabled=False, settings=DEFAULT_CHIME_SETTINGS
    )


def test_section_defaults_gather_the_ini_values() -> None:
    timer = TimerDefaults.from_section(make_timer_section(default_presets_minutes=(5,)))
    chime = ChimeDefaults.from_section(make_chime_section(default_enabled=True))

    settings = SettingsDefaults.from_section(make_settings_section(default_log_level=LogLevelEnum.DEBUG))

    todo = TodoDefaults.from_section(make_todo_section(default_list_priority=PriorityEnum.HIGH))

    sections = SectionDefaults.from_defaults(timer, chime, settings, todo)

    assert sections == SectionDefaults(
        timer=timer.settings,
        presets=(Duration(300),),
        chime_enabled=True,
        chime=DEFAULT_CHIME_SETTINGS,
        settings=SettingsDefaults(log_level=LogLevelEnum.DEBUG, notify_when_inactive=True),
        list_priority=PriorityEnum.HIGH,
    )


def test_new_settings_take_the_chosen_language_and_the_ini_values() -> None:
    clock = FakeClock()

    settings = _defaults(clock).new_settings(LanguageEnum.FRENCH)

    assert settings.general == GeneralSettings(
        language=LanguageEnum.FRENCH, log_level=LogLevelEnum.INFO, notify_when_inactive=True
    )
    assert settings.created_at == clock.now_utc()


def test_complete_adds_a_missing_timer() -> None:
    completed = _defaults().complete(replace(make_user_data(), timer=None))

    assert completed.timer is not None
    assert completed.timer.settings == DEFAULT_SETTINGS


def test_complete_seeds_favorites_only_when_the_key_is_absent() -> None:
    seeded = _defaults().complete(replace(make_user_data(), timer_presets=None))
    emptied = make_user_data().with_timer_presets(TimerPresetsCollection())

    assert seeded.timer_presets is not None
    assert [preset.duration.seconds for preset in seeded.timer_presets] == [900, 1800, 2700]
    assert _defaults().complete(emptied) is emptied


def test_complete_adds_a_missing_chime() -> None:
    completed = _defaults().complete(replace(make_user_data(), hourly_chime=None))

    assert completed.hourly_chime is not None
    assert completed.hourly_chime.settings == DEFAULT_CHIME_SETTINGS
    assert completed.timer_presets == make_user_data().timer_presets


def test_complete_keeps_a_complete_file_as_it_is() -> None:
    data = make_user_data()

    assert _defaults().complete(data) is data


def test_initial_data_has_an_inbox_named_in_the_current_language_and_no_task() -> None:
    clock = FakeClock()

    data = _defaults(clock).initial(make_settings())

    assert data.task_lists is not None
    assert [(item.name, item.priority, item.position, item.created_at) for item in data.task_lists] == [
        ("en:todo.default_list_name", PriorityEnum.NORMAL, 0, clock.now_utc())
    ]
    assert data.tasks == TasksCollection()


@pytest.mark.parametrize("lists", [None, TaskListsCollection()])
def test_complete_adds_an_inbox_when_the_file_has_no_list(lists: TaskListsCollection | None) -> None:
    completed = _defaults().complete(replace(make_user_data(), task_lists=lists, tasks=None))

    assert completed.task_lists is not None
    assert [item.name for item in completed.task_lists] == ["en:todo.default_list_name"]
    assert completed.tasks == TasksCollection()


def test_complete_session_publishes_a_change_only_when_a_section_was_added() -> None:
    bus = EventBus(RecordingErrorReporter())
    events: list[UserDataChangedEvent] = []
    bus.subscribe(UserDataChangedEvent, events.append)
    session = InMemorySession(bus, make_user_data())
    defaults = _defaults()

    defaults.complete_session(session)
    assert events == []

    session.reset(replace(make_user_data(), timer=None, timer_presets=None, hourly_chime=None))
    defaults.complete_session(session)
    assert len(events) == 1
    current = session.current()
    assert current.timer is not None
    assert current.timer_presets is not None
    assert current.hourly_chime is not None


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
        defaults=_defaults(),
        default_path=PATH,
        event_bus=bus,
    )

    commands.resolve_startup()

    assert session.current().timer is not None
    assert coordinator.status.state is SaveStateEnum.PENDING
