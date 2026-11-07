"""Modal dialogs requested by presenters, implemented by ``ui.support.QtDialogService``."""

from typing import Protocol


class DialogPort(Protocol):
    """Confirmations, messages and file pickers. Every text is already translated."""

    def confirm(self, title: str, message: str, accept_text: str, reject_text: str) -> bool:
        """Ask a yes/no question.

        Args:
            title: Window title.
            message: Question.
            accept_text: Label of the accepting button.
            reject_text: Label of the rejecting button.

        Returns:
            Whether the user accepted.
        """
        ...

    def inform(self, title: str, message: str, button_text: str) -> None:
        """Show an information message.

        Args:
            title: Window title.
            message: Message.
            button_text: Label of the closing button.
        """
        ...

    def warn(self, title: str, message: str, button_text: str) -> None:
        """Show a warning message.

        Args:
            title: Window title.
            message: Message.
            button_text: Label of the closing button.
        """
        ...

    def error(self, title: str, message: str, button_text: str) -> None:
        """Show an error message.

        Args:
            title: Window title.
            message: Message.
            button_text: Label of the closing button.
        """
        ...

    def choose_open_file(self, title: str, directory: str, name_filter: str) -> str | None:
        """Pick an existing file.

        Args:
            title: Window title.
            directory: Initial folder.
            name_filter: Qt filter such as ``Concentrator data (*.toml)``.

        Returns:
            The chosen path with ``/`` separators, or ``None`` when cancelled.
        """
        ...

    def choose_save_file(self, title: str, directory: str, name_filter: str) -> str | None:
        """Pick a file to create or overwrite.

        Args:
            title: Window title.
            directory: Initial folder or file path.
            name_filter: Qt filter.

        Returns:
            The chosen path with ``/`` separators, or ``None`` when cancelled.
        """
        ...

    def choose_folder(self, title: str, directory: str) -> str | None:
        """Pick a folder.

        Args:
            title: Window title.
            directory: Initial folder.

        Returns:
            The chosen folder with ``/`` separators, or ``None`` when cancelled.
        """
        ...
