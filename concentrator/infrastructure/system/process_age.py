"""Time elapsed since the operating system created this process (startup measurement, phase 8)."""

import ctypes
import logging
import sys
from ctypes import wintypes
from typing import Final

_logger = logging.getLogger(__name__)

FILETIME_TICKS_PER_MS: Final = 10_000
DWORD_BITS: Final = 32


def _ticks(value: wintypes.FILETIME) -> int:
    """Convert a ``FILETIME`` to 100 ns ticks.

    Args:
        value: Windows time.

    Returns:
        Its ticks since 1601-01-01 UTC.
    """
    return (value.dwHighDateTime << DWORD_BITS) | value.dwLowDateTime


def process_age_ms() -> int | None:
    """Measure the time since the process was created, interpreter start and imports included.

    Returns:
        Whole milliseconds, or ``None`` outside Windows or when the system call fails (logged at DEBUG).
    """
    if sys.platform != "win32":
        return None
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    except OSError as error:
        _logger.debug("kernel32 unavailable: %s", error)
        return None
    times = kernel32.GetProcessTimes
    times.argtypes = [wintypes.HANDLE, *([ctypes.POINTER(wintypes.FILETIME)] * 4)]
    times.restype = wintypes.BOOL
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    created, ended, kernel, user, now = (wintypes.FILETIME() for _ in range(5))
    process = kernel32.GetCurrentProcess()
    if not times(process, ctypes.byref(created), ctypes.byref(ended), ctypes.byref(kernel), ctypes.byref(user)):
        _logger.debug("GetProcessTimes failed: error %d", ctypes.get_last_error())
        return None
    kernel32.GetSystemTimePreciseAsFileTime(ctypes.byref(now))
    return max(0, (_ticks(now) - _ticks(created)) // FILETIME_TICKS_PER_MS)


def log_startup_time() -> None:
    """Log the startup time; called on the first event-loop turn after the main window is shown.

    The phase 8 target is 2 s with 1,000 tasks (``scripts/bench_app.py --startup`` reads this line).
    """
    elapsed = process_age_ms()
    if elapsed is not None:
        _logger.info("Startup took %d ms (process start to main window shown)", elapsed)
