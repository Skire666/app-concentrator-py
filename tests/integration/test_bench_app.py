"""The application benchmark still runs (a few tasks, child process, temporary profile)."""

import subprocess
import sys
from pathlib import Path
from typing import Final

import pytest

REPO_ROOT: Final = Path(__file__).resolve().parents[2]
TIMEOUT_S: Final = 120
EXPECTED_STAGES: Final = ("file: ", "save (writer thread): ", "read: ", "table snapshot (5 rows): ", "search filter")


@pytest.mark.slow
def test_benchmark_runs_every_stage_on_a_few_tasks() -> None:
    completed = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "bench_app.py"), "--tasks", "5", "--repeat", "1"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=REPO_ROOT,
        timeout=TIMEOUT_S,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    lines = completed.stdout.splitlines()
    assert lines[0] == "tasks: 5, history events per task: 10"
    for stage in EXPECTED_STAGES:
        assert any(line.startswith(stage) for line in lines), stage
