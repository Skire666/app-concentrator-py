"""Opens folders (and, from phase 6, links) with the Windows shell."""

from pathlib import Path
from typing import Protocol

from concentrator.domain.common.validation_result import ValidationResult


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
