"""Storage throughput benchmark (phase 1 spec): TOML decode and encode, full read and write pipelines.

Builds a synthetic TOML document shaped like task data (lines of text with apostrophes, a path and a
URL; history events) and prints the time and MB/s of each stage. 1,000 tasks are enough (ADR-035);
the numbers feed the phase 8 startup target.

Usage: ``uv run python scripts/bench_storage.py [--tasks 1000] [--events 20] [--repeat 3]``.
"""

import argparse
import json
import sys
import time
from collections.abc import Callable, Sequence
from typing import Annotated, Final

from pydantic import BaseModel, ConfigDict, Field

from concentrator.infrastructure.persistence.toml_codec import TomlCodec

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
    options = parser.parse_args(argv)
    for line in run(int(options.tasks), int(options.events), int(options.repeat)):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
