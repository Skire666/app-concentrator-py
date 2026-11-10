"""Storage throughput benchmark (phase 1 spec): TOML decode and encode, full read and write pipelines.

Builds a synthetic TOML document shaped like task data (lines of text with apostrophes, a path and a
URL; history events) and prints the time and MB/s of each stage. 1,000 tasks are enough (ADR-035);
the numbers feed the phase 8 startup target.

Usage: ``uv run python scripts/bench_storage.py [--tasks 1000] [--events 20] [--repeat 3]``.

``--seed-tasks 1000 --into <copy of a data file>`` instead adds 1,000 tasks to the first list of that file
(phase 5 manual test): open the copy afterwards with "Use another file...".
"""

import argparse
import json
import sys
import time
import uuid
from collections.abc import Callable, Sequence
from datetime import UTC, date, datetime, timedelta
from datetime import time as clock_time
from importlib import metadata
from pathlib import Path
from typing import Annotated, Final

from pydantic import BaseModel, ConfigDict, Field

from concentrator.application.settings.settings_defaults import SettingsDefaults
from concentrator.application.storage.user_data import StoredUserData, UserDataLimits
from concentrator.application.timer.timer_defaults import TimerDefaults
from concentrator.application.todo.todo_defaults import TodoDefaults
from concentrator.domain.common.multiline_text import MultilineText
from concentrator.domain.todo.task import Task, TaskId
from concentrator.domain.todo.task_draft import TaskDraft
from concentrator.domain.todo.task_event_kind_enum import TaskEventKindEnum
from concentrator.domain.todo.task_list import TaskListId
from concentrator.domain.todo.task_lists_collection import TaskListsCollection
from concentrator.domain.todo.tasks_collection import TasksCollection
from concentrator.infrastructure.config.ini_config_loader import IniConfigLoader
from concentrator.infrastructure.persistence.toml_codec import TomlCodec
from concentrator.infrastructure.persistence.user_data_codec import UserDataCodec
from concentrator.infrastructure.system.app_paths import AppPaths

PACKAGE_NAME: Final = "concentrator"
SEED_DUE_SPREAD_DAYS: Final = 21
SEED_NO_DUE_EVERY: Final = 4
SEED_DUE_TIME_EVERY: Final = 5
SEED_DUE_HOUR: Final = 17
SEED_TRANSITIONS: Final = (
    (),
    (),
    (),
    (),
    (),
    (),
    (),
    (TaskEventKindEnum.COMPLETED,),
    (TaskEventKindEnum.COMPLETED,),
    (TaskEventKindEnum.COMPLETED, TaskEventKindEnum.ARCHIVED),
)
"""Seven open tasks out of ten, two done, one archived."""
NOT_A_FILE: Final = "not a file:"
INVALID_FILE: Final = "invalid data file:"
NO_LIST: Final = "the data file has no list yet: open it once with Concentrator"


class SeedError(ValueError):
    """The data file cannot receive seeded tasks (``args``: message and details)."""


BYTES_PER_MB: Final = 1_000_000
DEFAULT_TASKS: Final = 1000
DEFAULT_EVENTS: Final = 20
DEFAULT_REPEAT: Final = 3
LINES_PER_TASK: Final = 4
EVENT_KINDS: Final = 4
APOSTROPHE_EVERY: Final = 3
TIMESTAMP: Final = "2026-11-06T16:44:03Z"
DUE_DATE: Final = "2026-11-10"
_STRICT: Final = ConfigDict(strict=True, extra="forbid", frozen=True)


class BenchEvent(BaseModel):
    """History event of a task (benchmark only)."""

    model_config = _STRICT

    at: str
    kind: int
    details: dict[str, str]


class BenchTask(BaseModel):
    """Task shaped like phase 5 data (benchmark only)."""

    model_config = _STRICT

    id: str
    created_at: str
    updated_at: str
    list_id: str
    text: list[str]
    due_date: str
    state: Annotated[int, Field(ge=0)]
    history: list[BenchEvent]


class BenchDocument(BaseModel):
    """Root of the synthetic document (benchmark only)."""

    model_config = _STRICT

    schema_version: int
    tasks: list[BenchTask]


