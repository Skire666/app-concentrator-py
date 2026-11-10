"""``LinkOpenerPort`` on ``QDesktopServices.openUrl``."""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import override

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

from concentrator.application.ports.link_opener_port import LinkOpenerPort
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult

_logger = logging.getLogger(__name__)


class QtLinkOpener(LinkOpenerPort):
    """Opens locations as they are: nothing is checked before handing them to Windows (AGENTS.md 5.1)."""

    def __init__(self, open_url: Callable[[QUrl], bool] = QDesktopServices.openUrl) -> None:
        """Create the opener.

        Args:
            open_url: Hands a URL to the shell (``QDesktopServices.openUrl``; replaced in tests).
        """
        self._open_url = open_url

    @override
    def open_folder(self, path: Path, *, create_missing: bool = False) -> ValidationResult:
        if create_missing and not path.is_dir():
            try:
                path.mkdir(parents=True, exist_ok=True)
            except OSError as error:
                _logger.warning("Cannot create the folder %s before opening it: %s", path, error)
                return ValidationResult.warning(ErrorCodeEnum.LINK_OPEN_FAILED, path=path.as_posix())
        if not self._open_url(QUrl.fromLocalFile(str(path))):
            _logger.warning("Windows refused to open the folder %s", path)
            return ValidationResult.warning(ErrorCodeEnum.LINK_OPEN_FAILED, path=path.as_posix())
        _logger.info("Folder opened: %s", path)
        return ValidationResult.success()
