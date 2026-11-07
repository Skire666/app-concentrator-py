"""Result of one asynchronous save, delivered on the main thread."""

from dataclasses import dataclass
from datetime import datetime

from concentrator.domain.common.validation_result import ValidationResult


@dataclass(frozen=True, slots=True, kw_only=True)
class SaveOutcome:
    """What happened to one save request.

    Attributes:
        revision: Revision of the data that was saved.
        saved_at: ``saved_at`` written in the file, ``None`` when nothing was written.
        validation: Success (possibly with ``STORAGE_BACKUP_FAILED`` warnings) or the failure.
    """

    revision: int
    saved_at: datetime | None
    validation: ValidationResult