def make_task(number: int, events: int) -> dict[str, object]:
    """One synthetic task with accented text, apostrophes, a path and a URL.

    Args:
        number: Task number (makes ids unique).
        events: History events of the task.

    Returns:
        Plain JSON-compatible data.
    """
    text = [
        f"Ligne {line} de la tâche {number} : préparer le dossier, appeler, vérifier." for line in range(LINES_PER_TASK)
    ]
    if number % APOSTROPHE_EVERY == 0:
        text[1] = "Voir l'arborescence D:/Projets/Concentrator et l'URL https://example.org/issue/42?tab=notes"
    history = [
        {"at": TIMESTAMP, "kind": kind % EVENT_KINDS, "details": {"from": f"{number:012d}"} if kind == 0 else {}}
        for kind in range(events)
    ]
    return {
        "id": f"019a5c1e-7a40-7c3e-9d5a-{number:012d}",
        "created_at": TIMESTAMP,
        "updated_at": TIMESTAMP,
        "list_id": "019a5c1e-7a40-7c3e-9d5a-000000000001",
        "text": text,
        "due_date": DUE_DATE,
        "state": number % 3,
        "history": history,
    }


def build_document(tasks: int, events: int) -> dict[str, object]:
    """Build the synthetic document.

    Args:
        tasks: Number of tasks.
        events: History events per task.

    Returns:
        The document.
    """
    return {"schema_version": 1, "tasks": [make_task(number, events) for number in range(tasks)]}


def best_time(operation: Callable[[], object], repeat: int) -> float:
    """Best wall time of several runs.

    Args:
        operation: Work to time.
        repeat: Number of runs.

    Returns:
        Seconds of the fastest run.
    """
    timings: list[float] = []
    for _ in range(repeat):
        start = time.perf_counter()
        operation()
        timings.append(time.perf_counter() - start)
    return min(timings)


def read_pipeline(text: str) -> BenchDocument:
    """The application's read pipeline: TOML -> json.dumps -> pydantic.

    Args:
        text: TOML document.

    Returns:
        The validated DTO.

    Raises:
        ValueError: If the document does not parse (cannot happen with generated data).
    """
    parsed = TomlCodec.decode(text)
    if not parsed.is_success:
        raise ValueError(parsed.validation.error_codes)
    return BenchDocument.model_validate_json(json.dumps(parsed.data, ensure_ascii=False))


def run(tasks: int, events: int, repeat: int) -> list[str]:
    """Time every stage.

    Args:
        tasks: Number of tasks.
        events: History events per task.
        repeat: Runs per stage (best kept).

    Returns:
        Report lines.
    """
    document = build_document(tasks, events)
    text = TomlCodec.encode(document)
    megabytes = len(text.encode("utf-8")) / BYTES_PER_MB
    model = read_pipeline(text)
    stages: dict[str, Callable[[], object]] = {
        "toml decode (tomllib)": lambda: TomlCodec.decode(text),
        "toml encode": lambda: TomlCodec.encode(document),
        "read pipeline (toml+pydantic)": lambda: read_pipeline(text),
        "write pipeline (pydantic+toml)": lambda: TomlCodec.encode(model.model_dump(mode="json")),
    }
    lines = [f"document: {megabytes:.2f} MB, {len(model.tasks)} tasks, {events} events each, best of {repeat}"]
    for name, operation in stages.items():
        seconds = best_time(operation, repeat)
        lines.append(f"{name:<34} {seconds * 1000:9.1f} ms {megabytes / seconds:8.2f} MB/s")
    return lines


def _codec() -> tuple[UserDataCodec, int]:
    """Build the application's codec with the limits of the shipped ``concentrator.ini``.

    Returns:
        The codec and the history cap (``todo.max_history_events``).

    Raises:
        ValueError: If the ini cannot be loaded.
    """
    paths = AppPaths.from_runtime()
    config = IniConfigLoader(paths).load(paths.config_file)
    if config.data is None:
        raise ValueError(config.validation.error_codes)
    todo = TodoDefaults.from_section(config.data.todo).limits
    limits = UserDataLimits(
        timer=TimerDefaults.from_section(config.data.timer).limits,
        settings=SettingsDefaults.from_section(config.data.settings),
        todo=todo,
    )
    return UserDataCodec(metadata.version(PACKAGE_NAME), limits), todo.max_history_events


