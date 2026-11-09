"""Checks that the sound of a form draft can be played (timer alarm, hourly chime)."""

from collections.abc import Callable

from concentrator.domain.common.severity_enum import SeverityEnum
from concentrator.domain.common.validation_issue import ValidationIssue
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.timer.sound_ref import SoundRef
from concentrator.domain.timer.timer_config_rules import SOUND_FIELD, TimerConfigRules


class SoundCheck:
    """Checks each sound once, since the check reads the disk.

    A problem with the stored sound (a custom file deleted since) is a warning: the other settings can
    still be saved, and the player falls back to the default sound. A problem with a newly chosen sound
    blocks saving.
    """

    def __init__(self, stored: SoundRef, check: Callable[[SoundRef], ValidationResult]) -> None:
        """Start checking.

        Args:
            stored: Sound of the stored settings.
            check: Tells whether a sound exists and can be played.
        """
        self._stored = stored
        self._check = check
        self._checked: dict[SoundRef, ValidationResult] = {}

    def issues(self, sound: SoundRef) -> ValidationResult:
        """Check a sound of the draft.

        Args:
            sound: Sound being edited.

        Returns:
            The issues on ``sound`` (none when the rules already reject the sound).
        """
        if not TimerConfigRules.validate_sound(sound).is_success:
            return ValidationResult.success()
        if sound not in self._checked:
            self._checked[sound] = self._check(sound)
        severity = SeverityEnum.WARNING if sound == self._stored else SeverityEnum.ERROR
        issues = (
            ValidationIssue(code=issue.code, severity=severity, field=SOUND_FIELD, params=issue.params)
            for issue in self._checked[sound].issues
        )
        return ValidationResult.of(*issues)

    def commit(self, sound: SoundRef) -> None:
        """Make a saved sound the stored one.

        Args:
            sound: Sound just saved.
        """
        self._stored = sound
