"""Events published by the storage side of the application."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from concentrator.application.storage.save_state_enum import SaveStateEnum
from concentrator.domain.common.validation_result import ValidationResult


@dataclass(frozen=True, slots=True)
class UserDataChangedEvent:
    """The in-memory user data changed (the save coordinator schedules a save).

    Attributes:
        revision: Revision after the change.
    """

    revision: int


@dataclass(frozen=True, slots=True, kw_only=True)
class SaveStatusChangedEvent:
    """The save state changed (status bar, external modification dialog).

    Attributes:
        state: Current state.
        path: Open data file, ``None`` before one is open.
        saved_at: Last successful save (``saved_at`` of the file), ``None`` before the first one.
        validation: Issues of the last save: warnings when saved, the failure when failed.
        interactive_shutdown: Published by the flush of a window close whose caller asks the user
            itself (the external modification dialog then stays out of the way).
    """

    state: SaveStateEnum
    path: Path | None = None
    saved_at: datetime | None = None
    validation: ValidationResult = field(default_factory=ValidationResult.success)
    interactive_shutdown: bool = False
