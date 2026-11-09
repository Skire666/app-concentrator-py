"""``TimerPresetSchema`` elements <-> ``TimerPresetsCollection``."""

import logging
from collections.abc import Sequence
from typing import Final

from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.validation_issue import ValidationIssue
from concentrator.domain.timer.duration import Duration
from concentrator.domain.timer.timer_limits import TimerLimits
from concentrator.domain.timer.timer_preset import TimerPreset, TimerPresetId, normalize_label
from concentrator.domain.timer.timer_preset_rules import LABEL_FIELD, TimerPresetRules
from concentrator.domain.timer.timer_presets_collection import TimerPresetsCollection
from concentrator.infrastructure.persistence.schemas.timer_preset_schema import TimerPresetSchema

_logger = logging.getLogger(__name__)

_FIELD_SEPARATOR: Final = "."


def _log_ignored(issue: ValidationIssue, presets: Sequence[TimerPreset], field_prefix: str) -> None:
    """Log one value ignored when the favorites were read, without the user's text.

    Args:
        issue: Warning of ``TimerPresetRules.usable`` (field ``<index>.<field>``).
        presets: Favorites as read.
        field_prefix: Dotted path of the collection in the file.
    """
    index, _separator, field = issue.field.partition(_FIELD_SEPARATOR)
    preset_id = presets[int(index)].id
    if field == LABEL_FIELD:
        _logger.warning(
            "Favorite value ignored in the data file: %s.%s.%s (%s)", field_prefix, index, field, issue.code.name
        )
        return
    _logger.warning("Favorite %s (%s) of the data file ignored: %s", index, preset_id, issue.code.name)


class TimerPresetsMapper:
    """Converts the ``[[timer_presets]]`` elements."""

    @staticmethod
    def to_domain(
        schemas: Sequence[TimerPresetSchema], field_prefix: str, limits: TimerLimits
    ) -> DataResult[TimerPresetsCollection]:
        """Build the favorites, keeping those that work (owner decision at the phase 3 review).

        Labels are cleaned (``normalize_label``); a value that breaks a rule is ignored and logged at
        WARNING (``TimerPresetRules.usable``), so a favorite never makes the whole file unusable.

        Args:
            schemas: Validated DTOs, in file order.
            field_prefix: Dotted path of the collection in the file (``timer_presets``).
            limits: Bounds from ``concentrator.ini``.

        Returns:
            The kept favorites (always a success).
        """
        presets = [
            TimerPreset(
                id=TimerPresetId(schema.id),
                created_at=schema.created_at,
                updated_at=schema.updated_at,
                label=normalize_label(schema.label),
                duration=Duration(schema.duration_seconds),
                position=schema.position,
            )
            for schema in schemas
        ]
        usable = TimerPresetRules.usable(presets, limits)
        for issue in usable.validation.issues:
            _log_ignored(issue, presets, field_prefix)
        return DataResult.ok(usable.value_or(TimerPresetsCollection()))

    @staticmethod
    def to_schema(presets: TimerPresetsCollection) -> tuple[TimerPresetSchema, ...]:
        """Build the DTOs written to the file, in display order.

        Args:
            presets: Validated favorites.

        Returns:
            The DTOs sorted by position.
        """
        return tuple(
            TimerPresetSchema(
                id=preset.id,
                created_at=preset.created_at,
                updated_at=preset.updated_at,
                label=preset.label,
                duration_seconds=preset.duration.seconds,
                position=preset.position,
            )
            for preset in presets.ordered()
        )
