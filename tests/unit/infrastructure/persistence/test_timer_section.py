"""The ``[timer]`` section: codec, mapper and singleton store."""

from dataclasses import replace

import pytest

from concentrator.application.common.event_bus import EventBus
from concentrator.application.storage.storage_events import UserDataChangedEvent
from concentrator.application.storage.user_data import StoredUserData, UserData
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.timer.sound_kind_enum import SoundKindEnum
from concentrator.domain.timer.timer_config import TimerConfigId
from concentrator.infrastructure.persistence.store_timer_config import StoreTimerConfigReader, StoreTimerConfigWriter
from concentrator.infrastructure.persistence.user_data_codec import UserDataCodec
from concentrator.infrastructure.persistence.user_data_store import UserDataStore
from tests.fakes.recording_error_reporter import RecordingErrorReporter
from tests.fakes.timer_factory import DEFAULT_SETTINGS, make_timer_config
from tests.fakes.user_data_factory import SAVED_AT, SPEC_EXAMPLE_TEXT, USER_DATA_LIMITS, make_stored, make_user_data

CODEC = UserDataCodec(app_version="0.1.0", limits=USER_DATA_LIMITS)
TIMER_START = SPEC_EXAMPLE_TEXT.index("[timer]")


def _timer_edited(old: str, new: str) -> str:
    head, timer = SPEC_EXAMPLE_TEXT[:TIMER_START], SPEC_EXAMPLE_TEXT[TIMER_START:]
    assert old in timer
    return head + timer.replace(old, new, 1)


def test_spec_example_timer_section_round_trips() -> None:
    stored = make_stored()

    assert CODEC.decode(CODEC.encode(stored)).data == stored
    assert "sound = { kind = 2, value = 'D:/Music/Alarms/long alarm.mp3' }\n" in CODEC.encode(stored)


def test_file_without_timer_section_loads_with_an_empty_timer() -> None:
    result = CODEC.decode(SPEC_EXAMPLE_TEXT[:TIMER_START].rstrip("\n") + "\n")

    assert result.data is not None
    assert result.data.data.timer is None


def test_empty_timer_is_not_written() -> None:
    stored = StoredUserData(data=replace(make_user_data(), timer=None), saved_at=SAVED_AT)

    assert "[timer]" not in CODEC.encode(stored)


def test_unknown_sound_kind_becomes_unknown_and_fails_the_rules() -> None:
    result = CODEC.decode(_timer_edited("kind = 2", "kind = 7"))

    assert result.data is None
    assert result.validation.error_codes == (ErrorCodeEnum.ENUM_VALUE_UNKNOWN,)
    assert result.validation.issues[0].field == "timer.sound.kind"


def test_backslashes_typed_by_hand_are_normalized() -> None:
    text = _timer_edited("value = 'D:/Music/Alarms/long alarm.mp3'", "value = 'D:\\Music\\Alarms\\long alarm.mp3'")

    result = CODEC.decode(text)

    assert result.data == make_stored()


@pytest.mark.parametrize(
    ("old", "new", "code", "field"),
    [
        ("volume = 80", "volume = 101", ErrorCodeEnum.TIMER_VOLUME_OUT_OF_RANGE, "timer.volume"),
        (
            "duration_seconds = 1500",
            "duration_seconds = 0",
            ErrorCodeEnum.TIMER_DURATION_TOO_SHORT,
            "timer.duration_seconds",
        ),
        ("loop_count = 3", "loop_count = 100", ErrorCodeEnum.TIMER_LOOP_COUNT_OUT_OF_RANGE, "timer.loop_count"),
        (
            "auto_stop_seconds = 120",
            "auto_stop_seconds = 2",
            ErrorCodeEnum.TIMER_AUTO_STOP_OUT_OF_RANGE,
            "timer.auto_stop_seconds",
        ),
        ("kind = 2", "kind = 0", ErrorCodeEnum.TIMER_SOUND_UNSET, "timer.sound"),
        ("loop_forever = false", "loop_forever = 1", ErrorCodeEnum.STORAGE_FIELD_INVALID_TYPE, "timer.loop_forever"),
        ("volume = 80\n", "", ErrorCodeEnum.STORAGE_FIELD_MISSING, "timer.volume"),
        ("value = 'D:", "colour = 1, value = 'D:", ErrorCodeEnum.STORAGE_FIELD_UNEXPECTED, "timer.sound.colour"),
    ],
)
def test_invalid_timer_values_are_reported_per_field(old: str, new: str, code: ErrorCodeEnum, field: str) -> None:
    result = CODEC.decode(_timer_edited(old, new))

    assert result.data is None
    assert result.validation.error_codes == (code,)
    assert result.validation.issues[0].field == field


class StoreSetup:
    def __init__(self, data: UserData) -> None:
        bus = EventBus(RecordingErrorReporter())
        self.events: list[UserDataChangedEvent] = []
        bus.subscribe(UserDataChangedEvent, self.events.append)
        self.store = UserDataStore(bus)
        self.store.reset(data)
        self.reader = StoreTimerConfigReader(self.store)
        self.writer = StoreTimerConfigWriter(self.store)


def test_reader_returns_the_timer_configuration() -> None:
    setup = StoreSetup(make_user_data())

    assert setup.reader.read().data == make_timer_config()


def test_reader_reports_a_missing_section() -> None:
    setup = StoreSetup(replace(make_user_data(), timer=None))

    result = setup.reader.read()

    assert result.validation.error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)
    assert result.validation.issues[0].field == "timer"


def test_writer_replaces_the_configuration_and_publishes_a_change() -> None:
    setup = StoreSetup(make_user_data())
    changed = make_timer_config(DEFAULT_SETTINGS)

    result = setup.writer.update(changed)

    assert result.data == changed
    assert setup.store.current().timer == changed
    assert len(setup.events) == 1


@pytest.mark.parametrize("data", [make_user_data(), replace(make_user_data(), timer=None)])
def test_writer_refuses_another_id_or_a_missing_section(data: UserData) -> None:
    setup = StoreSetup(data)
    other = replace(make_timer_config(), id=TimerConfigId("other"))

    result = setup.writer.update(other)

    assert result.validation.error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)
    assert setup.events == []


def test_sound_kind_is_written_as_an_integer() -> None:
    text = CODEC.encode(make_stored())

    assert f"kind = {SoundKindEnum.FILE.value}," in text
