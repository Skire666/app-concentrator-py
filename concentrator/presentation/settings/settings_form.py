"""Draft of the settings page: General values, chime switch and chime fields (``AGENTS.md`` section 8.4)."""

from collections.abc import Callable
from dataclasses import dataclass

from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.settings.general_settings import GeneralSettings
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.domain.settings.log_level_enum import LogLevelEnum
from concentrator.domain.settings.user_settings_rules import UserSettingsRules
from concentrator.domain.timer.chime_settings import ChimeSettings
from concentrator.domain.timer.sound_ref import SoundRef
from concentrator.presentation.common.form_state import FormState
from concentrator.presentation.timer.chime_settings_form import ChimeSettingsForm


@dataclass(frozen=True, slots=True, kw_only=True)
class GeneralDraft:
    """The single values of the page: General section and the chime switch.

    Attributes:
        language: UI language.
        log_level: Journal detail level.
        notify_when_inactive: Taskbar alert switch.
        chime_enabled: "Chime every hour".
    """

    language: LanguageEnum
    log_level: LogLevelEnum
    notify_when_inactive: bool
    chime_enabled: bool

    @property
    def general(self) -> GeneralSettings:
        """The values stored in the user settings."""
        return GeneralSettings(
            language=self.language, log_level=self.log_level, notify_when_inactive=self.notify_when_inactive
        )


def _general_draft(general: GeneralSettings, chime_enabled: bool) -> GeneralDraft:
    """Build the draft of stored values.

    Args:
        general: Stored General values.
        chime_enabled: Stored chime switch.

    Returns:
        The draft.
    """
    return GeneralDraft(
        language=general.language,
        log_level=general.log_level,
        notify_when_inactive=general.notify_when_inactive,
        chime_enabled=chime_enabled,
    )


def _validate_general(draft: GeneralDraft) -> ValidationResult:
    """Validate the General values.

    Args:
        draft: Draft.

    Returns:
        The rule issues (fields ``language`` and ``log_level``).
    """
    return UserSettingsRules.validate_general(draft.general)


class SettingsForm:
    """Two forms edited together: Save and Revert apply to both."""

    def __init__(
        self,
        general: GeneralSettings,
        chime: tuple[bool, ChimeSettings],
        check_sound: Callable[[SoundRef], ValidationResult],
    ) -> None:
        """Start editing the stored values.

        Args:
            general: Stored General values.
            chime: Stored chime switch and settings.
            check_sound: Tells whether a sound exists and can be played.
        """
        enabled, settings = chime
        self._general = FormState(_general_draft(general, enabled), _validate_general)
        self._chime = ChimeSettingsForm(settings, check_sound)

    @property
    def general(self) -> GeneralDraft:
        """Single values being edited."""
        return self._general.draft

    @property
    def chime(self) -> ChimeSettingsForm:
        """Chime fields being edited."""
        return self._chime

    @property
    def errors(self) -> ValidationResult:
        """Validation of both drafts."""
        return self._general.errors.merge(self._chime.errors)

    @property
    def is_dirty(self) -> bool:
        """Whether anything differs from the stored values."""
        return self._general.is_dirty or self._chime.is_dirty

    @property
    def can_submit(self) -> bool:
        """Whether something changed and nothing fails."""
        return self.is_dirty and not self.errors.is_failure

    def set_language(self, language: LanguageEnum) -> None:
        """Change the language.

        Args:
            language: Chosen language.
        """
        self._general.set_field("language", language)

    def set_log_level(self, log_level: LogLevelEnum) -> None:
        """Change the journal detail level.

        Args:
            log_level: Chosen level.
        """
        self._general.set_field("log_level", log_level)

    def set_notify_when_inactive(self, notify: bool) -> None:
        """Change the taskbar alert switch.

        Args:
            notify: New state.
        """
        self._general.set_field("notify_when_inactive", notify)

    def set_chime_enabled(self, enabled: bool) -> None:
        """Change the chime switch.

        Args:
            enabled: New state.
        """
        self._general.set_field("chime_enabled", enabled)

    def reset(self) -> None:
        """Discard every change (Revert)."""
        self._general.reset()
        self._chime.reset()

    def rebase(self, general: GeneralSettings, chime: tuple[bool, ChimeSettings]) -> None:
        """Follow stored values changed elsewhere (status bar, chime dialog, another data file).

        A field the user changed keeps its value; the others take the stored one.

        Args:
            general: Stored General values.
            chime: Stored chime switch and settings.
        """
        enabled, settings = chime
        self._general.rebase(_general_draft(general, enabled))
        self._chime.rebase(settings)
