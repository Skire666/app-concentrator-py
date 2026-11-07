"""Shared configuration and field types of the persistence DTOs."""

from datetime import UTC, datetime
from typing import Annotated, Final

from pydantic import ConfigDict, PlainSerializer

PERSISTENCE_MODEL_CONFIG: Final = ConfigDict(strict=True, extra="forbid", frozen=True)
TIMESTAMP_FORMAT: Final = "%Y-%m-%dT%H:%M:%SZ"


def format_timestamp(value: datetime) -> str:
    """Write an instant as ``YYYY-MM-DDTHH:MM:SSZ`` (whole seconds, UTC).

    Args:
        value: Timezone-aware instant.

    Returns:
        The text stored in the file.
    """
    return value.astimezone(UTC).strftime(TIMESTAMP_FORMAT)


type UtcTimestamp = Annotated[datetime, PlainSerializer(format_timestamp, return_type=str, when_used="json")]
