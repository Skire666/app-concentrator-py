"""Draft of the favorite dialog, validated on every change (``AGENTS.md`` section 8.4)."""

from dataclasses import dataclass

from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.timer.duration import Duration
from concentrator.domain.timer.timer_limits import TimerLimits
from concentrator.domain.timer.timer_preset import normalize_label
from concentrator.domain.timer.timer_preset_rules import TimerPresetRules
from concentrator.domain.timer.timer_presets_collection import TimerPresetsCollection
from concentrator.presentation.common.form_state import FormState


@dataclass(frozen=True, slots=True, kw_only=True)
class PresetDraft:
    """Values edited in the favorite dialog.

    Attributes:
        label: Label as typed (``""`` for the automatic label).
        duration: Countdown duration.
    """

    label: str
    duration: Duration


class PresetEditForm:
    """``FormState`` over ``PresetDraft``: label length, duration range and unique duration.

    A new favorite starts empty (no label, 00:00:00) and can be saved as soon as its draft is valid; its
    inline errors show only after the first change. An existing favorite can be saved once it changed.
    """

    def __init__(
        self, baseline: PresetDraft, *, limits: TimerLimits, presets: TimerPresetsCollection, preset_id: str
    ) -> None:
        """Start editing.

        Args:
            baseline: Values shown when the dialog opens.
            limits: Bounds from ``concentrator.ini``.
            presets: Current favorites (for the unique duration).
            preset_id: Favorite being edited, ``""`` for a new one.
        """
        self._limits = limits
        self._presets = presets
        self._preset_id = preset_id
        self._state = FormState(baseline, self._validate)

    @property
    def preset_id(self) -> str:
        """Favorite being edited, ``""`` for a new one."""
        return self._preset_id

    @property
    def is_new(self) -> bool:
        """Whether the dialog adds a favorite."""
        return not self._preset_id

    @property
    def draft(self) -> PresetDraft:
        """Values being edited."""
        return self._state.draft

    @property
    def errors(self) -> ValidationResult:
        """Validation of the draft."""
        return self._state.errors

    @property
    def shows_errors(self) -> bool:
        """Whether the inline errors are shown: always, except on a new favorite not changed yet."""
        return not self.is_new or self._state.is_dirty

    @property
    def can_submit(self) -> bool:
        """Whether Save is allowed: valid, and changed unless the favorite is new."""
        return (self.is_new or self._state.is_dirty) and not self._state.errors.is_failure

    def set_label(self, text: str) -> None:
        """Change the label.

        Args:
            text: Label as typed.
        """
        self._state.set_field("label", text)

    def set_duration(self, hours: int, minutes: int, seconds: int) -> None:
        """Change the duration.

        Args:
            hours: Hours.
            minutes: Minutes.
            seconds: Seconds.
        """
        self._state.set_field("duration", Duration.from_hms(hours, minutes, seconds))

    def _validate(self, draft: PresetDraft) -> ValidationResult:
        """Validate a draft as it would be stored.

        Args:
            draft: Draft.

        Returns:
            The issues on ``label`` and ``duration_seconds``.
        """
        return TimerPresetRules.validate_values(normalize_label(draft.label), draft.duration, self._limits).merge(
            TimerPresetRules.validate_unique_duration(self._presets, draft.duration, except_id=self._preset_id)
        )
