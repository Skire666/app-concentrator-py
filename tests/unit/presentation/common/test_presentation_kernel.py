from dataclasses import dataclass

import pytest

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.severity_enum import SeverityEnum
from concentrator.domain.common.validation_issue import ValidationIssue
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.action_sections import ACTION_SECTIONS, sections_for
from concentrator.presentation.common.field_error_snapshot import FieldErrorSnapshot
from concentrator.presentation.common.form_state import FormState
from concentrator.presentation.common.layout_keys import LAYOUT_MAIN_WINDOW_GEOMETRY, LAYOUT_PREFIX
from concentrator.presentation.common.layout_state_keeper import LayoutStateKeeper
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.common.ui_texts import UiTexts, action_label_key, error_message_key
from tests.fakes.fake_translator import FakeTranslator
from tests.fakes.in_memory_view_preferences import InMemoryViewPreferences


@dataclass(frozen=True)
class _Draft:
    name: str
    minutes: int


def _validate(draft: _Draft) -> ValidationResult:
    if not draft.name:
        return ValidationResult.failure(ErrorCodeEnum.REQUIRED_VALUE_MISSING, field="name")
    return ValidationResult.success()


@pytest.mark.parametrize("action", [action for action in ActionIdEnum if action.is_set], ids=lambda a: a.name)
def test_every_action_is_mapped_to_registered_sections(action: ActionIdEnum) -> None:
    sections = sections_for(action)

    assert action in ACTION_SECTIONS
    assert sections != ()
    assert all(section.is_set for section in sections)


def test_unmapped_action_has_no_section() -> None:
    assert sections_for(ActionIdEnum.UNKNOWN) == ()
    assert sections_for(ActionIdEnum.SHELL_TOGGLE_LANGUAGE) == (RenderSectionEnum.STATUS_BAR,)


def test_form_state_tracks_dirty_and_submittable_drafts() -> None:
    form = FormState(_Draft(name="Read", minutes=15), _validate)
    assert not form.is_dirty
    assert not form.can_submit

    form.set_field("minutes", 30)
    assert form.is_dirty
    assert form.can_submit
    assert form.draft == _Draft(name="Read", minutes=30)

    form.set_field("name", "")
    assert form.errors.issues_for("name")
    assert not form.can_submit


def test_form_state_reset_and_commit() -> None:
    form = FormState(_Draft(name="Read", minutes=15), _validate)
    form.set_draft(_Draft(name="", minutes=15))

    form.reset()
    assert form.draft == form.baseline
    assert form.errors.is_success

    form.set_field("minutes", 45)
    form.commit()
    assert form.baseline == _Draft(name="Read", minutes=45)
    assert not form.is_dirty


def test_form_state_rebase_keeps_edited_fields_and_follows_the_others() -> None:
    form = FormState(_Draft(name="Read", minutes=15), _validate)
    form.set_field("minutes", 45)

    form.rebase(_Draft(name="Write", minutes=20))

    assert form.baseline == _Draft(name="Write", minutes=20)
    assert form.draft == _Draft(name="Write", minutes=45)
    assert form.is_dirty


def test_form_state_rebase_on_the_edited_value_is_clean() -> None:
    form = FormState(_Draft(name="Read", minutes=15), _validate)
    form.set_field("name", "")

    form.rebase(_Draft(name="", minutes=15))

    assert not form.is_dirty
    assert form.errors.issues_for("name")


def test_layout_state_keeper_round_trip_under_the_layout_prefix() -> None:
    preferences = InMemoryViewPreferences()
    keeper = LayoutStateKeeper(preferences)

    assert keeper.load(LAYOUT_MAIN_WINDOW_GEOMETRY) is None
    keeper.save(LAYOUT_MAIN_WINDOW_GEOMETRY, "AAEC")

    assert keeper.load(LAYOUT_MAIN_WINDOW_GEOMETRY) == "AAEC"
    assert all(key.startswith(LAYOUT_PREFIX) for key in preferences.values)


@pytest.mark.parametrize("key", ["storage/data_file_path", "layout", "main_window/geometry"])
def test_layout_state_keeper_rejects_keys_outside_layout(key: str) -> None:
    keeper = LayoutStateKeeper(InMemoryViewPreferences())

    with pytest.raises(ValueError, match="layout/"):
        keeper.save(key, "x")
    with pytest.raises(ValueError, match="layout/"):
        keeper.load(key)


def test_ui_texts_translate_actions_and_issues() -> None:
    texts = UiTexts(FakeTranslator(missing=frozenset({"action.shell_toggle_language.tooltip"})))
    failure = ValidationResult.failure(ErrorCodeEnum.VALUE_OUT_OF_RANGE, field="minutes", min=1, max=10)
    warning = ValidationResult.warning(ErrorCodeEnum.TEXT_TOO_LONG, field="name", max=5)

    assert action_label_key(ActionIdEnum.SHELL_SHOW_FOCUS) == "action.shell_show_focus"
    assert error_message_key(ErrorCodeEnum.TEXT_TOO_LONG) == "error.text_too_long"
    assert texts.action_label(ActionIdEnum.SHELL_SHOW_FOCUS) == "en:action.shell_show_focus"
    assert texts.action_tooltip(ActionIdEnum.SHELL_SHOW_FOCUS) == "en:action.shell_show_focus.tooltip"
    assert not texts.action_tooltip(ActionIdEnum.SHELL_TOGGLE_LANGUAGE)
    assert (
        texts.issue_message(ValidationIssue(code=ErrorCodeEnum.FORMAT_INVALID, severity=SeverityEnum.ERROR))
        == "en:error.format_invalid"
    )
    assert texts.field_errors(failure.merge(warning)) == (
        FieldErrorSnapshot(field="minutes", message="en:error.value_out_of_range(min=1,max=10)"),
    )


def test_layout_state_keeper_reset_removes_only_layout_keys() -> None:
    preferences = InMemoryViewPreferences(
        {LAYOUT_MAIN_WINDOW_GEOMETRY: "AA==", "layout/journal_page/levels": "1", "storage/data_file_path": "C:/a"}
    )

    LayoutStateKeeper(preferences).reset()

    assert preferences.values == {"storage/data_file_path": "C:/a"}
