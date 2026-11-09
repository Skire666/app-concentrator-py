"""Business rules of the timer favorites."""

from typing import Final

from concentrator.domain.common.entity_rules import EntityRules
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.timer.duration import Duration
from concentrator.domain.timer.timer_config_rules import DURATION_FIELD, TimerConfigRules
from concentrator.domain.timer.timer_limits import TimerLimits
from concentrator.domain.timer.timer_preset import BLOCKED_LABEL_CHARACTERS, TimerPreset
from concentrator.domain.timer.timer_presets_collection import TimerPresetsCollection

LABEL_FIELD: Final = "label"
CHARACTER_SEPARATOR: Final = " "


class TimerPresetRules:
    """Stateless validation of the favorites. Field paths are those of a ``[[timer_presets]]`` element."""

    @staticmethod
    def validate(preset: TimerPreset, limits: TimerLimits) -> ValidationResult:
        """Check the identity, the label and the duration of one favorite.

        Args:
            preset: Favorite to check.
            limits: Bounds from ``concentrator.ini``.

        Returns:
            The merged result.
        """
        return EntityRules.validate_identity(preset).merge(
            TimerPresetRules.validate_values(preset.label, preset.duration, limits)
        )

    @staticmethod
    def validate_values(label: str, duration: Duration, limits: TimerLimits) -> ValidationResult:
        """Check the editable values (the edit dialog validates its draft with this method).

        Args:
            label: Label (normalized or as typed: only its length is checked).
            duration: Countdown duration.
            limits: Bounds from ``concentrator.ini``.

        Returns:
            The merged result, one issue per failing field.
        """
        return TimerPresetRules.validate_label(label, limits).merge(
            TimerConfigRules.validate_duration(duration, limits)
        )

    @staticmethod
    def validate_label(label: str, limits: TimerLimits) -> ValidationResult:
        """Check the characters and the length of a label (an empty label means the automatic one).

        Args:
            label: Label.
            limits: Bounds from ``concentrator.ini``.

        Returns:
            Success, ``PRESET_LABEL_CHARACTER_INVALID`` (``characters``: the blocked characters) or
            ``PRESET_LABEL_TOO_LONG`` (``max``).
        """
        if any(character in BLOCKED_LABEL_CHARACTERS for character in label):
            characters = CHARACTER_SEPARATOR.join(BLOCKED_LABEL_CHARACTERS)
            return ValidationResult.failure(
                ErrorCodeEnum.PRESET_LABEL_CHARACTER_INVALID, field=LABEL_FIELD, characters=characters
            )
        if len(label) <= limits.max_preset_label_length:
            return ValidationResult.success()
        return ValidationResult.failure(
            ErrorCodeEnum.PRESET_LABEL_TOO_LONG, field=LABEL_FIELD, max=limits.max_preset_label_length
        )

    @staticmethod
    def validate_unique_duration(
        presets: TimerPresetsCollection, duration: Duration, except_id: str = ""
    ) -> ValidationResult:
        """Check that no other favorite has a duration.

        Args:
            presets: Current favorites.
            duration: Duration of the new or edited favorite.
            except_id: Favorite being edited.

        Returns:
            Success or ``PRESET_DURATION_DUPLICATE`` on ``duration_seconds`` (``duration`` as ``HH:MM:SS``).
        """
        if presets.with_duration(duration, except_id) is None:
            return ValidationResult.success()
        return ValidationResult.failure(
            ErrorCodeEnum.PRESET_DURATION_DUPLICATE, field=DURATION_FIELD, duration=duration.as_clock_text()
        )

    @staticmethod
    def validate_room(presets: TimerPresetsCollection, limits: TimerLimits) -> ValidationResult:
        """Check that one more favorite can be added.

        Args:
            presets: Current favorites.
            limits: Bounds from ``concentrator.ini``.

        Returns:
            Success or ``PRESET_LIMIT_REACHED`` (``max``).
        """
        if len(presets) < limits.max_presets:
            return ValidationResult.success()
        return ValidationResult.failure(ErrorCodeEnum.PRESET_LIMIT_REACHED, max=limits.max_presets)

    @staticmethod
    def validate_collection(presets: TimerPresetsCollection, limits: TimerLimits) -> ValidationResult:
        """Check a whole collection read from a file: every favorite, the limit and the unique durations.

        Args:
            presets: Favorites in stored order.
            limits: Bounds from ``concentrator.ini``.

        Returns:
            The merged result; fields are ``<position in the file>.<field>``.
        """
        results = [
            TimerPresetRules.validate(preset, limits).prefixed(str(index)) for index, preset in enumerate(presets)
        ]
        seen: set[Duration] = set()
        for index, preset in enumerate(presets):
            if preset.duration in seen:
                duplicate = ValidationResult.failure(
                    ErrorCodeEnum.PRESET_DURATION_DUPLICATE,
                    field=f"{index}.{DURATION_FIELD}",
                    duration=preset.duration.as_clock_text(),
                )
                results.append(duplicate)
            seen.add(preset.duration)
        if len(presets) > limits.max_presets:
            results.append(ValidationResult.failure(ErrorCodeEnum.PRESET_LIMIT_REACHED, max=limits.max_presets))
        return ValidationResult.success().merge(*results)
