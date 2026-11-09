"""``[[timer_presets]]`` and ``[hourly_chime]``: codec, mappers and stores."""

from dataclasses import replace
from typing import Final

import pytest

from concentrator.application.common.event_bus import EventBus
from concentrator.application.storage.storage_events import UserDataChangedEvent
from concentrator.application.storage.user_data import StoredUserData, UserData
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.timer.duration import Duration
from concentrator.domain.timer.hourly_chime import HourlyChimeId
from concentrator.domain.timer.timer_presets_collection import TimerPresetsCollection
from concentrator.infrastructure.persistence.store_hourly_chime import StoreHourlyChimeReader, StoreHourlyChimeWriter
from concentrator.infrastructure.persistence.store_timer_presets import StoreTimerPresetReader, StoreTimerPresetWriter
from concentrator.infrastructure.persistence.user_data_codec import UserDataCodec
from concentrator.infrastructure.persistence.user_data_store import UserDataStore
from tests.fakes.recording_error_reporter import RecordingErrorReporter
from tests.fakes.timer_extras_factory import make_chime, make_preset, make_presets
from tests.fakes.user_data_factory import SAVED_AT, SPEC_EXAMPLE_TEXT, USER_DATA_LIMITS, make_user_data

CODEC: Final = UserDataCodec(app_version="0.1.0", limits=USER_DATA_LIMITS)
PRESETS_START: Final = SPEC_EXAMPLE_TEXT.index("[[timer_presets]]")
CHIME_START: Final = SPEC_EXAMPLE_TEXT.index("[hourly_chime]")
PRESET_BLOCK: Final = SPEC_EXAMPLE_TEXT[PRESETS_START:CHIME_START]


def _encode(data: UserData) -> str:
    return CODEC.encode(StoredUserData(data=data, saved_at=SAVED_AT))


def _chime_edited(old: str, new: str) -> str:
    chime = SPEC_EXAMPLE_TEXT[CHIME_START:]
    assert old in chime
    return SPEC_EXAMPLE_TEXT[:CHIME_START] + chime.replace(old, new, 1)


def _with_presets(*blocks: str) -> str:
    return SPEC_EXAMPLE_TEXT[:PRESETS_START] + "".join(blocks) + SPEC_EXAMPLE_TEXT[CHIME_START:]


def _preset_block(preset_id: str, seconds: int, position: int, label: str = "") -> str:
    block = PRESET_BLOCK.replace("019a5c20-1111-7aaa-8bbb-1c2d3e4f5a6b", preset_id)
    return (
        block.replace("duration_seconds = 900", f"duration_seconds = {seconds}")
        .replace("position = 0", f"position = {position}")
        .replace("label = ''", f"label = '{label}'")
    )


def test_spec_example_sections_are_read() -> None:
    result = CODEC.decode(SPEC_EXAMPLE_TEXT)

    assert result.data is not None
    assert result.data.data == make_user_data()


def test_favorites_are_written_in_position_order() -> None:
    stored_order = TimerPresetsCollection((make_preset(45, 2), make_preset(15, 0), make_preset(30, 1)))

    text = _encode(make_user_data().with_timer_presets(stored_order))

    assert text.index("duration_seconds = 900") < text.index("duration_seconds = 1800")
    assert text.index("duration_seconds = 1800") < text.index("duration_seconds = 2700")
    decoded = CODEC.decode(text).data
    assert decoded is not None
    assert decoded.data.timer_presets == stored_order.ordered()


def test_no_favorite_is_written_as_an_empty_array_and_read_back_empty() -> None:
    text = _encode(make_user_data().with_timer_presets(TimerPresetsCollection()))

    assert "\ntimer_presets = []\n[settings]" not in text
    assert "app_version = '0.1.0'\ntimer_presets = []\n" in text
    assert "[[timer_presets]]" not in text
    decoded = CODEC.decode(text).data
    assert decoded is not None
    assert decoded.data.timer_presets == TimerPresetsCollection()


