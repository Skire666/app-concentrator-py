"""ADR-026: only the process that keeps running opens the log file."""

import logging
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from concentrator.application.common.app_config import AppConfig
from concentrator.bootstrap.app import acquire_single_instance, claim_instance
from concentrator.bootstrap.runtime import Runtime, configure_runtime
from concentrator.infrastructure.config.ini_config_loader import IniConfigLoader
from concentrator.infrastructure.system.app_paths import AppPaths

pytestmark = pytest.mark.ui

REPO_ROOT = Path(__file__).resolve().parents[3]
REAL_PATHS = AppPaths.from_runtime()
SECOND_LAUNCH_MODULE = "tests.integration.bootstrap.second_launch_process"
SECOND_LAUNCH_TIMEOUT_MS = 30_000


class _Install:
    """Temporary installation sharing its user folders with a child "second launch"."""

    def __init__(self, root: Path, *, file_max_bytes: int = 2_000_000) -> None:
        self.app_dir = root / "app"
        self.app_dir.mkdir()
        text = REAL_PATHS.config_file.read_text(encoding="utf-8")
        text = text.replace("file_max_bytes = 2000000", f"file_max_bytes = {file_max_bytes}")
        (self.app_dir / "concentrator.ini").write_text(text, encoding="utf-8")
        self.appdata = root / "roaming"
        self.localappdata = root / "local"
        environment = {"APPDATA": str(self.appdata), "LOCALAPPDATA": str(self.localappdata)}
        self.paths = AppPaths(self.app_dir, REAL_PATHS.assets_dir, self.app_dir / "concentrator.ini", environment)
        self.log_dir = self.localappdata / "Concentrator" / "logs"

    def config(self) -> AppConfig:
        config = IniConfigLoader(self.paths).load(self.paths.config_file).data
        assert config is not None
        return config

    def log_text(self) -> str:
        return "".join(path.read_text(encoding="utf-8") for path in sorted(self.log_dir.glob("concentrator.log*")))

    def run_second_launch(self, qtbot: QtBot) -> tuple[int, str]:
        """Start the whole application again; the test process keeps its event loop running meanwhile."""
        arguments = [str(self.app_dir), str(self.paths.assets_dir), str(self.appdata), str(self.localappdata)]
        command = [sys.executable, "-m", SECOND_LAUNCH_MODULE, *arguments]
        with subprocess.Popen(
            command, cwd=REPO_ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True
        ) as process:
            try:
                qtbot.waitUntil(lambda: process.poll() is not None, timeout=SECOND_LAUNCH_TIMEOUT_MS)
            finally:
                if process.poll() is None:
                    process.kill()
            _, errors = process.communicate()
        return process.returncode, errors


def _app() -> QApplication:
    application = QApplication.instance()
    assert isinstance(application, QApplication)
    return application


@pytest.fixture
def runtime_factory() -> Iterator[list[Runtime]]:
    runtimes: list[Runtime] = []
    root = logging.getLogger()
    level = root.level
    yield runtimes
    for runtime in runtimes:
        runtime.shutdown()
    root.setLevel(level)


def test_instance_holding_the_lock_gets_the_buffered_startup_records(
    qtbot: QtBot, tmp_path: Path, runtime_factory: list[Runtime]
) -> None:
    del qtbot
    install = _Install(tmp_path)
    config = install.config()
    runtime = configure_runtime(config)
    runtime_factory.append(runtime)
    logging.getLogger("tests.startup").info("record logged before the lock")
    assert not install.log_dir.exists()

    check = claim_instance(_app(), config, install.paths, runtime)
    assert check.guard is not None
    check.guard.release()

    log = install.log_text()
    assert log.index("record logged before the lock") < log.index("Single-instance lock acquired")


def test_unguarded_instance_still_opens_the_log_file(
    qtbot: QtBot, tmp_path: Path, runtime_factory: list[Runtime]
) -> None:
    del qtbot
    install = _Install(tmp_path)
    config = install.config()
    runtime = configure_runtime(config)
    runtime_factory.append(runtime)
    no_localappdata = AppPaths(install.app_dir, install.paths.assets_dir, install.paths.config_file, {})

    check = claim_instance(_app(), config, no_localappdata, runtime)

    assert check.guard is None
    assert not check.other_instance_running
    assert "running without single-instance protection" in install.log_text()


def test_second_launch_does_not_create_the_log_file(qtbot: QtBot, tmp_path: Path) -> None:
    install = _Install(tmp_path)
    first = acquire_single_instance(_app(), install.config(), install.paths)
    assert first.guard is not None
    activations: list[str] = []
    first.guard.set_activation_handler(lambda: activations.append("shown"))

    try:
        exit_code, errors = install.run_second_launch(qtbot)
        qtbot.waitUntil(lambda: activations == ["shown"], timeout=2000)
    finally:
        first.guard.release()

    assert exit_code == 0, errors
    assert "Another instance is running" in errors
    assert not install.log_dir.exists()


def test_log_file_rolls_over_while_running_after_a_second_launch(
    qtbot: QtBot, tmp_path: Path, runtime_factory: list[Runtime]
) -> None:
    install = _Install(tmp_path, file_max_bytes=10_000)
    config = install.config()
    runtime = configure_runtime(config)
    runtime_factory.append(runtime)
    first = claim_instance(_app(), config, install.paths, runtime)
    assert first.guard is not None

    try:
        exit_code, errors = install.run_second_launch(qtbot)
        for index in range(200):
            logging.getLogger("tests.rollover").info("line %03d written after the second launch", index)
    finally:
        first.guard.release()

    assert exit_code == 0, errors
    assert (install.log_dir / "concentrator.log.1").is_file()
    log = install.log_text()
    assert "line 199 written after the second launch" in log
    assert "Another instance is running" not in log
