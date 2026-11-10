import logging

import pytest

from concentrator.application.journal.log_levels import log_level_of, python_level_of
from concentrator.domain.settings.log_level_enum import LogLevelEnum


@pytest.mark.parametrize("level", [level for level in LogLevelEnum if level.is_set], ids=lambda level: level.name)
def test_every_real_level_round_trips(level: LogLevelEnum) -> None:
    python_level = python_level_of(level)

    assert python_level is not None
    assert python_level == logging.getLevelNamesMapping()[level.name]
    assert log_level_of(python_level) is level


@pytest.mark.parametrize("level", [LogLevelEnum.UNSET, LogLevelEnum.UNKNOWN])
def test_unreal_levels_have_no_python_level(level: LogLevelEnum) -> None:
    assert python_level_of(level) is None


@pytest.mark.parametrize(
    ("python_level", "expected"),
    [(5, LogLevelEnum.DEBUG), (25, LogLevelEnum.INFO), (45, LogLevelEnum.ERROR), (60, LogLevelEnum.CRITICAL)],
)
def test_custom_levels_count_as_the_standard_level_below(python_level: int, expected: LogLevelEnum) -> None:
    assert log_level_of(python_level) is expected
