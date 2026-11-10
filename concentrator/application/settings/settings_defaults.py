"""General values of ``concentrator.ini`` turned into domain objects."""

from dataclasses import dataclass
from typing import Self

from concentrator.application.common.app_config import SettingsSection
from concentrator.domain.settings.general_settings import GeneralSettings
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.domain.settings.log_level_enum import LogLevelEnum


@dataclass(frozen=True, slots=True, kw_only=True)
class SettingsDefaults:
    """General values of a new data file, and of a file written before they existed (phase 4).

    Attributes:
        log_level: Journal detail level (``settings.default_log_level``).
        notify_when_inactive: Taskbar alert switch (``settings.default_notify_when_inactive``).
    """

    log_level: LogLevelEnum
    notify_when_inactive: bool

    @classmethod
    def from_section(cls, section: SettingsSection) -> Self:
        """Build the values from the ``[settings]`` section.

        Args:
            section: Loaded section.

        Returns:
            The defaults.
        """
        return cls(log_level=section.default_log_level, notify_when_inactive=section.default_notify_when_inactive)

    def general(self, language: LanguageEnum) -> GeneralSettings:
        """General values of a new data file.

        Args:
            language: Language chosen in the first-run dialog.

        Returns:
            The values.
        """
        return GeneralSettings(
            language=language, log_level=self.log_level, notify_when_inactive=self.notify_when_inactive
        )
