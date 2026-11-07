"""Events published by the settings use cases."""

from dataclasses import dataclass

from concentrator.domain.settings.user_settings import UserSettings


@dataclass(frozen=True, slots=True)
class UserSettingsChangedEvent:
    """The user settings changed in memory.

    Attributes:
        settings: The new settings.
    """

    settings: UserSettings
