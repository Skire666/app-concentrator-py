"""In-memory ``UserData`` of the open file (main thread only)."""

import logging
from typing import Final, override

from concentrator.application.common.event_bus import EventBus
from concentrator.application.ports.user_data_session_port import UserDataSessionPort
from concentrator.application.storage.storage_events import UserDataChangedEvent
from concentrator.application.storage.user_data import UserData

_logger = logging.getLogger(__name__)

_NO_DATA: Final = "no data file is open yet"


class UserDataStore(UserDataSessionPort):
    """Holds the current snapshot; ``apply`` publishes ``UserDataChangedEvent`` for real changes."""

    def __init__(self, event_bus: EventBus) -> None:
        """Create an empty store (no file open yet).

        Args:
            event_bus: Receives the change events.
        """
        self._event_bus = event_bus
        self._data: UserData | None = None
        self._revision = 0

    @property
    def is_open(self) -> bool:
        """Whether a data file was loaded."""
        return self._data is not None

    @override
    def current(self) -> UserData:
        if self._data is None:
            raise RuntimeError(_NO_DATA)
        return self._data

    @override
    def revision(self) -> int:
        return self._revision

    @override
    def reset(self, data: UserData) -> None:
        self._data = data
        self._revision += 1
        _logger.debug("User data reset (revision %d)", self._revision)

    @override
    def apply(self, data: UserData) -> int:
        """Replace the snapshot after a change; an equal snapshot changes nothing.

        Args:
            data: New snapshot.

        Returns:
            The revision after the call.

        Raises:
            RuntimeError: If no data file is open (programming error).
        """
        if self._data is None:
            raise RuntimeError(_NO_DATA)
        if data == self._data:
            return self._revision
        self._data = data
        self._revision += 1
        self._event_bus.publish(UserDataChangedEvent(revision=self._revision))
        return self._revision
