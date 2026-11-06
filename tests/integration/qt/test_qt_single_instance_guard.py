import subprocess
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import QLockFile, QObject
from pytestqt.qtbot import QtBot

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.infrastructure.qt.qt_single_instance_guard import QtSingleInstanceGuard, server_name_for

pytestmark = pytest.mark.ui

REPO_ROOT = Path(__file__).resolve().parents[3]
SECOND_INSTANCE_MODULE = "tests.integration.qt.second_instance_process"


class _Guards:
    def __init__(self, lock_dir: Path) -> None:
        self.owner = QObject()
        self.lock_dir = lock_dir
        self.key = f"concentrator-test-{uuid.uuid4().hex[:8]}"
        self.created: list[QtSingleInstanceGuard] = []

    def new(self, timeout_ms: int = 1000) -> QtSingleInstanceGuard:
        guard = QtSingleInstanceGuard(lock_dir=self.lock_dir, key=self.key, timeout_ms=timeout_ms, parent=self.owner)
        self.created.append(guard)
        return guard


@pytest.fixture
def guards(qtbot: QtBot, tmp_path: Path) -> Iterator[_Guards]:
    del qtbot  # ensures the QApplication exists
    factory = _Guards(tmp_path / "lock")
    yield factory
    for guard in factory.created:
        guard.release()


def test_server_name_is_per_key_and_per_user() -> None:
    assert server_name_for("concentrator", "ana") != server_name_for("concentrator", "bob")
    assert server_name_for("concentrator", "ana").startswith("concentrator-")


def test_first_guard_acquires_and_creates_the_lock_file(guards: _Guards) -> None:
    result = guards.new().acquire()

    assert result.data is True
    assert not result.validation.has_warnings
    assert (guards.lock_dir / f"{guards.key}.lock").is_file()


def test_second_instance_process_notifies_the_first_and_exits(qtbot: QtBot, guards: _Guards) -> None:
    first = guards.new()
    activations: list[str] = []
    first.set_activation_handler(lambda: activations.append("shown"))
    assert first.acquire().data is True
    command = [sys.executable, "-m", SECOND_INSTANCE_MODULE, str(guards.lock_dir), guards.key]

    with subprocess.Popen(command, cwd=REPO_ROOT, stdout=subprocess.PIPE, text=True) as process:
        qtbot.waitUntil(lambda: process.poll() is not None, timeout=20000)
        output, _ = process.communicate()

    assert output.strip() == "False success"
    qtbot.waitUntil(lambda: activations == ["shown"], timeout=2000)


def test_lock_is_free_again_after_release(guards: _Guards) -> None:
    first = guards.new()
    assert first.acquire().data is True

    first.release()

    assert guards.new().acquire().data is True


def test_unanswered_notification_is_a_warning(guards: _Guards) -> None:
    guards.lock_dir.mkdir(parents=True)
    holder_without_server = QLockFile(str(guards.lock_dir / f"{guards.key}.lock"))
    assert holder_without_server.tryLock(0)

    result = guards.new(timeout_ms=150).acquire()

    assert result.data is False
    assert result.validation.error_codes == (ErrorCodeEnum.INSTANCE_SERVER_FAILED,)


def test_lock_folder_that_cannot_be_created_fails(qtbot: QtBot, tmp_path: Path) -> None:
    del qtbot
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    guard = QtSingleInstanceGuard(lock_dir=blocker / "lock", key="k", timeout_ms=100, parent=QObject())

    result = guard.acquire()

    assert result.data is None
    assert result.validation.error_codes == (ErrorCodeEnum.INSTANCE_LOCK_FAILED,)
