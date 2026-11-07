"""The in-memory user data of the open file."""

from typing import Protocol

from concentrator.application.storage.user_data import UserData


class UserDataSessionPort(Protocol):
    """Holds the current ``UserData`` snapshot; each change increments the revision."""

    def current(self) -> UserData:
        """Return the current snapshot.

        Returns:
            The data of the open file.
        """
        ...

    def revision(self) -> int:
        """Return the revision of the current snapshot.

        Returns:
            A number that grows at every change and reset.
        """
        ...

    def reset(self, data: UserData) -> None:
        """Replace the whole snapshot after a file is opened or reloaded (publishes no change event).

        Args:
            data: Data just loaded or written.
        """
        ...

    def apply(self, data: UserData) -> int:
        """Replace the snapshot after a change and publish ``UserDataChangedEvent`` (the save follows).

        Args:
            data: Changed data; an equal snapshot changes nothing.

        Returns:
            The revision after the call.
        """
        ...
