import logging
from dataclasses import dataclass

import pytest

from concentrator.application.common.event_bus import EventBus
from tests.fakes.recording_error_reporter import RecordingErrorReporter


@dataclass(frozen=True)
class _Pinged:
    value: int


@dataclass(frozen=True)
class _Other:
    pass


class _Recorder:
    def __init__(self) -> None:
        self.received: list[int] = []

    def on_pinged(self, event: _Pinged) -> None:
        self.received.append(event.value)


class _BoomError(RuntimeError):
    def __init__(self, value: int) -> None:
        super().__init__(f"boom {value}")


def _failing_handler(event: _Pinged) -> None:
    raise _BoomError(event.value)


@pytest.fixture
def reporter() -> RecordingErrorReporter:
    return RecordingErrorReporter()


@pytest.fixture
def bus(reporter: RecordingErrorReporter) -> EventBus:
    return EventBus(reporter)


def test_publish_delivers_to_subscribers_of_the_exact_type_in_order(bus: EventBus) -> None:
    calls: list[str] = []
    bus.subscribe(_Pinged, lambda event: calls.append(f"first {event.value}"))
    bus.subscribe(_Pinged, lambda event: calls.append(f"second {event.value}"))
    bus.subscribe(_Other, lambda _event: calls.append("other"))

    bus.publish(_Pinged(1))

    assert calls == ["first 1", "second 1"]


def test_publish_without_subscriber_does_nothing(bus: EventBus, reporter: RecordingErrorReporter) -> None:
    bus.publish(_Other())

    assert reporter.errors == []


def test_failing_handler_is_logged_reported_and_does_not_stop_others(
    bus: EventBus, reporter: RecordingErrorReporter, caplog: pytest.LogCaptureFixture
) -> None:
    recorder = _Recorder()
    bus.subscribe(_Pinged, _failing_handler)
    bus.subscribe(_Pinged, recorder.on_pinged)

    with caplog.at_level(logging.ERROR, logger="concentrator.application.common.event_bus"):
        bus.publish(_Pinged(7))

    assert recorder.received == [7]
    assert [str(error) for error in reporter.errors] == ["boom 7"]
    assert len(caplog.records) == 1
    assert caplog.records[0].exc_info is not None
    assert "_Pinged" in caplog.records[0].getMessage()


def test_handler_subscribed_during_delivery_only_gets_later_events(bus: EventBus) -> None:
    late = _Recorder()

    def subscribe_late(_event: _Pinged) -> None:
        bus.subscribe(_Pinged, late.on_pinged)

    bus.subscribe(_Pinged, subscribe_late)

    bus.publish(_Pinged(1))
    bus.publish(_Pinged(2))

    assert late.received == [2]
