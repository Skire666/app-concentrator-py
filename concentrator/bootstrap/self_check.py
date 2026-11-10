"""``CONCENTRATOR_SELF_CHECK=1``: validates a (frozen) installation without showing a window."""

import logging
from datetime import UTC, date, datetime, time
from pathlib import Path
from typing import Final

from PySide6.QtGui import QIcon, QImageReader

from concentrator.application.common.app_config import AppConfig
from concentrator.application.settings.settings_defaults import SettingsDefaults
from concentrator.application.storage.user_data import StoredUserData, UserData, UserDataLimits
from concentrator.application.timer.chime_defaults import ChimeDefaults
from concentrator.application.timer.timer_defaults import TimerDefaults
from concentrator.application.todo.todo_defaults import TodoDefaults
from concentrator.bootstrap.translator_loader import CATALOG_LANGUAGES
from concentrator.domain.common.multiline_text import MultilineText
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.domain.settings.user_settings import UserSettings, UserSettingsId
from concentrator.domain.timer.hourly_chime import HourlyChime, HourlyChimeId
from concentrator.domain.timer.timer_config import TimerConfig, TimerConfigId
from concentrator.domain.timer.timer_preset import TimerPreset, TimerPresetId
from concentrator.domain.timer.timer_presets_collection import TimerPresetsCollection
from concentrator.domain.todo.task import Task, TaskId
from concentrator.domain.todo.task_draft import TaskDraft
from concentrator.domain.todo.task_event_kind_enum import TaskEventKindEnum
from concentrator.domain.todo.task_list import TaskList, TaskListId
from concentrator.domain.todo.task_lists_collection import TaskListsCollection
from concentrator.domain.todo.tasks_collection import TasksCollection
from concentrator.infrastructure.i18n.json_catalog_translator import CATALOG_SUFFIX, load_catalogs
from concentrator.infrastructure.persistence.user_data_codec import UserDataCodec
from concentrator.infrastructure.qt.qt_sound_player import MP3_MIME_TYPE, decodable_mime_types
from concentrator.infrastructure.system.app_paths import AppPaths
from concentrator.infrastructure.system.builtin_sound_catalog import SOUND_SUFFIX
from concentrator.ui.panels.module_bar_panel import MODULE_ICON_FILES

_logger = logging.getLogger(__name__)

SVG_FORMAT = b"svg"
ICON_CHECK_SIZE_PX = 32
ROUND_TRIP_ID: Final = UserSettingsId("00000000-0000-7000-8000-000000000000")
ROUND_TRIP_TIMER_ID: Final = TimerConfigId("00000000-0000-7000-8000-000000000001")
ROUND_TRIP_CHIME_ID: Final = HourlyChimeId("00000000-0000-7000-8000-000000000002")
ROUND_TRIP_PRESET_ID: Final = "00000000-0000-7000-8001-{index:012d}"
ROUND_TRIP_TIME: Final = datetime(2026, 1, 1, tzinfo=UTC)
ROUND_TRIP_LIST_ID: Final = TaskListId("00000000-0000-7000-8000-000000000003")
ROUND_TRIP_TASK_ID: Final = TaskId("00000000-0000-7000-8000-000000000004")
ROUND_TRIP_TEXT: Final = ("Self-check task", "l'arborescence D:/Projets et https://example.org/?q='x'")
ROUND_TRIP_DUE: Final = (date(2026, 1, 2), time(14, 30))


def _required_files(paths: AppPaths, config: AppConfig) -> list[Path]:
    """Files the application cannot run without.

    Args:
        paths: Application paths.
        config: Loaded configuration (default alarm and chime sounds).

    Returns:
        The ini, the catalogs, the icons and the default alarm and chime sounds.
    """
    catalogs = [paths.i18n_dir / f"{language.iso_code}{CATALOG_SUFFIX}" for language in CATALOG_LANGUAGES]
    icons = [paths.icons_dir / name for name in MODULE_ICON_FILES.values()]
    sounds = [
        paths.sounds_dir / f"{name}{SOUND_SUFFIX}" for name in (config.timer.default_sound, config.chime.default_sound)
    ]
    return [paths.config_file, *catalogs, paths.app_icon_file, *icons, *sounds]


def audio_failures() -> list[str]:
    """Check that the Qt multimedia FFmpeg plugin is bundled and decodes MP3 (ADR-004).

    Returns:
        One description per problem.
    """
    if MP3_MIME_TYPE in decodable_mime_types():
        return []
    return ["Qt multimedia cannot decode MP3 (FFmpeg plugin missing)"]


def _svg_failures(paths: AppPaths) -> list[str]:
    """Check that the Qt SVG image plugin is bundled and renders the module icons.

    Args:
        paths: Application paths.

    Returns:
        One description per problem.
    """
    formats = {bytes(item.data()) for item in QImageReader.supportedImageFormats()}
    if SVG_FORMAT not in formats:
        return ["Qt SVG image plugin missing"]
    return [
        f"icon cannot be rendered: {name}"
        for name in MODULE_ICON_FILES.values()
        if QIcon(str(paths.icons_dir / name)).pixmap(ICON_CHECK_SIZE_PX, ICON_CHECK_SIZE_PX).isNull()
    ]


