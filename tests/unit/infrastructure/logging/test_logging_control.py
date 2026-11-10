import logging
from collections.abc import Iterator

import pytest

from concentrator.domain.settings.log_level_enum import LogLevelEnum
from concentrator.infrastructure.logging.logging_control import LoggingControl


@pytest.fixture
def root_level() -> Iterator[None]:
    root = logging.getLogger()
    previous = root.level
    yield
    root.setLevel(previous)


@pytest.mark.usefixtures("root_level")
@pytest.mark.parametrize(
    ("level", "expected"),
    [(LogLevelEnum.DEBUG, logging.DEBUG), (LogLevelEnum.WARNING, logging.WARNING), (LogLevelEnum.CRITICAL, 50)],
)
def test_set_level_changes_the_root_logger(level: LogLevelEnum, expected: int) -> None:
    LoggingControl().set_level(level)

    assert logging.getLogger().level == expected


@pytest.mark.usefixtures("root_level")
def test_set_level_logs_the_change_once(caplog: pytest.LogCaptureFixture) -> None:
    control = LoggingControl()
    logging.getLogger().setLevel(logging.INFO)

    with caplog.at_level(logging.INFO, logger="concentrator.infrastructure.logging.logging_control"):
        control.set_level(LogLevelEnum.INFO)
        control.set_level(LogLevelEnum.ERROR)
        control.set_level(LogLevelEnum.ERROR)

    assert [record.getMessage() for record in caplog.records] == ["Log level set to ERROR"]


@pytest.mark.parametrize("level", [LogLevelEnum.UNSET, LogLevelEnum.UNKNOWN])
def test_unreal_level_is_ignored_with_a_warning(level: LogLevelEnum, caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger("tests.logging_control")
    logger.setLevel(logging.INFO)

    LoggingControl(logger).set_level(level)

    assert logger.level == logging.INFO
    assert "ignored" in caplog.text
