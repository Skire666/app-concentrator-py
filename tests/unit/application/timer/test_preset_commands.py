import pytest

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.timer.duration import Duration
from concentrator.domain.timer.timer_state_enum import TimerStateEnum
from tests.fakes.timer_extras_factory import make_presets
from tests.fakes.timer_factory import DEFAULT_SETTINGS, LIMITS
from tests.fakes.timer_stack import TimerStack


@pytest.fixture
def stack() -> TimerStack:
    return TimerStack()


def _ordered(stack: TimerStack) -> list[tuple[str, int]]:
    return [(preset.id, preset.duration.seconds) for preset in stack.preset_queries.presets()]


def test_apply_and_start_sets_the_duration_and_runs_in_one_call(stack: TimerStack) -> None:
    result = stack.preset_commands.apply_and_start("preset-15")

    assert result.is_success
    assert stack.engine.session.state is TimerStateEnum.RUNNING
    assert stack.engine.settings().duration == Duration(900)
    assert stack.queries.current_view().displayed_seconds == 900
    assert len(stack.config_events) == 1


def test_apply_and_start_with_the_current_duration_only_starts(stack: TimerStack) -> None:
    stack.presets.presets = make_presets(25)

    assert stack.preset_commands.apply_and_start("preset-25").is_success
    assert stack.engine.session.state is TimerStateEnum.RUNNING
    assert stack.config_events == []


@pytest.mark.parametrize("state", [TimerStateEnum.RUNNING, TimerStateEnum.PAUSED, TimerStateEnum.RINGING])
def test_apply_and_start_outside_idle_is_refused_and_keeps_the_configuration(
    stack: TimerStack, state: TimerStateEnum
) -> None:
    if state is TimerStateEnum.RINGING:
        stack.run_to_ringing()
    else:
        stack.commands.start()
        if state is TimerStateEnum.PAUSED:
            stack.commands.pause()

    result = stack.preset_commands.apply_and_start("preset-15")

    assert result.error_codes == (ErrorCodeEnum.TIMER_TRANSITION_INVALID,)
    assert stack.engine.session.state is state
    assert stack.engine.settings() == DEFAULT_SETTINGS


def test_apply_and_start_of_an_unknown_favorite_is_not_found(stack: TimerStack) -> None:
    assert stack.preset_commands.apply_and_start("nope").error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)
    assert stack.engine.session.state is TimerStateEnum.IDLE


def test_apply_and_start_reports_a_failed_configuration_write(stack: TimerStack) -> None:
    stack.config.write_failure = ValidationResult.failure(ErrorCodeEnum.ENTITY_NOT_FOUND)

    result = stack.preset_commands.apply_and_start("preset-15")

    assert result.error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)
    assert stack.engine.session.state is TimerStateEnum.IDLE


def test_create_adds_the_favorite_last_with_a_normalized_label(stack: TimerStack) -> None:
    result = stack.preset_commands.create("  Pomodoro ", Duration(1500))

    assert result.data is not None
    assert (result.data.id, result.data.label, result.data.position) == ("preset-0001", "Pomodoro", 3)
    assert result.data.created_at == stack.clock.now_utc()
    assert _ordered(stack)[-1] == ("preset-0001", 1500)
    assert len(stack.preset_events) == 1


def test_create_refuses_a_duplicate_duration_and_an_invalid_value(stack: TimerStack) -> None:
    duplicate = stack.preset_commands.create("", Duration(900))
    invalid = stack.preset_commands.create("x" * 41, Duration(0))

    assert duplicate.validation.error_codes == (ErrorCodeEnum.PRESET_DURATION_DUPLICATE,)
    assert invalid.validation.error_codes == (
        ErrorCodeEnum.PRESET_LABEL_TOO_LONG,
        ErrorCodeEnum.TIMER_DURATION_TOO_SHORT,
    )
    assert stack.presets.writes == 0
    assert stack.preset_events == []


def test_create_refuses_a_favorite_beyond_the_limit(stack: TimerStack) -> None:
    stack.presets.presets = make_presets(*range(1, LIMITS.max_presets + 1))

    result = stack.preset_commands.create("", Duration(3600))

    assert result.validation.error_codes == (ErrorCodeEnum.PRESET_LIMIT_REACHED,)
    assert not stack.preset_queries.can_add()


def test_update_changes_label_and_duration(stack: TimerStack) -> None:
    stack.clock.advance(seconds=60)

    result = stack.preset_commands.update("preset-30", " Deep work ", Duration(2400))

    assert result.data is not None
    assert (result.data.label, result.data.duration, result.data.updated_at) == (
        "Deep work",
        Duration(2400),
        stack.clock.now_utc(),
    )
    assert len(stack.preset_events) == 1


def test_update_without_change_writes_nothing(stack: TimerStack) -> None:
    result = stack.preset_commands.update("preset-30", "  ", Duration(1800))

    assert result.is_success
    assert stack.presets.writes == 0
    assert stack.preset_events == []


def test_update_may_keep_its_own_duration_but_not_take_another_one(stack: TimerStack) -> None:
    own = stack.preset_commands.update("preset-30", "Half hour", Duration(1800))
    other = stack.preset_commands.update("preset-30", "", Duration(900))

    assert own.is_success
    assert other.validation.error_codes == (ErrorCodeEnum.PRESET_DURATION_DUPLICATE,)


def test_update_of_an_unknown_favorite_is_not_found(stack: TimerStack) -> None:
    assert stack.preset_commands.update("nope", "", Duration(60)).validation.error_codes == (
        ErrorCodeEnum.ENTITY_NOT_FOUND,
    )


def test_delete_removes_the_favorite(stack: TimerStack) -> None:
    assert stack.preset_commands.delete("preset-45").is_success
    assert _ordered(stack) == [("preset-15", 900), ("preset-30", 1800)]
    assert len(stack.preset_events) == 1


def test_delete_of_an_unknown_favorite_is_not_found(stack: TimerStack) -> None:
    assert stack.preset_commands.delete("nope").error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)
    assert stack.preset_events == []


def test_move_first_then_back_changes_the_display_order(stack: TimerStack) -> None:
    assert stack.preset_commands.move("preset-45", -1).is_success
    assert stack.preset_commands.move("preset-45", -1).is_success

    assert _ordered(stack) == [("preset-45", 2700), ("preset-15", 900), ("preset-30", 1800)]
    assert stack.presets.writes == 4
    assert len(stack.preset_events) == 2


def test_move_at_the_end_is_skipped_without_event(stack: TimerStack) -> None:
    assert stack.preset_commands.move("preset-45", 1).is_skipped
    assert stack.preset_events == []


def test_move_reports_a_write_failure(stack: TimerStack) -> None:
    stack.presets.write_failure = ValidationResult.failure(ErrorCodeEnum.ENTITY_NOT_FOUND)

    assert stack.preset_commands.move("preset-30", 1).error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)
    assert stack.preset_events == []


def test_queries_give_one_favorite_and_the_limits(stack: TimerStack) -> None:
    assert stack.preset_queries.preset("preset-30").data == stack.presets.presets.get("preset-30").data
    assert stack.preset_queries.limits is LIMITS
    assert stack.preset_queries.can_add()