def _round_trip_data(
    timer: TimerDefaults, chime: ChimeDefaults, defaults: SettingsDefaults, todo: TodoDefaults
) -> UserData:
    """Content of a new data file with every section, built from the ini defaults.

    Args:
        timer: ``[timer]`` values (configuration and favorites).
        chime: ``[chime]`` values.
        defaults: ``[settings]`` values.
        todo: ``[todo]`` values.

    Returns:
        The data.
    """
    settings = UserSettings.create(ROUND_TRIP_ID, ROUND_TRIP_TIME, defaults.general(LanguageEnum.ENGLISH))
    timer_config = TimerConfig.create(ROUND_TRIP_TIMER_ID, ROUND_TRIP_TIME, timer.settings)
    presets = TimerPresetsCollection(
        TimerPreset.create(
            TimerPresetId(ROUND_TRIP_PRESET_ID.format(index=index)),
            ROUND_TRIP_TIME,
            label="",
            duration=duration,
            position=index,
        )
        for index, duration in enumerate(timer.presets)
    )
    hourly_chime = HourlyChime.create(
        ROUND_TRIP_CHIME_ID, ROUND_TRIP_TIME, enabled=chime.enabled, settings=chime.settings
    )
    data = UserData.initial(settings, timer_config, presets, hourly_chime, _round_trip_lists(todo))
    return data.with_tasks(_round_trip_tasks(todo))


def _round_trip_lists(todo: TodoDefaults) -> TaskListsCollection:
    """One list with a two-line description.

    Args:
        todo: ``[todo]`` values.

    Returns:
        The lists.
    """
    task_list = TaskList.create(
        ROUND_TRIP_LIST_ID,
        ROUND_TRIP_TIME,
        name="Inbox",
        description=MultilineText(ROUND_TRIP_TEXT),
        priority=todo.list_priority,
        position=0,
    )
    return TaskListsCollection((task_list,))


def _round_trip_tasks(todo: TodoDefaults) -> TasksCollection:
    """One completed task with a due date and time, apostrophes and a history of two events.

    Args:
        todo: ``[todo]`` values.

    Returns:
        The tasks.
    """
    due_date, due_time = ROUND_TRIP_DUE
    draft = TaskDraft(
        list_id=ROUND_TRIP_LIST_ID, text=MultilineText(ROUND_TRIP_TEXT), due_date=due_date, due_time=due_time
    )
    task = Task.create(ROUND_TRIP_TASK_ID, ROUND_TRIP_TIME, draft)
    done = task.transitioned(TaskEventKindEnum.COMPLETED, ROUND_TRIP_TIME, todo.limits.max_history_events)
    return TasksCollection((done.value_or(task),))


def storage_failures(app_version: str, config: AppConfig) -> list[str]:
    """Round-trip an in-memory ``UserData`` through codec, schemas and mappers (no file, ADR-034).

    A frozen bundle missing ``tomllib`` or ``pydantic`` pieces fails here.

    Args:
        app_version: Version written in the document.
        config: Loaded configuration (timer defaults and limits).

    Returns:
        One description per problem.
    """
    timer = TimerDefaults.from_section(config.timer)
    settings = SettingsDefaults.from_section(config.settings)
    todo = TodoDefaults.from_section(config.todo)
    codec = UserDataCodec(app_version, UserDataLimits(timer=timer.limits, settings=settings, todo=todo.limits))
    data = _round_trip_data(timer, ChimeDefaults.from_section(config.chime), settings, todo)
    stored = StoredUserData(data=data, saved_at=ROUND_TRIP_TIME)
    decoded = codec.decode(codec.encode(stored))
    if decoded.data == stored:
        return []
    return [f"user data round trip: {[code.name for code in decoded.validation.error_codes]}"]


def run_self_check(paths: AppPaths, config: AppConfig, app_version: str) -> bool:
    """Check the assets, catalogs, SVG rendering, MP3 decoding and user data pipeline; log the outcome.

    Args:
        paths: Application paths.
        config: Loaded configuration (its loading is the first check).
        app_version: Version used for the user data round trip.

    Returns:
        Whether every check passed.
    """
    failures = [f"missing file: {path}" for path in _required_files(paths, config) if not path.is_file()]
    catalogs = load_catalogs(paths.i18n_dir, CATALOG_LANGUAGES, config.i18n.fallback_language)
    if not catalogs.is_success or catalogs.validation.has_warnings:
        failures.append(f"catalogs: {[code.name for code in catalogs.validation.error_codes]}")
    failures.extend(_svg_failures(paths))
    failures.extend(audio_failures())
    failures.extend(storage_failures(app_version, config))
    if failures:
        _logger.error("Self-check failed: %s", failures)
        return False
    _logger.info("Self-check passed (app dir %s, assets %s)", paths.app_dir, paths.assets_dir)
    return True
