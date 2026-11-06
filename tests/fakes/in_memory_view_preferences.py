"""Dictionary-backed view preferences."""

from typing import override

from concentrator.application.ports.view_preferences_port import ViewPreferencesPort


class InMemoryViewPreferences(ViewPreferencesPort):
    """Stores preferences in ``values``."""

    def __init__(self, values: dict[str, str] | None = None) -> None:
        self.values: dict[str, str] = dict(values or {})

    @override
    def get_text(self, key: str) -> str | None:
        return self.values.get(key)

    @override
    def set_text(self, key: str, value: str) -> None:
        self.values[key] = value

    @override
    def remove(self, key: str) -> None:
        self.values.pop(key, None)
