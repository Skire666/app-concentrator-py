from dataclasses import replace

import pytest

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.timer.volume import Volume
from tests.fakes.timer_extras_factory import DEFAULT_CHIME_SETTINGS
from tests.fakes.timer_stack import TimerStack


@pytest.fixture
def stack() -> TimerStack:
    return TimerStack()


def test_set_enabled_switches_and_publishes(stack: TimerStack) -> None:
    stack.clock.advance(seconds=30)

    assert stack.chime_commands.set_enabled(True).is_success

    assert stack.chime_queries.enabled() is True
    assert stack.chime.chime is not None
    assert stack.chime.chime.updated_at == stack.clock.now_utc()
    assert [event.chime.enabled for event in stack.chime_events] == [True]


def test_set_enabled_to_the_same_value_writes_nothing(stack: TimerStack) -> None:
    assert stack.chime_commands.set_enabled(False).is_success
    assert stack.chime.updates == []
    assert stack.chime_events == []


def test_update_settings_stores_valid_values(stack: TimerStack) -> None:
    quiet = replace(DEFAULT_CHIME_SETTINGS, volume=Volume(20), start_hour=0, end_hour=23)

    assert stack.chime_commands.update_settings(quiet).is_success

    assert stack.chime_queries.settings() == quiet
    assert len(stack.chime_events) == 1


def test_update_settings_without_change_writes_nothing(stack: TimerStack) -> None:
    assert stack.chime_commands.update_settings(DEFAULT_CHIME_SETTINGS).is_success
    assert stack.chime.updates == []


def test_update_settings_refuses_invalid_hours(stack: TimerStack) -> None:
    result = stack.chime_commands.update_settings(replace(DEFAULT_CHIME_SETTINGS, start_hour=21))

    assert result.error_codes == (ErrorCodeEnum.CHIME_HOURS_REVERSED,)
    assert stack.chime.updates == []


def test_save_stores_the_switch_and_the_settings_in_one_write(stack: TimerStack) -> None:
    quiet = replace(DEFAULT_CHIME_SETTINGS, volume=Volume(20), start_hour=9, end_hour=17)

    assert stack.chime_commands.save(enabled=True, settings=quiet).is_success

    assert len(stack.chime.updates) == 1
    assert stack.chime_queries.enabled() is True
    assert stack.chime_queries.settings() == quiet
    assert len(stack.chime_events) == 1


def test_save_without_change_writes_nothing(stack: TimerStack) -> None:
    assert stack.chime_commands.save(enabled=False, settings=DEFAULT_CHIME_SETTINGS).is_success
    assert stack.chime.updates == []


def test_save_refuses_invalid_hours(stack: TimerStack) -> None:
    result = stack.chime_commands.save(enabled=True, settings=replace(DEFAULT_CHIME_SETTINGS, start_hour=21))

    assert result.error_codes == (ErrorCodeEnum.CHIME_HOURS_REVERSED,)
    assert stack.chime.updates == []


def test_missing_chime_is_reported(stack: TimerStack) -> None:
    stack.chime.chime = None

    assert stack.chime_commands.set_enabled(True).error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)
    assert stack.chime_commands.update_settings(DEFAULT_CHIME_SETTINGS).error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)
    assert stack.chime_commands.save(enabled=True, settings=DEFAULT_CHIME_SETTINGS).error_codes == (
        ErrorCodeEnum.ENTITY_NOT_FOUND,
    )
    assert stack.chime_queries.enabled() is stack.chime_defaults.enabled


def test_write_failure_publishes_nothing(stack: TimerStack) -> None:
    stack.chime.write_failure = ValidationResult.failure(ErrorCodeEnum.ENTITY_NOT_FOUND)

    assert stack.chime_commands.set_enabled(True).error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)
    assert stack.chime_events == []
