"""``TimerPresetSchema`` elements <-> ``TimerPresetsCollection``."""

from collections.abc import Sequence

from concentrator.domain.common.data_result import DataResult
from concentrator.domain.timer.duration import Duration
from concentrator.domain.timer.timer_limits import TimerLimits
from concentrator.domain.timer.timer_preset import TimerPreset, TimerPresetId
from concentrator.domain.timer.timer_preset_rules import TimerPresetRules
from concentrator.domain.timer.timer_presets_collection import TimerPresetsCollection
from concentrator.infrastructure.persistence.schemas.timer_preset_schema import TimerPresetSchema


class TimerPresetsMapper:
    """Converts the ``[[timer_presets]]`` elements."""

    @staticmethod
    def to_domain(
        schemas: Sequence[TimerPresetSchema], field_prefix: str, limits: TimerLimits
    ) -> DataResult[TimerPresetsCollection]:
        """Build and validate the favorites.

        Args:
            schemas: Validated DTOs, in file order.
            field_prefix: Dotted path of the collection in the file (``timer_presets``).
            limits: Bounds from ``concentrator.ini``.

        Returns:
            The favorites in file order, or the failures with fields such as ``timer_presets.1.label``.
        """
        presets = (
            TimerPreset(
                id=TimerPresetId(schema.id),
                created_at=schema.created_at,
                updated_at=schema.updated_at,
                label=schema.label,
                duration=Duration(schema.duration_seconds),
                position=schema.position,
            )
            for schema in schemas
        )
        collection = TimerPresetsCollection.from_items(presets, field_prefix)
        if collection.data is None:
            return DataResult.fail(collection.validation)
        validation = TimerPresetRules.validate_collection(collection.data, limits).prefixed(field_prefix)
        if validation.is_failure:
            return DataResult.fail(validation)
        return DataResult.ok(collection.data, validation)

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
