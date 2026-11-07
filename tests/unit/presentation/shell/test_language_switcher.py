import pytest

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from tests.fakes.storage_stack import StorageStack


@pytest.fixture
def stack() -> StorageStack:
    stack = StorageStack()
    stack.renderer.register(RenderSectionEnum.STATUS_BAR, lambda: stack.translator.language, lambda _value: None)
    return stack


def test_toggle_stores_then_shows_the_other_language(stack: StorageStack) -> None:
    result = stack.switcher.toggle()

    assert result.is_success
    assert stack.settings.settings.language is LanguageEnum.FRENCH
    assert stack.translator.language is LanguageEnum.FRENCH
    assert stack.hint.read() is LanguageEnum.FRENCH
    assert stack.scheduler.pending_count == 1


def test_toggle_twice_comes_back(stack: StorageStack) -> None:
    stack.switcher.toggle()
    stack.switcher.toggle()

    assert stack.translator.language is LanguageEnum.ENGLISH
    assert stack.settings.settings.language is LanguageEnum.ENGLISH


def test_settings_failure_leaves_the_translator_alone(stack: StorageStack) -> None:
    stack.settings.write_failure = ValidationResult.failure(ErrorCodeEnum.ENTITY_NOT_FOUND)

    result = stack.switcher.toggle()

    assert result.error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)
    assert stack.translator.language is LanguageEnum.ENGLISH
    assert stack.hint.read() is LanguageEnum.UNSET


def test_follow_refused_by_the_translator_keeps_the_hint(stack: StorageStack) -> None:
    stack.translator.refused = frozenset({LanguageEnum.FRENCH})

    result = stack.switcher.follow(LanguageEnum.FRENCH)

    assert result.is_failure
    assert stack.hint.read() is LanguageEnum.UNSET
    assert stack.scheduler.pending_count == 0


def test_follow_shows_a_stored_language_without_storing_it(stack: StorageStack) -> None:
    stack.switcher.follow(LanguageEnum.FRENCH)

    assert stack.translator.language is LanguageEnum.FRENCH
    assert stack.settings.updates == 0
