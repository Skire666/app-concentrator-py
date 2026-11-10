"""The editable values of the General section of the settings."""

from dataclasses import dataclass

from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.domain.settings.log_level_enum import LogLevelEnum


@dataclass(frozen=True, slots=True, kw_only=True)
class GeneralSettings:
    """Language, log detail level and taskbar alert; checked by ``UserSettingsRules``.

    Attributes:
        language: UI language.
        log_level: Lowest severity of the records written to the log and shown in the journal.
        notify_when_inactive: Whether a timer that rings while no Concentrator window is active
            makes the taskbar button flash (ADR-038, ADR-040).
    """

    language: LanguageEnum
    log_level: LogLevelEnum
    notify_when_inactive: bool
