"""The storage benchmark still runs (tiny document, child process)."""

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TIMEOUT_S = 60


@pytest.mark.slow
def test_benchmark_runs_on_a_tiny_document() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "bench_storage.py"),
            "--tasks",
            "5",
            "--events",
            "2",
            "--repeat",
            "1",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=REPO_ROOT,
        timeout=TIMEOUT_S,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    lines = completed.stdout.splitlines()
    assert lines[0].startswith("document: ")
    assert len(lines) == 5
    assert all("MB/s" in line for line in lines[1:])
