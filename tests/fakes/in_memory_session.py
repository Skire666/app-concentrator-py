"""Session fake: ``change`` replaces the data and publishes ``UserDataChangedEvent`` like the store."""

from typing import override

from concentrator.application.common.event_bus import EventBus
from concentrator.application.ports.user_data_session_port import UserDataSessionPort
from concentrator.application.storage.storage_events import UserDataChangedEvent
from concentrator.application.storage.user_data import UserData
from tests.fakes.user_data_factory import make_user_data


class InMemorySession(UserDataSessionPort):
    def __init__(self, event_bus: EventBus, data: UserData | None = None) -> None:
        self._event_bus = event_bus
        self.data = data or make_user_data()
        self._revision = 0
        self.resets = 0

    @override
    def current(self) -> UserData:
        return self.data

    @override
    def revision(self) -> int:
        return self._revision

    @override
    def reset(self, data: UserData) -> None:
        self.resets += 1
        self.data = data
        self._revision += 1

    def change(self, data: UserData | None = None) -> None:
        self.data = data or self.data
        self._revision += 1
        self._event_bus.publish(UserDataChangedEvent(revision=self._revision))
