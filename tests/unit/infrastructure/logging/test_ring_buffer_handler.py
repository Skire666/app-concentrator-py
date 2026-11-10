import logging
import threading
from collections.abc import Iterator
from datetime import UTC

import pytest

from concentrator.infrastructure.logging.ring_buffer_handler import RingBufferHandler


@pytest.fixture
def logger() -> Iterator[logging.Logger]:
    test_logger = logging.getLogger("tests.ring_buffer")
    test_logger.setLevel(logging.DEBUG)
    test_logger.propagate = False
    yield test_logger
    for handler in test_logger.handlers[:]:
        if isinstance(handler, RingBufferHandler):
            test_logger.removeHandler(handler)
    test_logger.propagate = True


def test_error_count_counts_error_and_critical_records_even_once_evicted(logger: logging.Logger) -> None:
    buffer = _attach(logger, 2)

    logger.error("one")
    logger.warning("not an error")
    logger.critical("two")
    logger.info("pushes the errors out")
    logger.info("again")

    assert buffer.error_count() == 2
    assert [entry.message for entry in buffer.entries_since(0)] == ["pushes the errors out", "again"]


def _fail() -> None:
    raise ValueError("bad")


def _attach(logger: logging.Logger, capacity: int) -> RingBufferHandler:
    handler = RingBufferHandler(capacity)
    logger.addHandler(handler)
    return handler


def test_records_get_increasing_sequence_numbers_and_details(logger: logging.Logger) -> None:
    buffer = _attach(logger, 10)

    logger.info("first %s", "value")
    logger.warning("second")

    entries = buffer.entries_since(0)
    assert [entry.sequence for entry in entries] == [1, 2]
    assert [entry.message for entry in entries] == ["first value", "second"]
    assert entries[1].level == logging.WARNING
    assert entries[1].level_name == "WARNING"
    assert entries[1].logger_name == "tests.ring_buffer"
    assert entries[1].thread_name == threading.current_thread().name
    assert entries[1].created_at.tzinfo is UTC


def test_buffer_is_bounded_and_keeps_the_newest(logger: logging.Logger) -> None:
    buffer = _attach(logger, 3)

    for index in range(5):
        logger.info("message %d", index)

    entries = buffer.entries_since(0)
    assert [entry.message for entry in entries] == ["message 2", "message 3", "message 4"]
    assert [entry.sequence for entry in entries] == [3, 4, 5]


def test_entries_since_returns_only_newer_records(logger: logging.Logger) -> None:
    buffer = _attach(logger, 10)
    for index in range(4):
        logger.info("message %d", index)

    assert [entry.sequence for entry in buffer.entries_since(2)] == [3, 4]
    assert buffer.entries_since(4) == ()


def test_exception_traceback_is_part_of_the_message(logger: logging.Logger) -> None:
    buffer = _attach(logger, 10)

    try:
        _fail()
    except ValueError:
        logger.exception("failed")

    message = buffer.entries_since(0)[0].message
    assert message.startswith("failed")
    assert "ValueError: bad" in message


def test_malformed_arguments_are_kept_as_text() -> None:
    buffer = RingBufferHandler(10)
    record = logging.LogRecord("tests", logging.INFO, __file__, 1, "two %s %s", ("only one",), None)

    buffer.handle(record)

    assert buffer.entries_since(0)[0].message.startswith("<unformattable log message 'two %s %s'")
