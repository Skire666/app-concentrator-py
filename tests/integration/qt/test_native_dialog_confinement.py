"""The native position filter keeps a dialog inside the main window on the real Windows platform."""

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.ui

REPO_ROOT = Path(__file__).resolve().parents[3]
NATIVE_DIALOG_MODULE = "tests.integration.qt.native_dialog_process"
TIMEOUT_S = 60


@pytest.mark.skipif(sys.platform != "win32", reason="Win32 window messages")
def test_tracked_dialog_cannot_be_moved_outside_the_host_window() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", NATIVE_DIALOG_MODULE],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=TIMEOUT_S,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    host, dialog, released = ([int(value) for value in line.split()] for line in completed.stdout.splitlines())
    assert host[:2] == [200, 150]
    assert dialog[0] == host[0]
    assert dialog[1] + dialog[3] == host[1] + host[3]
    assert released[:2] == [-5000, 5000]
