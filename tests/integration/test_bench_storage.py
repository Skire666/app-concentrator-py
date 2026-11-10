"""The storage benchmark still runs (tiny document, child process)."""

import subprocess
import sys
from pathlib import Path

import pytest

from concentrator.domain.todo.task_state_enum import TaskStateEnum
from concentrator.infrastructure.persistence.user_data_codec import UserDataCodec
from tests.fakes.todo_factory import SPEC_LIST_ID
from tests.fakes.user_data_factory import SPEC_EXAMPLE_TEXT, USER_DATA_LIMITS

REPO_ROOT = Path(__file__).resolve().parents[2]
TIMEOUT_S = 60
SEEDED = 30
CODEC = UserDataCodec("0.1.0", USER_DATA_LIMITS)


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


def _seed(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "bench_storage.py"), *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=REPO_ROOT,
        timeout=TIMEOUT_S,
        check=False,
    )


@pytest.mark.slow
def test_seed_adds_tasks_to_the_first_list_of_a_copy(tmp_path: Path) -> None:
    data_file = tmp_path / "copy.toml"
    data_file.write_bytes(SPEC_EXAMPLE_TEXT.encode("utf-8"))

    completed = _seed("--seed-tasks", "30", "--into", str(data_file))

    assert completed.returncode == 0, completed.stderr
    decoded = CODEC.decode(data_file.read_text(encoding="utf-8"))
    assert decoded.data is not None
    tasks = decoded.data.data.tasks
    assert tasks is not None
    assert len(tasks.in_list(SPEC_LIST_ID)) == SEEDED
    assert {task.state for task in tasks} == {TaskStateEnum.OPEN, TaskStateEnum.DONE, TaskStateEnum.ARCHIVED}
    assert any(task.due_time is not None for task in tasks)
    assert any(task.due_date is None for task in tasks)


@pytest.mark.slow
def test_seed_refuses_a_missing_file(tmp_path: Path) -> None:
    completed = _seed("--seed-tasks", "3", "--into", str(tmp_path / "missing.toml"))

    assert completed.returncode == 1
    assert "not a file" in completed.stderr
