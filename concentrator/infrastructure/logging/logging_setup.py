"""Root logger configuration in two stages (ADR-026).

Stage 1 (``configure_logging``): journal ring buffer, optional stream, captured warnings and an in-memory
startup buffer. No folder is created and no file is opened. Stage 2 (``LoggingRuntime.attach_log_file``),
only in the process that keeps running: rotating log file, filled first with the buffered startup
records, then ``faulthandler``. A second launch that hands over to the running instance never opens
the log file, so it cannot make the rotation of the running instance fail (Windows refuses to rename
a file another process holds open).
"""

import faulthandler
import logging
import sys
from dataclasses import dataclass
from logging.handlers import MemoryHandler, RotatingFileHandler
from pathlib import Path
from typing import Final, TextIO

from concentrator.application.common.app_config import LoggingSection
from concentrator.infrastructure.logging.ring_buffer_handler import RingBufferHandler

_logger = logging.getLogger(__name__)

LOG_FORMAT: Final = "%(asctime)s | %(levelname)-8s | %(threadName)s | %(name)s | %(message)s"
FAULTHANDLER_FILE_NAME: Final = "faulthandler.log"


@dataclass(frozen=True, slots=True)
class _LogFileSettings:
    """What stage 2 needs to open the files."""

    config: LoggingSection
    log_dir: Path
    formatter: logging.Formatter
    enable_faulthandler: bool


def _file_handler(settings: _LogFileSettings) -> logging.Handler | None:
    """Create the log folder and the rotating file handler.

    Args:
        settings: File settings.

    Returns:
        The handler, or ``None`` when the folder or the file cannot be created.
    """
    config = settings.config
    try:
        settings.log_dir.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            settings.log_dir / config.file_name,
            maxBytes=config.file_max_bytes,
            backupCount=config.file_backup_count,
            encoding="utf-8",
        )
    except OSError as error:
        _logger.warning("Log file disabled, cannot open it in %s: %s", settings.log_dir, error)
        return None
    handler.setFormatter(settings.formatter)
    return handler


def _open_fault_file(log_dir: Path) -> TextIO | None:
    """Enable ``faulthandler`` into a file of the log folder.

    Args:
        log_dir: Log folder.

    Returns:
        The open file, or ``None`` when it cannot be opened.
    """
    try:
        fault_file = (log_dir / FAULTHANDLER_FILE_NAME).open("a", encoding="utf-8")
    except OSError as error:
        _logger.warning("faulthandler disabled, cannot open its file in %s: %s", log_dir, error)
        return None
    faulthandler.enable(file=fault_file)
    return fault_file


class LoggingRuntime:
    """Handlers installed on the root logger; ``shutdown`` removes them and flushes the files."""

    def __init__(
        self,
        ring_buffer: RingBufferHandler,
        handlers: list[logging.Handler],
        startup_buffer: MemoryHandler,
        file_settings: _LogFileSettings,
    ) -> None:
        """Keep references to what stage 1 installed.

        Args:
            ring_buffer: Journal buffer (also in ``handlers``).
            handlers: Every handler added to the root logger, except the startup buffer.
            startup_buffer: Records waiting for the log file.
            file_settings: What stage 2 needs.
        """
        self.ring_buffer = ring_buffer
        self._handlers = handlers
        self._startup_buffer: MemoryHandler | None = startup_buffer
        self._file_settings = file_settings
        self._fault_file: TextIO | None = None

    @property
    def has_log_file(self) -> bool:
        """Whether stage 2 opened the rotating log file."""
        return any(isinstance(handler, RotatingFileHandler) for handler in self._handlers)

    def attach_log_file(self) -> bool:
        """Stage 2: open the log file, write the buffered startup records into it, enable ``faulthandler``.

        Called once this process holds the single-instance lock (or runs unguarded, or self-checks).
        A folder that cannot be used only disables the file: the journal keeps working.

        Returns:
            Whether the log file is open (idempotent: later calls change nothing).
        """
        startup_buffer = self._startup_buffer
        if startup_buffer is None:
            return self.has_log_file
        self._startup_buffer = None
        logging.getLogger().removeHandler(startup_buffer)
        file_handler = _file_handler(self._file_settings)
        if file_handler is not None:
            startup_buffer.setTarget(file_handler)
            startup_buffer.flush()
            logging.getLogger().addHandler(file_handler)
            self._handlers.append(file_handler)
            if self._file_settings.enable_faulthandler:
                self._fault_file = _open_fault_file(self._file_settings.log_dir)
        startup_buffer.close()
        return file_handler is not None

    def shutdown(self) -> None:
        """Remove every handler (buffered records without log file are dropped), stop capturing warnings."""
        root = logging.getLogger()
        if self._startup_buffer is not None:
            root.removeHandler(self._startup_buffer)
            self._startup_buffer.close()
            self._startup_buffer = None
        for handler in self._handlers:
            handler.flush()
            root.removeHandler(handler)
            handler.close()
        logging.captureWarnings(False)
        if self._fault_file is not None:
            faulthandler.disable()
            self._fault_file.close()
            self._fault_file = None


def configure_logging(
    config: LoggingSection, log_dir: Path, *, stream: TextIO | None = sys.stderr, enable_faulthandler: bool = True
) -> LoggingRuntime:
    """Stage 1: install the in-memory handlers on the root logger. Creates no folder, opens no file.

    Args:
        config: ``[logging]`` section.
        log_dir: Resolved ``paths.log_dir``, used by ``attach_log_file``.
        stream: Console stream; ``None`` in windowed and frozen runs (``sys.stderr`` is ``None``).
        enable_faulthandler: Whether stage 2 dumps fatal errors into ``faulthandler.log``.

    Returns:
        The installed runtime: call ``attach_log_file`` once this process keeps running, ``shutdown`` on quit.
    """
    formatter = logging.Formatter(LOG_FORMAT)
    root = logging.getLogger()
    root.setLevel(config.level)
    ring_buffer = RingBufferHandler(config.journal_buffer_size)
    handlers: list[logging.Handler] = [ring_buffer]
    if stream is not None:
        stream_handler = logging.StreamHandler(stream)
        stream_handler.setFormatter(formatter)
        handlers.append(stream_handler)
    startup_buffer = MemoryHandler(config.journal_buffer_size, target=None, flushOnClose=False)
    for handler in (*handlers, startup_buffer):
        root.addHandler(handler)
    logging.captureWarnings(True)
    settings = _LogFileSettings(config, log_dir, formatter, enable_faulthandler)
    return LoggingRuntime(ring_buffer, handlers, startup_buffer, settings)
