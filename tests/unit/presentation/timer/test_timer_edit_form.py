from dataclasses import replace

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.severity_enum import SeverityEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.timer.duration import Duration
from concentrator.domain.timer.sound_ref import SoundRef
from concentrator.domain.timer.timer_settings import TimerSettings
from concentrator.domain.timer.volume import Volume
from concentrator.presentation.timer.timer_edit_form import TimerEditForm
from tests.fakes.timer_factory import DEFAULT_SETTINGS, LIMITS

MISSING = SoundRef.file("E:/gone.mp3")


class SoundChecker:
    def __init__(self, missing: frozenset[SoundRef] = frozenset({MISSING})) -> None:
        self.missing = missing
        self.calls: list[SoundRef] = []

    def __call__(self, sound: SoundRef) -> ValidationResult:
        self.calls.append(sound)
        if sound in self.missing:
            return ValidationResult.failure(ErrorCodeEnum.AUDIO_FILE_NOT_FOUND)
        return ValidationResult.success()


def _form(baseline: TimerSettings = DEFAULT_SETTINGS, checker: SoundChecker | None = None) -> TimerEditForm:
    return TimerEditForm(baseline, LIMITS, checker or SoundChecker())


def test_a_new_form_is_clean_and_cannot_be_submitted() -> None:
    form = _form()

    assert not form.is_dirty
    assert not form.can_submit
    assert form.errors.is_success


def test_a_valid_change_makes_the_form_submittable() -> None:
    form = _form()

    form.set_duration(0, 30, 0)

    assert form.draft.duration == Duration(1800)
    assert form.is_dirty
    assert form.can_submit


def test_changing_back_to_the_baseline_is_clean_again() -> None:
    form = _form()
    form.set_volume(10)

    form.set_volume(DEFAULT_SETTINGS.volume.percent)

    assert not form.is_dirty


def test_an_invalid_change_shows_an_inline_error_and_blocks_saving() -> None:
    form = _form()

    form.set_duration(0, 0, 0)

    assert form.errors.error_codes == (ErrorCodeEnum.TIMER_DURATION_TOO_SHORT,)
    assert form.errors.issues[0].field == "duration_seconds"
    assert form.is_dirty
    assert not form.can_submit


def test_every_setter_changes_its_field() -> None:
    form = _form()

    form.set_sound(SoundRef.builtin("alarm-soft"))
    form.set_volume(42)
    form.set_loop_count(7)
    form.set_loop_forever(True)
    form.set_auto_stop(30)
    form.set_auto_restart(True)

    assert form.draft == replace(
        DEFAULT_SETTINGS,
        sound=SoundRef.builtin("alarm-soft"),
        volume=Volume(42),
        loop_count=7,
        loop_forever=True,
        auto_stop_seconds=30,
        auto_restart=True,
    )


def test_a_missing_chosen_sound_blocks_saving() -> None:
    form = _form()

    form.set_sound(MISSING)

    assert form.errors.error_codes == (ErrorCodeEnum.AUDIO_FILE_NOT_FOUND,)
    assert form.errors.issues[0].field == "sound"
    assert not form.can_submit


def test_a_missing_stored_sound_is_only_a_warning() -> None:
    form = _form(replace(DEFAULT_SETTINGS, sound=MISSING))

    form.set_volume(10)

    assert form.errors.issues[0].severity is SeverityEnum.WARNING
    assert form.can_submit


def test_the_sound_is_checked_once_per_sound() -> None:
    checker = SoundChecker()
    form = _form(checker=checker)

    form.set_volume(10)
    form.set_volume(20)
    form.set_sound(SoundRef.builtin("alarm-soft"))
    form.set_volume(30)

    assert checker.calls == [DEFAULT_SETTINGS.sound, SoundRef.builtin("alarm-soft")]


def test_an_unset_sound_is_reported_by_the_rules_only() -> None:
    checker = SoundChecker()
    form = _form(checker=checker)

    form.set_sound(SoundRef.file(""))

    assert form.errors.error_codes == (ErrorCodeEnum.TIMER_SOUND_UNSET,)
    assert SoundRef.file("") not in checker.calls


def test_commit_makes_the_draft_the_baseline() -> None:
    form = _form()
    form.set_sound(MISSING)
    form.set_volume(5)

    form.commit()

    assert not form.is_dirty
    assert form.baseline.volume == Volume(5)
    assert form.errors.issues[0].severity is SeverityEnum.WARNING
