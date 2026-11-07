from pathlib import Path

import pytest

from concentrator.application.storage.save_state_enum import SaveStateEnum
from concentrator.application.storage.storage_events import SaveStatusChangedEvent
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.presentation.common.date_time_formatter import DateTimeFormatter
from concentrator.presentation.storage.save_status_texts import SaveStatusTexts
from tests.fakes.fake_clock import FakeClock
from tests.fakes.fake_translator import FakeTranslator
from tests.fakes.user_data_factory import SAVED_AT

PATH = Path("D:/sync/concentrator.toml")


def _texts() -> SaveStatusTexts:
    translator = FakeTranslator()
    return SaveStatusTexts(translator, DateTimeFormatter(translator, FakeClock()))


@pytest.mark.parametrize(
    ("state", "text"),
    [
        (SaveStateEnum.NO_FILE, "en:status.save.no_file"),
        (SaveStateEnum.UNKNOWN, "en:status.save.no_file"),
        (SaveStateEnum.PENDING, "en:status.save.pending"),
        (SaveStateEnum.SAVING, "en:status.save.saving"),
        (SaveStateEnum.SAVED, "en:status.save.saved"),
    ],
)
def test_simple_states(state: SaveStateEnum, text: str) -> None:
    assert _texts().describe(SaveStatusChangedEvent(state=state)).text == text


def test_saved_shows_the_local_time_and_the_path() -> None:
    described = _texts().describe(SaveStatusChangedEvent(state=SaveStateEnum.SAVED, path=PATH, saved_at=SAVED_AT))

    assert described.text == "en:status.save.saved_at(time=en:format.time_with_seconds(hour=17,minute=44,second=03))"
    assert described.tooltip == "en:status.save.tooltip.path(path=D:/sync/concentrator.toml)"


def test_saved_with_a_warning_lists_it_in_the_tooltip() -> None:
    status = SaveStatusChangedEvent(
        state=SaveStateEnum.SAVED,
        path=PATH,
        saved_at=SAVED_AT,
        validation=ValidationResult.warning(ErrorCodeEnum.STORAGE_BACKUP_FAILED),
    )

    assert _texts().describe(status).tooltip.splitlines()[1] == "en:error.storage_backup_failed"


def test_failure_says_it_retries() -> None:
    status = SaveStatusChangedEvent(
        state=SaveStateEnum.FAILED, path=PATH, validation=ValidationResult.failure(ErrorCodeEnum.STORAGE_REPLACE_FAILED)
    )

    described = _texts().describe(status)

    assert described.text == "en:status.save.failed(reason=en:error.storage_replace_failed)"
    assert "en:error.storage_replace_failed" in described.tooltip


def test_external_change_says_saving_stopped() -> None:
    status = SaveStatusChangedEvent(
        state=SaveStateEnum.FAILED, validation=ValidationResult.failure(ErrorCodeEnum.STORAGE_FILE_CHANGED_EXTERNALLY)
    )

    described = _texts().describe(status)

    assert described.text == "en:status.save.stopped(reason=en:error.storage_file_changed_externally)"
    assert described.tooltip == "en:error.storage_file_changed_externally"
