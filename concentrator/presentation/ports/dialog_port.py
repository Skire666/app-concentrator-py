"""Modal dialogs requested by presenters, implemented by ``ui.support.QtDialogService``."""

from dataclasses import dataclass
from datetime import date
from typing import Protocol


@dataclass(frozen=True, slots=True, kw_only=True)
class DatePrompt:
    """A question asking for one date (Set due date...).

    Attributes:
        title: Window title.
        label: Caption of the date field.
        initial: Date shown when the dialog opens.
        date_format: Display format of the date field, from the catalog.
        accept_text: Label of the accepting button.
        reject_text: Label of the rejecting button.
    """

    title: str
    label: str
    initial: date
    date_format: str
    accept_text: str
    reject_text: str


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

    def choose(self, title: str, message: str, options: tuple[str, ...], cancel_index: int) -> int:
        """Ask a question with several answers, such as Save / Discard / Cancel.

        Args:
            title: Window title.
            message: Question.
            options: Button labels, in order; the first one is the default button.
            cancel_index: Index of the answer given by Escape and the close button.

        Returns:
            Index of the chosen answer.
        """
        ...

    def ask_date(self, prompt: DatePrompt) -> date | None:
        """Ask for a date.

        Args:
            prompt: Texts and initial date.

        Returns:
            The date chosen, ``None`` when the user cancelled (Cancel, Escape, close button).
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
        """Pick the path of a file to create.

        The picker never asks whether to replace an existing file: the caller decides (creating a data
        file refuses an existing path with ``STORAGE_FILE_ALREADY_EXISTS``).

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
