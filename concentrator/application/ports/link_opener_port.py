"""Opens folders and the links of the tasks with the Windows shell."""

from pathlib import Path
from typing import Protocol

from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.todo.link_target import LinkTarget


class LinkOpenerPort(Protocol):
    """Hands a location to Windows, which opens it in its default program (Explorer for a folder)."""

    def open_folder(self, path: Path, *, create_missing: bool = False) -> ValidationResult:
        """Open a folder in Explorer.

        Args:
            path: Folder to open.
            create_missing: Create the folder (and its parents) first when it does not exist.

        Returns:
            Success, or a ``LINK_OPEN_FAILED`` warning (already logged) when the folder cannot be
            created or Windows refused to open it.
        """
        ...

    def open(self, target: LinkTarget) -> ValidationResult:
        """Open a link of a task as it is, like a double click in Explorer (ADR-014).

        Nothing is checked first: no existence, reachability or file type test.

        Args:
            target: Normalized link.

        Returns:
            Success, or a ``LINK_OPEN_FAILED`` warning (logged without the link) when Windows refused it.
        """
        ...
