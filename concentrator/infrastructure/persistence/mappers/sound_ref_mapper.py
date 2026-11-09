"""``SoundRefSchema`` <-> ``SoundRef`` (alarm and hourly chime)."""

from concentrator.domain.timer.sound_kind_enum import SoundKindEnum
from concentrator.domain.timer.sound_ref import SoundRef
from concentrator.infrastructure.persistence.schemas.timer_config_schema import SoundRefSchema


def sound_to_domain(schema: SoundRefSchema) -> SoundRef:
    """Build a sound; an unknown kind becomes ``UNKNOWN`` (the rules report it), a path is normalized.

    Args:
        schema: Validated DTO.

    Returns:
        The sound.
    """
    return SoundRef.of(SoundKindEnum.parse(schema.kind), schema.value)


def sound_to_schema(sound: SoundRef) -> SoundRefSchema:
    """Build the DTO written to the file.

    Args:
        sound: Validated sound.

    Returns:
        The DTO; the kind is written as an integer.
    """
    return SoundRefSchema(kind=sound.kind.value, value=sound.value)
