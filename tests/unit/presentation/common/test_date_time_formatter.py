from datetime import UTC, datetime

from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.presentation.common.date_time_formatter import DateTimeFormatter
from tests.fakes.fake_clock import FakeClock
from tests.fakes.fake_translator import FakeTranslator

EARLY = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)


def test_time_with_seconds_is_local_and_zero_padded() -> None:
    formatter = DateTimeFormatter(FakeTranslator(), FakeClock())

    assert formatter.time_with_seconds(EARLY) == "en:format.time_with_seconds(hour=04,minute=04,second=05)"


def test_date_is_zero_padded() -> None:
    formatter = DateTimeFormatter(FakeTranslator(LanguageEnum.FRENCH), FakeClock())

    assert formatter.date(EARLY) == "fr:format.date(day=02,month=01,year=2026)"


def test_date_time_combines_both() -> None:
    text = DateTimeFormatter(FakeTranslator(), FakeClock()).date_time(EARLY)

    assert text.startswith("en:format.datetime(date=en:format.date(day=02,month=01,year=2026),time=")
    assert "hour=04" in text


def test_time_with_milliseconds_pads_the_milliseconds() -> None:
    formatter = DateTimeFormatter(FakeTranslator(), FakeClock())

    text = formatter.time_with_milliseconds(EARLY.replace(microsecond=7_900))

    assert text == "en:format.time_with_milliseconds(hour=04,minute=04,second=05,millisecond=007)"
