"""Outcome of one action of a startup dialog."""

from dataclasses import dataclass, field

from concentrator.application.storage.startup_plan import StartupPlan
from concentrator.domain.common.validation_result import ValidationResult


@dataclass(frozen=True, slots=True, kw_only=True)
class StartupChoice:
    """What the startup flow does after an action.

    Attributes:
        plan: The new situation, ``None`` when it did not change (cancelled picker, failure shown).
        quit: The user chose to quit.
        validation: Result of the action (for the action gate log).
    """

    plan: StartupPlan | None = None
    quit: bool = False
    validation: ValidationResult = field(default_factory=ValidationResult.success)
