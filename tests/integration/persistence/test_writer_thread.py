import logging
import threading
from collections.abc import Callable, Iterator

import pytest

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.infrastructure.persistence.writer_thread import WriterThread
from tests.fakes.immediate_dispatcher import ImmediateDispatcher
from tests.fakes.recording_error_reporter import RecordingErrorReporter

TIMEOUT_MS = 5000


@pytest.fixture
def reporter() -> RecordingErrorReporter:
    return RecordingErrorReporter()


@pytest.fixture
def writer(reporter: RecordingErrorReporter) -> Iterator[WriterThread]:
    thread = WriterThread(ImmediateDispatcher(), reporter)
    yield thread
    thread.shutdown()


def test_submitted_jobs_run_in_order_on_the_writer_thread(writer: WriterThread) -> None:
    seen: list[tuple[int, str]] = []

    def job(number: int) -> Callable[[], int]:
        return lambda: (seen.append((number, threading.current_thread().name)), number)[1]

    results: list[int] = []
    for number in range(5):
        writer.submit(job(number), -1, results.append)

    assert writer.flush(TIMEOUT_MS).is_success
    assert results == [0, 1, 2, 3, 4]
    assert [number for number, _name in seen] == [0, 1, 2, 3, 4]
    assert all(name.startswith("writer") for _number, name in seen)


def test_run_sync_returns_the_result(writer: WriterThread) -> None:
    assert writer.run_sync(lambda: 42, -1, TIMEOUT_MS, -2) == 42


def test_failing_job_gives_the_fallback_and_is_reported(
    writer: WriterThread, reporter: RecordingErrorReporter, caplog: pytest.LogCaptureFixture
) -> None:
    def broken() -> int:
        raise RuntimeError("bug")

    with caplog.at_level(logging.CRITICAL):
        result = writer.run_sync(broken, -1, TIMEOUT_MS, -2)

    assert result == -1
    assert [type(error) for error in reporter.errors] == [RuntimeError]
    assert "A write job failed" in caplog.text
    assert "RuntimeError: bug" in caplog.text


def test_failing_submitted_job_gives_the_fallback_to_on_done(
    writer: WriterThread, reporter: RecordingErrorReporter
) -> None:
    def broken() -> int:
        raise ValueError("bug")

    results: list[int] = []
    writer.submit(broken, -1, results.append)
    writer.flush(TIMEOUT_MS)

    assert results == [-1]
    assert len(reporter.errors) == 1


def test_run_sync_and_flush_time_out_while_a_job_blocks(writer: WriterThread) -> None:
    release = threading.Event()
    writer.submit(lambda: release.wait(TIMEOUT_MS / 1000), False, lambda _result: None)

    try:
        assert writer.run_sync(lambda: 1, -1, 50, -2) == -2
        assert writer.flush(50).error_codes == (ErrorCodeEnum.STORAGE_FLUSH_TIMEOUT,)
    finally:
        release.set()
    assert writer.flush(TIMEOUT_MS).is_success
