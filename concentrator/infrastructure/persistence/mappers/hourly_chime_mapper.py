"""``HourlyChimeSchema`` <-> ``HourlyChime``."""

from concentrator.domain.common.data_result import DataResult
from concentrator.domain.timer.chime_settings import ChimeSettings
from concentrator.domain.timer.hourly_chime import HourlyChime, HourlyChimeId
from concentrator.domain.timer.hourly_chime_rules import HourlyChimeRules
from concentrator.domain.timer.volume import Volume
from concentrator.infrastructure.persistence.mappers.sound_ref_mapper import sound_to_domain, sound_to_schema
from concentrator.infrastructure.persistence.schemas.hourly_chime_schema import HourlyChimeSchema


class HourlyChimeMapper:
    """Converts the ``[hourly_chime]`` section."""

    @staticmethod
    def to_domain(schema: HourlyChimeSchema, field_prefix: str) -> DataResult[HourlyChime]:
        """Build and validate the chime; an unknown sound kind becomes ``UNKNOWN``.

        Args:
            schema: Validated DTO.
            field_prefix: Dotted path of the section in the file (``hourly_chime``).

        Returns:
            The chime, or the rule failures with fields such as ``hourly_chime.end_hour``.
        """
        settings = ChimeSettings(
            sound=sound_to_domain(schema.sound),
            volume=Volume(schema.volume),
            start_hour=schema.start_hour,
            end_hour=schema.end_hour,
        )
        chime = HourlyChime(
            id=HourlyChimeId(schema.id),
            created_at=schema.created_at,
            updated_at=schema.updated_at,
            enabled=schema.enabled,
            settings=settings,
        )
        validation = HourlyChimeRules.validate(chime).prefixed(field_prefix)
        if validation.is_failure:
            return DataResult.fail(validation)
        return DataResult.ok(chime, validation)

    @staticmethod
    def to_schema(chime: HourlyChime) -> HourlyChimeSchema:
        """Build the DTO written to the file.

        Args:
            chime: Validated chime.

        Returns:
            The DTO; enums are written as integers.
        """
        settings = chime.settings
        return HourlyChimeSchema(
            id=chime.id,
            created_at=chime.created_at,
            updated_at=chime.updated_at,
            enabled=chime.enabled,
            sound=sound_to_schema(settings.sound),
            volume=settings.volume.percent,
            start_hour=settings.start_hour,
            end_hour=settings.end_hour,
        )
