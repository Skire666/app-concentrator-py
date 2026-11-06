"""Windows shell integration through ctypes (no-op on other platforms)."""

import ctypes
import logging
import sys
from typing import Final

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult

_logger = logging.getLogger(__name__)

S_OK: Final = 0
DWORD_MASK: Final = 0xFFFFFFFF
ASFW_ANY: Final = DWORD_MASK  # (DWORD)-1: any process may take the foreground


def set_app_user_model_id(app_id: str) -> ValidationResult:
    """Set the AppUserModelID of the process, so the taskbar and toasts show Concentrator, not Python.

    Must run before the ``QApplication`` exists.

    Args:
        app_id: Identifier such as ``skire666.Concentrator`` (at most 128 characters).

    Returns:
        Success, or ``APP_USER_MODEL_ID_FAILED`` when the shell call fails.
    """
    if sys.platform != "win32":
        return ValidationResult.success()
    try:
        function = ctypes.WinDLL("shell32").SetCurrentProcessExplicitAppUserModelID
    except (OSError, AttributeError) as error:
        _logger.warning("SetCurrentProcessExplicitAppUserModelID unavailable: %s", error)
        return ValidationResult.failure(ErrorCodeEnum.APP_USER_MODEL_ID_FAILED)
    function.argtypes = [ctypes.c_wchar_p]
    function.restype = ctypes.c_long
    hresult = int(function(app_id))
    if hresult != S_OK:
        code = f"0x{hresult & DWORD_MASK:08X}"
        _logger.warning("SetCurrentProcessExplicitAppUserModelID failed with HRESULT %s", code)
        return ValidationResult.failure(ErrorCodeEnum.APP_USER_MODEL_ID_FAILED, hresult=code)
    return ValidationResult.success()


def allow_set_foreground_window() -> bool:
    """Let another process (the first instance) bring its window to the front.

    Called by a second instance just before it asks the first one to show itself; best effort; Windows
    otherwise only flashes the taskbar button.

    Returns:
        Whether Windows granted the permission.
    """
    if sys.platform != "win32":
        return False
    try:
        function = ctypes.WinDLL("user32").AllowSetForegroundWindow
    except (OSError, AttributeError) as error:
        _logger.warning("AllowSetForegroundWindow unavailable: %s", error)
        return False
    function.argtypes = [ctypes.c_ulong]
    function.restype = ctypes.c_int
    granted = bool(function(ASFW_ANY))
    if not granted:
        _logger.info("AllowSetForegroundWindow was refused; the first instance will flash instead")
    return granted
