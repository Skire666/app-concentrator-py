"""Root logger configuration: rotating file, journal ring buffer, optional stream, warnings, faulthandler."""

import faulthandler
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Final, TextIO

from concentrator.application.common.app_config import LoggingSection
from concentrator.infrastructure.logging.ring_buffer_handler import RingBufferHandler

_logger = logging.getLogger(__name__)

LOG_FORMAT: Final = "%(asctime)s | %(levelname)-8s | %(threadName)s | %(name)s | %(message)s"
FAULTHANDLER_FILE_NAME: Final = "faulthandler.log"


class LoggingRuntime:
    """Handlers installed on the root logger; ``shutdown`` removes them and flushes the files."""

    def __init__(
        self, ring_buffer: RingBufferHandler, handlers: tuple[logging.Handler, ...], fault_file: TextIO | None
    ) -> None:
        """Keep references to what was installed.

        Args:
            ring_buffer: Journal buffer (also in ``handlers``).
            handlers: Every handler added to the root logger.
            fault_file: File receiving ``faulthandler`` dumps, if it could be opened.
        """
        self.ring_buffer = ring_buffer
        self._handlers = handlers
        self._fault_file = fault_file

    def shutdown(self) -> None:
        """Flush and remove the handlers, stop capturing warnings, close the faulthandler file."""
        root = logging.getLogger()
        for handler in self._handlers:
            handler.flush()
            root.removeHandler(handler)
            handler.close()
        logging.captureWarnings(False)
        if self._fault_file is not None:
            faulthandler.disable()
            self._fault_file.close()
            self._fault_file = None


def _file_handler(config: LoggingSection, log_dir: Path, formatter: logging.Formatter) -> logging.Handler | None:
    """Create the rotating file handler.

    Args:
        config: ``[logging]`` section.
        log_dir: Folder of the log file (created if needed).
        formatter: Line format.

    Returns:
        The handler, or ``None`` when the folder or the file cannot be created.
    """
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            log_dir / config.file_name,
            maxBytes=config.file_max_bytes,
            backupCount=config.file_backup_count,
            encoding="utf-8",
        )
    except OSError as error:
        _logger.warning("Log file disabled, cannot open it in %s: %s", log_dir, error)
        return None
    handler.setFormatter(formatter)
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


def configure_logging(
    config: LoggingSection, log_dir: Path, *, stream: TextIO | None = sys.stderr, enable_faulthandler: bool = True
) -> LoggingRuntime:
    """Install the handlers on the root logger.

    A log folder that cannot be created only disables the file handler (the journal still works).

    Args:
        config: ``[logging]`` section.
        log_dir: Resolved ``paths.log_dir``.
        stream: Console stream; ``None`` in windowed and frozen runs (``sys.stderr`` is ``None``).
        enable_faulthandler: Whether to dump fatal errors into ``faulthandler.log``.

    Returns:
        The installed runtime, to be shut down on quit.
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
    for handler in handlers:
        root.addHandler(handler)
    file_handler = _file_handler(config, log_dir, formatter)
    if file_handler is not None:
        root.addHandler(file_handler)
        handlers.append(file_handler)
    logging.captureWarnings(True)
    fault_file = _open_fault_file(log_dir) if enable_faulthandler and file_handler is not None else None
    return LoggingRuntime(ring_buffer, tuple(handlers), fault_file)
