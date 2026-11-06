"""Icons read from the bundled ``assets/icons`` folder."""

import logging
from pathlib import Path

from PySide6.QtGui import QIcon

_logger = logging.getLogger(__name__)


class IconLoader:
    """Loads icons by file name; a missing file gives an empty icon and a WARNING."""

    def __init__(self, icons_dir: Path) -> None:
        """Create a loader.

        Args:
            icons_dir: Folder of the icon files.
        """
        self._icons_dir = icons_dir

    def icon(self, file_name: str) -> QIcon:
        """Load one icon.

        Args:
            file_name: File inside the icons folder, for example ``module-focus.svg``.

        Returns:
            The icon (null when the file is missing).
        """
        path = self._icons_dir / file_name
        if not path.is_file():
            _logger.warning("Icon not found: %s", path)
            return QIcon()
        return QIcon(str(path))