def test_file_without_the_phase_3_sections_reads_them_as_absent() -> None:
    result = CODEC.decode(SPEC_EXAMPLE_TEXT[:PRESETS_START].rstrip("\n") + "\n")

    assert result.data is not None
    assert (result.data.data.timer_presets, result.data.data.hourly_chime) == (None, None)


def test_absent_sections_are_not_written() -> None:
    text = _encode(replace(make_user_data(), timer_presets=None, hourly_chime=None))

    assert "timer_presets" not in text
    assert "hourly_chime" not in text


def test_a_label_with_an_apostrophe_round_trips() -> None:
    data = make_user_data().with_timer_presets(TimerPresetsCollection((make_preset(25, label="Tom's tea"),)))

    text = _encode(data)

    assert "label = '''Tom's tea'''" in text
    decoded = CODEC.decode(text).data
    assert decoded is not None
    assert decoded.data == data


def _favorites(text: str) -> list[tuple[str, str, int]]:
    result = CODEC.decode(text)
    assert result.data is not None
    assert result.validation.is_success
    presets = result.data.data.timer_presets
    assert presets is not None
    return [(preset.id, preset.label, preset.duration.seconds) for preset in presets.ordered()]


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("position = 1\n", ""),
        ("position = 1", "position = '1'"),
        ("label = ''", "label = ''\ncolour = 1"),
        ("duration_seconds = 900", "duration_seconds = 0"),
        ("created_at = '2026-11-06T16:40:00Z'", "created_at = 'yesterday'"),
    ],
)
def test_a_broken_favorite_is_ignored_with_a_warning(old: str, new: str, caplog: pytest.LogCaptureFixture) -> None:
    text = _with_presets(_preset_block("a", 600, 0), _preset_block("b", 900, 1).replace(old, new, 1))

    assert _favorites(text) == [("a", "", 600)]
    assert "Favorite 1 " in caplog.text
    assert "of the data file ignored" in caplog.text


@pytest.mark.parametrize("label", ["x" * 41, "a/b", "<b>x</b>"])
def test_a_bad_label_is_cleared_and_the_favorite_kept(label: str, caplog: pytest.LogCaptureFixture) -> None:
    text = _with_presets(_preset_block("a", 900, 0, label=label))

    assert _favorites(text) == [("a", "", 900)]
    assert "Favorite value ignored in the data file" in caplog.text
    assert label not in caplog.text


def test_a_label_written_on_two_lines_is_cleaned() -> None:
    text = _with_presets(_preset_block("a", 900, 0).replace("label = ''", 'label = "  Deep\\nwork  "'))

    assert _favorites(text) == [("a", "Deep work", 900)]


def test_duplicate_durations_and_ids_keep_the_first_favorite() -> None:
    text = _with_presets(_preset_block("a", 900, 0), _preset_block("b", 900, 1), _preset_block("a", 1800, 2))

    assert _favorites(text) == [("a", "", 900)]


def test_favorites_above_the_ini_limit_are_ignored() -> None:
    limit = USER_DATA_LIMITS.timer.max_presets
    blocks = [_preset_block(f"p{index}", 60 * (index + 1), index) for index in range(limit + 1)]

    assert len(_favorites(_with_presets(*blocks))) == limit


def test_favorites_that_are_not_a_list_still_make_the_file_invalid() -> None:
    without_presets = SPEC_EXAMPLE_TEXT[:PRESETS_START] + SPEC_EXAMPLE_TEXT[CHIME_START:]
    text = without_presets.replace("app_version = '0.1.0'\n", "app_version = '0.1.0'\ntimer_presets = 3\n")

    result = CODEC.decode(text)

    assert result.data is None
    assert result.validation.error_codes == (ErrorCodeEnum.STORAGE_FIELD_INVALID_TYPE,)


