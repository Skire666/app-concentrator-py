"""One instance per Windows user: ``QLockFile`` decides, ``QLocalServer`` carries "show yourself" (ADR-007)."""

import getpass
import hashlib
import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import Final

from PySide6.QtCore import QLockFile, QObject
from PySide6.QtNetwork import QLocalServer, QLocalSocket

from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult

_logger = logging.getLogger(__name__)

ACTIVATE_MESSAGE: Final = b"activate\n"
LOCK_FILE_SUFFIX: Final = ".lock"
USER_HASH_LENGTH: Final = 16
CONNECT_RETRY_DELAY_S: Final = 0.05


def server_name_for(key: str, user: str) -> str:
    """Name of the local server: global on Windows (named pipe), hence the per-user suffix.

    Args:
        key: ``app.single_instance_key``.
        user: Windows user name.

    Returns:
        ``<key>-<first 16 hex digits of sha256(user)>``.
    """
    digest = hashlib.sha256(user.encode("utf-8")).hexdigest()
    return f"{key}-{digest[:USER_HASH_LENGTH]}"


class QtSingleInstanceGuard:
    """Holds the per-user lock while the application runs and listens for activation requests."""

    def __init__(self, *, lock_dir: Path, key: str, timeout_ms: int, parent: QObject, user: str | None = None) -> None:
        """Create an idle guard.

        Args:
            lock_dir: Folder of the lock file (``{localappdata}/<app name>``), created if needed.
            key: ``app.single_instance_key``.
            timeout_ms: ``app.single_instance_timeout_ms``: how long a second instance tries to reach the first.
            parent: Main-thread owner of the local server.
            user: Windows user name; defaults to the current user.
        """
        self._lock_path = lock_dir / f"{key}{LOCK_FILE_SUFFIX}"
        self._server_name = server_name_for(key, user or getpass.getuser())
        self._timeout_ms = timeout_ms
        self._lock = QLockFile(str(self._lock_path))
        self._lock.setStaleLockTime(0)  # stale only when the owning process is dead, never by age
        self._server = QLocalServer(parent)
        self._server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        self._server.newConnection.connect(self._on_new_connection)
        self._on_activation: Callable[[], None] = lambda: None

    @property
    def server_name(self) -> str:
        """Name of the local server (per key and per user)."""
        return self._server_name

    def set_activation_handler(self, handler: Callable[[], None]) -> None:
        """Choose what happens when a second instance asks this one to show itself.

        Args:
            handler: Called on the main thread.
        """
        self._on_activation = handler

    def acquire(self, before_notify: Callable[[], object] | None = None) -> DataResult[bool]:
        """Take the lock, or notify the instance that holds it.

        Args:
            before_notify: Called just before notifying the first instance (lets Windows hand it the
                foreground).

        Returns:
            ``True``: this process is the only instance (warning ``INSTANCE_SERVER_FAILED`` if it cannot
            listen). ``False``: another instance runs and was asked to show itself (warning
            ``INSTANCE_SERVER_FAILED`` if it did not answer). Failure ``INSTANCE_LOCK_FAILED`` when the lock
            cannot be created at all.
        """
        try:
            self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            _logger.warning("Cannot create the lock folder %s: %s", self._lock_path.parent, error)
            return DataResult.fail(ValidationResult.failure(ErrorCodeEnum.INSTANCE_LOCK_FAILED))
        if self._lock.tryLock(0):
            return DataResult.ok(True, self._listen())
        if self._lock.error() != QLockFile.LockError.LockFailedError:
            _logger.warning("Cannot acquire the instance lock %s: %s", self._lock_path, self._lock.error().name)
            return DataResult.fail(ValidationResult.failure(ErrorCodeEnum.INSTANCE_LOCK_FAILED))
        if before_notify is not None:
            before_notify()
        return DataResult.ok(False, self._notify_first_instance())

    def release(self) -> None:
        """Stop listening and release the lock (on quit)."""
        self._server.close()
        if self._lock.isLocked():
            self._lock.unlock()

    def _listen(self) -> ValidationResult:
        """Start the local server.

        Returns:
            Success, or a warning when the server cannot listen (the lock still protects).
        """
        QLocalServer.removeServer(self._server_name)
        if self._server.listen(self._server_name):
            return ValidationResult.success()
        _logger.warning("Cannot listen on %s: %s", self._server_name, self._server.errorString())
        return ValidationResult.warning(ErrorCodeEnum.INSTANCE_SERVER_FAILED)

    def _notify_first_instance(self) -> ValidationResult:
        """Send the activation message, retrying while the first instance is still starting.

        Returns:
            Success, or a warning when no answer came before the timeout.
        """
        deadline = time.monotonic() + self._timeout_ms / 1000
        while (remaining_ms := int((deadline - time.monotonic()) * 1000)) > 0:
            socket = QLocalSocket()
            socket.connectToServer(self._server_name)
            if socket.waitForConnected(remaining_ms) and self._send_activation(socket, remaining_ms):
                return ValidationResult.success()
            time.sleep(CONNECT_RETRY_DELAY_S)
        _logger.warning("The running instance did not answer on %s", self._server_name)
        return ValidationResult.warning(ErrorCodeEnum.INSTANCE_SERVER_FAILED)

    @staticmethod
    def _send_activation(socket: QLocalSocket, timeout_ms: int) -> bool:
        """Write the activation message and close the connection, flushing it.

        Args:
            socket: Connected socket.
            timeout_ms: Time left.

        Returns:
            Whether the message left this process.
        """
        socket.write(ACTIVATE_MESSAGE)
        written = socket.waitForBytesWritten(timeout_ms) or socket.bytesToWrite() == 0
        socket.disconnectFromServer()
        if socket.state() != QLocalSocket.LocalSocketState.UnconnectedState:
            written = socket.waitForDisconnected(timeout_ms) or written
        return written

    def _on_new_connection(self) -> None:
        """Read the activation request of every pending connection."""
        while self._server.hasPendingConnections():
            socket = self._server.nextPendingConnection()
            socket.readyRead.connect(lambda current=socket: self._read_request(current))
            socket.disconnected.connect(socket.deleteLater)
            if socket.bytesAvailable() > 0:
                self._read_request(socket)

    def _read_request(self, socket: QLocalSocket) -> None:
        """Activate on an ``activate`` message.

        Args:
            socket: Connection from a second instance.
        """
        if bytes(socket.readAll().data()).startswith(ACTIVATE_MESSAGE.strip()):
            _logger.info("Another launch asked this instance to show itself")
            self._on_activation()
