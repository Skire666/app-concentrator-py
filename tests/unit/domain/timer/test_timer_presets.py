from dataclasses import replace
from datetime import UTC, datetime

import pytest

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.severity_enum import SeverityEnum
from concentrator.domain.timer.duration import Duration
from concentrator.domain.timer.timer_preset import TimerPreset, TimerPresetId, normalize_label
from concentrator.domain.timer.timer_preset_rules import TimerPresetRules
from concentrator.domain.timer.timer_presets_collection import TimerPresetsCollection
from tests.fakes.timer_extras_factory import make_preset, make_presets
from tests.fakes.timer_factory import LIMITS

NOW = datetime(2026, 11, 9, 10, 0, tzinfo=UTC)


def _ids(presets: TimerPresetsCollection) -> list[str]:
    return [preset.id for preset in presets]


@pytest.mark.parametrize(
    ("typed", "stored"),
    [("", ""), ("  Pomodoro  ", "Pomodoro"), ("Deep\nwork", "Deep work"), ("a \t  b", "a b"), ("   ", "")],
)
def test_normalize_label_trims_and_joins_lines(typed: str, stored: str) -> None:
    assert normalize_label(typed) == stored


def test_create_sets_both_timestamps_and_normalizes_the_label() -> None:
    preset = TimerPreset.create(TimerPresetId("p"), NOW, label=" Tea ", duration=Duration(180), position=4)

    assert (preset.created_at, preset.updated_at, preset.label, preset.position) == (NOW, NOW, "Tea", 4)


def test_with_values_and_with_position_touch_updated_at_only() -> None:
    preset = make_preset(15)

    edited = preset.with_values(" Focus ", Duration(1200), NOW)
    moved = preset.with_position(3, NOW)

    assert (edited.label, edited.duration, edited.updated_at, edited.created_at) == (
        "Focus",
        Duration(1200),
        NOW,
        preset.created_at,
    )
    assert (moved.position, moved.updated_at, moved.duration) == (3, NOW, preset.duration)


def test_business_copy_has_a_new_identity_and_the_same_values() -> None:
    copy = make_preset(15, label="Tea").business_copy("copy", NOW)

    assert (copy.id, copy.created_at, copy.updated_at, copy.label, copy.duration) == (
        "copy",
        NOW,
        NOW,
        "Tea",
        Duration(900),
    )


def test_ordered_sorts_by_position_whatever_the_stored_order() -> None:
    presets = TimerPresetsCollection((make_preset(45, 2), make_preset(15, 0), make_preset(30, 1)))

    assert _ids(presets.ordered()) == ["preset-15", "preset-30", "preset-45"]


def test_next_position_follows_the_highest_one() -> None:
    assert TimerPresetsCollection().next_position() == 0
    assert TimerPresetsCollection((make_preset(15, 7), make_preset(30, 2))).next_position() == 8


def test_with_duration_finds_another_favorite_only() -> None:
    presets = make_presets()

    assert presets.with_duration(Duration(1800)) == presets.get("preset-30").data
    assert presets.with_duration(Duration(1800), except_id="preset-30") is None
    assert presets.with_duration(Duration(60)) is None


def test_valid_favorite_passes_the_rules() -> None:
    assert TimerPresetRules.validate(make_preset(15, label="Pomodoro"), LIMITS).is_success


def test_rules_check_identity_label_and_duration() -> None:
    preset = replace(make_preset(15, label="x" * 41, seconds=0), id=TimerPresetId(""))

    codes = TimerPresetRules.validate(preset, LIMITS).error_codes

    assert codes == (
        ErrorCodeEnum.REQUIRED_VALUE_MISSING,
        ErrorCodeEnum.PRESET_LABEL_TOO_LONG,
        ErrorCodeEnum.TIMER_DURATION_TOO_SHORT,
    )


@pytest.mark.parametrize(("length", "valid"), [(0, True), (40, True), (41, False)])
def test_label_length_limit(length: int, valid: bool) -> None:
    result = TimerPresetRules.validate_label("x" * length, LIMITS)

    assert result.is_success is valid
    if not valid:
        assert (result.issues[0].field, result.issues[0].params) == ("label", (("max", "40"),))


