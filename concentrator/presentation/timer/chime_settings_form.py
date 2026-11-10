"""Draft of the hourly chime dialog, validated on every change (``AGENTS.md`` section 8.4)."""

from collections.abc import Callable

from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.timer.chime_settings import ChimeSettings
from concentrator.domain.timer.hourly_chime_rules import HourlyChimeRules
from concentrator.domain.timer.sound_ref import SoundRef
from concentrator.domain.timer.volume import Volume
from concentrator.presentation.common.form_state import FormState
from concentrator.presentation.timer.sound_check import SoundCheck


class ChimeSettingsForm:
    """``FormState`` over ``ChimeSettings``: domain rules plus a check that the sound can be played."""

    def __init__(self, baseline: ChimeSettings, check_sound: Callable[[SoundRef], ValidationResult]) -> None:
        """Start editing.

        Args:
            baseline: Stored settings.
            check_sound: Tells whether a sound exists and can be played.
        """
        self._sound_check = SoundCheck(baseline.sound, check_sound)
        self._state = FormState(baseline, self._validate)

    @property
    def draft(self) -> ChimeSettings:
        """Values being edited."""
        return self._state.draft

    @property
    def baseline(self) -> ChimeSettings:
        """Values the draft is compared with."""
        return self._state.baseline

    @property
    def errors(self) -> ValidationResult:
        """Validation of the draft."""
        return self._state.errors

    @property
    def can_submit(self) -> bool:
        """Whether the draft changed and has no failing issue."""
        return self._state.can_submit

    @property
    def is_dirty(self) -> bool:
        """Whether the draft differs from the baseline."""
        return self._state.is_dirty

    def reset(self) -> None:
        """Discard the changes."""
        self._state.reset()

    def commit(self) -> None:
        """Make the saved draft the baseline; its sound becomes the stored one."""
        self._sound_check.commit(self._state.draft.sound)
        self._state.commit()

    def rebase(self, baseline: ChimeSettings) -> None:
        """Follow stored settings changed elsewhere; edited fields keep their value.

        Args:
            baseline: New stored settings.
        """
        self._sound_check.commit(baseline.sound)
        self._state.rebase(baseline)

    def set_sound(self, sound: SoundRef) -> None:
        """Change the sound.

        Args:
            sound: Built-in sound or file.
        """
        self._state.set_field("sound", sound)

    def set_volume(self, percent: int) -> None:
        """Change the volume.

        Args:
            percent: Volume in percent.
        """
        self._state.set_field("volume", Volume(percent))

    def set_start_hour(self, hour: int) -> None:
        """Change the first full hour that chimes.

        Args:
            hour: Hour (0-23).
        """
        self._state.set_field("start_hour", hour)

    def set_end_hour(self, hour: int) -> None:
        """Change the last full hour that chimes.

        Args:
            hour: Hour (0-23).
        """
        self._state.set_field("end_hour", hour)

    def _validate(self, settings: ChimeSettings) -> ValidationResult:
        """Validate a draft.

        Args:
            settings: Draft.

        Returns:
            The rule issues, plus the sound check on ``sound``.
        """
        return HourlyChimeRules.validate_settings(settings).merge(self._sound_check.issues(settings.sound))
