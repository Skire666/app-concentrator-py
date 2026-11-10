"""Shared configuration and field types of the persistence DTOs."""

from datetime import UTC, date, datetime, time
from typing import Annotated, Final

from pydantic import ConfigDict, PlainSerializer

PERSISTENCE_MODEL_CONFIG: Final = ConfigDict(strict=True, extra="forbid", frozen=True)
TIMESTAMP_FORMAT: Final = "%Y-%m-%dT%H:%M:%SZ"
MINUTES_FORMAT: Final = "%H:%M"


def format_timestamp(value: datetime) -> str:
    """Write an instant as ``YYYY-MM-DDTHH:MM:SSZ`` (whole seconds, UTC).

    Args:
        value: Timezone-aware instant.

    Returns:
        The text stored in the file.
    """
    return value.astimezone(UTC).strftime(TIMESTAMP_FORMAT)


type UtcTimestamp = Annotated[datetime, PlainSerializer(format_timestamp, return_type=str, when_used="json")]


def format_date(value: date) -> str:
    """Write a local date as ``YYYY-MM-DD``.

    Args:
        value: Date.

    Returns:
        The text stored in the file.
    """
    return value.isoformat()


def format_minutes(value: time) -> str:
    """Write a local time of day as ``HH:MM``.

    Args:
        value: Time.

    Returns:
        The text stored in the file.
    """
    return value.strftime(MINUTES_FORMAT)


type LocalDate = Annotated[date, PlainSerializer(format_date, return_type=str, when_used="json")]
type LocalMinutes = Annotated[time, PlainSerializer(format_minutes, return_type=str, when_used="json")]
