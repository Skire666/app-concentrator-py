from dataclasses import replace

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.severity_enum import SeverityEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.timer.sound_ref import SoundRef
from concentrator.domain.timer.volume import Volume
from concentrator.presentation.timer.chime_settings_form import ChimeSettingsForm
from tests.fakes.timer_extras_factory import DEFAULT_CHIME_SETTINGS

MISSING = SoundRef.file("D:/gone.mp3")


def _check(sound: SoundRef) -> ValidationResult:
    if sound == MISSING:
        return ValidationResult.failure(ErrorCodeEnum.AUDIO_FILE_NOT_FOUND)
    return ValidationResult.success()


def test_dirty_until_reset() -> None:
    form = ChimeSettingsForm(DEFAULT_CHIME_SETTINGS, _check)

    form.set_volume(20)
    assert form.is_dirty

    form.reset()
    assert not form.is_dirty
    assert form.draft == DEFAULT_CHIME_SETTINGS


def test_commit_makes_the_saved_sound_the_stored_one() -> None:
    form = ChimeSettingsForm(DEFAULT_CHIME_SETTINGS, _check)
    form.set_sound(MISSING)
    assert form.errors.severity is SeverityEnum.ERROR

    form.commit()
    form.set_volume(20)

    assert form.baseline.sound == MISSING
    assert form.errors.severity is SeverityEnum.WARNING


def test_rebase_follows_untouched_fields() -> None:
    form = ChimeSettingsForm(DEFAULT_CHIME_SETTINGS, _check)
    form.set_start_hour(9)

    form.rebase(replace(DEFAULT_CHIME_SETTINGS, volume=Volume(10), start_hour=7))

    assert form.draft == replace(DEFAULT_CHIME_SETTINGS, volume=Volume(10), start_hour=9)
    assert form.is_dirty
