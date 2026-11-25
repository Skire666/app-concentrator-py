"""Application benchmark of the phase 8 performance targets, on the shipped ini and catalogs.

Everything runs in a temporary ``%APPDATA%`` and ``%LOCALAPPDATA%``: the real data file, ``ui-state.ini``
and logs are never touched. A data file of ``--tasks`` open tasks in one list, each with a full history
(``todo.max_history_events``), is created, then the script prints the best of ``--repeat`` runs of:

- save: one save on the writer thread (encode, atomic write, ``.bak``);
- read: file read, TOML, schema, mapper and domain rules (main thread at startup);
- table: the task table snapshot (production presenters, real translator);
- search: one search applied to the tasks (the filter behind each debounced key press).

``--startup`` also launches the application on that file (``python -m concentrator``, or ``--exe`` for a
build), offscreen, and reads ``Startup took <ms> ms`` from its log; close Concentrator first.

Usage: ``uv run python scripts/bench_app.py [--tasks 1000] [--repeat 5] [--startup [--exe <path>]]``.
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
import time
import uuid
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from importlib import metadata
from pathlib import Path
from typing import Final

from PySide6.QtWidgets import QApplication

from concentrator.application.common.app_config import AppConfig
from concentrator.application.settings.settings_defaults import SettingsDefaults
from concentrator.application.storage.user_data import UserData, UserDataLimits
from concentrator.application.timer.timer_defaults import TimerDefaults
from concentrator.application.todo.todo_defaults import TodoDefaults
from concentrator.application.todo.todo_queries import TodoQueries
from concentrator.bootstrap.core import Core, build_core
from concentrator.bootstrap.runtime import ForwardingErrorReporter
from concentrator.bootstrap.storage import build_storage
from concentrator.bootstrap.todo import build_todo
from concentrator.bootstrap.translator_loader import load_translator
from concentrator.domain.common.multiline_text import MultilineText
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.domain.todo.task import Task, TaskId
from concentrator.domain.todo.task_draft import TaskDraft
from concentrator.domain.todo.task_event_kind_enum import TaskEventKindEnum
from concentrator.domain.todo.task_list import TaskListId
from concentrator.domain.todo.tasks_collection import TasksCollection
from concentrator.infrastructure.config.ini_config_loader import IniConfigLoader
from concentrator.infrastructure.persistence.store_todo import StoreTaskListReader, StoreTaskReader
from concentrator.infrastructure.persistence.toml_user_data_file import TomlUserDataFile
from concentrator.infrastructure.persistence.user_data_codec import UserDataCodec
from concentrator.infrastructure.persistence.user_data_store import UserDataStore
from concentrator.infrastructure.persistence.writer_thread import WriterThread
from concentrator.infrastructure.system.app_paths import AppPaths
from concentrator.presentation.common.layout_state_keeper import LayoutStateKeeper
from concentrator.presentation.todo.todo_view import TodoView
from concentrator.presentation.todo.todo_view_state import TodoViewState

PACKAGE_NAME: Final = "concentrator"
DEFAULT_TASKS: Final = 1000
DEFAULT_REPEAT: Final = 5
DEFAULT_STARTUP_RUNS: Final = 3
MS_PER_SECOND: Final = 1000
BYTES_PER_KB: Final = 1000
SAVE_TIMEOUT_MS: Final = 60_000
STARTUP_TIMEOUT_S: Final = 60.0
POLL_INTERVAL_S: Final = 0.1
LINES_PER_TASK: Final = 4
APOSTROPHE_EVERY: Final = 3
DUE_SPREAD_DAYS: Final = 9
SEARCHES: Final = ("task 7", "line 2", "arborescence", "nothing matches this")
STARTUP_LINE: Final = re.compile(r"Startup took (\d+) ms")
OFFSCREEN: Final = ("-platform", "offscreen")
ENVIRONMENT_OVERRIDES: Final = ("APPDATA", "LOCALAPPDATA")
TRANSITIONS: Final = (TaskEventKindEnum.COMPLETED, TaskEventKindEnum.REOPENED)
INVALID_INI: Final = "invalid concentrator.ini:"
CANNOT_CREATE: Final = "cannot create the data file:"
UNREADABLE_SEED: Final = "cannot read the seeded file:"
SAVE_FAILED: Final = "a save failed, so its time means nothing:"
NO_LIST: Final = "the new data file has no list"
NO_STARTUP_LINE: Final = "no startup line in the log: is Concentrator already running?"


class BenchError(RuntimeError):
    """The benchmark cannot run (message in ``args``)."""


def best_ms(operation: Callable[[], object], repeat: int) -> float:
    """Run an operation several times.

    Args:
        operation: What to measure.
        repeat: Number of runs.

    Returns:
        The fastest run in milliseconds.
    """
    best = float("inf")
    for _ in range(repeat):
        started = time.perf_counter()
        operation()
        best = min(best, (time.perf_counter() - started) * MS_PER_SECOND)
    return best


def make_task(number: int, list_id: TaskListId, now: datetime, max_events: int) -> Task:
    """One open task of one to four lines with a full history (completed and reopened in turn).

    Args:
        number: Task number.
        list_id: List of the task.
        now: Creation instant.
        max_events: History cap.

    Returns:
        The task.
    """
    lines = [f"Task {number}: prepare the file, call the client, check the figures"]
    lines.extend(f"Line {line} of task {number}" for line in range(1, number % LINES_PER_TASK + 1))
    if number % APOSTROPHE_EVERY == 0:
        lines.append("See l'arborescence D:/Projets/Concentrator and https://example.org/issue/42")
    due_date = now.date() + timedelta(days=number % DUE_SPREAD_DAYS)
    task = Task.create(
        TaskId(str(uuid.uuid7())), now, TaskDraft(list_id=list_id, text=MultilineText(tuple(lines)), due_date=due_date)
    )
    for step in range(max_events):
        task = task.transitioned(TRANSITIONS[step % len(TRANSITIONS)], now, max_events).value_or(task)
    return task.transitioned(TaskEventKindEnum.REOPENED, now, max_events).value_or(task)


def seeded(data: UserData, count: int, max_events: int) -> UserData:
    """Add ``count`` open tasks to the first list.

    Args:
        data: Content of a new data file (the Inbox).
        count: Number of tasks.
        max_events: History cap.

    Returns:
        The data with the tasks.

    Raises:
        BenchError: If the data has no list.
    """
    first = data.task_lists.first() if data.task_lists is not None else None
    if first is None:
        raise BenchError(NO_LIST)
    now = datetime.now(UTC).replace(microsecond=0)
    return data.with_tasks(TasksCollection(make_task(number, first.id, now, max_events) for number in range(count)))


def load_config() -> tuple[AppPaths, AppConfig]:
    """Load the shipped ini with the (temporary) environment.

    Returns:
        The paths and the configuration.

    Raises:
        BenchError: If the ini is invalid.
    """
    paths = AppPaths.from_runtime()
    loaded = IniConfigLoader(paths).load(paths.config_file)
    if loaded.data is None:
        raise BenchError(INVALID_INI, [code.name for code in loaded.validation.error_codes])
    return paths, loaded.data


def codec_of(config: AppConfig) -> UserDataCodec:
    """Build the codec as the application does (bounds of ``concentrator.ini``).

    Args:
        config: Loaded configuration.

    Returns:
        The codec.
    """
    limits = UserDataLimits(
        timer=TimerDefaults.from_section(config.timer).limits,
        settings=SettingsDefaults.from_section(config.settings),
        todo=TodoDefaults.from_section(config.todo).limits,
    )
    return UserDataCodec(metadata.version(PACKAGE_NAME), limits)


def measure_storage(core: Core, config: AppConfig, data: UserData, repeat: int) -> list[str]:
    """Write the seeded data file, then time its save and its read.

    Args:
        core: Main-thread services.
        config: Loaded configuration.
        data: Seeded data.
        repeat: Runs per stage.

    Returns:
        Report lines.

    Raises:
        BenchError: If a save fails or the file cannot be read back.
    """
    path = config.paths.default_data_file
    writer = WriterThread(core.dispatcher, ForwardingErrorReporter())
    try:
        adapter = TomlUserDataFile(
            codec=codec_of(config), writer=writer, clock=core.clock, storage=config.storage, backup_dir=path.parent
        )

        def save() -> None:
            outcome = adapter.save(path, data, 1, timeout_ms=SAVE_TIMEOUT_MS)
            if outcome.validation.is_failure:
                raise BenchError(SAVE_FAILED, [code.name for code in outcome.validation.error_codes])

        save_ms = best_ms(save, repeat)
        loaded = adapter.load(path)
        if loaded.data is None:
            raise BenchError(UNREADABLE_SEED, [code.name for code in loaded.validation.error_codes])
        read_ms = best_ms(lambda: adapter.load(path), repeat)
    finally:
        writer.shutdown()
    size_kb = path.stat().st_size / BYTES_PER_KB
    return [f"file: {size_kb:.0f} kB", f"save (writer thread): {save_ms:.0f} ms", f"read: {read_ms:.0f} ms"]


def measure_table(core: Core, setup: tuple[AppPaths, AppConfig], store: UserDataStore, repeat: int) -> list[str]:
    """Time the task table snapshot of the production presenters.

    Args:
        core: Main-thread services.
        setup: Application paths and configuration.
        store: Data of the seeded file.
        repeat: Runs.

    Returns:
        Report lines.
    """
    paths, config = setup
    todo = build_todo(config, load_translator(paths, config), core, store)
    rows = len(todo.table.build_snapshot().table.rows)
    table_ms = best_ms(todo.table.build_snapshot, repeat)
    return [f"table snapshot ({rows} rows): {table_ms:.1f} ms"]


def measure_search(core: Core, config: AppConfig, store: UserDataStore, repeat: int) -> list[str]:
    """Time the filter applied after a debounced key press of the search field.

    Args:
        core: Main-thread services.
        config: Loaded configuration.
        store: Data of the seeded file.
        repeat: Runs per search.

    Returns:
        Report lines.
    """
    queries = TodoQueries(StoreTaskListReader(store), StoreTaskReader(store))
    state = TodoViewState(LayoutStateKeeper(core.preferences), TodoDefaults.from_section(config.todo))
    view = TodoView(queries, state, core.clock)
    view.sync()
    shown = len(view.visible())
    timings = [[_search_ms(view, state, search) for _ in range(repeat)] for search in SEARCHES]
    first = timings[0][0]
    worst = max(min(runs) for runs in timings)
    return [
        f"search filter over {shown} tasks: first search {first:.1f} ms (texts folded once)",
        f"search filter, worst of {len(SEARCHES)} searches: {worst:.1f} ms",
    ]


def _search_ms(view: TodoView, state: TodoViewState, search: str) -> float:
    """Time one search typed after an empty search field.

    Args:
        view: Tasks of the table.
        state: Its query.
        search: Text typed.

    Returns:
        The time to filter the tasks, in milliseconds.
    """
    state.set_search("")
    view.visible()
    started = time.perf_counter()
    state.set_search(search)
    view.visible()
    return (time.perf_counter() - started) * MS_PER_SECOND


def startup_ms(command: Sequence[str], log_file: Path) -> int:
    """Launch the application once, offscreen, and read its startup time from the log.

    Args:
        command: Application command line.
        log_file: Log file of the temporary profile.

    Returns:
        The startup time in milliseconds.

    Raises:
        BenchError: If the log line does not appear in time.
    """
    log_file.unlink(missing_ok=True)
    process = subprocess.Popen(command, env={**os.environ, "QT_QPA_PLATFORM": "offscreen"})
    try:
        deadline = time.monotonic() + STARTUP_TIMEOUT_S
        while time.monotonic() < deadline and process.poll() is None:
            found = STARTUP_LINE.search(log_file.read_text(encoding="utf-8")) if log_file.is_file() else None
            if found is not None:
                return int(found.group(1))
            time.sleep(POLL_INTERVAL_S)
    finally:
        _stop_tree(process)
    raise BenchError(NO_STARTUP_LINE)


def _stop_tree(process: subprocess.Popen[bytes]) -> None:
    """Stop the application and its children (the ``python.exe`` of a venv is a launcher with a child).

    Args:
        process: Launched application.
    """
    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, check=False)
    process.wait()


def measure_startup(config: AppConfig, exe: Path | None, runs: int) -> list[str]:
    """Time the startup of the application on the seeded file (first run cold, then warm).

    Args:
        config: Loaded configuration.
        exe: Built executable, or ``None`` for ``python -m concentrator``.
        runs: Launches.

    Returns:
        Report lines.
    """
    command = [str(exe.resolve())] if exe is not None else [sys.executable, "-m", PACKAGE_NAME]
    log_file = config.paths.log_dir / config.logging.file_name
    times = [startup_ms(command, log_file) for _ in range(runs)]
    label = exe.name if exe is not None else "python -m concentrator"
    return [f"startup ({label}, offscreen): " + ", ".join(f"{value} ms" for value in times)]


def run(tasks: int, repeat: int, startup: tuple[bool, Path | None]) -> list[str]:
    """Seed a temporary profile and measure every stage.

    Args:
        tasks: Number of tasks.
        repeat: Runs per stage.
        startup: Whether to launch the application, and the executable to launch.

    Returns:
        Report lines.

    Raises:
        BenchError: If a stage cannot run.
    """
    paths, config = load_config()
    app = QApplication([sys.argv[0], *OFFSCREEN])
    core = build_core(app, config, ForwardingErrorReporter())
    storage = build_storage(
        core, config, load_translator(paths, config), ForwardingErrorReporter(), metadata.version(PACKAGE_NAME)
    )
    try:
        created = storage.startup.create_at(config.paths.default_data_file, LanguageEnum.ENGLISH)
        if not created.is_success:
            raise BenchError(CANNOT_CREATE, [code.name for code in created.validation.error_codes])
        max_events = TodoDefaults.from_section(config.todo).limits.max_history_events
        data = seeded(storage.store.current(), tasks, max_events)
        storage.store.reset(data)
        core.preferences.sync()
        lines = [f"tasks: {tasks}, history events per task: {max_events}"]
        lines += measure_storage(core, config, data, repeat)
        lines += measure_table(core, (paths, config), storage.store, repeat)
        lines += measure_search(core, config, storage.store, repeat)
    finally:
        storage.writer.shutdown()
    if startup[0]:
        lines += measure_startup(config, startup[1], DEFAULT_STARTUP_RUNS)
    return lines


def main(argv: Sequence[str]) -> int:
    """Parse the options, run in a temporary profile and print the report.

    Args:
        argv: Command-line arguments.

    Returns:
        The exit code.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", type=int, default=DEFAULT_TASKS, help="number of tasks")
    parser.add_argument("--repeat", type=int, default=DEFAULT_REPEAT, help="runs per stage")
    parser.add_argument("--startup", action="store_true", help="also launch the application and time its startup")
    parser.add_argument("--exe", type=Path, default=None, help="built Concentrator.exe to launch with --startup")
    options = parser.parse_args(argv)
    with tempfile.TemporaryDirectory(prefix="concentrator-bench-", ignore_cleanup_errors=True) as folder:
        for name in ENVIRONMENT_OVERRIDES:
            os.environ[name] = str(Path(folder) / name.lower())
        try:
            lines = run(options.tasks, options.repeat, (options.startup, options.exe))
        except BenchError as error:
            sys.stderr.write(f"bench_app: {' '.join(map(str, error.args))}\n")
            return 1
    sys.stdout.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
