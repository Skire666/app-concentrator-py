import io
import logging
import warnings
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest

from concentrator.application.common.app_config import LoggingSection
from concentrator.infrastructure.logging.logging_setup import FAULTHANDLER_FILE_NAME, configure_logging
from tests.fakes.app_config_factory import make_app_config

LOGGING: LoggingSection = make_app_config().logging
LOGGER = "tests.setup"


@pytest.fixture(autouse=True)
def restore_root_logger() -> Iterator[None]:
    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level
    yield
    for handler in root.handlers[:]:
        if handler not in handlers:
            root.removeHandler(handler)
    root.setLevel(level)
    logging.captureWarnings(False)


def _messages(path: Path) -> list[str]:
    return [line.rsplit(" | ", 1)[-1] for line in path.read_text(encoding="utf-8").splitlines()]


def test_stage_one_keeps_records_in_memory_and_creates_no_folder(tmp_path: Path) -> None:
    runtime = configure_logging(LOGGING, tmp_path / "logs", stream=None)

    logging.getLogger(LOGGER).info("buffered %d", 1)
    journal = [entry.message for entry in runtime.ring_buffer.entries_since(0)]
    runtime.shutdown()

    assert journal == ["buffered 1"]
    assert not (tmp_path / "logs").exists()
    assert not runtime.has_log_file


def test_attach_writes_the_buffered_records_first_then_the_new_ones(tmp_path: Path) -> None:
    stream = io.StringIO()
    runtime = configure_logging(LOGGING, tmp_path / "logs", stream=stream, enable_faulthandler=False)
    logging.getLogger(LOGGER).info("Startup step %d", 1)
    logging.getLogger(LOGGER).debug("hidden at INFO")

    assert runtime.attach_log_file()
    logging.getLogger(LOGGER).info("Window shown")
    runtime.shutdown()

    log_file = tmp_path / "logs" / "concentrator.log"
    lines = log_file.read_text(encoding="utf-8").splitlines()
    assert _messages(log_file) == ["Startup step 1", "Window shown"]
    assert lines[0].endswith("| INFO     | MainThread | tests.setup | Startup step 1")
    assert stream.getvalue().splitlines() == lines


def test_attach_is_idempotent(tmp_path: Path) -> None:
    runtime = configure_logging(LOGGING, tmp_path, stream=None, enable_faulthandler=False)
    logging.getLogger(LOGGER).info("once")

    assert runtime.attach_log_file()
    assert runtime.attach_log_file()
    runtime.shutdown()

    assert _messages(tmp_path / "concentrator.log") == ["once"]


def test_shutdown_removes_every_handler(tmp_path: Path) -> None:
    root = logging.getLogger()
    before = set(root.handlers)
    runtime = configure_logging(LOGGING, tmp_path, stream=io.StringIO(), enable_faulthandler=False)
    runtime.attach_log_file()
    assert set(root.handlers) > before

    runtime.shutdown()

    assert set(root.handlers) == before


def test_shutdown_before_attach_removes_the_startup_buffer(tmp_path: Path) -> None:
    root = logging.getLogger()
    before = set(root.handlers)
    runtime = configure_logging(LOGGING, tmp_path, stream=None)

    runtime.shutdown()

    assert set(root.handlers) == before


def test_warnings_are_captured_into_the_log(tmp_path: Path) -> None:
    runtime = configure_logging(LOGGING, tmp_path, stream=None, enable_faulthandler=False)

    with warnings.catch_warnings():
        warnings.simplefilter("always")
        warnings.warn("legacy call", UserWarning, stacklevel=1)

    messages = [entry.message for entry in runtime.ring_buffer.entries_since(0)]
    runtime.shutdown()
    assert any("legacy call" in message for message in messages)


def test_faulthandler_file_is_opened_by_attach_only(tmp_path: Path) -> None:
    runtime = configure_logging(LOGGING, tmp_path, stream=None, enable_faulthandler=True)
    assert not (tmp_path / FAULTHANDLER_FILE_NAME).exists()

    runtime.attach_log_file()
    runtime.shutdown()

    assert (tmp_path / FAULTHANDLER_FILE_NAME).is_file()


def test_unusable_log_folder_keeps_the_journal_working(tmp_path: Path) -> None:
    blocker = tmp_path / "file-not-folder"
    blocker.write_text("x", encoding="utf-8")
    runtime = configure_logging(LOGGING, blocker / "logs", stream=None, enable_faulthandler=True)

    attached = runtime.attach_log_file()
    logging.getLogger(LOGGER).info("still recorded")
    messages = [entry.message for entry in runtime.ring_buffer.entries_since(0)]
    runtime.shutdown()

    assert not attached
    assert any(message.startswith("Log file disabled") for message in messages)
    assert "still recorded" in messages


def test_log_file_rolls_over_while_running(tmp_path: Path) -> None:
    config = replace(LOGGING, file_max_bytes=400, file_backup_count=2)
    runtime = configure_logging(config, tmp_path, stream=None, enable_faulthandler=False)
    runtime.attach_log_file()

    for index in range(40):
        logging.getLogger(LOGGER).info("line %02d of the rollover test", index)
    runtime.shutdown()

    assert (tmp_path / "concentrator.log.1").is_file()
    assert (tmp_path / "concentrator.log.2").is_file()
    assert not (tmp_path / "concentrator.log.3").exists()
    assert _messages(tmp_path / "concentrator.log")[-1] == "line 39 of the rollover test"