@pytest.mark.parametrize(
    ("old", "new", "code", "field"),
    [
        ("start_hour = 8", "start_hour = 24", ErrorCodeEnum.CHIME_HOUR_OUT_OF_RANGE, "hourly_chime.start_hour"),
        ("start_hour = 8", "start_hour = 21", ErrorCodeEnum.CHIME_HOURS_REVERSED, "hourly_chime.end_hour"),
        ("volume = 60", "volume = 101", ErrorCodeEnum.TIMER_VOLUME_OUT_OF_RANGE, "hourly_chime.volume"),
        ("kind = 1", "kind = 9", ErrorCodeEnum.ENUM_VALUE_UNKNOWN, "hourly_chime.sound.kind"),
        ("enabled = false", "enabled = 0", ErrorCodeEnum.STORAGE_FIELD_INVALID_TYPE, "hourly_chime.enabled"),
        ("end_hour = 20\n", "", ErrorCodeEnum.STORAGE_FIELD_MISSING, "hourly_chime.end_hour"),
    ],
)
def test_invalid_chime_values_are_reported_per_field(old: str, new: str, code: ErrorCodeEnum, field: str) -> None:
    result = CODEC.decode(_chime_edited(old, new))

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
        self.presets = StoreTimerPresetReader(self.store)
        self.preset_writer = StoreTimerPresetWriter(self.store)
        self.chime = StoreHourlyChimeReader(self.store)
        self.chime_writer = StoreHourlyChimeWriter(self.store)


def test_preset_reader_offers_the_generic_reads() -> None:
    setup = StoreSetup(make_user_data().with_timer_presets(make_presets()))

    assert setup.presets.exists("preset-30").data is True
    assert setup.presets.read_item("preset-30").data == make_preset(30, 1)
    assert setup.presets.all_items().data == make_presets()
    found = setup.presets.find(_LongerThan(1000)).data
    assert found is not None
    assert [preset.id for preset in found] == ["preset-30", "preset-45"]


def test_preset_reader_sees_no_favorite_before_completion() -> None:
    setup = StoreSetup(replace(make_user_data(), timer_presets=None))

    assert setup.presets.all_items().data == TimerPresetsCollection()


def test_preset_writer_changes_the_store_and_publishes() -> None:
    setup = StoreSetup(make_user_data().with_timer_presets(make_presets()))

    setup.preset_writer.create(make_preset(60, 3))
    setup.preset_writer.update(make_preset(15, 0, label="Short"))
    setup.preset_writer.delete("preset-45")

    presets = setup.store.current().timer_presets
    assert isinstance(presets, TimerPresetsCollection)
    assert [(preset.id, preset.label) for preset in presets] == [
        ("preset-15", "Short"),
        ("preset-30", ""),
        ("preset-60", ""),
    ]
    assert len(setup.events) == 3


def test_chime_reader_and_writer() -> None:
    setup = StoreSetup(make_user_data())
    enabled = make_chime(enabled=True)

    assert setup.chime.read().data == make_chime()
    assert setup.chime_writer.update(enabled).data == enabled
    assert setup.store.current().hourly_chime == enabled
    assert len(setup.events) == 1


@pytest.mark.parametrize("data", [make_user_data(), replace(make_user_data(), hourly_chime=None)])
def test_chime_writer_refuses_another_id_or_a_missing_section(data: UserData) -> None:
    setup = StoreSetup(data)

    result = setup.chime_writer.update(replace(make_chime(), id=HourlyChimeId("other")))

    assert result.validation.error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)
    assert setup.events == []


def test_chime_reader_reports_a_missing_section() -> None:
    result = StoreSetup(replace(make_user_data(), hourly_chime=None)).chime.read()

    assert result.validation.error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)
    assert result.validation.issues[0].field == "hourly_chime"


class _LongerThan:
    def __init__(self, seconds: int) -> None:
        self._seconds = seconds

    def matches(self, entity: object) -> bool:
        duration = getattr(entity, "duration", Duration(0))
        return isinstance(duration, Duration) and duration.seconds > self._seconds


def test_a_favorite_with_a_number_json_cannot_hold_is_ignored(caplog: pytest.LogCaptureFixture) -> None:
    broken = _preset_block("b", 900, 1).replace("duration_seconds = 900", "duration_seconds = nan")

    assert _favorites(_with_presets(_preset_block("a", 600, 0), broken)) == [("a", "", 600)]
    assert "Favorite 1 of the data file ignored: number that JSON cannot represent" in caplog.text
