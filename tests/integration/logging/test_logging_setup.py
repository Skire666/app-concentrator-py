import io
import logging
import warnings
from collections.abc import Iterator
from pathlib import Path

import pytest

from concentrator.application.common.app_config import LoggingSection
from concentrator.infrastructure.logging.logging_setup import FAULTHANDLER_FILE_NAME, configure_logging
from tests.fakes.app_config_factory import make_app_config

LOGGING: LoggingSection = make_app_config().logging


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


def test_configure_logging_writes_formatted_lines_to_file_buffer_and_stream(tmp_path: Path) -> None:
    stream = io.StringIO()
    runtime = configure_logging(LOGGING, tmp_path / "logs", stream=stream, enable_faulthandler=False)

    logging.getLogger("tests.setup").info("Startup step %d", 1)
    logging.getLogger("tests.setup").debug("hidden at INFO")
    runtime.shutdown()

    line = (tmp_path / "logs" / "concentrator.log").read_text(encoding="utf-8").strip()
    assert line.endswith("| INFO     | MainThread | tests.setup | Startup step 1")
    assert "hidden at INFO" not in line
    assert stream.getvalue().strip() == line
    assert [entry.message for entry in runtime.ring_buffer.entries_since(0)] == ["Startup step 1"]


def test_shutdown_removes_the_handlers(tmp_path: Path) -> None:
    root = logging.getLogger()
    before = set(root.handlers)
    runtime = configure_logging(LOGGING, tmp_path, stream=None, enable_faulthandler=False)
    assert set(root.handlers) > before

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


def test_faulthandler_file_is_created_and_closed(tmp_path: Path) -> None:
    runtime = configure_logging(LOGGING, tmp_path, stream=None, enable_faulthandler=True)

    runtime.shutdown()

    assert (tmp_path / FAULTHANDLER_FILE_NAME).is_file()


def test_unusable_log_folder_keeps_the_journal_working(tmp_path: Path) -> None:
    blocker = tmp_path / "file-not-folder"
    blocker.write_text("x", encoding="utf-8")

    runtime = configure_logging(LOGGING, blocker / "logs", stream=None, enable_faulthandler=True)
    logging.getLogger("tests.setup").info("still recorded")
    messages = [entry.message for entry in runtime.ring_buffer.entries_since(0)]
    runtime.shutdown()

    assert any(message.startswith("Log file disabled") for message in messages)
    assert "still recorded" in messages