def test_unique_duration_ignores_the_edited_favorite() -> None:
    presets = make_presets()

    duplicate = TimerPresetRules.validate_unique_duration(presets, Duration(900))

    assert duplicate.error_codes == (ErrorCodeEnum.PRESET_DURATION_DUPLICATE,)
    assert (duplicate.issues[0].field, duplicate.issues[0].params) == ("duration_seconds", (("duration", "00:15:00"),))
    assert TimerPresetRules.validate_unique_duration(presets, Duration(900), except_id="preset-15").is_success


def test_room_runs_out_at_the_limit() -> None:
    full = make_presets(*range(1, LIMITS.max_presets + 1))

    assert TimerPresetRules.validate_room(make_presets(), LIMITS).is_success
    result = TimerPresetRules.validate_room(full, LIMITS)
    assert result.error_codes == (ErrorCodeEnum.PRESET_LIMIT_REACHED,)
    assert result.issues[0].params == (("max", "12"),)


def test_usable_favorites_keep_valid_ones_unchanged() -> None:
    result = TimerPresetRules.usable(make_presets().items, LIMITS)

    assert result.data == make_presets()
    assert not result.validation.issues


def test_usable_favorites_clear_a_bad_label_and_keep_the_favorite() -> None:
    presets = (make_preset(15, 0, label="y" * 41), make_preset(30, 1, label="a/b"))

    result = TimerPresetRules.usable(presets, LIMITS)

    assert result.data is not None
    assert [preset.label for preset in result.data] == ["", ""]
    assert [(issue.code, issue.field, issue.severity) for issue in result.validation.issues] == [
        (ErrorCodeEnum.PRESET_LABEL_TOO_LONG, "0.label", SeverityEnum.WARNING),
        (ErrorCodeEnum.PRESET_LABEL_CHARACTER_INVALID, "1.label", SeverityEnum.WARNING),
    ]


def test_usable_favorites_drop_bad_durations_identities_and_duplicates() -> None:
    presets = (
        make_preset(15, 0),
        make_preset(30, 1, seconds=0),
        make_preset(45, 2, preset_id="preset-15"),
        make_preset(15, 3, preset_id="again"),
        replace(make_preset(60, 4), id=TimerPresetId(" ")),
    )

    result = TimerPresetRules.usable(presets, LIMITS)

    assert result.data is not None
    assert [preset.id for preset in result.data] == ["preset-15"]
    assert [(issue.code, issue.field) for issue in result.validation.issues] == [
        (ErrorCodeEnum.TIMER_DURATION_TOO_SHORT, "1.duration_seconds"),
        (ErrorCodeEnum.ENTITY_DUPLICATE_ID, "2.id"),
        (ErrorCodeEnum.PRESET_DURATION_DUPLICATE, "3.duration_seconds"),
        (ErrorCodeEnum.REQUIRED_VALUE_MISSING, "4.id"),
    ]


def test_usable_favorites_keep_the_first_ones_by_position_up_to_the_limit() -> None:
    too_many = list(make_presets(*range(1, LIMITS.max_presets + 2)))
    too_many.reverse()

    result = TimerPresetRules.usable(too_many, LIMITS)

    assert result.data is not None
    assert len(result.data) == LIMITS.max_presets
    assert result.data.get(f"preset-{LIMITS.max_presets + 1}").data is None
    assert [(issue.code, issue.field) for issue in result.validation.issues] == [
        (ErrorCodeEnum.PRESET_LIMIT_REACHED, "0")
    ]


@pytest.mark.parametrize("character", ["<", ">", "!", "/", "\\"])
def test_label_refuses_the_blocked_characters(character: str) -> None:
    result = TimerPresetRules.validate_label(f"Deep{character}work", LIMITS)

    assert result.error_codes == (ErrorCodeEnum.PRESET_LABEL_CHARACTER_INVALID,)
    assert (result.issues[0].field, result.issues[0].params) == ("label", (("characters", "< > ! / \\"),))


def test_label_accepts_accents_apostrophes_and_punctuation() -> None:
    assert TimerPresetRules.validate_label("Thé d'après-midi : 1,5 h ?", LIMITS).is_success