def _seed_draft(number: int, list_id: TaskListId, today: date) -> TaskDraft:
    """Values of one seeded task: one to four lines, a path or an apostrophe now and then, mixed due dates.

    Args:
        number: Task number.
        list_id: List of the task.
        today: Local date of the seeding.

    Returns:
        The draft.
    """
    lines = [f"Seeded task {number}: prepare, call, check"]
    lines.extend(f"Line {line} of task {number}" for line in range(1, number % LINES_PER_TASK + 1))
    if number % APOSTROPHE_EVERY == 0:
        lines.append("See l'arborescence D:/Projets/Concentrator and https://example.org/issue/42")
    offset = number % SEED_DUE_SPREAD_DAYS - SEED_DUE_SPREAD_DAYS // 2
    due_date = None if number % SEED_NO_DUE_EVERY == 0 else today + timedelta(days=offset)
    due_time = clock_time(SEED_DUE_HOUR, 0) if due_date is not None and number % SEED_DUE_TIME_EVERY == 0 else None
    return TaskDraft(list_id=list_id, text=MultilineText(tuple(lines)), due_date=due_date, due_time=due_time)


def _seed_task(number: int, list_id: TaskListId, now: datetime, max_events: int) -> Task:
    """One seeded task, open, done or archived.

    Args:
        number: Task number.
        list_id: List of the task.
        now: Creation instant.
        max_events: History cap.

    Returns:
        The task.
    """
    task = Task.create(TaskId(str(uuid.uuid7())), now, _seed_draft(number, list_id, now.astimezone().date()))
    kinds = SEED_TRANSITIONS[number % len(SEED_TRANSITIONS)]
    for kind in kinds:
        task = task.transitioned(kind, now, max_events).value_or(task)
    return task


def seed(path: Path, count: int) -> str:
    """Add tasks to the first list of an existing data file (a copy: Concentrator must not have it open).

    Args:
        path: Data file to extend.
        count: Number of tasks to add.

    Returns:
        A one-line report.

    Raises:
        SeedError: If the file does not exist, is not a valid data file or has no list.
    """
    if not path.is_file():
        raise SeedError(NOT_A_FILE, path)
    codec, max_events = _codec()
    decoded = codec.decode(path.read_text(encoding="utf-8-sig"))
    if decoded.data is None:
        raise SeedError(INVALID_FILE, [code.name for code in decoded.validation.error_codes])
    data = decoded.data.data
    first = (data.task_lists or TaskListsCollection()).first()
    if first is None:
        raise SeedError(NO_LIST)
    now = datetime.now(UTC).replace(microsecond=0)
    added = [_seed_task(number, first.id, now, max_events) for number in range(count)]
    tasks = TasksCollection((*(data.tasks or TasksCollection()), *added))
    path.write_bytes(codec.encode(StoredUserData(data=data.with_tasks(tasks), saved_at=now)).encode("utf-8"))
    return f"{count} tasks added to the first list of {path} ({len(tasks)} tasks in total)"


def main(argv: Sequence[str]) -> int:
    """Parse the options and print the report.

    Args:
        argv: Command-line arguments without the program name.

    Returns:
        The exit code.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", type=int, default=DEFAULT_TASKS, help="number of tasks")
    parser.add_argument("--events", type=int, default=DEFAULT_EVENTS, help="history events per task")
    parser.add_argument("--repeat", type=int, default=DEFAULT_REPEAT, help="runs per stage")
    parser.add_argument("--seed-tasks", type=int, default=0, help="add this many tasks to the file given by --into")
    parser.add_argument("--into", type=Path, default=None, help="data file (a copy) that receives the seeded tasks")
    options = parser.parse_args(argv)
    if options.seed_tasks:
        if options.into is None:
            parser.error("--seed-tasks needs --into")
        try:
            print(seed(Path(options.into), int(options.seed_tasks)))
        except SeedError as error:
            print("error:", *error.args, file=sys.stderr)
            return 1
        return 0
    for line in run(int(options.tasks), int(options.events), int(options.repeat)):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
