"""``UserDataSchema`` <-> ``StoredUserData``."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from concentrator.application.storage.user_data import StoredUserData, UserData, UserDataLimits
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.time_rules import TimeRules
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.timer.hourly_chime import HourlyChime
from concentrator.domain.timer.timer_config import TimerConfig
from concentrator.domain.timer.timer_presets_collection import TimerPresetsCollection
from concentrator.domain.todo.task_lists_collection import TaskListsCollection
from concentrator.domain.todo.tasks_collection import TasksCollection
from concentrator.infrastructure.persistence.mappers.hourly_chime_mapper import HourlyChimeMapper
from concentrator.infrastructure.persistence.mappers.task_lists_mapper import TaskListsMapper
from concentrator.infrastructure.persistence.mappers.tasks_mapper import TasksMapper
from concentrator.infrastructure.persistence.mappers.timer_config_mapper import TimerConfigMapper
from concentrator.infrastructure.persistence.mappers.timer_presets_mapper import TimerPresetsMapper
from concentrator.infrastructure.persistence.mappers.user_settings_mapper import UserSettingsMapper
from concentrator.infrastructure.persistence.schemas.user_data_schema import UserDataSchema

SETTINGS_FIELD: Final = "settings"
TIMER_FIELD: Final = "timer"
PRESETS_FIELD: Final = "timer_presets"
CHIME_FIELD: Final = "hourly_chime"
SAVED_AT_FIELD: Final = "saved_at"
TASK_LISTS_FIELD: Final = "task_lists"
TASKS_FIELD: Final = "tasks"


def _optional[S, T](schema: S | None, convert: Callable[[S], DataResult[T]]) -> DataResult[T | None]:
    """Map a section the file may not have yet.

    Args:
        schema: The section, ``None`` when the file does not have it.
        convert: Mapper of a present section.

    Returns:
        The domain value, ``None`` for an absent section, or the rule failures.
    """
    if schema is None:
        return DataResult[T | None](data=None, validation=ValidationResult.success())
    mapped = convert(schema)
    if mapped.data is None:
        return DataResult.fail(mapped.validation)
    return DataResult[T | None](data=mapped.data, validation=mapped.validation)


def _todo(
    schema: UserDataSchema, limits: UserDataLimits
) -> tuple[DataResult[TaskListsCollection | None], DataResult[TasksCollection | None]]:
    """Map the lists, then the tasks, which must belong to those lists.

    Args:
        schema: Validated DTO.
        limits: Bounds from ``concentrator.ini``.

    Returns:
        The lists and the tasks (``None`` for an absent section), or their rule failures.
    """
    lists = _optional(
        schema.task_lists, lambda section: TaskListsMapper.to_domain(section, TASK_LISTS_FIELD, limits.todo)
    )
    known = lists.data or TaskListsCollection()
    tasks = _optional(schema.tasks, lambda section: TasksMapper.to_domain(section, TASKS_FIELD, known, limits.todo))
    return lists, tasks


@dataclass(frozen=True, slots=True, kw_only=True)
class _Sections:
    """The sections a file may not have yet, mapped to the domain.

    Attributes:
        timer: ``[timer]``.
        presets: ``[[timer_presets]]``.
        chime: ``[hourly_chime]``.
        lists: ``[[task_lists]]``.
        tasks: ``[[tasks]]``.
    """

    timer: DataResult[TimerConfig | None]
    presets: DataResult[TimerPresetsCollection | None]
    chime: DataResult[HourlyChime | None]
    lists: DataResult[TaskListsCollection | None]
    tasks: DataResult[TasksCollection | None]

    @property
    def validation(self) -> ValidationResult:
        """Issues of every section, merged."""
        return self.timer.validation.merge(
            self.presets.validation, self.chime.validation, self.lists.validation, self.tasks.validation
        )


def _sections(schema: UserDataSchema, limits: UserDataLimits) -> _Sections:
    """Map every optional section.

    Args:
        schema: Validated DTO.
        limits: Bounds from ``concentrator.ini``.

    Returns:
        The mapped sections.
    """
    lists, tasks = _todo(schema, limits)
    return _Sections(
        timer=_optional(schema.timer, lambda section: TimerConfigMapper.to_domain(section, TIMER_FIELD, limits.timer)),
        presets=_optional(
            schema.timer_presets, lambda section: TimerPresetsMapper.to_domain(section, PRESETS_FIELD, limits.timer)
        ),
        chime=_optional(schema.hourly_chime, lambda section: HourlyChimeMapper.to_domain(section, CHIME_FIELD)),
        lists=lists,
        tasks=tasks,
    )


class UserDataMapper:
    """Converts the whole file."""

    @staticmethod
    def to_domain(schema: UserDataSchema, limits: UserDataLimits) -> DataResult[StoredUserData]:
        """Build and validate every section.

        Args:
            schema: Validated DTO.
            limits: Bounds from ``concentrator.ini`` applied by the domain rules, and the defaults of
                the settings an older file does not have.

        Returns:
            The data and its ``saved_at``, or every rule failure (dotted file paths). A section the
            file does not have yet is ``None``.
        """
        settings = UserSettingsMapper.to_domain(schema.settings, SETTINGS_FIELD, limits.settings)
        sections = _sections(schema, limits)
        validation = settings.validation.merge(
            sections.validation, TimeRules.validate_utc(schema.saved_at, SAVED_AT_FIELD)
        )
        if settings.data is None or validation.is_failure:
            return DataResult.fail(validation)
        data = UserData(
            schema_version=schema.schema_version,
            settings=settings.data,
            timer=sections.timer.data,
            timer_presets=sections.presets.data,
            hourly_chime=sections.chime.data,
            task_lists=sections.lists.data,
            tasks=sections.tasks.data,
        )
        return DataResult.ok(StoredUserData(data=data, saved_at=schema.saved_at), validation)

    @staticmethod
    def to_schema(data: UserData, saved_at: datetime, app_version: str) -> UserDataSchema:
        """Build the DTO written to the file.

        Args:
            data: Validated data.
            saved_at: Instant of this save (timezone-aware UTC).
            app_version: Version of the running application.

        Returns:
            The DTO; a section that is ``None`` is not written.
        """
        presets = data.timer_presets
        return UserDataSchema(
            schema_version=data.schema_version,
            saved_at=saved_at,
            app_version=app_version,
            settings=UserSettingsMapper.to_schema(data.settings),
            timer=None if data.timer is None else TimerConfigMapper.to_schema(data.timer),
            timer_presets=None if presets is None else TimerPresetsMapper.to_schema(presets),
            hourly_chime=None if data.hourly_chime is None else HourlyChimeMapper.to_schema(data.hourly_chime),
            task_lists=None if data.task_lists is None else TaskListsMapper.to_schema(data.task_lists),
            tasks=None if data.tasks is None else TasksMapper.to_schema(data.tasks),
        )
