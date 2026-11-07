"""``TimerConfigSchema`` <-> ``TimerConfig``."""

from concentrator.domain.common.data_result import DataResult
from concentrator.domain.timer.duration import Duration
from concentrator.domain.timer.sound_kind_enum import SoundKindEnum
from concentrator.domain.timer.sound_ref import SoundRef
from concentrator.domain.timer.timer_config import TimerConfig, TimerConfigId
from concentrator.domain.timer.timer_config_rules import TimerConfigRules
from concentrator.domain.timer.timer_limits import TimerLimits
from concentrator.domain.timer.timer_settings import TimerSettings
from concentrator.domain.timer.volume import Volume
from concentrator.infrastructure.persistence.schemas.timer_config_schema import SoundRefSchema, TimerConfigSchema


class TimerConfigMapper:
    """Converts the ``[timer]`` section."""

    @staticmethod
    def to_domain(schema: TimerConfigSchema, field_prefix: str, limits: TimerLimits) -> DataResult[TimerConfig]:
        """Build and validate the configuration; an unknown sound kind becomes ``UNKNOWN``.

        Args:
            schema: Validated DTO.
            field_prefix: Dotted path of the section in the file (``timer``).
            limits: Bounds from ``concentrator.ini``.

        Returns:
            The configuration, or the rule failures with fields such as ``timer.volume``.
        """
        settings = TimerSettings(
            duration=Duration(schema.duration_seconds),
            sound=SoundRef.of(SoundKindEnum.parse(schema.sound.kind), schema.sound.value),
            volume=Volume(schema.volume),
            loop_count=schema.loop_count,
            loop_forever=schema.loop_forever,
            auto_stop_seconds=schema.auto_stop_seconds,
            auto_restart=schema.auto_restart,
        )
        config = TimerConfig(
            id=TimerConfigId(schema.id), created_at=schema.created_at, updated_at=schema.updated_at, settings=settings
        )
        validation = TimerConfigRules.validate(config, limits).prefixed(field_prefix)
        if validation.is_failure:
            return DataResult.fail(validation)
        return DataResult.ok(config, validation)

    @staticmethod
    def to_schema(config: TimerConfig) -> TimerConfigSchema:
        """Build the DTO written to the file.

        Args:
            config: Validated configuration.

        Returns:
            The DTO; enums are written as integers.
        """
        settings = config.settings
        return TimerConfigSchema(
            id=config.id,
            created_at=config.created_at,
            updated_at=config.updated_at,
            duration_seconds=settings.duration.seconds,
            sound=SoundRefSchema(kind=settings.sound.kind.value, value=settings.sound.value),
            volume=settings.volume.percent,
            loop_count=settings.loop_count,
            loop_forever=settings.loop_forever,
            auto_stop_seconds=settings.auto_stop_seconds,
            auto_restart=settings.auto_restart,
        )
