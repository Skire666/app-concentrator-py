"""Builds the form part of the ``SETTINGS`` snapshot: General and Hourly chime sections, Save and Revert."""

from types import MappingProxyType
from typing import Final

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.domain.settings.log_level_enum import LogLevelEnum
from concentrator.domain.settings.user_settings_rules import LANGUAGE_FIELD, LOG_LEVEL_FIELD
from concentrator.presentation.common.action_button import action_button
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.ui_texts import UiTexts
from concentrator.presentation.journal.journal_entries import LEVEL_KEYS
from concentrator.presentation.settings.settings_form import SettingsForm
from concentrator.presentation.settings.settings_snapshot import (
    ChimeSectionSnapshot,
    ChoiceFieldSnapshot,
    GeneralSectionSnapshot,
    SettingsFormSnapshot,
    ToggleFieldSnapshot,
)
from concentrator.presentation.timer.chime_fields import ChimeFields

LANGUAGES: Final = (LanguageEnum.ENGLISH, LanguageEnum.FRENCH)
LOG_LEVELS: Final = tuple(level for level in LogLevelEnum if level.is_set)
_LANGUAGE_KEYS: Final = MappingProxyType(
    {LanguageEnum.ENGLISH: "settings.language.en", LanguageEnum.FRENCH: "settings.language.fr"}
)
_NOT_LISTED: Final = -1


class SettingsFormBuilder:
    """Translates a ``SettingsForm`` into its sections."""

    def __init__(self, translator: TranslatorPort, gate: ActionGate, fields: ChimeFields) -> None:
        """Create the builder.

        Args:
            translator: Current-language translator.
            gate: Busy state of Save and Revert.
            fields: Describes the chime fields.
        """
        self._translator = translator
        self._texts = UiTexts(translator)
        self._gate = gate
        self._fields = fields

    def build(self, form: SettingsForm) -> SettingsFormSnapshot:
        """Describe the form.

        Args:
            form: Form being edited.

        Returns:
            The form snapshot.
        """
        tr = self._translator.tr
        return SettingsFormSnapshot(
            general=self._general(form),
            chime=ChimeSectionSnapshot(
                title=tr("settings.section.chime"),
                enabled=ToggleFieldSnapshot(text=tr("settings.chime.enabled"), checked=form.general.chime_enabled),
                fields=self._fields.snapshot(form.chime),
                hint=tr("chime.edit.hint"),
            ),
            status=tr("settings.unsaved") if form.is_dirty else "",
            save=action_button(self._texts, self._gate, ActionIdEnum.SETTINGS_SAVE, enabled=form.can_submit),
            revert=action_button(self._texts, self._gate, ActionIdEnum.SETTINGS_REVERT, enabled=form.is_dirty),
        )

    def _general(self, form: SettingsForm) -> GeneralSectionSnapshot:
        """Describe the General section.

        Args:
            form: Form being edited.

        Returns:
            The section snapshot.
        """
        tr = self._translator.tr
        draft = form.general
        errors = form.errors
        return GeneralSectionSnapshot(
            title=tr("settings.section.general"),
            language=ChoiceFieldSnapshot(
                label=tr("settings.language"),
                tooltip="",
                options=tuple(tr(_LANGUAGE_KEYS[language]) for language in LANGUAGES),
                selected=LANGUAGES.index(draft.language) if draft.language in LANGUAGES else _NOT_LISTED,
                error=self._texts.field_message(errors, LANGUAGE_FIELD),
            ),
            log_level=ChoiceFieldSnapshot(
                label=tr("settings.log_level"),
                tooltip=tr("settings.log_level.tooltip"),
                options=tuple(tr(LEVEL_KEYS[level]) for level in LOG_LEVELS),
                selected=LOG_LEVELS.index(draft.log_level) if draft.log_level in LOG_LEVELS else _NOT_LISTED,
                error=self._texts.field_message(errors, LOG_LEVEL_FIELD),
            ),
            notify_when_inactive=ToggleFieldSnapshot(
                text=tr("settings.notify_when_inactive"), checked=draft.notify_when_inactive
            ),
        )
