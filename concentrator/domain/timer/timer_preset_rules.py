"""Business rules of the timer favorites."""

from collections.abc import Sequence
from dataclasses import replace
from typing import Final

from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.entity_rules import ID_FIELD, EntityRules
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.severity_enum import SeverityEnum
from concentrator.domain.common.validation_issue import ValidationIssue
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
    def usable(presets: Sequence[TimerPreset], limits: TimerLimits) -> DataResult[TimerPresetsCollection]:
        """Keep the favorites read from a file that work, in position order (owner decision at the review).

        A label that breaks a rule is cleared (the automatic label is shown) and the favorite is kept. A
        favorite with a bad identity or duration, a repeated id or duration, or beyond
        ``timer.max_presets`` is left out; the first favorites by position win.

        Args:
            presets: Favorites in file order.
            limits: Bounds from ``concentrator.ini``.

        Returns:
            The kept favorites, with one WARNING issue per ignored value (fields
            ``<position in the file>.<field>``).
        """
        kept: list[TimerPreset] = []
        warnings: list[ValidationIssue] = []
        for index, preset in sorted(enumerate(presets), key=lambda pair: pair[1].position):
            cleared, label = TimerPresetRules._with_usable_label(preset, limits)
            refused = TimerPresetRules._refusal(cleared, kept, limits)
            warnings.extend(_as_warnings(label.merge(refused), index))
            if not refused.is_failure:
                kept.append(cleared)
        return DataResult.ok(TimerPresetsCollection(kept), ValidationResult.of(*warnings))

    @staticmethod
    def _with_usable_label(preset: TimerPreset, limits: TimerLimits) -> tuple[TimerPreset, ValidationResult]:
        """Clear a label that breaks a rule.

        Args:
            preset: Favorite read from a file.
            limits: Bounds from ``concentrator.ini``.

        Returns:
            The favorite (with an empty label if its label was refused) and the label issues.
        """
        label = TimerPresetRules.validate_label(preset.label, limits)
        if label.is_failure:
            return replace(preset, label=""), label
        return preset, label

    @staticmethod
    def _refusal(preset: TimerPreset, kept: Sequence[TimerPreset], limits: TimerLimits) -> ValidationResult:
        """Tell why a favorite read from a file cannot be kept.

        Args:
            preset: Favorite with a usable label.
            kept: Favorites kept so far.
            limits: Bounds from ``concentrator.ini``.

        Returns:
            Success, the identity or duration failures, ``ENTITY_DUPLICATE_ID``,
            ``PRESET_DURATION_DUPLICATE`` or ``PRESET_LIMIT_REACHED``.
        """
        own = EntityRules.validate_identity(preset).merge(TimerConfigRules.validate_duration(preset.duration, limits))
        if own.is_failure:
            return own
        if any(item.id == preset.id for item in kept):
            return ValidationResult.failure(ErrorCodeEnum.ENTITY_DUPLICATE_ID, field=ID_FIELD)
        duplicate = TimerPresetRules.validate_unique_duration(TimerPresetsCollection(kept), preset.duration)
        if duplicate.is_failure:
            return duplicate
        return TimerPresetRules.validate_room(TimerPresetsCollection(kept), limits)


def _as_warnings(result: ValidationResult, index: int) -> list[ValidationIssue]:
    """Turn the issues of one favorite into warnings placed under its position in the file.

    Args:
        result: Issues of the favorite.
        index: Its position in the file.

    Returns:
        The warnings.
    """
    return [replace(issue, severity=SeverityEnum.WARNING) for issue in result.prefixed(str(index)).issues]
